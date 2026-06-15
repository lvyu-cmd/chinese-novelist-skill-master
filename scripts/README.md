# Chinese Novelist Skill - 脚本工具集

自动化校验脚本，供Agent在创作各阶段调用。

## 脚本清单

| 脚本 | 功能 | 调用时机 |
|------|------|---------|
| common.py | 公共模块(编码/Markdown/字数/计划读取) | 被其他脚本import |
| check_chapter_wordcount.py | 章节字数检查 | Phase3每章写完后 / Phase4校验 |
| check_ai_style.py | AI废词+文风质量扫描 | Phase3润色后 / Phase4文风校验 |
| check_foreshadowing.py | 伏笔追踪表完整性校验 | Phase4伏笔闭环 / 修订模式二 |
| check_project_integrity.py | 项目完整性+顶层约束一致性 | Phase2设定后 / 修订入口检查 |
| alidate_all.py | 全流程一键校验(串联以上) | Phase4完成后 / 修订出口检查 |

所有脚本支持 --json 输出供程序化读取。

## 详细用法

### check_chapter_wordcount.py
`ash
python scripts/check_chapter_wordcount.py 第01章-xxx.md        # 单章
python scripts/check_chapter_wordcount.py --all <项目目录>      # 批量
python scripts/check_chapter_wordcount.py --all <目录> 3500     # 自定义阈值
python scripts/check_chapter_wordcount.py --json --all <目录>   # JSON输出
`

### check_ai_style.py
`ash
python scripts/check_ai_style.py 第01章-xxx.md                 # 单章扫描
python scripts/check_ai_style.py --all <项目目录>               # 批量
python scripts/check_ai_style.py --all --threshold 3 <目录>     # 自定义废词阈值(默认5)
`
扫描: AI废词(4类词库) / "的"字密度 / 句式多样性(连续同主语+超长句) / 展示vs讲述

### check_foreshadowing.py
`ash
python scripts/check_foreshadowing.py <项目目录>               # 校验伏笔
python scripts/check_foreshadowing.py --json <项目目录>         # JSON
`
检查: 孤儿伏笔(预计揭晓但状态仍活跃) / 状态统计

### check_project_integrity.py
`ash
python scripts/check_project_integrity.py <项目目录>           # 完整性校验
python scripts/check_project_integrity.py --json <项目目录>     # JSON
`
检查: 14份设定文件 / JSON结构(V2) / topLevelConstraints / memory目录

### validate_all.py
`ash
python scripts/validate_all.py <项目目录>                      # 全量校验
python scripts/validate_all.py --json <项目目录>                # JSON
python scripts/validate_all.py <目录> --min-words 3500 --threshold 3
`
串联四模块，输出总评(pass/warn/fail)。