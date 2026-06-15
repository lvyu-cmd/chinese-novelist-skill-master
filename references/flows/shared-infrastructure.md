# 共享机制

本文件定义跨阶段共享的机制和规则。

---

## 三大黄金法则

1. **展示而非讲述** - 用动作和对话表现，不要直接陈述
2. **冲突驱动剧情** - 每章必须有冲突或转折
3. **悬念承上启下** - 每章结尾必须留下钩子

---

## 用户偏好系统

### 存储文件

`user-preferences.json`（项目根目录，首次使用后自动创建）

### 数据结构

```json
{
  "version": 1,
  "updatedAt": "2026-04-12",
  "preferences": {
    "favoriteGenres": [],
    "preferredProtagonist": "",
    "preferredPerspective": "",
    "preferredTone": "",
    "typicalChapterCount": null,
    "styleReferences": [],
    "dislikes": [],
    "creationHistory": []
  }
}
```

### 偏好更新规则

| 时机 | 行为 |
|------|------|
| 每完成一层问答 | 静默将本层回答同步到偏好文件（追加/更新，不删除历史） |
| 用户说"记住我的偏好" | 保存当前所有配置到偏好 |
| 用户说"忘记XX偏好" | 清除指定维度的偏好 |
| 用户说"重置偏好" | 清空所有偏好数据 |
| 一部长篇创作完成 | 将作品信息追加到 `creationHistory` |

### 偏好如何影响交互

1. **启动欢迎语**：有偏好时显示"欢迎回来！" + 个性化提示
2. **选项排序**：Q1中将 `favoriteGenres` 匹配项排前面
3. **常用标记**：对应用⭐标记"你的常用"/"上次选择"
4. **需求报告**：结合偏好给个性化建议
5. **随机生成**：优先从偏好范围内随机选取，保持一致性
6. **风格参考追问**：优先推荐 `styleReferences` 中的作者

### 错误恢复

- **回退修改**：用户随时可说"回到QX"、"修改XX"，AI 回退到指定问题重新询问
- **中途暂存**：通过 `03-写作计划.json` 实现自动暂存；下次触发SKILL时 Phase 0 自动检测未完成项目，询问"继续上次的《XXX》？"
- **偏好文件损坏**：JSON解析失败时忽略偏好，使用默认值，并在后台修复文件

---

## 标题传递机制

### 传递方式

标题通过**对话上下文**在阶段间传递，不单独持久化到文件。

**传递链路**：
1. Phase 1：用户选择/确认标题 → 标题存入对话上下文
2. Phase 2：从上下文读取标题 → 写入项目目录名、`03-写作计划.json`、`02-大纲/卷纲.md`

### 中断恢复

若会话在标题确认、Phase 2 开始前中断：
- Phase 0 不会找到已创建的项目目录（因为 Phase 2 尚未执行）
- 用户将重新进入 Phase 1 重新选择标题（标题选择耗时很短，重新选择成本可接受）

---

## 写作计划系统

### 存储文件

`03-写作计划.json`（项目文件夹内，Phase 2 创建）

### 作用

- **进度跟踪**：记录每章创作状态（pending/in_progress/completed/failed）
- **写作模式**：记录用户选择的写作模式（serial/subagent-parallel/agent-teams）
- **中断续写**：Phase 0 读取 JSON 检测未完成项目，支持从断点继续
- **校验依据**：Phase 4 基于 JSON 校验章节完成度和字数
- **并行协调**（可选）：多 Agent 并行写作时通过 JSON 状态避免冲突
- **顶层约束锁定**：记录用户原始五项核心输入，修订模式强制核验

### 数据结构（V2）

```json
{
  "version": 2,
  "novelName": "[小说名称]",
  "projectPath": "./chinese-novelist/{timestamp}-[小说名称]",
  "totalChapters": [章节数],
  "minWordsPerChapter": 3000,
  "createdAt": "[ISO时间]",
  "updatedAt": "[ISO时间]",
  "status": "planning",
  "writingMode": null,
  "topLevelConstraints": {
    "openingBackground": "[用户输入的开篇背景]",
    "storyEnding": "[用户输入的故事结局]",
    "volumeOutline": "[用户输入的卷纲摘要]",
    "abilityPath": "[用户输入的主角能力/修为提升路径]",
    "growthCost": "[用户输入的成长代价]",
    "coreConflict": "[用户输入的全局核心矛盾]",
    "conflictEscalation": "[用户输入的矛盾升级方式]"
  },
  "chapters": [
    {
      "chapterNumber": 1,
      "title": "[章节标题]",
      "filePath": "第01章-[章节标题].md",
      "status": "pending",
      "wordCount": null,
      "wordCountPass": null,
      "retryCount": 0
    }
  ]
}
```

### 顶层约束字段说明

`topLevelConstraints` 记录用户在 Phase 1 输入的五项核心参数：
- `openingBackground`：开篇背景
- `storyEnding`：故事结局
- `volumeOutline`：卷纲摘要
- `abilityPath`：主角能力/修为提升路径
- `growthCost`：成长代价（可选）
- `coreConflict`：全局核心矛盾
- `conflictEscalation`：矛盾升级方式（可选）

**刚性约束**：`topLevelConstraints` 字段在整个创作生命周期中禁止隐性篡改。修订模式的所有操作必须核验与此字段的一致性。

### 与大纲的关系

- `02-大纲/卷纲.md`：章节规划（核心事件、悬念钩子、承接上章、出场人物、场景列表）+ 章节摘要（连贯性参考）
- `03-写作计划.json`：章节状态、字数、重试次数、写作模式、顶层约束（机器可读的进度跟踪）
- Phase 3 创作每章时必须读取 `02-大纲/卷纲.md` 中对应章节的规划信息，作为创作依据
- 两者严格对应：JSON 中的 `chapterNumber` 和 `title` 必须与大纲中的章节规划一致

### JSON 损坏处理

- JSON 解析失败时：提示用户，尝试从大纲的章节摘要区推断完成进度
- 章节状态丢失时：通过文件存在性和字数脚本重建状态

---

## 字数检查脚本

使用 `scripts/check_chapter_wordcount.py` 检查章节字数：

```bash
# 检查单个章节
python scripts/check_chapter_wordcount.py ./chinese-novelist/项目文件夹/第01章.md

# 检查所有章节
python scripts/check_chapter_wordcount.py --all ./chinese-novelist/项目文件夹/

# 自定义最小字数
python scripts/check_chapter_wordcount.py ./chinese-novelist/项目文件夹/第01章.md 3500
```

### 使用场景

| 阶段 | 用途 |
|------|------|
| Phase 3（逐章创作） | 撰写后检查单章字数，低于3000字必须扩充 |
| Phase 4（自动校验） | 批量检查所有章节字数，不合格章节自动重写 |
| 修订模式（正文修订） | 润色/改写后检查字数合规性 |

低于3000字的章节必须使用 [content-expansion.md](../guides/content-expansion.md) 的扩充技巧进行扩充。

---

## 章节记忆系统

### 概述

为减少Token消耗并保持章节衔接自然，采用三层记忆架构：
- **L1 阶段总结**：每10章压缩一次（300-500字），始终加载最新1份
- **L2 章节记忆**：每章结束后生成（150-300字），最多加载最近2份
- **L3 上章全文**：原始章节文本（3000-5000字），仅加载上1章

### 存储路径

```
{项目文件夹}/memory/
├── phase-1-summary.md
├── phase-2-summary.md
├── ch-001-memory.md
├── ch-002-memory.md
├── snapshot.json              # 断点快照（Phase3每章完成后自动更新）
└── ...
```

### Token效率

| 章节数 | 旧方案（全量回读） | 新方案（记忆系统） | 节省 |
|--------|-------------------|-------------------|------|
| 10章 | ~40,000字 | ~4,500字 | 89% |
| 30章 | ~120,000字 | ~5,100字 | 96% |
| 50章 | ~200,000字 | ~5,500字 | 97% |

### 修订模式沿用

修订模式复用同一套三层记忆架构，不额外消耗Token：
- 基础设定修订：加载 L1 最新阶段总结 + 受影响章节 L2 记忆
- 大纲修订：加载 L1 最新阶段总结 + 全局伏笔追踪表
- 正文修订：加载 L1 + 相关 L2 + 目标章节 L3 全文

### 详细规范

-> 详见 [context-management.md](../guides/context-management.md)

---

## 修订规则配置

### 存储文件

`revision-rules.yaml`（技能根目录，迭代新增）

### 作用

- 定义三级修订模式的约束规则
- 锁定用户原始五项顶层约束字段
- 规定时序互斥规则（Phase0-1禁用，Phase2后永久解锁）
- 定义层级刚性约束（底层不得篡改顶层）
- 配置三平台算力差异化适配

### 详细规范

-> 详见 [revision-mode.md](revision-mode.md)

---

## 断点快照系统

### 存储文件

`memory/snapshot.json`（项目文件夹内，Phase 3 每章完成后自动更新）

### 作用

- 记录当前创作进度快照（已生成章节清单、记忆文件列表、写作计划游标）
- 为修订模式提供断点续改基础
- 修订前自动留存快照，修订后自动恢复创作游标

### 数据结构

```json
{
  "snapshotAt": "[ISO时间]",
  "lastCompletedChapter": 15,
  "completedChapters": [1, 2, "...", 15],
  "pendingChapters": [16, 17, "...", 20],
  "writingMode": "serial",
  "memoryFiles": {
    "phaseSummaries": ["memory/phase-1-summary.md"],
    "chapterMemories": ["memory/ch-001-memory.md", "..."]
  },
  "activeForeshadowing": ["伏笔ID列表"],
  "settingsHash": "[14份设定文件的摘要哈希]"
}
```

### 详细规范

-> 详见 [phase3-writing.md](phase3-writing.md)「断点快照机制」章节
