# Chinese Novelist Skill — 脚本工具集

项目内置的自动化校验脚本，供 Agent 在创作各阶段调用。

## 脚本清单

| 脚本 | 功能 | 调用时机 |
|------|------|---------|
| `check_chapter_wordcount.py` | 章节字数检查 | Phase 3 每章写完后 / Phase 4 校验 |
| `check_ai_style.py` | AI废词 + 文风质量扫描 | Phase 3 深度润色后 / Phase 4 文风校验 |
| `check_foreshadowing.py` | 伏笔追踪表完整性校验 | Phase 4 伏笔闭环检查 / 修订模式模式二 |
| `check_project_integrity.py` | 项目完整性 + 顶层约束一致性 | Phase 2 设定生成后 / 修订模式入口检查 |
| `validate_all.py` | 全流程一键校验（串联以上四个） | Phase 4 完成后 / 修订模式出口检查 |

## 详细用法

### check_chapter_wordcount.py — 字数检查

```bash
# 检查单个章节
python scripts/check_chapter_wordcount.py <项目目录>/第01章-xxx.md

# 检查所有章节
python scripts/check_chapter_wordcount.py --all <项目目录>

# 自定义最小字数
python scripts/check_chapter_wordcount.py <项目目录>/第01章-xxx.md 3500

# JSON输出（供Agent程序化读取）
python scripts/check_chapter_wordcount.py --json --all <项目目录>
```

### check_ai_style.py — AI废词 + 文风扫描

```bash
# 扫描单章
python scripts/check_ai_style.py <项目目录>/第01章-xxx.md

# 批量扫描所有章节
python scripts/check_ai_style.py --all <项目目录>

# 自定义废词阈值（默认5次）
python scripts/check_ai_style.py --all <项目目录> --threshold 3

# JSON输出
python scripts/check_ai_style.py --all --json <项目目录>
```

扫描项：
- AI高频废词（此刻、见状、不由得等，分4类词库）
- "的"字密度（单句超过2个"的"标记为过载）
- 句式多样性（连续同主语、超长句检测）
- 展示vs讲述（直接陈述情绪/性格的句式标记）

### check_foreshadowing.py — 伏笔校验

```bash
# 校验伏笔完整性
python scripts/check_foreshadowing.py <项目目录>

# JSON输出
python scripts/check_foreshadowing.py --json <项目目录>
```

检查项：
- 孤儿伏笔（预计揭晓章节已完成但状态仍为活跃）
- 伏笔状态统计（按状态/类型分布）
- 支持Markdown表格和列表两种格式解析

### check_project_integrity.py — 项目完整性

```bash
# 校验项目完整性
python scripts/check_project_integrity.py <项目目录>

# JSON输出
python scripts/check_project_integrity.py --json <项目目录>
```

检查项：
- 14份必需设定文件是否存在
- 03-写作计划.json 结构完整性（V2格式、字段枚举、章节号连续性）
- topLevelConstraints 五项必填项是否已填写
- memory/ 目录结构（阶段总结、章节记忆、快照）
- 已完成章节文件是否存在

### validate_all.py — 全流程一键校验

```bash
# 全量校验
python scripts/validate_all.py <项目目录>

# JSON输出
python scripts/validate_all.py --json <项目目录>

# 自定义参数
python scripts/validate_all.py <项目目录> --min-words 3500 --threshold 3
```

串联四个子模块，输出统一报告，含总评（pass/warn/fail）。
