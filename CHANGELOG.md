# CHANGELOG

## 2026-07-02 — 项目结构重构

### .claude/ 子目录拆分
- CLAUDE.md 从 338 行精简到 68 行（-80%），详细内容拆分到 `.claude/` 子目录
- 新增 7 个文件：`references/repo-structure.md`, `references/publishing.md`, `references/doc-sources.md`, `maintenance/sync-strategy.md`, `maintenance/update-workflow.md`, `history/lessons-learned.md`, `tracking/todos.md`
- CLAUDE.md 新增「写入规则」自指标准：不可逆错误判断 → CLAUDE.md vs `.claude/`

### docs/official/ 去重归档
- 删除 105 个根目录重复文件（子目录已有同名）
- 41 个孤儿文件移入子目录（deepagents 9 / langchain 22 / langgraph 10）
- 新建 `contributing/`、`reference/` 子目录
- 全部 165 个文件添加 `fetchedAt` YAML frontmatter 日期标记

### tools/update_skill.py 增强
- `sync_docs()` 输出到类别子目录（不再扁平放根目录）
- 新增 `add_frontmatter()` 自动添加 YAML frontmatter + `fetchedAt`
- 新增 `url_to_category()` 按 URL 路径自动归类
- `diff_docs()` 支持子目录查找关键文件

### 文档确认
- Learn 板块确认无独立教程页面（`/learn/*` 均 404），内容已在产品子目录中
