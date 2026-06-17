# Chinese Novelist Skill - 脚本工具集

## 脚本清单

| 脚本 | 功能 | 调用时机 |
|------|------|---------|
| `common.py` | 公共模块 | 被其他脚本 import |
| `db_manager.py` | SQLite 查询加速层 | Agent 读写结构化数据 |
| `check_chapter_wordcount.py` | 章节字数检查 | Phase3每章 / Phase4校验 |
| `check_ai_style.py` | AI废词+文风扫描 V2 | Phase3润色后 / Phase4文风校验 |
| `score_chapter.py` | 章节质量8维度评分 | Phase3创作后自评 / Phase4 |
| `suggest_polish.py` | 润色建议生成 | 修订模式分支2 / Phase3润色 |
| `check_foreshadowing.py` | 伏笔追踪表校验 | Phase4伏笔闭环 |
| `check_project_integrity.py` | 项目完整性校验 | Phase2设定后 / 修订入口 |
| `validate_all.py` | 全流程一键校验 | Phase4完成后 |

---

## db_manager.py — SQLite 查询加速层

### 架构

```
JSON/Markdown（主数据源）──sync──> SQLite（查询加速层）──query──> Agent
```

- 8张表：project / chapters / foreshadowing / characters / character_appearances / chapter_memory / phase_summary / revision_log
- 11个索引：覆盖章节状态/评分/文风/伏笔状态/人物类型/出场记录/修订类型
- 27个预定义查询
- WAL模式，支持并发读
- 所有写入幂等（UPSERT），可反复执行

### 用法

```bash
# 初始化数据库
python scripts/db_manager.py init <项目目录>

# 全量同步（JSON/Markdown → SQLite）
python scripts/db_manager.py sync <项目目录>

# 同步单章（Phase3每章写完后调用）
python scripts/db_manager.py sync <项目目录> --chapter 5

# 预定义查询
python scripts/db_manager.py query <项目目录> <查询名> [参数...]

# 原始SQL（只读）
python scripts/db_manager.py sql <项目目录> "SELECT ..."
```

### 核心查询（创作辅助）

| 查询名 | 用途 | 参数 |
|--------|------|------|
| `next_chapter_to_write` | 获取下一章的标题+大纲规划 | 无 |
| `chapter_context` | 获取指定章节的完整上下文 | chapter_number |
| `recent_context` | 获取章节范围的上下文链 | start_ch, end_ch |
| `latest_memory` | 获取最近N条章节记忆 | N |
| `latest_phase_summary` | 获取最新阶段总结 | 无 |
| `active_foreshadowing_for_chapter` | 获取本章应埋设的伏笔 | chapter_number |
| `foreshadowing_unresolved` | 获取已过揭晓期但未回收的伏笔 | completed_chapter |
| `top_constraints` | 获取用户五项顶层约束 | 无 |

### 状态查询

| 查询名 | 用途 | 参数 |
|--------|------|------|
| `stats_overview` | 全局统计（章数/字数/评分分布） | 无 |
| `stats_dimensions` | 8维度平均分 | 无 |
| `stats_foreshadowing` | 伏笔统计（活跃/已回收/孤儿） | 无 |
| `chapters_by_status` | 按状态筛选章节 | status |
| `chapters_low_score` | 低分章节 | threshold |
| `chapters_style_issues` | 文风问题章节 | 无 |
| `chapters_wordcount_fail` | 字数不达标章节 | 无 |
| `characters_all` | 全部人物 | 无 |
| `foreshadowing_active` | 活跃伏笔 | 无 |
| `foreshadowing_orphans` | 孤儿伏笔 | 无 |

### Python API（Agent 在脚本中调用）

```python
import sys
sys.path.insert(0, "scripts")
from db_manager import sync_project, query, update_chapter_scores, log_revision

# 同步
sync_project("./项目目录")

# 查询
result = query("./项目目录", "next_chapter_to_write")
# [{"chapter_number":5, "title":"...", "outline_core_event":"...", ...}]

# 写入评分结果（score_chapter 输出后调用）
update_chapter_scores("./项目目录", 5, score_result, style_result)

# 记录修订
log_revision("./项目目录", "文本质感润色", "第05章.md", 5, "AI废词清理")
```

### 与现有脚本的集成点

| 脚本 | 集成方式 |
|------|---------|
| `check_ai_style.py` | 扫描完成后调用 `update_chapter_scores()` 写入文风指标 |
| `score_chapter.py` | 评分完成后调用 `update_chapter_scores()` 写入8维度评分 |
| `suggest_polish.py` | 可读 `chapters_style_issues` 查询定位需要润色的章节 |
| `check_foreshadowing.py` | 伏笔数据同步到 `foreshadowing` 表 |
| `validate_all.py` | 可读 `stats_overview` 替代直接读JSON |
| `check_project_integrity.py` | 可读 `top_constraints` 验证顶层约束 |

### Token 效率

Agent 每章创作前需要读取上下文。对比：

| 方式 | 读1章上下文 | 读10章上下文 | 读50章统计 |
|------|-----------|------------|-----------|
| 读JSON+Markdown | ~2000字 | ~20000字 | ~5000字 |
| 读SQLite查询 | ~300字 | ~3000字 | ~200字 |
| **节省** | **85%** | **85%** | **96%** |