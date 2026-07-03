# Skill 同步策略

## 唯一真相源

**`E:\My_Projections\langchain_v1\skills\langchain-v1-suite\` 是 LangChain 1.0 Skill Suite 的唯一真相源。**

其他位置（如 `E:\AI_skill\`）的 skill 目录为**部署副本**，仅做单向同步：

```
skills/langchain-v1-suite/（当前项目）  ──单向同步──→  E:\AI_skill/langchain-v1-suite/
    真相源                                              部署副本（只读，不直接编辑）
```

## 同步规则

| 规则 | 说明 |
|------|------|
| **修改方向** | 永远改当前项目 `skills/langchain-v1-suite/`，再同步到部署副本 |
| **禁止反向同步** | 部署副本的修改会被覆盖，不要直接改 `E:\AI_skill\` 下的 skill |
| **同步时机** | 每次 skill 更新完成后立即同步（Step 5 of 维护流程） |
| **同步内容** | 整个 `langchain-v1-suite/` 目录（含父 SKILL.md + 4 子技能 + CHANGELOG + references/） |
| **删除残留** | 先删后拷，避免 cp -r 嵌套陷阱 |

## 同步命令

```bash
# 全量同步（skill 更新后执行）—— 先删后拷
rm -rf "E:/AI_skill/langchain-v1-suite"
cp -r skills/langchain-v1-suite "E:/AI_skill/langchain-v1-suite/"
```

## 旧部署副本清理

层级结构重构（2026-07-03）后，旧版独立 skill 目录（`E:/AI_skill/langchain-v1/`、`E:/AI_skill/agent-sdk-router/` 等）可删除：

```bash
rm -rf "E:/AI_skill/langchain-v1"
rm -rf "E:/AI_skill/langgraph-v1"
rm -rf "E:/AI_skill/deepagents-v1"
rm -rf "E:/AI_skill/agent-sdk-router"
rm -rf "E:/AI_skill/langsmith-trace"
```

## 旧文档清理

`docs/langchain_docs_ref/`（107 文件）已于 2026-06-21 确认为 `docs/official/`（165 文件）的严格子集，已删除。以后只维护 `docs/official/`。
