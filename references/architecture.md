# Chinese Novelist Skill — 使用说明与架构文档

> `chinese-novelist` 技能的完整使用指南，适配 Codex、Trae、Claude Code 三大平台。

---

## 一、平台安装

### Claude Code

```bash
# 方式1：克隆到 skills 目录
git clone https://github.com/PenglongHuang/chinese-novelist-skill.git ~/.claude/skills/chinese-novelist

# 方式2：手动复制
cp -r chinese-novelist-skill-master ~/.claude/skills/chinese-novelist
```

安装后 Claude Code 自动识别 `SKILL.md`，输入触发词即可激活。

### Codex

```bash
# 复制到 Codex skills 目录
cp -r chinese-novelist-skill-master $CODEX_HOME/skills/chinese-novelist

# 或放到 ~/.codex/skills/（CODEX_HOME 未设置时的默认路径）
cp -r chinese-novelist-skill-master ~/.codex/skills/chinese-novelist
```

Codex 通过 `agents/openai.yaml` 中的 `display_name` 和 `description` 识别技能。

### Trae

```bash
# Trae 的 skills 目录（具体路径参考 Trae 文档）
cp -r chinese-novelist-skill-master <trae-skills-path>/chinese-novelist
```

Trae 兼容标准 `SKILL.md` 格式，frontmatter 中的 `name` + `description` 用于触发判断。

### 通用验证

安装完成后，在任意平台输入以下内容测试触发：

```
帮我写一部小说
```

如果弹出创作控制台，说明安装成功。

---

## 二、快速上手

### 最简用法（一句话触发）

```
帮我写一部小说
```

Agent 弹出控制台后，按引导回答三个问题即可：

1. **开篇背景**：你想写什么世界的故事？
2. **故事结局**：故事最终怎么收尾？
3. **卷纲**：打算写多少章？各卷大概讲什么？

回答完毕后 Agent 自动生成全部设定并开始创作。

### 完整用法示例

```
帮我写一部小说

开篇背景：末世三年后的废土世界，主角是前特种兵，现在是拾荒者
故事结局：主角牺牲自己拯救最后的人类聚居地
卷纲：30章，分3卷
  第1卷（1-10章）：拾荒求生，卷末发现地下避难所
  第2卷（11-20章）：组建队伍对抗变异兽潮，卷末发现病毒真相
  第3卷（21-30章）：深入变异体巢穴，卷末终极对决
```

### 续更已有项目

```
继续上次的创作
```

Agent 自动检测未完成项目，从中断章节继续。

### 修改已完成章节

```
帮我修改第3章的文风，去掉AI味
```

### 查看/修改设定

```
帮我看看主角的人设，然后把他的性格改得更冷酷一些
```

---

## 三、用户交互流程

```
用户输入触发词
      ↓
Phase 0: 控制台弹出 → 加载偏好 → 检测中断
      ↓
Phase 1: 三个问题
  Q1: 开篇背景（自由描述或选题材）
  Q2: 故事结局（自由描述或选类型）
  Q3: 卷纲（选章节数或自定义）
      ↓
用户确认输入
      ↓
Phase 2: Agent 黑箱生成全部设定（无需等待）
  → 输出规划摘要供确认
  → 选择写作模式
      ↓
Phase 3: 自动创作（全程无需干预）
  → 逐章输出 → 每章生成记忆 → 每10章生成阶段总结
      ↓
Phase 4: 自动校验（字数/伏笔/时间线/人设/文风）
  → 输出完成报告
```

---

## 四、设计理念

用户只需提供三项核心输入，Agent 黑箱生成全部设定：

```
用户输入（3项）          Agent 黑箱生成（全部）
┌─────────────┐      ┌──────────────────────────┐
│ 1. 开篇背景  │      │ 世界观                    │
│ 2. 故事结局  │ ───→ │ 五类角色档案              │
│ 3. 卷纲      │      │ 六份大纲体系文件           │
└─────────────┘      │ 写作计划 JSON              │
                     │ 上下文记忆系统（自动维护）   │
                     └──────────────────────────┘
```

---

## 五、技能文件结构

```
chinese-novelist/
├── SKILL.md                          # 主文件（触发+核心规则）
├── agents/
│   └── openai.yaml                   # Codex/Trae UI 元数据
├── assets/                           # 截图素材
├── references/
│   ├── architecture.md               # 本文档
│   ├── flows/                        # 流程文档（Agent 执行指令）
│   │   ├── phase0-initialization.md
│   │   ├── phase1-input.md
│   │   ├── phase2-planning.md
│   │   ├── phase3-writing.md
│   │   ├── phase4-validation.md
│   │   └── shared-infrastructure.md
│   └── guides/                       # 写作指南（按需加载）
│       ├── chapter-guide.md
│       ├── chapter-template.md
│       ├── character-building.md
│       ├── character-template.md
│       ├── content-expansion.md
│       ├── context-management.md
│       ├── dialogue-writing.md
│       ├── hook-techniques.md
│       ├── outline-template.md
│       ├── plot-control-dashboard.md
│       ├── plot-structures.md
│       └── title-guide.md
└── scripts/
    └── check_chapter_wordcount.py
```

---

## 六、项目产出文件结构

```
chinese-novelist/{YYYYMMDD-HHmmss}-{小说名称}/
├── 00-世界观.md                      # 核心世界观设定
├── 01-人物卡/                        # 五类角色档案
│   ├── 主角.md
│   ├── 重要角色.md
│   ├── 次要角色.md
│   ├── 重要反派.md
│   └── 次要反派.md
├── 02-大纲/                          # 六份大纲体系
│   ├── 卷纲.md
│   ├── 时间线.md
│   ├── 伏笔布局.md
│   ├── 进阶条件.md
│   ├── 成长体系.md
│   └── 境界功法.md
├── memory/                           # 上下文记忆系统（自动维护）
│   ├── phase-1-summary.md
│   ├── ch-001-memory.md
│   └── ...
├── 03-写作计划.json
├── 第01章-xxx.md
└── ...
```

---

## 七、四阶段执行流程

### Phase 0：初始化
- 输出标准化创作控制台
- 加载用户偏好（`user-preferences.json`）
- 检测未完成项目（中断续写）

### Phase 1：三项核心输入
- 开篇背景：世界/时代/初始情境
- 故事结局：最终走向和收束方式
- 卷纲：各卷大体内容和卷末效果
- → 详见 [phase1-input.md](flows/phase1-input.md)

### Phase 2：黑箱生成
Agent 根据三项输入自主生成：
1. `00-世界观.md` — 完整世界观设定
2. `01-人物卡/` — 五类角色档案
3. `02-大纲/` — 六份大纲体系文件
4. `03-写作计划.json` — 进度跟踪
- → 详见 [phase2-planning.md](flows/phase2-planning.md)

### Phase 3：疯狂创作
- 三种写作模式：逐章串行 / 子Agent并行 / Agent Teams
- 每章执行：上下文加载 → 撰写(3000-5000字) → 去AI润色 → 生成记忆 → 触发阶段总结
- 全程无需用户确认
- → 详见 [phase3-writing.md](flows/phase3-writing.md)

### Phase 4：自动校验
- 字数/伏笔/时间线/人设/文风五项检查
- 不合格章节自动重写（最多3轮）
- → 详见 [phase4-validation.md](flows/phase4-validation.md)

---

## 八、上下文管理机制

详见 [context-management.md](guides/context-management.md)

### 三层记忆架构

| 层级 | 文件 | 大小 | 加载时机 |
|------|------|------|---------|
| L1 阶段总结 | `memory/phase-XX-summary.md` | 300-500字 | 每10章压缩一次，始终加载最新1份 |
| L2 章节记忆 | `memory/ch-XXX-memory.md` | 150-300字 | 每章生成，最多加载最近2份 |
| L3 上章全文 | 原始章节文件 | 3000-5000字 | 仅加载上1章，仅用于衔接段落 |

### Token 效率

```
全书上下文 = 阶段总结(~500字) + 近期记忆(~600字) + 上章全文(~4000字) ≈ 5,100字
```

| 章节数 | 旧方案（全量回读） | 新方案（记忆系统） | 节省 |
|--------|-------------------|-------------------|------|
| 10章 | ~40,000字 | ~4,500字 | 89% |
| 30章 | ~120,000字 | ~5,100字 | 96% |
| 50章 | ~200,000字 | ~5,500字 | 97% |

---

## 九、写作模式

| 模式 | 适用场景 | 机制 |
|------|---------|------|
| 逐章串行 | 短中篇(10-20章) | 主Agent自己逐章写，全程无中断 |
| 子Agent并行 | 中长篇(30-50章) | 分批派生子Agent，批次内串行、批次间并行 |
| Agent Teams | 复杂项目 | 多Agent协作，通过TaskList分配任务 |

并行模式下，上下文记忆文件确保跨批次衔接。

---

## 十、文风强制规范

### 杜绝
- AI模板化开篇、排比泛滥、空洞抒情、句式工整僵硬
- "此刻、见状、随即、不由得"等AI高频虚词
- 人物台词模板化、全员语气一致
- 解释剧情、点评人物、跳出叙事身份

### 执行
- 语言自然口语化，贴合人物身份
- 细节落地具象化，写动作有过程
- 节奏张弛有度，每章至少2个张力波峰
- 伏笔隐性铺垫，润物细无声
- 每章30%以上对话，每段对话有潜台词

---

## 十一、写作指南引用关系

### 从 SKILL.md 直接引用
- `context-management.md`

### 从 Phase 2 引用
- `character-building.md` / `character-template.md`
- `plot-structures.md` / `outline-template.md`
- `plot-control-dashboard.md`

### 从 Phase 3 引用
- `chapter-guide.md` / `chapter-template.md`
- `hook-techniques.md` / `dialogue-writing.md`
- `content-expansion.md` / `context-management.md`

### 独立参考
- `title-guide.md` — Phase 1 标题生成时按需加载

---

## 十二、常见问题

### Q: 创作中途断了怎么办？
A: 重新触发技能，Phase 0 会自动检测未完成项目并询问是否继续。从断点章节无缝续写。

### Q: 可以修改 Agent 生成的设定吗？
A: 可以。Phase 2 确认前可以要求修改任意设定文件，确认后也可以随时要求调整。

### Q: 每章字数不够怎么办？
A: Agent 内置字数检查脚本，低于3000字的章节会自动使用扩充技巧补充。

### Q: 如何切换写作模式？
A: Phase 2 确认后会询问选择写作模式。已开始创作后无法切换。

### Q: 不同平台有功能差异吗？
A: 核心功能完全一致。差异仅在于：Claude Code 支持 Agent Teams 模式，Codex 和 Trae 推荐使用逐章串行或子Agent并行模式。