# Chinese Novelist Skill

## 项目简介

`chinese-novelist` 是一款专为中文网络小说创作打造的 AI 技能，支持从零开始创作完整长篇小说。具备真人手写文风、沉浸式叙事、伏笔闭环等核心特点，适配悬疑、言情、奇幻、仙侠、科幻、历史、都市、末世、无限流、校园、权谋、甜宠、爽文等全品类小说创作。

### 核心特性

- **全流程创作**：世界观搭建 → 人物设定 → 大纲分卷 → 正文连载 → 细节补全 → 伏笔回收 → 结局收尾
- **真人手写文风**：拒绝 AI 流水线模板，强调自然流畅、有细节、有情绪、有烟火气
- **三层记忆系统**：L1 阶段总结 + L2 章节记忆 + L3 上章原文，节省 96% 上下文 Token
- **智能校验修复**：七维自动校验（字数/伏笔/时间线/人设/文风/能力路径/核心矛盾），不合格章节自动重写
- **三级修订模式**：支持设定生成后预修改、创作中途边改边写、完结后存量修改
- **章节评分系统**：多维度自动评估章节质量，提供优化建议
- **数据持久化**： SQLite 数据库存储项目数据，支持历史版本管理

---

## 快速开始

### 触发方式

在支持的平台中输入以下内容即可触发：

```
帮我写一部小说
```

### 创作流程

1. **提供五项核心输入**：
   - 开篇背景：故事发生的世界、时代、初始情境
   - 故事结局：故事最终走向和收束方式
   - 卷纲：大体内容划分和各卷/章结尾效果
   - 主角能力/修为提升路径：主角变强的方式、阶段、代价
   - 故事全局核心矛盾：贯穿全书的根本冲突/主题

2. **自动生成设定**：Agent 根据输入黑箱生成世界观、人物卡、大纲体系等全部设定文件

3. **选择写作模式**：逐章串行 / 子 Agent 并行 / Agent Teams

4. **自动创作**：全程无需干预，逐章输出正文

5. **自动校验**：完成后自动进行七维校验和修复

---

## 安装说明

### Claude Code

```bash
git clone https://github.com/lvyu-cmd/chinese-novelist-skill-master.git ~/.claude/skills/chinese-novelist
```

### Codex

```bash
cp -r chinese-novelist-skill-master ~/.codex/skills/chinese-novelist
```

### Trae

复制到 Trae 的 skills 目录即可，兼容标准 `SKILL.md` 格式。

---

## 项目结构

```
chinese-novelist/
├── SKILL.md                          # 主文件（触发+核心规则+修订模式入口）
├── agents/
│   └── openai.yaml                   # Codex/Trae UI 元数据
├── assets/                           # 截图素材
├── data/
│   └── novel.db                      # SQLite 数据库（项目数据持久化）
├── revision-rules.yaml               # 三级修订约束规则配置
├── references/
│   ├── architecture.md               # 架构文档
│   ├── flows/                        # 流程文档
│   │   ├── phase0-initialization.md  # 初始化与偏好加载
│   │   ├── phase1-input.md           # 五项核心输入
│   │   ├── phase2-planning.md        # 黑箱生成设定
│   │   ├── phase3-writing.md         # 疯狂创作
│   │   ├── phase4-validation.md      # 自动校验与修复
│   │   ├── revision-mode.md          # 三级修订流程
│   │   └── shared-infrastructure.md # 共享机制
│   └── guides/                       # 写作指南
│       ├── chapter-guide.md
│       ├── chapter-template.md
│       ├── character-building.md
│       ├── character-template.md
│       ├── content-expansion.md
│       ├── context-management.md     # 三层记忆架构
│       ├── dialogue-writing.md
│       ├── hook-techniques.md
│       ├── narrative-craft.md        # 叙事技巧指南
│       ├── outline-template.md
│       ├── pacing-control.md         # 节奏控制指南
│       ├── plot-control-dashboard.md
│       ├── plot-structures.md
│       └── title-guide.md
└── scripts/                          # 校验与管理脚本
    ├── check_chapter_wordcount.py    # 字数检查
    ├── check_ai_style.py             # AI风格检测
    ├── check_foreshadowing.py        # 伏笔检查
    ├── check_project_integrity.py    # 项目完整性检查
    ├── db_manager.py                 # 数据库管理
    ├── score_chapter.py              # 章节评分
    ├── suggest_polish.py             # 优化建议
    ├── validate_all.py               # 全量校验
    └── common.py                     # 公共模块
```

---

## 支持命令

```
帮我写一部小说                          # 新建创作项目
继续上次的创作                          # 从中断处续写
帮我修改第X章的文风                      # 修改指定章节文风
帮我看看主角的人设，然后把他改得更冷酷一些  # 修改人设
帮我检查一下世界观有没有逻辑冲突           # 设定校验
帮我调整第2卷的大纲                      # 修改大纲
```

---

## 校验脚本说明

| 脚本 | 功能 |
|------|------|
| `check_chapter_wordcount.py` | 检查章节字数是否达标（3000-5000字） |
| `check_ai_style.py` | 检测并清理 AI 风格痕迹 |
| `check_foreshadowing.py` | 检查伏笔铺设与回收完整性 |
| `check_project_integrity.py` | 检查项目文件结构完整性 |
| `score_chapter.py` | 多维度章节质量评分 |
| `suggest_polish.py` | 生成章节优化建议 |
| `validate_all.py` | 执行全部校验项 |

---

## 写作模式

| 模式 | 适用场景 | 说明 |
|------|---------|------|
| 逐章串行 | 10-20章短中篇 | 主 Agent 自己逐章写，全程无中断 |
| 子 Agent 并行 | 30-50章中长篇 | 分批派生子 Agent，批次内串行、批次间并行 |
| Agent Teams | 复杂项目 | 多 Agent 协作，通过 TaskList 分配任务 |

---

## 平台兼容性

| 平台 | 支持模式 | 特殊说明 |
|------|---------|---------|
| Claude Code | 逐章串行 / 子 Agent 并行 / Agent Teams | 支持完整功能 |
| Codex | 逐章串行 / 子 Agent 并行 | 推荐中短篇创作 |
| Trae | 逐章串行 / 子 Agent 并行 | 推荐中短篇创作 |

---

## 许可证

MIT License
