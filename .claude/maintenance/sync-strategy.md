# Skill 部署策略（2026-09-05 起：junction 化，不再复制）

## 唯一真相源

**`E:\My_Projections\langchain_v1\skills\langchain-v1-suite\` 是 LangChain 1.0 Skill Suite 的唯一真相源。**

## 部署方式：目录 Junction（自动一致）

`E:\AI_skill\` 下的相关目录与 `~/.agents/skills/langchain-v1` 均为 **Junction（目录联接）**，
直接指向真相源目录 —— **改真相源即时生效，不需要任何同步步骤，也不会失同步**。

```
skills/langchain-v1-suite/（真相源，仓库）  ──junction──→  E:\AI_skill\langchain-v1-suite
                                  │                        E:\AI_skill\langchain-v1        （平铺，兼容"单指 langchain 工具"语境）
                                  │                        E:\AI_skill\langgraph-v1       （平铺）
                                  │                        E:\AI_skill\deepagents-v1      （平铺）
                                  │                        E:\AI_skill\langsmith-trace   （平铺）
                                  │                        ~/.agents/skills/langchain-v1  （DSH 技能库）
```

> 保留「套件 + 平铺」双形态的原因：部分语境下 "langchain" 指 LangChain 公司全产品线（→套件入口路由），
> 部分语境单指 LangChain 开发框架（→ langchain-v1 平铺）。两者都 junction 到同一真相源，永远一致。

## 使用规则

| 规则 | 说明 |
|------|------|
| **修改方向** | 永远只改真相源 `skills/langchain-v1-suite/` |
| **禁止反向修改** | junction 是直通链接——在 `E:\AI_skill\...` 里改文件 = 直接改仓库，请勿在部署侧编辑 |
| **同步时机** | 无（自动一致） |
| **唯一例外** | 真相源目录结构变化（新增/删除/重命名技能）后，重建对应 junction |

## 重建 Junction 命令

```powershell
$repo = "E:\My_Projections\langchain_v1\skills\langchain-v1-suite"
# 需要时先删旧链接（Remove-Item 删的是链接本身，不会动真相源）
# 套件（统一语境入口）
New-Item -ItemType Junction -Path "E:\AI_skill\langchain-v1-suite" -Target $repo
# 平铺子技能（单指语境）
New-Item -ItemType Junction -Path "E:\AI_skill\langchain-v1"    -Target "$repo\langchain-v1"
New-Item -ItemType Junction -Path "E:\AI_skill\langgraph-v1"    -Target "$repo\langgraph-v1"
New-Item -ItemType Junction -Path "E:\AI_skill\deepagents-v1"   -Target "$repo\deepagents-v1"
New-Item -ItemType Junction -Path "E:\AI_skill\langsmith-trace" -Target "$repo\langsmith-trace"
# DSH 用户技能库（本会话技能目录）
New-Item -ItemType Junction -Path "$env:USERPROFILE\.agents\skills\langchain-v1" -Target "$repo\langchain-v1"
```

## 历史

- **2026-09-05**：由「先删后拷复制」改为 junction 化；删除复制残留 `E:\AI_skill\agent-sdk-router`（2026-06-14 旧版，功能已并入父技能路由决策表）；`~/.agents/skills/langchain-v1` 由 6/22 旧复制同步为 junction。
- **2026-07-03**：层级结构重构后旧版独立 skill 目录（平铺 + agent-sdk-router）本应删除，当时仅在文档标注，实际残留至 2026-09-05 才清理。
- `docs/langchain_docs_ref/`（107 文件）已于 2026-06-21 删除；只维护 `docs/official/`。
