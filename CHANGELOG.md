# CHANGELOG

## 2026-07-03 — Skill 层级结构重构

### 架构变更
- **新建父技能 `langchain-v1-suite`** — 统一入口
- **吸收 `agent-sdk-router`** — 路由逻辑融入父 skill，删除独立路由 skill
- **4 子技能归入父目录** — `langchain-v1/`, `langgraph-v1/`, `deepagents-v1/`, `langsmith-trace/` 移至 `langchain-v1-suite/` 下
- **渐进披露** — 父技能自动加载（~800 tokens），子技能按需 `read_file`。自动加载 5→1（-80%）
- 模式匹配 DeepAgents Hierarchical Skills 规范 (Section 8.2)

### 联动更新
- `CLAUDE.md`: 三层架构图 + 决策逻辑更新
- `README.md`: Skill 目录表 + 架构图 + 复制方式 + 更新日志
- `.claude/references/repo-structure.md`: 仓库树适配
- `.claude/maintenance/sync-strategy.md`: 同步命令简化为单目录
- `.claude/settings.local.json`: skillOverrides 层级配置
- 各子 skill CHANGELOG 保留在各自目录下

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
