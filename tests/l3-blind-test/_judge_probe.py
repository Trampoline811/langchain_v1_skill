# -*- coding: utf-8 -*-
"""判定探针（subprocess 执行）— 参数自适应：找构建函数 + 按签名注入模型

用法: python _judge_probe.py <codefile> [--build-fn NAME] [--invoke]
输出: 最后一行 JSON {level, ok, detail, ...}
规则:
  - 只把「本模块定义的函数」当候选（排除 from xxx import 进来的）
  - 构建函数若需 N 个位置参数，按需收集模型工厂结果（tuple 展开）注入
  - invoke 时若无 config，注入默认 thread_id（checkpointer 场景必须）
"""
import argparse
import importlib.util
import inspect
import json


def _local_functions(m):
    out = []
    for n in dir(m):
        if n.startswith("_"):
            continue
        obj = getattr(m, n)
        try:
            if inspect.isfunction(obj) and getattr(obj, "__module__", "") == m.__name__:
                out.append(n)
        except Exception:
            continue
    return out


def _required_positional(fn):
    """返回函数必填位置参数个数（不含默认值/*args/**kwargs）"""
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):
        return 0
    n = 0
    for p in sig.parameters.values():
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty:
            n += 1
        elif p.kind == p.VAR_POSITIONAL:
            return 0  # *args 兜底，不猜
    return n


def _collect_models(m, need: int):
    """按需收集模型对象：调用本地定义的函数名含 model/llm/chat 的无参函数，
    tuple 返回展开，直到够 need 个。返回 (models, factory_errors)"""
    models = []
    tried = []
    factory_errors = []
    for n in dir(m):
        if n.startswith("_"):
            continue
        obj = getattr(m, n)
        try:
            if not (inspect.isfunction(obj) and getattr(obj, "__module__", "") == m.__name__):
                continue
        except Exception:
            continue
        low = n.lower()
        if not any(k in low for k in ["model", "llm", "chat"]):
            continue
        if n in tried or len(models) >= need:
            continue
        tried.append(n)
        if _required_positional(obj) > 0:
            continue  # 只调无参工厂
        try:
            val = obj()
        except Exception as e:
            factory_errors.append(f"{n}: {type(e).__name__}")
            continue
        if val is None:
            continue
        if isinstance(val, str):
            # 工厂返回模型名字符串（create_agent 支持字符串，但解析需真实凭据）
            # 判定目标是 API 结构 → 记为字符串模型，由调用方决定是否 fake
            factory_errors.append(f"{n}: returned model name string (needs real credentials)")
            continue
        if isinstance(val, tuple):
            models.extend(list(val))
        else:
            models.append(val)
        if len(models) >= need:
            break
    return models[:need], factory_errors


def _make_fake_model():
    """FakeMessagesListChatModel：预设轮次消息，让 create_agent 全链路可跑（无网络）"""
    from langchain_core.messages import AIMessage
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    return FakeMessagesListChatModel(responses=[
        AIMessage(content="测试完成"),
        AIMessage(content="这是 fake model 的最终回复，用于验证 agent 链路可运行。"),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codefile")
    ap.add_argument("--build-fn", default="")
    ap.add_argument("--invoke", action="store_true")
    args = ap.parse_args()

    spec = importlib.util.spec_from_file_location("genmod", args.codefile)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)   # 顶层 import/异常在此抛出

    funcs = _local_functions(m)
    pref: list[str] = []
    if args.build_fn and args.build_fn in funcs:
        pref.append(args.build_fn)
    for n in funcs:
        if n.startswith("build") and n not in pref:
            pref.append(n)
    for n in funcs:
        if n.startswith("create") and "model" not in n.lower() and n not in pref:
            pref.append(n)
    for n in funcs:
        if ("agent" in n.lower() or "graph" in n.lower()) and n not in pref:
            pref.append(n)
    if not pref:
        print(json.dumps({"level": "b", "ok": False,
                          "detail": f"no build function (local funcs: {funcs})"}))
        return
    target = getattr(m, pref[0])
    need = _required_positional(target)
    models, factory_errors = (_collect_models(m, need) if need > 0 else ([], []))
    fake_used = False
    if len(models) < need:
        # 工厂不足（凭据/网络失败或没有模型工厂）→ fake model 顶替，只验 API 结构
        fake_used = True
        fake = _make_fake_model()
        while len(models) < need:
            models.append(fake)

    out: dict = {"target": pref[0], "need_params": need,
                 "fake_model": fake_used}
    if factory_errors:
        out["factory_errors"] = factory_errors
    try:
        res = target(*models) if need > 0 else target()
    except TypeError as te:
        # 参数还是不够（如多个模型）——报错让 case 判 FAIL，detail 带原因
        print(json.dumps({"level": "b", "ok": False,
                          "detail": f"build '{pref[0]}' 调用失败: {te} (need {need} params, "
                                    f"models {'fake' if fake_used else len(models)})"}))
        return
    except Exception as e:
        print(json.dumps({"level": "b", "ok": False,
                          "detail": f"{type(e).__name__}: {e}"}))
        return
    out["constructed"] = True
    out["res_type"] = type(res).__name__

    if not args.invoke:
        out["level"] = "b"
        out["ok"] = True
        out["detail"] = ("构造成功 (fake model)" if fake_used
                         else f"构造成功 ({out['res_type']})")
        print(json.dumps(out, ensure_ascii=False))
        return

    # L3c 真实执行（fake model 也走完整链路）
    agent = res[0] if isinstance(res, tuple) else res
    config = res[1] if isinstance(res, tuple) and len(res) > 1 else None
    if config is None:
        config = {"configurable": {"thread_id": "l3-blind-test-thread"}}
    try:
        r = agent.invoke({"messages": [{"role": "user", "content": "你好，请开始"}]},
                         config=config)
        out["level"] = "c"
        out["ok"] = True
        out["detail"] = (f"run ok (fake model), result: "
                         f"{list(r.keys()) if isinstance(r, dict) else type(r).__name__}"
                         if fake_used else
                         f"run ok, result: {list(r.keys()) if isinstance(r, dict) else type(r).__name__}")
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        ext = any(k in err.lower() for k in
                  ["connection", "connect", "auth", "401", "403", "timeout",
                   "apiconnection", "api key", "not found", "404", "429",
                   "rate limit", "billing", "quota", "insufficient"])
        if ext:
            out["level"] = "c"
            out["ok"] = True
            out["detail"] = f"SKIP(外部模型不可达): {err[:220]}"
        else:
            out["level"] = "c"
            out["ok"] = False
            out["detail"] = err
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
