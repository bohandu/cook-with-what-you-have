# 有啥吃啥

根据家里现有的食材，从 [HowToCook](https://github.com/Anduin2017/HowToCook) 中推荐真正能做、并且说明理由的菜谱。

这是一个本地优先的 Agent Skill：不需要服务器、账户、数据库或额外的模型 API Key。安装到 Codex、Claude Code 等兼容 Agent 后，直接用自然语言聊天即可。

## 功能

- **有啥吃啥**：根据现有食材返回三个按匹配度排序的候选
- **整餐搭配**：按用餐人数和菜品数量给出三个完整搭配方案
- **查询菜谱**：忠实展示 HowToCook 原始用料、计算和步骤
- **随便推荐**：在过敏、忌口、厨具和口味条件内提供灵感
- **个人档案**：本地记住常备品、厨具、默认人数和饮食习惯
- **可撤销更新**：每次档案变化都会提示，并支持撤销

## 示例

```text
你：我有豆腐、小葱、大蒜、生抽和香油，今天能做什么？

Agent：
1. 凉拌豆腐 — 高度匹配
   已有：豆腐、小葱、大蒜、生抽、香油
   缺少：无需补充关键食材

2. 葱煎豆腐 — 较为匹配
   已有：豆腐、葱、盐
   缺少：青辣椒、鸡精

3. 皮蛋豆腐 — 补位推荐
   已有：豆腐、生抽
   缺少：皮蛋、白砂糖、醋

想看哪一道的完整原菜谱？
```

首次使用时，Skill 会在一条消息中确认默认用餐人数、过敏与忌口，以及常见特殊厨具。之后直接使用，不会重复询问。

## 安装

下载本仓库后，将 [`skills/cook-with-what-you-have`](skills/cook-with-what-you-have) 整个目录复制到 Agent 的个人 Skill 目录。

### Codex

```text
~/.agents/skills/cook-with-what-you-have/
```

Codex 会自动发现新的 Skill；如果没有出现，重启 Codex。官方说明见 [Build skills](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)。

### Claude Code

```text
~/.claude/skills/cook-with-what-you-have/
```

Claude Code 通常会实时发现新 Skill；如果此前不存在顶层 `skills` 目录，重启一次。官方说明见 [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands#where-skills-live)。

安装完成后可以直接说：

```text
我有鸡蛋、西红柿和青椒，能做什么？
```

也可以显式调用 `$cook-with-what-you-have`（Codex）或 `/cook-with-what-you-have`（Claude Code）。

## 工作方式

Skill 随包携带固定版本的 HowToCook 菜谱文本和精简索引。Agent 只搜索与当前食材相关的索引记录，先返回三个简要候选；用户选择后才读取一道完整菜谱，因此不会一次性把全部菜谱放入上下文。

个人档案保存在用户主目录的 `.cook-with-what-you-have/`，不会上传到项目服务器。当前快照包含 368 道菜谱，固定于 HowToCook commit [`0477799`](https://github.com/Anduin2017/HowToCook/commit/0477799945082b72d6ac5c86a9752fddccf086e4)。

首次创建本地个人档案时，受沙箱保护的 Agent 可能会请求一次用户目录写入许可；不需要手动创建文件或填写配置。

## 开发

用户不需要 Python。以下命令只供维护者更新离线数据和运行测试：

```powershell
python tools\import_howtocook.py --commit 0477799945082b72d6ac5c86a9752fddccf086e4
python -m unittest discover -s tests -v
```

产品语义和已确认决策记录在 [`CONTEXT.md`](CONTEXT.md) 与 [`docs/adr`](docs/adr) 中。

## 数据来源与许可

菜谱来自 [Anduin2017/HowToCook](https://github.com/Anduin2017/HowToCook)，其内容采用 [Unlicense](skills/cook-with-what-you-have/references/howtocook/LICENSE)。本项目原创部分采用 [MIT License](LICENSE)。

本项目提供菜谱检索与匹配，不构成医疗或营养治疗建议。过敏信息仍应由用户自行核对原料标签和实际烹饪环境。
