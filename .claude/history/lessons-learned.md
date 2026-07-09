# 易犯错误（血泪教训）

> 以下来自 2026-06-22 AgentSeek 对标更新中实际犯过的错，写下来防止再犯。

## 错误 1：Skill vs Reference 边界判断失误

**症状**：把 langsmith-trace 先做成了 langchain-v1 的 reference（`references/langsmith-trace.md`），用户纠正后才发现应该独立为 skill。

**判断标准（自检 3 问）**：
| 问题 | 答"是"→ reference | 答"否"→ 考虑独立 skill |
|------|:--:|:--:|
| 内容只服务于当前这一个 skill？ | reference | skill |
| 没有独立的触发词/场景？ | reference | skill |
| 不是独立产品/工具？ | reference | skill |

**教训**：LangSmith 是独立可观测平台，跨 Framework/Runtime/Harness 三层，有独立 CLI 和触发词（"debug trace"、"LangSmith"）。满足 3 个"否" → 独立 skill。

## 错误 2：新增 skill 后忘记联动更新

**症状**：新增 `langsmith-trace` skill 后，忘记同步更新：
- `agent-sdk-router/SKILL.md` — 路由决策表缺新 skill
- `README.md` — Skill 目录表、架构图、选型速查
- `CLAUDE.md` — 仓库结构、决策逻辑

**教训**：新增/删除 skill 时，必须联动更新以下 **4 个文件**：

| 文件 | 更新内容 |
|------|---------|
| `skills/agent-sdk-router/SKILL.md` | 决策表 + 场景对照 + 执行协议 |
| `README.md` | Skill 目录表 + 架构图 + 选型速查 + 更新日志 |
| `CLAUDE.md` | 仓库结构 + 架构三层图 + 决策逻辑 + 核心原则条数 |
| `tools/update_skill.py` | 如有自动化同步脚本，也要更新 skill 列表 |

## 错误 3：cp -r 嵌套陷阱

**症状**：`cp -r skills/langchain-v1 "E:/AI_skill/langchain-v1/"` 在目标已存在时，会在目标下面创建 `langchain-v1/langchain-v1/` 嵌套目录。

**教训**：同步命令必须先删后拷：

```bash
# ❌ 错误 — 目标存在会嵌套
cp -r skills/langchain-v1 "E:/AI_skill/langchain-v1/"

# ✅ 正确 — 先删再拷
rm -rf "E:/AI_skill/langchain-v1"
cp -r skills/langchain-v1 "E:/AI_skill/langchain-v1/"
```

## 错误 4：同步不完整

**症状**：更新了 langchain-v1 后只同步了那一个 skill，忘了其他 skill 也需要同步（别的 skill 也可能有交叉引用更新）。

**教训**：每次任何 skill 更新后，**全量同步所有 skill** 到 `E:\AI_skill\`，不要只同步改动的那个。特别是路由 skill 和 README 的更新涉及多个文件时。

---

## 2026-07-03：专题报告写作与 deep-research 经验

> 以下来自今天生成 3 份专题报告 + 1 次 deep-research 实验的踩坑记录。

## 错误 5：deep-research 启动前不评估本地源

**症状**：没有检查本地 `docs/official/` 是否有足够覆盖，就启动了 deep-research。结果 340 万 tokens 花出去后，发现部分产出（Interpreter/PTC 相关）与本地源重叠，且 25 条 claim 中 16 条被对抗验证杀死。

**教训**：deep-research 只用于两个维度——**社区踩坑（本地没有）** 和 **跨框架对比（本地没有）**。其余情况先用本地 `ctx_batch_execute`。判断标准：

| 条件 | 启动 deep-research？ |
|------|:--:|
| `docs/official/` 已覆盖 topic 核心内容 | ❌ |
| 需要找 GitHub Issues / 论坛踩坑 | ✅ |
| 需要跨框架对比 | ✅ |
| 需要最新生产数据（通过率/版本） | ✅ |
| 本地源充足的小专题 | ❌（手动框架够用） |

> **预算参考**：deep-research 单次 ~300 万 tokens。建议 ≤ 3 次/月。

## 错误 6：deep-research 的框架价值被忽略

**症状**：一开始把 deep-research 当成"互联网版的自动化搜索"，只关注它的数据产出。后来才发现它的**分析管道**（多角度分解 → 源分级 → claim提取 → 3票对抗验证 → 信心标注 → 限定声明）可以在本地零成本复现。

**教训**：deep-research 的价值 = 框架（70%）+ 数据（30%）。框架应固化到 `topic-report-template.md` §五"深度分析框架"。本地版映射：

```
deep-research 步骤       本地适配               成本
5路并行 WebSearch   →   3-5 子问题手动分解      0
23源 111 claims      →   docs/official/ 分级提取  ~10K tokens
3-vote 对抗验证      →   2+ 独立源交叉核对        ~20K tokens
forum/issue pitfall  →   本地优先 + PITFALLS_TODO 0
caveats + openQ      →   写入每个报告末尾         ~2K tokens
```

## 错误 7：报告写完不验证结构

**症状**：写完 `langchain-skills-deep-dive.md` 后，§5 和 §6 的小节编号出现了两个 `### 5.3` 和两个 `### 6.2`。后来读报告时才偶然发现。

**教训**：每次写完/改完大文件，跑一次：

```bash
grep -n "^## \|^### " topics/xxx.md
```

检查是否有重复编号。特别是做了"插入新小节"类编辑后，后续每节都可能偏移。

## 错误 8：引用块打断 Markdown Table

**症状**：在 CLAUDE.md 中，一个引用块（`> **topics/ 扩展规则**：...`）被插在了 `| 目录 | 内容 | 性质 |` 表格的两行之间。GitHub 渲染器把引用块当成了表格中断，导致 `tests/` 和 `tools/` 两行从表格中掉出去。

**教训**：Markdown 的表格是**连续块**——表格行中间不能插入任何非表格内容（包括 `>` 引用、空行、代码块）。如果需要表格后加注释，放在表格**完全结束**之后。

**自查**：写完后用 `grep -n "^|" file.md` 确认表格行的连续性。

## 错误 9：中间件触发时机是普遍误解源

**症状**：多次出现"中间件在最后一轮调模型前才跑"的误解（用户自己也有这个直觉）。这是解释中间件时最容易混淆的点。

**教训**：任何涉及 `wrap_model_call` / `before_model` 的解释，**必须**在第一时间用**每次**而非"最后一次"来定义触发频率。使用静动分离图，在每次触发点标注 `← 注意：每次模型调用都触发！`。

> 固化在 `topic-report-template.md` §七 Q3 "纠偏→静动分离→时序→口诀"模式中。

## 错误 10：`tools` 注册位置（类变量 vs create_agent 参数）易混淆

**症状**：Skills 教程把 `tools = [load_skill]` 写在 `SkillMiddleware` 类上，初学者（包括今天的我们）会困惑"为什么不直接传 `create_agent(tools=[...])`？"

**教训**：两种方式效果相同。区别是组织习惯——`tools` 和 middleware 逻辑一体的放类变量，通用工具直接传 `create_agent`。写教程/报告时**主动澄清这个点**，避免读者卡住。

> 已补入 `langchain-skills-deep-dive.md` §五.1 末尾"常见疑问"引用块。
