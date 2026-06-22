"""
LangChain Skill 一键更新工具

用法:
  python update_skill.py              # 全量：拉取文档 → 清洗 → 提示更新
  python update_skill.py --check     # 轻量检测：对比 llms.txt 看有没有新页面
  python update_skill.py --docs-only  # 只拉取+清洗文档
  python update_skill.py --test-only  # 只跑盲测（需手动提供测试代码）
  python update_skill.py --package   # 打包上次结果到日期文件夹

工作流:
  1. sync_docs()     → GitHub 拉取最新 .mdx → 清洗 → 保存到 langchain_docs/
  2. diff_docs()     → 对比新旧文档，输出变更摘要
  3. [手动] 根据 diff 更新 SKILL.md
  4. run_tests()     → 跑 resume_agent.py 验证
  5. package()       → 打包到 dated 文件夹
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


def url_to_raw(url: str) -> str:
    """docs.langchain.com/oss/python/X → GitHub raw .mdx"""
    path = url.replace("https://docs.langchain.com/oss/python/", "")
    return f"{GITHUB_RAW_BASE}/{path}.mdx"


def url_to_name(url: str) -> str:
    """URL → 文件名"""
    path = url.replace("https://docs.langchain.com/oss/python/", "")
    return path.replace("/", "-")


def fetch_mdx(raw_url: str) -> tuple[str | None, int]:
    """拉取单个 .mdx 文件，返回 (内容, 状态码)"""
    try:
        req = Request(raw_url, headers={"User-Agent": "LangChainSkillUpdater/1.0"})
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8"), resp.status
    except HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, -1


def clean_mdx(text: str) -> str:
    """清洗 MDX → 纯净 Markdown"""
    import re
    md = text
    md = re.sub(r'^import\s+.*$', '', md, flags=re.MULTILINE)
    md = re.sub(r'^:::python\s*$', '', md, flags=re.MULTILINE)
    md = re.sub(r'^:::js\s*$', '', md, flags=re.MULTILINE)
    md = re.sub(r'^:::$', '', md, flags=re.MULTILINE)
    md = re.sub(r'</?CodeGroup>', '', md)
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
    """全量同步文档"""
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
        raw_url = url_to_raw(url)
        out_path = DOCS_DIR / f"{name}.md"

        print(f"  [{i+1}/{len(urls)}] {name}...", end=" ", flush=True)

        content, status = fetch_mdx(raw_url)
        if content is None:
            fail += 1
            failed_urls.append((url, status))
            print(f"FAIL ({status})")
            continue

        clean = clean_mdx(content)
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
        path = DOCS_DIR / f"{name}.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            h = hash_content(content)
            if name in cache and cache[name] != h:
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
    elif "--docs-only" in args:
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
