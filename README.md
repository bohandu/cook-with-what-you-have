# 有啥吃啥 🍳

打开冰箱：两个鸡蛋、半块豆腐、一把不知道该怎么处理的青菜。

**今晚到底吃什么？**

把家里有的食材告诉「有啥吃啥」，它会从 [HowToCook](https://github.com/Anduin2017/HowToCook) 中挑出真正能做的菜，告诉你还缺什么，也可以直接帮你搭配一顿饭。

这是一个本地优先的 Agent Skill。安装到 Codex、Claude Code 等兼容 Agent 后，不用注册账户，也不用准备额外的 API Key，直接聊天就能用。

## 它能帮你

- **有啥吃啥**：看看现有食材能做什么，并按匹配程度推荐三个选择
- **搭配一顿饭**：两个人、两菜一汤，或者几个人吃几个菜，都可以直接说
- **查询菜谱**：选好菜后，忠实展示 HowToCook 原菜谱的用量、计算和步骤
- **随便推荐**：没有想法时，结合口味、忌口和厨具给你一点灵感
- **记住你的习惯**：常备调料、默认人数、过敏原、忌口和厨具不用每次重复说明

## 聊起来是这样的

```text
你：家里只有鸡蛋。两个人吃，今天不想吃肉，可以买点青菜，
   帮我搭配两菜一汤。

有啥吃啥：
1. 韭菜炒蛋 + 虎皮青椒 + 金针菇汤
   酸辣下饭，采购也相对少。
   需要买：韭菜、青椒、金针菇、大蒜、生抽、醋、白糖

2. 西红柿炒鸡蛋 + 蒜蓉空心菜 + 黄瓜皮蛋汤
   酸甜、蒜香搭配，清爽但不会太寡淡。

3. 油醋爆蛋 + 地三鲜 + 勾芡香菇汤
   更浓郁、更下饭，不过需要补充的食材也更多。

你：就第一套。

有啥吃啥：接下来按两人份展开三道菜的完整用料和步骤……
```

不需要学习固定指令。你也可以直接说：

```text
我有豆腐、小葱和生抽，能做什么？
想吃宫保鸡丁，怎么做？
随便推荐一道不辣的菜。
以后默认三个人吃，刚才的修改撤销一下。
```

第一次使用时，它会一次性确认默认人数、过敏与忌口，以及你有哪些厨具。之后这些信息会保存在本地；每次档案发生变化都会明确提示，也可以撤销。

## 安装

下载本仓库，将 [`skills/cook-with-what-you-have`](skills/cook-with-what-you-have) 整个目录复制到你的个人 Skill 目录。

### Codex

```text
~/.agents/skills/cook-with-what-you-have/
```

### Claude Code

```text
~/.claude/skills/cook-with-what-you-have/
```

如果安装后没有被自动发现，重启一次 Agent。然后直接问：

```text
我有鸡蛋、西红柿和青椒，能做什么？
```

也可以显式调用 `$cook-with-what-you-have`（Codex）或 `/cook-with-what-you-have`（Claude Code）。

## 本地优先

菜谱和检索索引随 Skill 一起提供，个人档案保存在用户主目录的 `.cook-with-what-you-have/` 中。本项目不需要自己的服务器、账户或数据库。

## 数据来源与许可

菜谱来自 [Anduin2017/HowToCook](https://github.com/Anduin2017/HowToCook)，其内容采用 [Unlicense](skills/cook-with-what-you-have/references/howtocook/LICENSE)。本项目原创部分采用 [MIT License](LICENSE)。

过敏用户仍应自行核对食品包装上的原料信息，并留意实际烹饪环境中的交叉接触风险。
