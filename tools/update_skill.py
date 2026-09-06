"""
LangChain Skill 一键更新工具

用法:
  python update_skill.py                # 全量：刷新清单 → 拉取文档 → 清洗 → 提示更新
  python update_skill.py --check        # 轻量检测：对比官方 llms.txt 看有没有新页面
  python update_skill.py --refresh      # 只刷新 urls.md（自动合并官方分区页面清单）
  python update_skill.py --docs-only    # 只拉取+清洗文档（默认先自动 --refresh）
  python update_skill.py --docs-only --no-refresh  # 拉取但跳过清单刷新
  python update_skill.py --test-only    # 只跑盲测（需 .venv + API Key）
  python update_skill.py --package      # 打包上次结果到日期文件夹

工作流:
  1. refresh_urls() → 官方分区 llms.txt 自动合并进 tools/urls.md
  2. sync_docs()    → docs.langchain.com .md 直出拉取 → 清洗 → 保存到 docs/official/
  3. diff_docs()    → 对比新旧文档，输出变更摘要
  4. [手动] 根据 diff 更新 SKILL.md
  5. run_tests()    → 跑 tests/ 盲测验证
  6. package()      → 打包到 dated 文件夹
"""

import os
import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# ── 路径配置 ────────────────────────────────────────────
ROOT = Path(__file__).parent.parent    # 项目根目录
DOCS_DIR = ROOT / "docs" / "official"   # 官方文档下载目标
RAW_DIR = DOCS_DIR / ".raw"           # 原始 .mdx 缓存
SKILL_DIR = ROOT / "skills"           # skills 目录
URLS_FILE = ROOT / "tools" / "urls.md"  # URL 源清单
CACHE_FILE = ROOT / ".docs_cache.json"  # SHA256 缓存

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/langchain-ai/docs/main/src/oss"


# ═══════════════════════════════════════════════════════
# 1. 文档同步
# ═══════════════════════════════════════════════════════

def load_urls():
    """从 urls.md 加载所有 URL"""
    text = URLS_FILE.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines()
            if line.strip().startswith("https://")]


LLMS_SECTIONS = ["langchain", "langgraph", "deepagents", "concepts", "contributing"]


def refresh_urls():
    """自动把官方分区 llms.txt 的现行页面合并进 tools/urls.md（去重、保序）

    官方每季度会重排页面树；手工维护 urls.md 必然滞后。每次 --docs-only 前自动执行，
    也可单独 `python tools/update_skill.py --refresh`。网络不可用时静默沿用现有清单。
    """
    import re
    fetched: list[str] = []
    for sec in LLMS_SECTIONS:
        llms = f"https://docs.langchain.com/oss/python/{sec}/llms.txt"
        try:
            req = Request(llms, headers={"User-Agent": "LangChainSkillUpdater/1.0"})
            with urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8")
            urls = sorted(set(re.findall(r'https://docs\.langchain\.com/oss/python/[^\s)]+', text)))
            urls = [u.split('#')[0].rstrip('/') for u in urls]
            fetched.extend(urls)
            print(f"  refresh: {sec} = {len(urls)} 页")
        except Exception as e:
            print(f"  refresh {sec}: 失败（{e}），沿用现有清单")

    if not fetched:
        return None

    existing = load_urls() if URLS_FILE.exists() else []
    merged = list(dict.fromkeys(existing + fetched))
    added = [u for u in fetched if u not in set(existing)]
    removed = [u for u in existing if u not in set(fetched)]

    if merged == existing:
        print(f"  refresh: urls.md 已是最新（{len(merged)} 页）")
        return {"total": len(merged), "added": 0, "removed": 0}

    header = (
        "# LangChain 官方文档源 URL 清单（由 update_skill.py --refresh 自动合并官方 llms.txt 生成）\n"
        "# 上次刷新: {date}\n".format(date=datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    URLS_FILE.write_text(header + "\n".join(merged) + "\n", encoding="utf-8")
    print(f"  refresh: urls.md 更新 -> {len(merged)} 页（+{len(added)} 新增 / -{len(removed)} 移除）")
    return {"total": len(merged), "added": len(added), "removed": len(removed)}


def url_to_raw(url: str) -> str:
    """docs.langchain.com 页面 → 官方 .md 直出地址

    官方源码树已从 src/oss/python/* 重构到 src/oss/{langchain,deepagents,langgraph}/*，
    GitHub raw oss/python 映射已失效。docs.langchain.com 对任意页面支持 `<url>.md`
    直接返回 Markdown（含前置 Documentation Index 提示块，由 clean_mdx 剥离）。
    """
    return url + ".md"


def url_to_name(url: str) -> str:
    """URL → 文件名"""
    path = url.replace("https://docs.langchain.com/oss/python/", "")
    return path.replace("/", "-")


def url_to_category(url: str) -> str | None:
    """URL → 子目录名（langchain/langgraph/deepagents/concepts/contributing/reference）

    URL 路径第一段为类别，单段路径（如 learn、versioning）返回 None → 放根目录
    """
    path = url.replace("https://docs.langchain.com/oss/python/", "")
    parts = path.split("/")
    return parts[0] if len(parts) > 1 else None


def add_frontmatter(text: str, url: str) -> str:
    """给清洗后的 Markdown 添加 YAML frontmatter（含 fetchedAt 日期）"""
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 如果已有 frontmatter，只在末尾加 fetchedAt（如果尚无）
    if text.startswith("---"):
        if "fetchedAt:" in text[:200]:
            return text  # 已有日期，不动
        # 在第一个 --- 闭合前插入
        end = text.find("\n---", 3)
        if end > 0:
            return text[:end] + f"\nfetchedAt: {date_str}" + text[end:]

    # 无 frontmatter — 创建
    name = url_to_name(url)
    return f"---\ntitle: {name}\nfetchedAt: {date_str}\n---\n\n{text}"


def fetch_mdx(raw_url: str) -> tuple[str | None, int]:
    """拉取单个文档页（docs.langchain.com .md 直出），返回 (内容, 状态码)"""
    try:
        req = Request(raw_url, headers={"User-Agent": "LangChainSkillUpdater/1.0"})
        with urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8"), resp.status
    except HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, -1


def clean_mdx(text: str) -> str:
    """清洗文档页 → 纯净 Markdown（适配 docs.langchain.com 的 .md 直出格式）"""
    import re
    md = text
    # 剥离 .md 直出页顶部的 Documentation Index 提示块
    md = re.sub(r'^>\s*## Documentation Index.*?(?=^# |\Z)', '', md, flags=re.MULTILINE | re.DOTALL)
    # 代码块 info 串：```python Google theme={...} / ```python OpenAI → ```python
    md = re.sub(r'^```(\S+)\s+\S+.*$', r'```\1', md, flags=re.MULTILINE)
    # 残留 theme 属性（mermaid 等）
    md = re.sub(r'\s*theme=\{[^}]*\}', '', md)
    md = re.sub(r'\s*theme="[^"]*"', '', md)
    # .md 直出为多 Provider 重复代码块（Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama）
    # 清洗时不做去重（保留官方原文，体积换取完整性）；导入行 / 平台容器标签统一清理：
    md = re.sub(r'^import\s+.*$', '', md, flags=re.MULTILINE)
    md = re.sub(r'<CodeGroup>|</CodeGroup>', '', md)
    md = re.sub(r'<Tabs>|</Tabs>|<Tab\s+title="[^"]*">|</Tab>', '', md)
    md = re.sub(r'<Steps>|</Steps>|<Step\s+title="[^"]*">|</Step>', '', md)
    md = re.sub(r'^:::python\s*$', '', md, flags=re.MULTILINE)
    md = re.sub(r'^:::js\s*$', '', md, flags=re.MULTILINE)
    md = re.sub(r'^:::$', '', md, flags=re.MULTILINE)
    md = re.sub(r'<Columns[^>]*>', '', md)
    md = re.sub(r'</Columns>', '', md)
    md = re.sub(
        r'<Card\s+title="([^"]*)"[^>]*>([\s\S]*?)</Card>',
        lambda m: f"### {m.group(1)}\n{m.group(2).strip()}", md)
    md = re.sub(r'<CardGroup[^>]*>', '', md)
    md = re.sub(r'</CardGroup>', '', md)
    md = re.sub(
        r'<Tip>\s*([\s\S]*?)\s*</Tip>',
        lambda m: '\n> **Tip:** ' + m.group(1).strip().replace('\n', '\n> ') + '\n', md)
    md = re.sub(
        r'<Note>\s*([\s\S]*?)\s*</Note>',
        lambda m: '\n> **Note:** ' + m.group(1).strip().replace('\n', '\n> ') + '\n', md)
    md = re.sub(r'<Icon[^>]*/>', '', md)
    md = re.sub(r'<img\s+src="([^"]*)"\s+alt="([^"]*)"[^>]*/>', r'![\2](\1)', md)
    md = re.sub(r'@\[`?([^`\]]+)`?\]\(([^)]+)\)', r'[\1](\2)', md)
    md = re.sub(r'\{/\*\s*[\s\S]*?\s*\*/\}', '', md)
    md = re.sub(r'\n{4,}', '\n\n\n', md)
    return md.strip()


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def sync_docs():
    """全量同步文档 — 输出到类别子目录（langchain/deepagents/langgraph/concepts/...）

    文件名: {category}/{category}-{page}.md
    根目录文件（无类别前缀）: {page}.md
    """
    print("=" * 60)
    print("  Step 1: 同步官方文档")
    print("=" * 60)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    urls = load_urls()
    cache = load_cache()
    new_cache = {}

    ok, fail, changed, skipped = 0, 0, 0, 0
    failed_urls = []

    for i, url in enumerate(urls):
        name = url_to_name(url)
        category = url_to_category(url)
        raw_url = url_to_raw(url)

        # 确定输出路径：有类别→子目录，无类别→根目录
        if category:
            cat_dir = DOCS_DIR / category
            cat_dir.mkdir(parents=True, exist_ok=True)
            out_path = cat_dir / f"{name}.md"
        else:
            out_path = DOCS_DIR / f"{name}.md"

        label = f"{category}/{name}" if category else name
        print(f"  [{i+1}/{len(urls)}] {label}...", end=" ", flush=True)

        content, status = fetch_mdx(raw_url)
        if content is None:
            fail += 1
            failed_urls.append((url, status))
            print(f"FAIL ({status})")
            continue

        clean = add_frontmatter(clean_mdx(content), url)
        h = hash_content(clean)
        new_cache[name] = h

        if name in cache and cache[name] == h:
            skipped += 1
            print("unchanged")
        else:
            out_path.write_text(clean, encoding="utf-8")
            if name in cache:
                changed += 1
                print(f"UPDATED ({len(clean)} chars)")
            else:
                ok += 1
                print(f"NEW ({len(clean)} chars)")

    save_cache(new_cache)

    print(f"\n  Results: {ok} new | {changed} updated | {skipped} unchanged | {fail} failed")
    if failed_urls:
        print(f"  Failed URLs:")
        for u, s in failed_urls:
            print(f"    {u} → HTTP {s}")
    return {"ok": ok, "changed": changed, "skipped": skipped, "fail": fail}


# ═══════════════════════════════════════════════════════
# 2. 变更摘要
# ═══════════════════════════════════════════════════════

def diff_docs():
    """对比新旧文档，输出变更摘要"""
    print("\n" + "=" * 60)
    print("  Step 2: 变更摘要")
    print("=" * 60)

    cache = load_cache()
    if not cache:
        print("  (无历史缓存，跳过 diff)")

    # 重点文件列表：这些文件如果变了，skill 需要更新
    CRITICAL_FILES = [
        "langchain-agents", "langchain-models", "langchain-tools",
        "langchain-middleware-built-in", "langchain-structured-output",
        "langchain-streaming", "langchain-short-term-memory",
    ]

    changed_critical = []
    for name in CRITICAL_FILES:
        # 在根目录和子目录中查找
        found = False
        search_dirs = [DOCS_DIR] + [d for d in DOCS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]
        for search_dir in search_dirs:
            path = search_dir / f"{name}.md"
            if path.exists():
                found = True
                content = path.read_text(encoding="utf-8")
                h = hash_content(content)
                if name in cache and cache[name] != h:
                    changed_critical.append(name)
                break
        if not found and name not in cache:
            changed_critical.append(name)

    if changed_critical:
        print(f"  !! 关键文件已变更，需更新 skill:")
        for name in changed_critical:
            print(f"     - {name}.md")
    else:
        print("  关键文件无变化，skill 无需更新")

    return changed_critical


# ═══════════════════════════════════════════════════════
# 2.5 轻量检测（只对比 URL 清单，不下载）
# ═══════════════════════════════════════════════════════

LLMS_TXT_URL = "https://docs.langchain.com/llms-full.txt"


def fetch_llms_txt() -> set[str] | None:
    """拉取官方 llms.txt，提取所有 oss/python/ URL"""
    try:
        req = Request(LLMS_TXT_URL, headers={"User-Agent": "LangChainSkillUpdater/1.0"})
        with urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ERROR 拉取 llms-full.txt 失败: {e}")
        return None

    import re
    # llms-full.txt 中 URL 格式: https://docs.langchain.com/oss/python/langchain/overview
    # 可能带 #fragment，需要去掉
    urls = set(re.findall(r'https://docs\.langchain\.com/oss/python/[^\s)]+', text))
    # 去掉 # 片段，去重
    urls = {u.split('#')[0].rstrip('/') for u in urls}
    return urls


def check_llms():
    """对比 llms.txt 和 urls.md，输出新增/删除的页面"""
    print("=" * 60)
    print("  Check: 检测官方文档变更 (只对比 URL，不下载)")
    print("=" * 60)

    print(f"\n  拉取 {LLMS_TXT_URL} ...", end=" ", flush=True)
    live_urls = fetch_llms_txt()
    if live_urls is None:
        return None

    print(f"{len(live_urls)} 个页面")

    current_urls = set()
    if URLS_FILE.exists():
        current_urls = set(load_urls())

    new_urls = live_urls - current_urls
    removed_urls = current_urls - live_urls
    common = live_urls & current_urls

    print(f"\n  ┌─ 当前追踪: {len(current_urls)} 个")
    print(f"  ├─ 官方现存: {len(live_urls)} 个")
    print(f"  ├─ 未变化:   {len(common)} 个")
    print(f"  ├─ [NEW] 新增:  {len(new_urls)} 个")
    print(f"  └─ [DEL] 移除:  {len(removed_urls)} 个")

    if new_urls:
        print(f"\n  [NEW] 需要添加到 urls.md 的新页面:")
        for url in sorted(new_urls):
            name = url.replace("https://docs.langchain.com/oss/python/", "")
            print(f"     {name}")
            print(f"     {url}")

    if removed_urls:
        print(f"\n  [DEL] 官方已移除的页面 (可从 urls.md 删除):")
        for url in sorted(removed_urls):
            name = url.replace("https://docs.langchain.com/oss/python/", "")
            print(f"     {name}")

    if not new_urls and not removed_urls:
        print(f"\n  [OK] urls.md 与官方完全同步，无新增也无删除")

    return {"new": len(new_urls), "removed": len(removed_urls), "total": len(live_urls)}


# ═══════════════════════════════════════════════════════
# 3. 功能测试
# ═══════════════════════════════════════════════════════

def run_tests():
    """跑 resume_agent.py 验证"""
    print("\n" + "=" * 60)
    print("  Step 3: 功能测试")
    print("=" * 60)

    test_script = ROOT / "tests" / "resume_agent.py"
    if not test_script.exists():
        print("  resume_agent.py 不存在，跳过")
        return False

    import subprocess
    api_key = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    if not api_key:
        print("  WARNING: 无 API Key，请设置 DEEPSEEK_API_KEY")
        return False

    env = {**os.environ, "DEEPSEEK_API_KEY": api_key, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        ["uv", "run", "python", str(test_script), "--demo"],
        cwd=str(ROOT), env=env,
        capture_output=True, text=True, timeout=120,
    )

    success = "structured_output" in result.stdout or "structured_response" in result.stdout
    print(f"  {'PASS' if success else 'FAIL'}: exit={result.returncode}")
    if not success:
        print(f"  stderr: {result.stderr[:500]}")
    return success


# ═══════════════════════════════════════════════════════
# 4. 打包
# ═══════════════════════════════════════════════════════

def package(date_str: str = None):
    """打包本次更新结果到日期文件夹"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d_%H%M")

    pkg_dir = ROOT / f"update_{date_str}"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # 复制所有 skill 文件
    shutil.copytree(SKILL_DIR, pkg_dir / "skills", dirs_exist_ok=True)

    # 复制测试文件
    for f in ["resume_agent.py", "sample_resume.txt", "blind_test_analysis.md"]:
        src = ROOT / "tests" / f
        if src.exists():
            shutil.copy2(src, pkg_dir / f)

    # 复制文档列表 + 缓存
    if URLS_FILE.exists():
        shutil.copy2(URLS_FILE, pkg_dir / "urls.md")
    if CACHE_FILE.exists():
        shutil.copy2(CACHE_FILE, pkg_dir / ".docs_cache.json")

    # 生成 manifest
    manifest = {
        "date": date_str,
        "skill_version": "1.0",
        "docs_synced_at": datetime.now().isoformat(),
    }
    (pkg_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  Package created: {pkg_dir}")
    return pkg_dir


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

def main():
    args = set(sys.argv[1:])

    if "--check" in args:
        check_llms()
    elif "--refresh" in args:
        refresh_urls()
    elif "--docs-only" in args:
        if "--no-refresh" not in args:
            refresh_urls()   # 先自动合并最新官方清单（网络失败则沿用现有）
        sync_docs()
        diff_docs()
    elif "--test-only" in args:
        run_tests()
    elif "--package" in args:
        package()
    else:
        # 全量
        result = sync_docs()
        changed = diff_docs()
        test_ok = run_tests()

        print("\n" + "=" * 60)
        print("  Summary")
        print("=" * 60)
        print(f"  Docs: {result}")
        print(f"  Critical changes: {len(changed)}")
        print(f"  Tests: {'PASS' if test_ok else 'FAIL'}")

        if changed:
            print(f"\n  Action: 关键文件有变更，请更新 SKILL.md 后运行 --package")

        # 自动打包
        if test_ok:
            package()


if __name__ == "__main__":
    main()
