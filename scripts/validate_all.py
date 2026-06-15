#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全流程一键校验脚本
串联字数检查 + AI废词扫描 + 伏笔校验 + 项目完整性校验，输出统一报告。

用法:
  全量校验:     python validate_all.py <项目目录>
  输出JSON:     python validate_all.py --json <项目目录>
  自定义字数:   python validate_all.py <项目目录> --min-words 3500
  自定义废词:   python validate_all.py <项目目录> --threshold 3
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 导入同目录下的子模块
sys.path.insert(0, str(Path(__file__).parent))
from check_chapter_wordcount import check_all as wc_check_all, count_chinese_chars
from check_ai_style import scan_all as style_scan_all
from check_foreshadowing import find_foreshadowing_file, parse_foreshadowing_table, get_completed_chapters, check_orphans, check_stats
from check_project_integrity import validate_project as integrity_validate


def run_full_validation(project_dir: str, min_words: int = 3000, threshold: int = 5, json_out: bool = False):
    pdir = Path(project_dir)
    if not pdir.exists():
        print(f"错误: 项目目录不存在 - {project_dir}")
        return

    # 1. 字数检查
    wc_results = wc_check_all(str(pdir), min_words=min_words)
    wc_passed = sum(1 for r in wc_results if r.get("status") == "pass")
    wc_failed = sum(1 for r in wc_results if r.get("status") == "fail")
    wc_total_words = sum(r.get("chinese_count", 0) for r in wc_results if r.get("exists"))

    # 2. AI废词扫描
    style_results = style_scan_all(str(pdir), threshold=threshold)
    style_pass = sum(1 for r in style_results if r.get("grade") == "pass")
    style_warn = sum(1 for r in style_results if r.get("grade") == "warn")
    style_fail = sum(1 for r in style_results if r.get("grade") == "fail")

    # 3. 伏笔校验
    fs_file = find_foreshadowing_file(pdir)
    fs_entries = []
    fs_orphans = []
    fs_stats = {}
    if fs_file:
        fs_entries = parse_foreshadowing_table(fs_file)
        completed = get_completed_chapters(pdir)
        fs_orphans = check_orphans(fs_entries, completed)
        fs_stats = check_stats(fs_entries)

    # 4. 项目完整性（捕获输出）
    integrity_result = None
    integrity_errors = 0
    integrity_warnings = 0
    plan_file = pdir / "03-写作计划.json"
    if plan_file.exists():
        try:
            import io as _io
            from contextlib import redirect_stdout
            buf = _io.StringIO()
            # 直接调用内部函数获取结果
            from check_project_integrity import (
                check_required_files, check_json_structure,
                check_top_level_constraints, check_memory_dir, check_chapter_files
            )
            import json as _json
            missing = check_required_files(pdir)
            json_check = check_json_structure(pdir)
            tlc_check = check_top_level_constraints(pdir)
            memory_check = check_memory_dir(pdir)

            chapter_file_check = {"missing_required_files": [], "wordcount_suspects": []}
            if json_check.get("exists") and not json_check.get("errors"):
                try:
                    with open(plan_file, "r", encoding="utf-8") as f:
                        plan = _json.load(f)
                    chapter_file_check = check_chapter_files(pdir, plan.get("chapters", []))
                except Exception:
                    pass

            all_errors = []
            all_errors.extend([f"缺少文件: {m}" for m in missing])
            all_errors.extend(json_check.get("errors", []))
            all_errors.extend(tlc_check.get("errors", []))
            all_errors.extend([f"章节文件缺失: {m}" for m in chapter_file_check.get("missing_required_files", [])])

            all_warnings = []
            all_warnings.extend(tlc_check.get("warnings", []))
            all_warnings.extend(chapter_file_check.get("wordcount_suspects", []))

            integrity_errors = len(all_errors)
            integrity_warnings = len(all_warnings)
            integrity_result = {
                "grade": "pass" if not all_errors else "fail",
                "errors": all_errors,
                "warnings": all_warnings,
                "memory": memory_check,
                "top_level_constraints": tlc_check,
            }
        except Exception:
            pass

    # 汇总
    overall = "pass"
    if wc_failed > 0 or style_fail > 0 or integrity_errors > 0:
        overall = "fail"
    elif style_warn > 0 or len(fs_orphans) > 0 or integrity_warnings > 0:
        overall = "warn"

    report = {
        "project": str(pdir),
        "overall_grade": overall,
        "wordcount": {
            "total_chapters": len(wc_results),
            "passed": wc_passed,
            "failed": wc_failed,
            "total_chinese_words": wc_total_words,
        },
        "ai_style": {
            "total_chapters": len(style_results),
            "pass": style_pass,
            "warn": style_warn,
            "fail": style_fail,
        },
        "foreshadowing": {
            "total_entries": fs_stats.get("total", 0),
            "orphan_count": len(fs_orphans),
            "orphans": fs_orphans,
            "status_distribution": fs_stats.get("by_status", {}),
        },
        "project_integrity": {
            "errors": integrity_errors,
            "warnings": integrity_warnings,
            "detail": integrity_result,
        },
    }

    if json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # 人类可读输出
    print(f"\n{'=' * 64}")
    print(f"  全流程校验报告")
    print(f"{'=' * 64}")
    print(f"  项目: {pdir.name}")

    # 字数
    print(f"\n  [字数检查] {wc_passed}/{len(wc_results)} 章达标 | 总中文字: {wc_total_words:,}")
    if wc_failed:
        for r in wc_results:
            if r.get("status") == "fail":
                print(f"    ! {Path(r['file']).name}: {r['chinese_count']}字")

    # AI废词
    print(f"\n  [文风质量] 通过: {style_pass} | 警告: {style_warn} | 不合格: {style_fail}")
    for r in style_results:
        if r.get("grade") != "pass" and r.get("exists"):
            issues_str = "; ".join(r.get("issues", [])[:2])
            print(f"    {'!' if r['grade'] == 'warn' else 'X'} {Path(r['file']).name}: {issues_str}")

    # 伏笔
    print(f"\n  [伏笔追踪] 总计: {fs_stats.get('total', 0)} | 孤儿: {len(fs_orphans)}")
    if fs_orphans:
        for o in fs_orphans[:3]:
            print(f"    ! [{o['id']}] {o['content']}...")

    # 完整性
    if integrity_result:
        print(f"\n  [项目完整性] 错误: {integrity_errors} | 警告: {integrity_warnings}")
        if integrity_result.get("errors"):
            for e in integrity_result["errors"][:3]:
                print(f"    ! {e}")
        mc = integrity_result.get("memory", {})
        if mc.get("exists"):
            print(f"    记忆系统: 阶段总结 {mc['phase_summaries']} | 章节记忆 {mc['chapter_memories']} | 快照 {'有' if mc['has_snapshot'] else '无'}")
    else:
        print(f"\n  [项目完整性] 写作计划文件不存在，跳过")

    # 总评
    grade_icon = {"pass": "+", "warn": "!", "fail": "X"}
    print(f"\n{'-' * 64}")
    print(f"  总评: [{grade_icon.get(overall, '?')}] {overall.upper()}")
    print(f"{'-' * 64}")


def main():
    args = sys.argv[1:]
    if not args:
        print("用法:")
        print("  python validate_all.py <项目目录> [--json] [--min-words N] [--threshold N]")
        return

    json_out = "--json" in args
    if json_out:
        args.remove("--json")

    min_words = 3000
    threshold = 5
    if "--min-words" in args:
        idx = args.index("--min-words")
        min_words = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]
    if "--threshold" in args:
        idx = args.index("--threshold")
        threshold = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    run_full_validation(args[0], min_words=min_words, threshold=threshold, json_out=json_out)


if __name__ == "__main__":
    main()
