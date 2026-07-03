# LangSmith CLI 命令完整参考

> **来源**: AgentSeek `langsmith-trace/reference/cli-commands.md`（ob-labs/agentseek），社区实战验证

---

## ⚠️ 安全警告

所有命令假定 `LANGSMITH_API_KEY` 已设环境变量。**绝对不要用 `--api-key` CLI 标志。**

## 命令树

```
langsmith
├── project
│   └── list              List tracing projects
├── trace
│   ├── list              List traces (filters apply to root run)
│   ├── get               Get single trace with full run hierarchy
│   └── export            Export traces to JSONL (one file per trace)
├── run
│   ├── list              List runs (flat, filters apply to any run)
│   ├── get               Get single run by ID
│   └── export            Export runs to single JSONL file
├── dataset
│   ├── list / get / create / delete
│   ├── export            Export dataset to file
│   └── upload            Upload local JSON as dataset
├── example
│   ├── list / create / delete
├── evaluator
│   ├── list / upload / delete
├── experiment
│   ├── list / get
├── thread
│   ├── list / get
└── --help
```

---

## 常用 Flags

### Data inclusion（`list` 和 `get` 通用）

| Flag | 效果 |
|------|--------|
| `--include-io` | 添加 inputs, outputs, error 字段 |
| `--include-metadata` | 添加 status, duration_ms, token_usage, costs, tags |
| `--include-feedback` | 添加 feedback_stats |
| `--full` | 三合一（但 `run get` 上推荐单独用 `--include-io`） |

### Filtering

| Flag | 说明 |
|------|-------------|
| `--project NAME` | Project 名称 |
| `--limit N` | 最大结果数 |
| `--last-n-minutes N` | 时间窗口（分钟） |
| `--since TIMESTAMP` | ISO 时间戳之后 |
| `--error` / `--no-error` | 按错误状态过滤 |
| `--name NAME` | 按 run name 精确匹配 |
| `--min-latency SECONDS` | 最小延迟 |
| `--max-latency SECONDS` | 最大延迟 |
| `--min-tokens N` | 最小 token 数 |
| `--tags tag1,tag2` | 包含任一 tag（OR） |
| `--trace-ids id1,id2` | 限定特定 trace |
| `--run-type TYPE` | `run list` 专用：llm, chain, tool, retriever, prompt, parser |
| `--filter QUERY` | 原生 LangSmith filter DSL（高级） |

**Display：**
- `--show-hierarchy` —（`trace list` 专用）内联展示每个 trace 的完整 run tree

### Output

| Flag | 说明 |
|------|-------------|
| `--format json` | 机器可读（默认） |
| `--format pretty` | 人类可读：表格、树、语法高亮 JSON |
| `-o FILE` | 输出到文件 |

---

## 常用命令示例

```bash
# 列出 projects，找到最近活动
langsmith project list

# 最近 trace + 时间信息
langsmith trace list --project default --limit 10 --include-metadata

# 最近一小时的失败 trace
langsmith trace list --project default --error --last-n-minutes 60

# 慢 trace（>5s）
langsmith trace list --project default --min-latency 5.0 --limit 10

# 获取完整 trace 树
langsmith trace get <trace-id> --project default

# Trace 内所有 run + IO（排障推荐）
langsmith run list --trace-ids <trace-id> --project default --include-io

# 只看 LLM 调用
langsmith run list --trace-ids <trace-id> --project default --run-type llm --include-io

# 只看工具调用
langsmith run list --trace-ids <trace-id> --project default --run-type tool --include-io

# 单个 run 详情
langsmith run get <run-id> --include-io

# 导出 trace 用于创建 dataset
langsmith trace export ./traces --project default --limit 20 --full

# 高级：按 feedback score 过滤
langsmith trace list --filter 'and(eq(feedback_key, "correctness"), gte(feedback_score, 0.8))'
```

---

> **返回**: [`SKILL.md`](../SKILL.md) §6 实用命令速查
