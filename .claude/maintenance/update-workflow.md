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

## 轻量检测（只检测不下载）

```bash
curl -sL https://docs.langchain.com/llms.txt | grep -oP 'https://[^ ]+' | sort > llms_new.txt
diff llms_old.txt llms_new.txt
```
