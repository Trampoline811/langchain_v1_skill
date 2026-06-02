# LangChain Skill 维护指南

## 维护触发条件

以下任一情况出现时更新 skill：

| 信号 | 检测方式 |
|------|---------|
| LangChain 发布新 minor 版本（1.x → 1.y） | 关注 `releases-changelog.md` 或 PyPI |
| 用户报告 skill 生成的代码过时报错 | 日志/反馈 |
| 定期巡检（建议每 2-3 月一次） | 日历提醒 |

## 全量更新流程（30 分钟）

### Step 1: 同步官方文档

```bash
# 在辅助端工作目录
cd E:/AI_resource/Dong_RAG/langchain_docs

# 删除旧文档，重新下载全部
rm -f *.md
bash dl_all.sh          # 如不存在，用下方脚本

# 清洗 MDX → MD
bash clean_all.sh       # 运行 clean_mdx.js
```

### Step 2: 对比 diff

```bash
# 如果有 git 追踪
git diff langchain_docs/ | head -200

# 或手动对比关键文件
diff old/langchain-agents.md new/langchain-agents.md
```

重点关注：
- `create_agent` 签名是否有新参数
- `init_chat_model` 参数变化
- 新增 / 废弃的 middleware

### Step 3: 更新 Skill

只改相关部分，不改整体结构：

| 文件 | 更新内容 |
|------|---------|
| `SKILL.md` | 新增/废弃的 API 签名 |
| `references/api-reference.md` | 中间件增删、参数变化 |
| `references/migration-comparison.md` | 如无大改可不动 |

### Step 4: 验证

```bash
cd E:/AI_resource/Dong_RAG/skill_test
uv run python resume_agent.py --demo
# 确认无 deprecation warning，输出正常
```

## 轻量更新（只检测不下载）

只看 `llms.txt` 是否新增了页面：

```bash
curl -sL https://docs.langchain.com/llms.txt | grep -oP 'https://[^ ]+' | sort > llms_new.txt
diff llms_old.txt llms_new.txt
```

## 文档下载完整脚本

保存为 `E:/AI_resource/Dong_RAG/langchain_docs/sync_docs.sh`：

```bash
#!/bin/bash
# 全量同步 LangChain 官方文档
set -e
DIR="E:/AI_resource/Dong_RAG/langchain_docs"

# URL → GitHub raw .mdx 映射规则:
# docs.langchain.com/oss/python/X → raw.githubusercontent.com/langchain-ai/docs/main/src/oss/X.mdx

cd "$DIR"

# 如果你维护了 URL 列表
while read url; do
  raw=$(echo "$url" | sed 's|docs.langchain.com/oss/python/|raw.githubusercontent.com/langchain-ai/docs/main/src/oss/|').mdx
  name=$(echo "$url" | sed 's|https://docs.langchain.com/oss/python/||' | sed 's|/|-|g')
  curl -sL "$raw" -o ".raw/${name}.mdx" && echo "OK $name" || echo "FAIL $name"
done < urls.md

# 清洗
node clean_mdx.js

echo "Done. Check diff: git diff --stat"
```

## 核心原则

1. **不要手动维护 API 签名** — 从 GitHub 拉最新 .mdx 是最准确的
2. **diff 驱动更新** — 只看变化部分，不重写
3. **保留盲测用例** — `resume_agent.py` 每次更新后跑一遍
4. **版本标注** — 在 SKILL.md frontmatter 或注释中记录基于哪个版本的文档
