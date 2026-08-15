# 采用 Agent 原生、运行时零依赖的 Skill

首个版本不附带需要 Node.js、Python 或包管理器执行的运行时脚本。Skill 由精简的 `SKILL.md`、按需读取的规则文件、预生成 JSONL 菜谱索引和 HowToCook 原始 Markdown 组成；Codex、Claude Code 等具备本地文件读写与文本搜索能力的 Agent 自行完成索引检索、语义判断和个人档案更新。

Python 导入器只供项目维护者在发布前固定上游 commit、复制原始菜谱并生成静态索引，不是用户安装或使用步骤。这样实现满足“安装 Skill 后直接聊天”的产品要求，代价是候选排序仍会受到不同 Agent 推理能力的影响；通过明确排序规则、静态契约测试和典型对话评测集控制差异。
