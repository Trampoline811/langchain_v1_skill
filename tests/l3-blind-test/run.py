# -*- coding: utf-8 -*-
"""L3 盲测执行器 — 生成→执行→判定 闭环

用法:
  python tests/l3-blind-test/run.py --group on            # skill ON（读 langchain-v1 SKILL.md）
  python tests/l3-blind-test/run.py --group off           # skill OFF（裸写对照）
  python tests/l3-blind-test/run.py --group on --max-level c   # 到 L3c 真执行（需 key）
  python tests/l3-blind-test/run.py --group on --case 1    # 只跑用例 1
  python tests/l3-blind-test/run.py --group on --no-llm    # 不生成，只对已有文件跑判定

三级判定:
  L3a py_compile 语法
  L3b import + 调工厂函数（build_agent 等）构造成功
  L3c agent 真跑一轮（需 DEEPSEEK_API_KEY；生成代码须用 init_chat_model 且可连网）
"""
import argparse
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]      # 项目根
L3DIR = pathlib.Path(__file__).resolve().parent
CASES = L3DIR / "cases.py"
SKILL_MAP = {
    "langchain-v1": ROOT / "skills" / "langchain-v1-suite" / "langchain-v1" / "SKILL.md",
    "deepagents-v1": ROOT / "skills" / "langchain-v1-suite" / "deepagents-v1" / "SKILL.md",
    "langgraph-v1": ROOT / "skills" / "langchain-v1-suite" / "langgraph-v1" / "SKILL.md",
}
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
GEN_DIR = L3DIR / "generated"
REPORT_DIR = L3DIR / "reports"

BLACKLIST = ["AgentExecutor", "initialize_agent", "create_react_agent",
             "ConversationBufferMemory", "ChatOpenAI", "LLMChain",
             "MultiAgentChain", "Tool.from_function", "ConversationSummaryMemory"]


def load_cases():
    spec = importlib.util.spec_from_file_location("_l3cases", CASES)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CASES


def build_system(group: str, skill: str = "langchain-v1") -> str:
    if group == "off":
        return "You are an expert Python developer. Write clean, runnable Python code."
    skill_file = SKILL_MAP.get(skill, SKILL_MAP["langchain-v1"])
    text = skill_file.read_text(encoding="utf-8")
    # 截断保护：skill 全文可能很长，取前 ~30k 字符避免超上下文（保留 API 速查主体）
    if len(text) > 30000:
        text = text[:30000] + "\n...(截断)"
    return (
        f"You are an expert Python developer. You MUST follow the {skill} coding "
        "rules below exactly — never use the blacklisted v0.x APIs.\n\n"
        "===== CODING RULES (authoritative) =====\n" + text
    )


def gen_code(client, system: str, case: dict, model: str) -> str:
    """调 LLM 生成用例代码，返回纯 Python 源码"""
    user = case["prompt"] + (
        "\n\n只输出一个完整 Python 文件（含 import 与 __main__ 入口），不要解释。"
        "\n硬性要求：1) 禁止在函数/类之外初始化或连接任何模型（import 语句本身除外，"
        "模型只能在函数内创建）；2) import 只能引用真实存在、可用的模块；"
        "3) 输出必须完整、语法正确，禁止中途截断。"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=8000,
    )
    text = resp.choices[0].message.content or ""
    # 提取 ```python ... ``` 块
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.S)
    return blocks[0].strip() if blocks else text.strip()


def run_level(code: str, build_fn: str | None, case_name: str,
              max_level: str = "c") -> dict:
    """三级判定: 返回 {level, ok, detail}（委托 _judge_probe.py 子进程执行）"""
    work = L3DIR / ".tmp_judge"
    work.mkdir(exist_ok=True)
    f = work / f"{case_name}.py"
    f.write_text(code, encoding="utf-8")
    try:
        # L3a 语法
        r = subprocess.run([str(VENV_PY), "-m", "py_compile", str(f)],
                           capture_output=True, encoding="utf-8", errors="replace",
                           timeout=60)
        if r.returncode != 0:
            return {"level": "a", "ok": False,
                    "detail": r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "syntax error"}
        # L3b(+L3c) import + 构造 + 可选 invoke —— 探针文件
        probe_py = L3DIR / "_judge_probe.py"
        cmd = [str(VENV_PY), "-X", "utf8", str(probe_py), str(f)]
        if build_fn:
            cmd += ["--build-fn", build_fn]
        has_key = bool(os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY"))
        if max_level == "c" and has_key:
            cmd += ["--invoke"]
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace",
                           timeout=180, cwd=str(ROOT))
        if r.returncode != 0:
            # 顶层 import 失败（含缺依赖 ModuleNotFoundError）→ 归为 b 级 FAIL
            tail = (r.stderr or r.stdout).strip()
            return {"level": "b", "ok": False, "detail": tail.splitlines()[-1] if tail else "import failed"}
        try:
            out = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return {"level": "b", "ok": False, "detail": r.stdout[-500:]}
        if not has_key and max_level == "c":
            out["ok"] = True
            out["detail"] = f"{out.get('detail', '构造成功')}（无 key，L3c 跳过）"
        return {"level": out.get("level", "b"), "ok": out.get("ok", False),
                "detail": out.get("detail", "")}
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def static_score(code: str, case: dict) -> tuple[int, list[str]]:
    """静态评分 0-4：每出现一个黑名单扣 1 分，最低 0"""
    hits = [b for b in BLACKLIST if b in code]
    # 白名单命中数（辅助判断）
    score = max(0, 4 - len(set(hits)))
    return score, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", choices=["on", "off"], default="on")
    ap.add_argument("--case", type=int, default=None)
    ap.add_argument("--max-level", choices=["a", "b", "c"], default="c")
    ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--no-llm", action="store_true", help="不调 LLM 生成，判定已有文件")
    args = ap.parse_args()

    cases = load_cases()
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]

    GEN_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    group_dir = GEN_DIR / args.group
    group_dir.mkdir(exist_ok=True)

    # LLM client
    client = None
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not args.no_llm:
        if not key:
            print("!! 需设置 DEEPSEEK_API_KEY 才能生成代码；用 --no-llm 可只判定已有文件")
            sys.exit(1)
        from openai import OpenAI
        client = OpenAI(base_url="https://api.deepseek.com/v1", api_key=key)

    sys_cache: dict[str, str] = {}

    rows = []
    for case in cases:
        cid = case["id"]
        skill = case.get("skill", "langchain-v1")
        if skill not in sys_cache:
            sys_cache[skill] = build_system(args.group, skill)
        system = sys_cache[skill]
        fname = f"case{cid}_{case['name']}.py"
        fpath = group_dir / fname
        print(f"\n===== 用例 {cid}: {case['name']} ({args.group} 组, skill={skill}) =====")

        if args.no_llm:
            if not fpath.exists():
                print(f"  !! 文件不存在: {fpath}")
                rows.append({"case": cid, "name": case["name"], "code": "", "score": None,
                             "hits": [], "judge": "FILE-MISSING", "detail": "未生成"})
                continue
            code = fpath.read_text(encoding="utf-8")
        else:
            code = gen_code(client, system, case, args.model)
            fpath.write_text(code, encoding="utf-8")
            print(f"  生成 -> {fpath.relative_to(ROOT)} ({len(code)} chars)")
            time.sleep(1)  # 避免限流

        score, hits = static_score(code, case)
        # 判定（max-level 控制最深跑哪级；FAIL@a 且可再生成 → 自动重试最多 2 次，
        # 自愈 LLM 长文件截断/笔误类语法噪声）
        attempts = 0
        while True:
            if args.max_level == "a":
                judge, detail = "L3a-PASS", "语法通过"
                break
            res = run_level(code, case.get("build_fn"), case["name"],
                            max_level=args.max_level)
            judge = "PASS" if res["ok"] else f"FAIL@{res['level']}"
            detail = res["detail"]
            if (not args.no_llm and res["ok"] is False
                    and res.get("level") == "a" and attempts < 2):
                attempts += 1
                print(f"  L3a 语法失败 -> 重新生成 (第 {attempts}/2 次)…")
                code = gen_code(client, system, case, args.model)
                fpath.write_text(code, encoding="utf-8")
                time.sleep(1)
                continue
            break

        print(f"  静态分: {score}/4  | 黑名单命中: {hits if hits else '无'}")
        print(f"  判定: {judge}  {detail[:200]}")
        rows.append({"case": cid, "name": case["name"], "skill": skill, "code": code,
                     "score": score, "hits": hits, "judge": judge, "detail": detail})

    # 报告
    ts = time.strftime("%Y%m%d_%H%M")
    rep = REPORT_DIR / f"report_{args.group}_{ts}.md"
    lines = [f"# L3 盲测报告 — {args.group} 组（{ts}）", ""]
    scored = [r for r in rows if r["score"] is not None]
    total = sum(r["score"] for r in scored)
    lines += [f"总分: {total}/{4*len(scored)}（每例 4 分 × {len(scored)} 例）", ""]
    lines += ["| 用例 | 技能 | 静态分 | 黑名单 | 判定 | 说明 |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['case']} {r['name']} | {r['skill']} "
                     f"| {r['score'] if r['score'] is not None else '-'}/4 "
                     f"| {', '.join(r['hits']) if r['hits'] else '无'} | {r['judge']} | {str(r['detail'])[:80]} |")
    lines += ["", "## 生成代码", ""]
    for r in rows:
        lines += [f"### case{r['case']} {r['name']}", f"`generated/{args.group}/case{r['case']}_{r['name']}.py`", ""]
    rep.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n报告: {rep.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
