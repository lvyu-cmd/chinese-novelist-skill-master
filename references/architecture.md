# Chinese Novelist Skill — 使用说明与架构文档

> `chinese-novelist` 技能的完整使用指南，适配 Codex、Trae、Claude Code 三大平台。

---

## 一、平台安装

### Claude Code

```bash
# 方式1：克隆到 skills 目录
git clone https://github.com/lvyu-cmd/chinese-novelist-skill-master.git ~/.claude/skills/chinese-novelist

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

Agent 弹出控制台后，按引导回答五个问题即可：

1. **开篇背景**：你想写什么世界的故事？
2. **故事结局**：故事最终怎么收尾？
3. **卷纲**：打算写多少章？各卷大概讲什么？
4. **能力路径**：主角怎么变强？
5. **核心矛盾**：贯穿全书的根本冲突是什么？

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
能力路径：混合型（实战经验积累 + 科技装备改造）
核心矛盾：生存危机（人类存亡 vs 变异体进化）
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

### 修订模式（新增）

```
帮我检查一下世界观有没有逻辑冲突
帮我调整第2卷的大纲
帮我润色第5章的文风
```

设定固化后随时可触发修订模式，详见下方「修订模式」章节。

---

## 三、用户交互流程

```
用户输入触发词
      ↓
Phase 0: 控制台弹出 → 加载偏好 → 检测中断
      ↓
Phase 1: 五个问题
  Q1: 开篇背景（自由描述或选题材）
  Q2: 故事结局（自由描述或选类型）
  Q3: 卷纲（选章节数或自定义）
  Q4: 能力路径（主角变强方式）
  Q5: 核心矛盾（贯穿全书的根本冲突）
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
Phase 4: 自动校验（字数/伏笔/时间线/人设/文风/能力路径/核心矛盾）
  → 输出完成报告
      ↓
修订模式（随时可用，独立触发）
  → 三级修订：设定 → 大纲 → 正文
```

---

## 四、设计理念

用户只需提供五项核心输入，Agent 黑箱生成全部设定：

```
用户输入（5项）              Agent 黑箱生成（全部）
┌───────────────┐      ┌──────────────────────────┐
│ 1. 开篇背景    │      │ 世界观（锚定能力路径）     │
│ 2. 故事结局    │      │ 五类角色档案              │
│ 3. 卷纲        │ ───→ │ 六份大纲体系文件           │
│ 4. 能力路径    │      │ 伏笔布局（依托核心矛盾）   │
│ 5. 核心矛盾    │      │ 写作计划 JSON（锁定约束）  │
└───────────────┘      │ 上下文记忆系统（自动维护）  │
                       └──────────────────────────┘
```

---

## 五、技能文件结构

```
chinese-novelist/
├── SKILL.md                          # 主文件（触发+核心规则+修订模式入口）
├── agents/
│   └── openai.yaml                   # Codex/Trae UI 元数据
├── assets/                           # 截图素材
├── revision-rules.yaml               # 三级修订约束规则配置
├── references/
│   ├── architecture.md               # 本文档
│   ├── flows/                        # 流程文档（Agent 执行指令）
│   │   ├── phase0-initialization.md
│   │   ├── phase1-input.md           # 五项核心输入
│   │   ├── phase2-planning.md        # 黑箱生成（绑定能力路径/核心矛盾）
│   │   ├── phase3-writing.md         # 疯狂创作+断点快照
│   │   ├── phase4-validation.md      # 七维校验（新增能力路径/核心矛盾）
│   │   ├── shared-infrastructure.md  # 共享机制（含顶层约束说明）
│   │   └── revision-mode.md          # 三级修订完整流程
│   └── guides/                       # 写作指南（按需加载）
│       ├── chapter-guide.md
│       ├── chapter-template.md
│       ├── character-building.md
│       ├── character-template.md
│       ├── content-expansion.md
│       ├── context-management.md     # 三层记忆架构+修订沿用策略
│       ├── dialogue-writing.md
│       ├── hook-techniques.md
│       ├── outline-template.md
│       ├── plot-control-dashboard.md
│       ├── plot-structures.md
│       └── title-guide.md
├── scripts/
│   └── check_chapter_wordcount.py    # 字数检查脚本
└── .git/
```

---

## 六、项目文件结构（创作产出）

```
{项目文件夹}/
├── 00-世界观.md            # 力量体系/势力/世界禁忌/能力底层规则
├── 01-人物卡/              # 五类角色档案
│   ├── 主角.md
│   ├── 重要角色.md
│   ├── 次要角色.md
│   ├── 重要反派.md
│   └── 次要反派.md
├── 02-大纲/                # 六份大纲体系（绑定主线矛盾+能力路径）
│   ├── 卷纲.md
│   ├── 时间线.md
│   ├── 伏笔布局.md
│   ├── 进阶条件.md
│   ├── 成长体系.md
│   └── 境界功法.md
├── memory/                 # 上下文记忆系统（自动维护）
│   ├── phase-1-summary.md
│   ├── ch-001-memory.md
│   ├── snapshot.json       # 断点快照
│   └── ...
├── 03-写作计划.json        # 进度跟踪（含五项顶层约束锁定）
├── 第01章-xxx.md
└── ...
```

---

## 七、四阶段执行流程

### Phase 0：初始化
- 输出标准化创作控制台
- 加载用户偏好（`user-preferences.json`）
- 检测未完成项目（中断续写）

### Phase 1：五项核心输入
- 开篇背景：世界/时代/初始情境
- 故事结局：最终走向和收束方式
- 卷纲：各卷大体内容和卷末效果
- 能力路径：主角变强的方式、阶段、代价
- 核心矛盾：贯穿全书的根本冲突/主题
- → 详见 [phase1-input.md](flows/phase1-input.md)

### Phase 2：黑箱生成
Agent 根据五项输入自主生成：
1. `00-世界观.md` — 完整世界观设定（锚定能力路径）
2. `01-人物卡/` — 五类角色档案
3. `02-大纲/` — 六份大纲体系文件（伏笔依托核心矛盾，成长依托能力路径）
4. `03-写作计划.json` — 进度跟踪（锁定五项顶层约束）
- → 详见 [phase2-planning.md](flows/phase2-planning.md)

### Phase 3：疯狂创作
- 三种写作模式：逐章串行 / 子Agent并行 / Agent Teams
- 每章执行：上下文加载 → 撰写(3000-5000字) → 去AI润色 → 生成记忆 → 触发阶段总结 → 留存断点快照
- 全程无需用户确认
- → 详见 [phase3-writing.md](flows/phase3-writing.md)

### Phase 4：自动校验
- 七维校验：字数/伏笔/时间线/人设/文风/能力路径一致性/核心矛盾贯穿性
- 不合格章节自动重写（最多3轮）
- → 详见 [phase4-validation.md](flows/phase4-validation.md)

---

## 八、修订模式（V2新增）

独立于主流水线的三级存量修订模块。Phase2设定固化后永久解锁。

### 三级修订结构

| 模式 | 层级 | 范围 | 功能 |
|------|------|------|------|
| 模式一 | 顶层 | 00-世界观 + 01-人物卡 | 设定扫描、逻辑冲突检测、改写 |
| 模式二 | 中层 | 02-大纲 六份文件 | 大纲违规检测、章节增删/时间线调整 |
| 模式三 | 底层 | 已产出章节 | 分支1：剧情结构性修改 / 分支2：文本质感润色 |

### 三类适用场景

1. **设定生成后预修改**：Phase 2 完成后、Phase 3 开始前，用户可先修订设定
2. **创作中途边改边写**：Phase 3 进行中，随时触发修订，修订后自动续写
3. **完结后存量修改**：Phase 4 完成后，对已完成小说进行设定/大纲/正文修订

### 核心约束

- 强制自上而下执行：基础设定 → 大纲 → 正文，禁止逆向
- 下层修订不得反向篡改上层基础设定
- 所有修订强制核验能力路径、核心矛盾一致性
- 修订完成后自动同步记忆索引，无需重启会话

→ 详见 [revision-mode.md](flows/revision-mode.md)

---

## 九、上下文管理机制

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

修订模式沿用同一套记忆架构，不额外消耗Token。

---

## 十、写作模式

| 模式 | 适用场景 | 机制 |
|------|---------|------|
| 逐章串行 | 短中篇(10-20章) | 主Agent自己逐章写，全程无中断 |
| 子Agent并行 | 中长篇(30-50章) | 分批派生子Agent，批次内串行、批次间并行 |
| Agent Teams | 复杂项目 | 多Agent协作，通过TaskList分配任务 |

并行模式下，上下文记忆文件确保跨批次衔接。

---

## 十一、文风强制规范

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

## 十二、写作指南引用关系

### 从 SKILL.md 直接引用
- `context-management.md`

### 从 Phase 1 引用
- （无 guides 引用，仅使用 AskUserQuestion）

### 从 Phase 2 引用
- `character-building.md` / `character-template.md`
- `plot-structures.md` / `outline-template.md`
- `plot-control-dashboard.md`

### 从 Phase 3 引用
- `chapter-guide.md` / `chapter-template.md`
- `hook-techniques.md` / `dialogue-writing.md`
- `content-expansion.md` / `context-management.md`

### 从修订模式引用
- `revision-rules.yaml`（约束规则配置）
- `context-management.md`（修订沿用记忆策略）
- Phase 4 校验标准（正文修订复用）

### 独立参考
- `title-guide.md` — Phase 1 标题生成时按需加载

---

## 十三、常见问题

### Q: 创作中途断了怎么办？
A: 重新触发技能，Phase 0 会自动检测未完成项目并询问是否继续。从断点章节无缝续写。

### Q: 可以修改 Agent 生成的设定吗？
A: 可以。Phase 2 确认前可以要求修改任意设定文件，确认后也可随时触发修订模式进行三级修订。

### Q: 每章字数不够怎么办？
A: Agent 内置字数检查脚本，低于3000字的章节会自动使用扩充技巧补充。

### Q: 如何切换写作模式？
A: Phase 2 确认后会询问选择写作模式。已开始创作后无法切换。

### Q: 不同平台有功能差异吗？
A: 核心功能完全一致。差异仅在于：Claude Code 支持 Agent Teams 模式和批量修订，Codex 和 Trae 推荐使用逐章串行或子Agent并行模式。

### Q: 什么时候可以用修订模式？
A: Phase 2 设定文件全部生成完毕后即可使用，覆盖创作全生命周期（设定后预修改、中途边改边写、完结后存量修改）。

### Q: 修订模式会破坏已完成的章节吗？
A: 不会。已定稿章节原文永久锁定，修订仅同步更新记忆索引和伏笔台账。未生成章节会套用修订后的新约束。

### Q: 修订模式的层级顺序可以跳过吗？
A: 不可以。强制自上而下执行（设定→大纲→正文），避免层级逻辑崩坏。如需同时修改多层级，按顺序逐级执行。
