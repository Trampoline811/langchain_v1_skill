# 联动更新清单（Cascade Update Checklist）

> **目的**：任何内容变更后，主动检查本清单中对应的联动文件，避免遗漏同步更新。
> **使用时机**：每次修改项目文件**之前**浏览一遍相关触发条件，修改**之后**逐项验证。

---

## 触发条件速查表

| 你改了什么... | 跳转到 |
|--------------|--------|
| `docs/official/` 下官方文档 | [§ A1](#a1-官方文档更新) |
| `docs/community/` 下社区文档 | [§ A2](#a2-社区文档更新) |
| `topics/` 下专题报告 | [§ B](#b-专题报告变更) |
| `skills/` 下 skill 文件 | [§ C](#c-skill-变更) |
| 项目目录结构（新建/删除/移动/重命名目录） | [§ D](#d-项目结构调整) |
| `.claude/` 下配置/参考/维护文档 | [§ E](#e-claude-配置变更) |

---

## A1. 官方文档更新

**触发**：`docs/official/` 下任何文件增删改、`docs/official/` 整体重新拉取。

### 必须检查

| # | 联动文件 | 检查内容 | 严重度 |
|---|---------|---------|:---:|
| 1 | `skills/langchain-v1-suite/langchain-v1/SKILL.md` | API 签名、参数是否与最新文档一致 | 🔴 |
| 2 | `skills/langchain-v1-suite/langchain-v1/references/api-reference.md` | 新增/废弃 API 同步 | 🔴 |
| 3 | `skills/langchain-v1-suite/langchain-v1/CHANGELOG.md` | 记录本次更新 | 🟡 |
| 4 | `skills/langchain-v1-suite/langgraph-v1/` 下 3 个文件 | 同上，如有 Runtime 层变化 | 🔴 |
| 5 | `skills/langchain-v1-suite/deepagents-v1/` 下 3 个文件 | 同上，如有 Harness 层变化 | 🔴 |
| 6 | 已生成的 `topics/` 专题报告 | 如有报告引用的 API 已过时，更新报告 + 日期 | 🟡 |

### 更新方法

1. 执行 `tools/update_skill.py --docs-only` 拉取最新文档
2. `git diff docs/official/` 查看具体变化
3. 按 [update-workflow.md](update-workflow.md) Step 1-5 全量流程执行
4. 跑盲测验证：`python tests/resume_agent.py --demo`

---

## A2. 社区文档更新

**触发**：`docs/community/` 下新增社区、增删文件、或在已有社区目录下修改内容。

### 分析步骤（内容评估）

> 社区文件获取后，先评估技术价值，再决定如何处理。跳过此步骤直接做联动更新 = "搬了仓库但不知道里面是什么"。

1. **快速扫描**：对新增/修改的社区文件，提取技术关键词（API 名、中间件名、模式名）
2. **关联度矩阵**：与现有 4 个 skill + 3 个 topic 做匹配度打分
3. **分类决策**（见下方决策门）

### 决策门（Classification Gate）

| 内容特征 | 归入 | 执行路径 |
|---------|------|---------|
| 新 API 用法 / 未收录的代码模式 / 新参数 | **更新 skill** | 走 [update-workflow.md](update-workflow.md) Step 3-5 |
| 架构视角 / 跨模式对比 / 最佳实践总结 | **更新/新建 topic** | 走本清单 [§ B](#b-专题报告变更) |
| 两者都有 | **先 skill 后 topic** | 确保交叉引用 |
| 仅为已有内容补充 | **引用链接** | 仅更新 skill reference 或 topic 参考资料 |

### 必须检查

| # | 联动文件 | 检查内容 | 严重度 |
|---|---------|---------|:---:|
| 1 | `docs/community/README.md` | 社区列表、文件数量是否同步 | 🔴 |
| 2 | `.claude/references/repo-structure.md` | `docs/community/` 树结构是否反映当前实际 | 🔴 |
| 3 | 该社区的 `INDEX.md` | 如有，文件索引是否与实际文件一致 | 🔴 |
| 4 | `topics/INDEX.md` | 如社区文档触发新专题报告生成，需添加索引 | 🟡 |
| 5 | `topics/` 下已有专题报告 | 如新社区内容与已有报告有交叉引用价值，更新参考资料 | 🟢 |

### 更新方法

1. 新增文件/目录后，立即更新本社区 `INDEX.md`
2. 立即更新 `docs/community/README.md`（社区列表）
3. 立即更新 `.claude/references/repo-structure.md`（目录树）
4. 如果内容触发了专题报告生成，走 [§ B](#b-专题报告变更)

> **例**：本次"沧海九粟"社区获取后，更新了以上 3 个文件 + 该社区 INDEX.md，共 4 处联动。

---

## B. 专题报告变更

**触发**：`topics/` 下新增报告、修改报告内容、调整报告结构。

### B1. 新增专题报告

| # | 联动文件 | 检查内容 | 严重度 |
|---|---------|---------|:---:|
| 1 | `topics/INDEX.md` | 表格加一行（文件 / 专题 / 描述 / 日期） | 🔴 |
| 2 | 报告末尾 `## 参考资料` 章节 | 按 [topic-report-template.md](../references/topic-report-template.md) §四 格式，列出所有引用源 | 🔴 |
| 3 | `.claude/references/repo-structure.md` | `topics/` 树新增条目（如有新子目录） | 🟡 |
| 4 | 其他相关专题报告 | 添加交叉引用（如 middleware ↔ skills ↔ routing 三者互引） | 🟡 |

### B2. 修改已有专题报告（内容/结构/小节增删）

| # | 联动文件 | 检查内容 | 严重度 |
|---|---------|---------|:---:|
| 1 | `topics/INDEX.md` | 日期更新为最新修改日期 | 🟡 |
| 2 | 其他交叉引用的专题报告 | 确认引用的小节编号未变（如 §5.1 是否还是原来的内容） | 🟡 |
| 3 | `grep -n "^## \|^### " topics/xxx.md` | 检查节编号是否连续、无重复 | 🔴 |

### B3. 验证

写完/改完报告后必须执行：
```bash
# 1. 检查节编号
grep -n "^## \|^### " topics/xxx.md

# 2. 确认 INDEX.md 日期已更新
grep "报告名" topics/INDEX.md
```

---

## C. Skill 变更

**触发**：`skills/` 下任何 skill 的 SKILL.md、references/*.md、CHANGELOG.md 变更。

### C1. 新增/删除 skill

| # | 联动文件 | 检查内容 | 严重度 |
|---|---------|---------|:---:|
| 1 | `skills/langchain-v1-suite/SKILL.md` | 路由决策表 + 子技能索引 | 🔴 |
| 2 | `README.md` | Skill 目录表 + 架构图 + 选型速查 | 🔴 |
| 3 | `CLAUDE.md` | 仓库结构 + 三层架构描述 | 🔴 |
| 4 | `tools/update_skill.py` | skill 列表（如有硬编码） | 🔴 |
| 5 | `.claude/references/repo-structure.md` | `skills/` 目录树 | 🟡 |

### C2. 修改 skill 内容

| # | 联动文件 | 检查内容 | 严重度 |
|---|---------|---------|:---:|
| 1 | 该 skill 的 `CHANGELOG.md` | 记录变化 | 🔴 |
| 2 | 其他引用了该 skill 的 skill（如 `langchain-v1` 引用 `langsmith-trace`） | 交叉引用段是否需更新 | 🟡 |
| 3 | `E:\AI_skill\` 部署副本 | `rm -rf` + `cp -r` 全量同步 | 🔴 |

### C3. 部署同步

```bash
# 2026-09-05 起 E:\AI_skill 与 ~/.agents/skills 均为 junction，指向真相源 → 无需同步动作
# 仅在真相源目录结构变化（新增/删除/重命名技能）时重建链接，见 sync-strategy.md「重建 Junction 命令」
# 旧命令（先删后拷）已废弃，勿再用 cp -r 覆盖 junction
```

---

## D. 项目结构调整

**触发**：项目根目录下任何目录的创建/删除/移动/重命名。

### 必须检查

| # | 联动文件 | 检查内容 | 严重度 |
|---|---------|---------|:---:|
| 1 | `.claude/references/repo-structure.md` | 目录树与实际结构一致 | 🔴 |
| 2 | `CLAUDE.md` | 工作区目录表 + `.claude/` 索引 | 🔴 |
| 3 | `README.md` | 仓库结构说明（如有目录图示） | 🔴 |
| 4 | `.gitignore` | 新目录如需排除，添加规则 | 🟡 |
| 5 | `tools/update_skill.py` | 如有硬编码路径引用 | 🟡 |
| 6 | `.claude/settings.local.json` | 如有目录路径的权限配置 | 🟡 |

> **例**：本次 `docs/community/` 下新增 `赋范/` 和 `沧海九粟/` 子目录，联动更新了 ① repo-structure.md、② community/README.md（项目 README 不受影响因为 community 语义未变）。

---

## E. .claude/ 配置变更

**触发**：`.claude/` 下任何文件的增删改。

### 必须检查

| # | 联动文件 | 检查内容 | 严重度 |
|---|---------|---------|:---:|
| 1 | `CLAUDE.md` 中的 `.claude/ 索引` 表 | 新文件是否需加入索引 | 🔴 |
| 2 | `.claude/references/repo-structure.md` | 如有新维护文档，目录树中体现 | 🟡 |
| 3 | 其他 `.claude/` 文档的交叉引用 | 如本清单被引用，确认引用路径正确 | 🟡 |

---

## 执行协议（给 Claude Code Agent）

> **每次用户说"更新了 X"时，Agent 必须主动执行以下协议。**

### 协议步骤

```
1. 识别触发条件
   用户改了什么？匹配触发条件速查表 → 定位到对应的 §A1~§E

2. 查看联动清单
   对照对应章节的"必须检查"表格，列出所有待更新的文件

3. 向用户汇报
   "这次更新涉及 X 个联动文件，我来逐个检查/更新：[清单]"

4. 逐项执行
   按严重度排序（🔴 先 → 🟡 后 → 🟢 最后）

5. 验证
   执行该章节的验证命令（如有），确认所有联动文件已更新
```

### 示例对话

```
用户: "我更新了 docs/official/langchain/ 下 3 个文件。"
Agent: "收到。根据联动清单 §A1，需要检查：
        1. langchain-v1/SKILL.md — API 签名是否一致
        2. api-reference.md — 新增/废弃 API
        3. CHANGELOG.md — 记录更新
        4. topics/ 下 3 份报告 — 是否有引用过时 API
        开始逐项检查..."
```

---

## 常见遗漏记录（血泪教训）

> 以下来自实际踩坑，每次更新前回顾一遍。

| # | 场景 | 遗漏了什么 | 预防 |
|---|------|-----------|------|
| ① | 新增 `topics/` 报告 | 忘记更新 `topics/INDEX.md` | 写入流程固化在 [topic-report-template.md](../references/topic-report-template.md) §六 |
| ② | 新增 skill | 忘记联动更新 4 个文件 | 写入流程固化在 [lessons-learned.md](../history/lessons-learned.md) 错误 2 |
| ③ | 社区文档新增内容 | 忘记更新 `repo-structure.md` | **本次补入 §A2** |
| ④ | 专题报告插入新小节 | 后续小节编号偏移，忘记检查 | `grep -n "^##"` 自检（[lessons-learned.md](../history/lessons-learned.md) 错误 7） |
| ⑤ | 移动目录 | 忘记 `sync-strategy.md` 和 `settings.local.json` 的路径引用 | **本次补入 §D** |

---

> **整理日期**: 2026-07-09
> **依赖**: [update-workflow.md](update-workflow.md) · [sync-strategy.md](sync-strategy.md) · [lessons-learned.md](../history/lessons-learned.md) · [topic-report-template.md](../references/topic-report-template.md)
