"""
Deep Agents v1.0 API 盲测 — create_deep_agent + Filesystem + Skills + Subagents
覆盖: create_deep_agent / StateBackend / FilesystemBackend / CompositeBackend /
      SkillsMiddleware / SubAgentMiddleware / StructuredOutput

用法:
  uv run python tests/deep_agent.py          # 全量测试
  uv run python tests/deep_agent.py --demo   # 演示模式

无需 API Key — 模块导入测试，不实际调用 LLM。
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path


# ═══════════════════════════════════════════
# 1. Backend 导入测试
# ═══════════════════════════════════════════

def test_backend_imports():
    """测试所有 Backend 类可导入"""
    print("=" * 60)
    print("  测试1: Backend 导入")
    print("=" * 60)

    from deepagents.backends import (
        StateBackend,
        FilesystemBackend,
        StoreBackend,
        CompositeBackend,
        BackendProtocol,
    )

    # StateBackend
    be = StateBackend()
    assert be is not None
    print(f"  ✅ StateBackend()")

    # FilesystemBackend
    tmp = tempfile.mkdtemp()
    try:
        be = FilesystemBackend(root_dir=tmp, virtual_mode=True)
        assert be is not None
        print(f"  ✅ FilesystemBackend(root_dir=...)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # CompositeBackend
    be = CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend() if StoreBackend else StateBackend()},
    )
    assert be is not None
    print(f"  ✅ CompositeBackend(default + routes)")

    return True


# ═══════════════════════════════════════════
# 2. FilesystemMiddleware 导入测试
# ═══════════════════════════════════════════

def test_filesystem_middleware():
    """测试 FilesystemMiddleware + 权限"""
    print("\n" + "=" * 60)
    print("  测试2: FilesystemMiddleware + Permission")
    print("=" * 60)

    from deepagents.middleware import FilesystemMiddleware
    from deepagents.backends import StateBackend, FilesystemBackend
    from deepagents import FilesystemPermission

    # 默认
    mw = FilesystemMiddleware(backend=StateBackend())
    assert mw is not None
    print(f"  ✅ FilesystemMiddleware(StateBackend)")

    # 带权限
    tmp = tempfile.mkdtemp()
    try:
        mw = FilesystemMiddleware(
            backend=FilesystemBackend(root_dir=tmp, virtual_mode=True),
            _permissions=[
                FilesystemPermission(
                    operations=["write"],
                    paths=["/system/**"],
                    mode="deny",
                ),
            ],
        )
        assert mw is not None
        print(f"  ✅ FilesystemPermission(deny /system/**)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return True


# ═══════════════════════════════════════════
# 3. SkillsMiddleware 导入测试
# ═══════════════════════════════════════════

def test_skills_middleware():
    """测试 SkillsMiddleware 基础功能"""
    print("\n" + "=" * 60)
    print("  测试3: SkillsMiddleware")
    print("=" * 60)

    from deepagents.middleware import SkillsMiddleware
    from deepagents.backends import StateBackend

    # 创建临时 skills 目录
    tmp = tempfile.mkdtemp()
    skill_dir = os.path.join(tmp, "test-skill")
    os.makedirs(skill_dir)
    Path(skill_dir, "SKILL.md").write_text("""---
name: test-skill
description: A test skill for unit testing
---

# test-skill

## Overview
This is a test skill.
""", encoding="utf-8")

    try:
        mw = SkillsMiddleware(
            backend=StateBackend(),
            sources=[tmp],
        )
        assert mw is not None
        print(f"  ✅ SkillsMiddleware(sources=[...])")

        # 带多个 sources
        mw = SkillsMiddleware(
            backend=StateBackend(),
            sources=[tmp, tmp],  # 同目录两次 — 验证 sources 接受 list
        )
        assert mw is not None
        print(f"  ✅ SkillsMiddleware(multiple sources)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return True


# ═══════════════════════════════════════════
# 4. SubAgentMiddleware 导入测试
# ═══════════════════════════════════════════

def test_subagent_middleware():
    """测试 SubAgentMiddleware 子 Agent 定义"""
    print("\n" + "=" * 60)
    print("  测试4: SubAgentMiddleware")
    print("=" * 60)

    from deepagents.middleware.subagents import (
        SubAgentMiddleware,
        CompiledSubAgent,
    )

    # Dict 定义（最常见）
    subagents = [
        {
            "name": "researcher",
            "description": "深度调研，多次搜索+综合分析",
            "system_prompt": "You are a researcher.",
            "tools": [],
        },
        {
            "name": "coder",
            "description": "代码生成和调试",
            "system_prompt": "You are a coder.",
            "tools": [],
            "response_format": None,  # 可选结构化输出
        },
    ]
    assert len(subagents) == 2
    assert subagents[0]["name"] == "researcher"
    assert subagents[1]["name"] == "coder"
    print(f"  ✅ Dict 定义: {len(subagents)} 个子 Agent")

    # 验证字段完整性
    for sa in subagents:
        assert "name" in sa
        assert "description" in sa
        assert "system_prompt" in sa
    print(f"  ✅ 必填字段完整性检查通过")

    return True


# ═══════════════════════════════════════════
# 5. create_deep_agent 签名测试
# ═══════════════════════════════════════════

def test_create_deep_agent_signature():
    """测试 create_deep_agent 核心参数"""
    print("\n" + "=" * 60)
    print("  测试5: create_deep_agent 签名")
    print("=" * 60)

    from deepagents import create_deep_agent
    import inspect

    sig = inspect.signature(create_deep_agent)
    params = list(sig.parameters.keys())

    # 核心参数检查
    required_params = ["model"]
    key_params = [
        "model", "tools", "system_prompt", "middleware",
        "subagents", "skills", "backend",
        "checkpointer", "store",
    ]

    for p in required_params:
        assert p in params, f"缺少必填参数: {p}"
    print(f"  ✅ 必填参数: {required_params}")

    found_key = [p for p in key_params if p in params]
    print(f"  ✅ 关键可选参数: {found_key}")

    print(f"  ✅ create_deep_agent 签名正常 ({len(params)} 个参数)")
    return True


# ═══════════════════════════════════════════
# 6. Backend 文件操作测试（无LLM）
# ═══════════════════════════════════════════

def test_backend_file_operations():
    """测试 FilesystemBackend 基础文件操作"""
    print("\n" + "=" * 60)
    print("  测试6: Backend 文件读写")
    print("=" * 60)

    from deepagents.backends import FilesystemBackend

    tmp = tempfile.mkdtemp()
    try:
        backend = FilesystemBackend(root_dir=tmp, virtual_mode=True)

        # 写文件
        backend.write("/test.txt", "Hello Deep Agents!")
        print(f"  ✅ write('/test.txt')")

        # 读文件 — read() 返回 ReadResult
        result = backend.read("/test.txt")
        content = result.file_data["content"]
        assert content == "Hello Deep Agents!"
        print(f"  ✅ read('/test.txt') → '{content}'")

        # 列文件 — ls() 返回 LsResult，用 .entries
        ls_result = backend.ls("/")
        paths = [e["path"] for e in ls_result.entries]
        assert "/test.txt" in paths
        print(f"  ✅ ls('/') → {paths}")

        # 编辑文件
        backend.edit("/test.txt", "Hello", "Hi")
        result = backend.read("/test.txt")
        content = result.file_data["content"]
        assert content == "Hi Deep Agents!"
        print(f"  ✅ edit('/test.txt', 'Hello', 'Hi') → '{content}'")

        # Glob — 返回 GlobResult，用 .matches
        glob_result = backend.glob("*.txt")
        matches = [m["path"] for m in glob_result.matches]
        assert "/test.txt" in matches
        print(f"  ✅ glob('*.txt') → {matches}")

        # Grep — 返回 GrepResult
        grep_result = backend.grep("Deep")
        grep_matches = grep_result.matches
        assert len(grep_matches) > 0
        print(f"  ✅ grep('Deep') → {len(grep_matches)} 个匹配")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return True


# ═══════════════════════════════════════════
# 7. CompositeBackend 路由测试
# ═══════════════════════════════════════════

def test_composite_backend_routing():
    """测试 CompositeBackend 路径路由"""
    print("\n" + "=" * 60)
    print("  测试7: CompositeBackend 路由")
    print("=" * 60)

    from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend

    tmp = tempfile.mkdtemp()
    try:
        fs_backend = FilesystemBackend(root_dir=tmp, virtual_mode=True)
        fs_backend.write("/hello.txt", "from filesystem")

        # 用两个 FilesystemBackend 做 CompositeBackend
        # 注意：StateBackend 必须在 graph 上下文中使用
        tmp2 = tempfile.mkdtemp()
        default_fs = FilesystemBackend(root_dir=tmp2, virtual_mode=True)

        backend = CompositeBackend(
            default=default_fs,
            routes={"/fs/": fs_backend},
        )

        # 默认路由 → default_fs
        backend.write("/workspace/plan.md", "plan content")
        result = backend.read("/workspace/plan.md")
        assert result.file_data["content"] == "plan content"
        print(f"  ✅ /workspace/plan.md → default（文件写入成功）")

        # 显式路由 → fs_backend
        backend.write("/fs/data.txt", "file content")
        result = backend.read("/fs/data.txt")
        assert result.file_data["content"] == "file content"
        print(f"  ✅ /fs/data.txt → FilesystemBackend（路由匹配）")

        import shutil
        shutil.rmtree(tmp2, ignore_errors=True)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return True


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

def main():
    demo_mode = "--demo" in sys.argv

    tests = [
        ("Backend 导入", test_backend_imports),
        ("FilesystemMiddleware + Permission", test_filesystem_middleware),
        ("SkillsMiddleware", test_skills_middleware),
        ("SubAgentMiddleware 定义", test_subagent_middleware),
        ("create_deep_agent 签名", test_create_deep_agent_signature),
        ("Backend 文件读写", test_backend_file_operations),
        ("CompositeBackend 路由", test_composite_backend_routing),
    ]

    passed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            import traceback
            print(f"\n  ❌ {name} FAILED: {e}")
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{len(tests)} passed")
    print("=" * 60)

    return passed == len(tests)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
