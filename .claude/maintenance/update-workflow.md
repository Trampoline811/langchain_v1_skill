# 维护流程

## 触发条件

| 信号 | 检测方式 |
|------|---------|
| LangChain 发布新 minor 版本（1.x → 1.y） | 关注 `releases-changelog.md` 或 PyPI |
| 用户报告 skill 生成的代码过时报错 | 日志/反馈 |
| 定期巡检（建议每 2-3 月一次） | 日历提醒 |
| 收到新版官方文档或社区案例 | 手动触发 |

## 全量更新流程（~30分钟）

### Step 1：同步官方文档

```bash
# 下载最新的官方 .mdx 文件
python tools/update_skill.py --docs-only

# 或手动：从 docs.langchain.com 拉取最新页面
# URL → GitHub raw .mdx 映射规则：
# docs.langchain.com/oss/python/X → raw.githubusercontent.com/langchain-ai/docs/main/src/oss/X.mdx
```

### Step 2：对比差异

```bash
git diff docs/
```

重点关注：
- `create_agent` 签名是否有新参数
- `init_chat_model` 参数变化
- 新增/废弃的 middleware
- `create_deep_agent` API 变化
- `StateGraph` API 变化

### Step 3：更新 Skill

只改相关部分，不改整体结构：

| 文件 | 更新内容 |
|------|---------|
| `SKILL.md` | 新增/废弃的 API 签名、核心速查表 |
| `references/api-reference.md` | 中间件增删、参数变化 |
| `references/migration-comparison.md` | 如有破坏性变更才更新 |
| `CHANGELOG.md` | 记录本次更新内容 |

### Step 4：验证

```bash
python tools/update_skill.py --test-only

# 或用盲测用例（3 个脚本，当前 17/17 通过）
python tests/resume_agent.py --demo
python tests/langgraph_agent.py
python tests/deep_agent.py
# 确认无 deprecation warning，输出正常
```

### Step 5：同步到部署副本

见 [[sync-strategy]] 中的同步命令。

## 社区内容更新流程

> 适用于 `docs/community/` 下新增/更新社区文章后，决定是否更新 skill 或出专题报告。

### 触发信号

| 信号 | 检测方式 |
|------|---------|
| 新增社区课程/文章 | 手动下载后存入 `docs/community/` |
| 已有社区内容更新（社区发布新版） | 社区源仓库 release / commit |
| 发现新社区源 | 用户主动获取 |

### 分析→决策→执行（4 步）

#### Step 1：快速扫描

对新增/修改的社区文件，提取：
- 技术关键词（API 名、类名、中间件名）
- 与现有 4 个 skill 的匹配度（deepagents-v1 / langchain-v1 / langgraph-v1 / langsmith-trace）
- 与现有 3 个 topic 的匹配度（middleware / skills / routing）

#### Step 2：分类决策（Decision Gate）

| 内容特征 | 归入 | 执行路径 |
|---------|------|---------|
| 新 API 用法 / 未收录的代码模式 / 新参数/新中间件 | **更新 skill** | 走 [全量更新流程](#全量更新流程约30分钟) Step 3-5 |
| 架构视角 / 跨模式对比 / 最佳实践总结 / 设计哲学 | **更新/新建 topic** | 走 `topics/INDEX.md` 扩展规则 + `topic-report-template.md` |
| 两者都有 | **先 skill 后 topic** | skill 写清楚 API 用法 → topic 引用 skill 做深度分析 |
| 仅为已有内容的重复/补充 | **引用链接** | 在 skill reference 或 topic 参考资料中加链接，不改结构 |

#### Step 3：执行更新

按上一步决策路径执行。具体联动文件清单见 `cascade-update-checklist.md` §A2 和 §B。

#### Step 4：验证

- Skill: 跑盲测验证（`python tests/resume_agent.py --demo`）
- Topic: `grep -n "^## \|^### " topics/xxx.md` 检查节编号
- 交叉引用: 确认 skill ↔ topic 引用路径正确

### 与官方文档更新流程的区别

| 维度 | 官方文档更新 | 社区内容更新 |
|------|------------|------------|
| 触发频率 | 版本发布（不频繁） | 社区动态（不定期） |
| 更新方式 | 自动化（`update_skill.py --docs-only`） | 手动分析→决策 |
| 覆盖范围 | 4 个 skill 全量 | 按关联度精准更新 |
| 主要产出 | skill 文件 | skill（API 层）+ topic（分析层） |

---

## 轻量检测（只检测不下载）

```bash
curl -sL https://docs.langchain.com/llms.txt | grep -oP 'https://[^ ]+' | sort > llms_new.txt
diff llms_old.txt llms_new.txt
```
