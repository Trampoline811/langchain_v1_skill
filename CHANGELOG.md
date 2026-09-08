# CHANGELOG

## 2026-09-08 — L3 盲测扩展：覆盖 deepagents / langgraph 子技能 + 判定语义硬化

- **L3 用例 5 → 7**：`cases.py` 每例新增 `skill` 字段，ON 组按用例注入对应子技能（langchain-v1 / deepagents-v1 / langgraph-v1）SKILL.md 为系统提示；新增 case6 深度研究规划 Agent（`create_deep_agent` + `@tool` + `response_format`）、case7 持久化记忆问答图（`StateGraph` + `Annotated` reducer + `compile(checkpointer=InMemorySaver())`）
- **判定语义硬化**（`_judge_probe.py`，四连修）：① fake model 驱动 L3c 受限（`NotImplementedError`）→ **SKIP 不判 FAIL**；② 凭据/网络类错误统一 SKIP——补全 **import 期**与**构造期**两处漏网（此前只覆盖 invoke 期），关键词含 api_key/credentials/401 等；③ 构造返回元组 `(agent, checkpointer)` 被误当 `(agent, config)` → 仅当第二元素为含 `configurable` 的 dict 才作 config（修复 HITL 用例误报 `'InMemorySaver' has no attribute 'items'`）；④ **dummy key 注入**：导入前为缺失 provider key 填占位 → L3b 构造 100% 真实验证（不再因缺凭据跳过），L3c 真跑必 401 → SKIP，零真实消耗
- **run.py 增强**：子进程捕获显式 `encoding="utf-8"`（原 GBK 解码 UTF-8 崩溃）；总分 `4×N` 动态化（原硬编码 /20）；报告加技能列；**语法失败自动重试生成**（最多 2 次，自愈长文件截断类噪声）；生成 prompt 加 3 条硬约束（模型只在函数内创建 / import 只引真实模块 / 禁止截断）
- **终版结果（D 语料，7 用例 × 2 组，2026-09-08 20:49/20:50）**：ON **27/28 静态 + 7/7 PASS**（构造全验证，L3c 凭据 SKIP；case1-5 零黑名单）；OFF **16/28 + 6/7 FAIL@b**（v0 API import 即炸）+ case7 PASS(SKIP)。静态差 11 分、可运行 7/7 vs 1/7 → **三子技能均有效**；多轮样本（A/B/C/D）方差分析：生成偶发语法截断/顶层初始化，重试+硬约束后收敛
- **盲测反哺 skill 两处微缺口**：langgraph-v1 SKILL 通篇无"禁 ChatOpenAI"约定（全量注入仍被违例）→ 补模型初始化警告行；deepagents-v1 的 ChatOpenAI 国内供应商示例易被误模仿 → 补"默认 init_chat_model/字符串传参，ChatOpenAI 仅自定义 base_url 场景"约定。修复后 ON 未来可望 28/28
- **已知边界**：case7（langgraph StateGraph）OFF 组也能构造通过——StateGraph API 跨 v0/v1 稳定，该用例判别力天然弱（对照意义小于 langchain/deepagents 用例），已记录

## 2026-09-07 — 新增 L3 盲测闭环（LLM 读 skill 写代码 → 自动执行 → 判跑通）

- **新增 `tests/l3-blind-test/`**：补齐"生成→执行→判定"自动化验证层（此前盲测只人工评分、生成代码不执行）。三级判定：L3a py_compile → L3b import+构造（参数自适应注入模型工厂，凭据失败降级 `FakeMessagesListChatModel` 只验 API 结构）→ L3c invoke 真跑（fake 或真实 LLM，外部凭据/网络错误判 SKIP 不判 FAIL）
- **首轮结果（DeepSeek 生成，5 用例由简到繁）**：ON 组（system=langchain-v1 SKILL.md 全文）**20/20 静态 + 5/5 构造 PASS、0 黑名单**；OFF 组（裸写对照）**8/20 静态 + 5/5 FAIL**（系统性误用已移除的 AgentExecutor/ChatOpenAI → import 即炸）。静态差 12 分、运行 5/5 vs 0/5 → **skill 有效且真跑通可判**
- **入口文件/盲测历史关系**：`blind_test.md`（A/B 5 用例设计）+ `blind_test_history.md`（早期 C/D/A/B 四组记录）+ `blind_test_analysis.md`（评分分析）保留；L3 = 设计方案的自动化落地（+ 新增 OFF 组真跑对照）
- **真实环境佐证**：OFF 组 import AgentExecutor 失败证明判定跑在 langchain 1.0 真环境（非风格打分）；ON 组代码全部真实可构造

## 2026-09-07 — docs 镜像收尾：修复 .md 双后缀 bug + 中间件对账补 ToolErrorMiddleware

- **根因修复**：官方 llms.txt 分区链接自带 `.md` 后缀，旧 `url_to_raw()` 二次追加 → 请求 `.md.md` 必 404（此前误判为"官方限流假 404"）。新增 `normalize_url()` 统一去尾 `.md`，`load_urls`/`refresh_urls`/`--retry-failed` 三处规范化
- **urls.md 去重**：legacy 段与 refresh 合并段同一页面两种形态 → 去重后 367 → 215 条唯一 URL；剔除 KNOWN_DEAD（rss.xml 非页面资源、deepagents/code-link 官方死链、changelog-js/-py 六页 .md 直出返回 HTML）
- **镜像完成**：215/215 全覆盖，`docs_failed.json` 清空（此前 172 "缺失" 中 144 为双后缀假缺失）
- **中间件对账**：官方 middleware-built-in 页全集 vs langchain-v1 §5.1 速查表，唯一缺口 `ToolErrorMiddleware`（工具异常转错误 ToolMessage 回喂 LLM，需 `langchain>=1.3.14`）已补入 SKILL + references/api-reference.md
- **新增镜像页**（此前因双后缀从未成功抓取）：langchain 错误码 8 页 + frontend generative-ui 4 页 + deepagents dynamic-subagents/fault-tolerance/multimodal/openwiki/rag/retrieval 6 页等；经查均无额外 skill API 缺口（dynamic-subagents/fault-tolerance 内容已由 deepagents-v1 先行覆盖）

## 2026-09-06 — 全量 docs 刷新 + 入口文件对齐 + 盲测跑通

- **官方 docs 全量刷新**：`docs.langchain.com` .md 直出全量镜像（含自动清单合并，367 条 URL）；脚本增强：限速 0.5s/页 + 失败重试（防官方批量限流假 404）+ `--section langchain|langgraph|deepagents|concepts` 分区分批拉取
- **盲测实跑**（.venv, langchain 1.4.0 / deepagents 0.7.x）：`tests/langgraph_agent.py` 4/4、`tests/deep_agent.py` 7/7 通过（无 LLM 导入级）；`resume_agent.py` 需 `DEEPSEEK_API_KEY` 后跑
- **入口文件对齐现状**：`CLAUDE.md`（本地）核心原则 1/2/3 与 Phase A ④ 更新为 junction/`.md 直出`语义、新增"官方更新了/刷 docs"触发词；`AGENTS.md`（入库）三层架构/仓库结构/发布策略/URL 说明/原则 5 全部对齐 2026-09 现状（此前仍是 4 技能平面 + agent-sdk-router 旧结构）
- **git 排除** `.memsearch/`（记忆系统存储，避免误入库）

## 2026-09-05 — 沧海九粟 ch13-16 + 官方 v0.7/v1.4 全面同步

- **社区归档**（`docs/community/沧海九粟/`，本地不入库）：ch13 评分量规、ch14 Streaming、ch15 Interpreters、ch16 动态子 Agent、release-v0-7 发布说明，INDEX.md 同步
- **deepagents-v1 skill**：版本基线更新至 v0.7（TodoListMiddleware opt-in / Backend Factory 移除 / 文件工具行为变化 / 同名中间件原位替换）；新增 QuickJS Interpreter+PTC、动态子 Agent、RubricMiddleware、Streaming v3 Typed Projections 四模块
- **langchain-v1 skill**：MCP 集成指引 v1.4 分叉（内置 `langchain.mcp.MCPAdapter` 取代 `langchain-mcp-adapters`）
- 盲测：`tests/deep_agent.py` 适配 deepagents v0.7（StoreBackend 显式 namespace、FilesystemMiddleware 私有权限参数防御降级）；langchain/langgraph 盲测所用 API 不受版本影响
- 工具链：`tools/update_skill.py` 改为官方 `docs.langchain.com/<url>.md` 直出拉取（官方源码树重构后旧 GitHub raw oss/python 映射已失效）；新增 `--refresh`：自动从官方分区 llms.txt 合并现行页面清单进 `tools/urls.md`（--docs-only 默认先刷新）
- 部署：`E:\AI_skill\`（套件 + 4 平铺）与 `~/.agents/skills/langchain-v1` 改为 **junction 直通真相源**，改仓库即时生效，不再需要手动同步（`sync-strategy.md` / `cascade-update-checklist.md` §C3 已同步更新）；删除复制残留 `agent-sdk-router`

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
