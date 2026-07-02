# 对外发布策略

**`CLAUDE.md` 不推送到 GitHub/Gitee**。他人 clone 仓库后只看到：
- `README.md` — 项目说明、三层架构、安装方式、选型速查
- `skills/` — 可直接使用的 5 个 Skill
- `docs/` — 已通过 `.gitignore` 排除（素材，最终用户不需要）
- `tools/` — 仅维护者需要

`.gitignore` 已排除：`docs/`、`.venv/`、`__pycache__/`、`*.pyc`、`.docs_cache.json`、`langchain_docs/`、`CLAUDE.md`
