#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
写作计划JSON + 顶层约束一致性校验脚本
检查 03-写作计划.json 的结构完整性、顶层约束字段、章节状态一致性。

用法:
  校验项目:     python check_project_integrity.py <项目目录>
  输出JSON:     python check_project_integrity.py --json <项目目录>
"""

import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 必需的项目文件 ──────────────────────────────────────────
REQUIRED_FILES = [
    "00-世界观.md",
    "01-人物卡/主角.md",
    "01-人物卡/重要角色.md",
    "01-人物卡/次要角色.md",
    "01-人物卡/重要反派.md",
    "01-人物卡/次要反派.md",
    "02-大纲/卷纲.md",
    "02-大纲/时间线.md",
    "02-大纲/伏笔布局.md",
    "02-大纲/进阶条件.md",
    "02-大纲/成长体系.md",
    "02-大纲/境界功法.md",
    "03-写作计划.json",
]

REQUIRED_TOP_LEVEL_KEYS = [
    "openingBackground",
    "storyEnding",
    "volumeOutline",
    "abilityPath",
    "coreConflict",
]

OPTIONAL_TOP_LEVEL_KEYS = [
    "growthCost",
    "conflictEscalation",
]

VALID_CHAPTER_STATUSES = {"pending", "in_progress", "completed", "failed", "draft"}
VALID_WRITING_MODES = {"serial", "subagent-parallel", "agent-teams", None}
VALID_PROJECT_STATUSES = {"planning", "in_progress", "validating", "completed"}


def check_required_files(project_dir: Path) -> list:
    """检查14份必需设定文件是否存在。"""
    missing = []
    for rel in REQUIRED_FILES:
        p = project_dir / rel
        if not p.exists():
            missing.append(rel)
    return missing


def check_json_structure(project_dir: Path) -> dict:
    """校验03-写作计划.json结构。"""
    plan_file = project_dir / "03-写作计划.json"
    if not plan_file.exists():
        return {"exists": False, "errors": ["文件不存在"]}

    try:
        with open(plan_file, "r", encoding="utf-8") as f:
            plan = json.load(f)
    except json.JSONDecodeError as e:
        return {"exists": True, "errors": [f"JSON解析失败: {e}"]}

    errors = []

    # 必需顶级字段
    for key in ["novelName", "totalChapters", "status", "chapters"]:
        if key not in plan:
            errors.append(f"缺少必需字段: {key}")

    # status枚举
    if plan.get("status") not in VALID_PROJECT_STATUSES:
        errors.append(f"无效的项目状态: {plan.get('status')}")

    # writingMode枚举
    wm = plan.get("writingMode")
    if wm not in VALID_WRITING_MODES:
        errors.append(f"无效的写作模式: {wm}")

    # chapters结构
    chapters = plan.get("chapters", [])
    if not isinstance(chapters, list):
        errors.append("chapters字段应为数组")
    elif len(chapters) == 0:
        errors.append("chapters为空数组")
    else:
        chapter_numbers = []
        for i, ch in enumerate(chapters):
            if "chapterNumber" not in ch:
                errors.append(f"chapters[{i}] 缺少 chapterNumber")
            else:
                chapter_numbers.append(ch["chapterNumber"])
            if "status" not in ch:
                errors.append(f"chapters[{i}] 缺少 status")
            elif ch["status"] not in VALID_CHAPTER_STATUSES:
                errors.append(f"chapters[{i}] 无效状态: {ch['status']}")
            if "filePath" not in ch:
                errors.append(f"chapters[{i}] 缺少 filePath")

        # 章节号连续性
        if chapter_numbers:
            expected = list(range(1, len(chapter_numbers) + 1))
            if chapter_numbers != expected:
                errors.append(f"章节号不连续: 期望 {expected}, 实际 {chapter_numbers}")

    return {
        "exists": True,
        "errors": errors,
        "version": plan.get("version"),
        "total_chapters": plan.get("totalChapters"),
        "status": plan.get("status"),
        "writing_mode": plan.get("writingMode"),
        "chapter_count": len(chapters),
    }


def check_top_level_constraints(project_dir: Path) -> dict:
    """校验topLevelConstraints字段。"""
    plan_file = project_dir / "03-写作计划.json"
    if not plan_file.exists():
        return {"exists": False, "errors": ["写作计划文件不存在"]}

    try:
        with open(plan_file, "r", encoding="utf-8") as f:
            plan = json.load(f)
    except json.JSONDecodeError:
        return {"exists": True, "errors": ["JSON解析失败"]}

    tlc = plan.get("topLevelConstraints")
    errors = []
    warnings = []

    if tlc is None:
        return {
            "exists": False,
            "errors": ["缺少 topLevelConstraints 字段（V2必需）"],
            "filled_required": 0,
            "total_required": len(REQUIRED_TOP_LEVEL_KEYS),
        }

    if not isinstance(tlc, dict):
        return {"exists": True, "errors": ["topLevelConstraints 应为对象"]}

    filled = 0
    for key in REQUIRED_TOP_LEVEL_KEYS:
        val = tlc.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"顶层约束必填项为空: {key}")
        else:
            filled += 1

    for key in OPTIONAL_TOP_LEVEL_KEYS:
        val = tlc.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            warnings.append(f"顶层约束可选项为空: {key}")

    return {
        "exists": True,
        "errors": errors,
        "warnings": warnings,
        "filled_required": filled,
        "total_required": len(REQUIRED_TOP_LEVEL_KEYS),
        "constraints": {k: str(tlc.get(k, ""))[:80] for k in REQUIRED_TOP_LEVEL_KEYS + OPTIONAL_TOP_LEVEL_KEYS},
    }


def check_chapter_files(project_dir: Path, chapters: list) -> dict:
    """检查章节文件与写作计划的一致性。"""
    missing_files = []
    wordcount_issues = []

    for ch in chapters:
        fp = project_dir / ch.get("filePath", "")
        if not fp.exists():
            if ch.get("status") in ("completed", "in_progress"):
                missing_files.append(ch.get("filePath", "?"))
        elif ch.get("status") == "completed":
            # 已完成章节检查文件大小
            size = fp.stat().st_size
            if size < 1000:  # 太小可能不是完整章节
                wordcount_issues.append(f"{ch.get('filePath')}: 文件仅 {size} 字节")

    return {
        "missing_required_files": missing_files,
        "wordcount_suspects": wordcount_issues,
    }


def check_memory_dir(project_dir: Path) -> dict:
    """检查memory目录结构。"""
    memory_dir = project_dir / "memory"
    if not memory_dir.exists():
        return {"exists": False, "phase_summaries": 0, "chapter_memories": 0, "has_snapshot": False}

    summaries = list(memory_dir.glob("phase-*-summary.md"))
    memories = list(memory_dir.glob("ch-*-memory.md"))
    snapshot = memory_dir / "snapshot.json"

    return {
        "exists": True,
        "phase_summaries": len(summaries),
        "chapter_memories": len(memories),
        "has_snapshot": snapshot.exists(),
    }


def validate_project(project_dir: str, json_out: bool = False):
    """主校验入口。"""
    pdir = Path(project_dir)
    if not pdir.exists():
        print(f"错误: 项目目录不存在 - {project_dir}")
        return

    missing = check_required_files(pdir)
    json_check = check_json_structure(pdir)
    tlc_check = check_top_level_constraints(pdir)
    memory_check = check_memory_dir(pdir)

    chapter_file_check = {"missing_required_files": [], "wordcount_suspects": []}
    if json_check.get("exists") and not json_check.get("errors"):
        try:
            with open(pdir / "03-写作计划.json", "r", encoding="utf-8") as f:
                plan = json.load(f)
            chapter_file_check = check_chapter_files(pdir, plan.get("chapters", []))
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # 汇总
    all_errors = []
    all_errors.extend([f"缺少文件: {m}" for m in missing])
    all_errors.extend(json_check.get("errors", []))
    all_errors.extend(tlc_check.get("errors", []))
    all_errors.extend([f"章节文件缺失: {m}" for m in chapter_file_check.get("missing_required_files", [])])

    all_warnings = []
    all_warnings.extend(tlc_check.get("warnings", []))
    all_warnings.extend(chapter_file_check.get("wordcount_suspects", []))

    grade = "pass" if not all_errors else "fail"

    result = {
        "project": str(pdir),
        "grade": grade,
        "error_count": len(all_errors),
        "warning_count": len(all_warnings),
        "errors": all_errors,
        "warnings": all_warnings,
        "file_check": {"missing": missing, "total_required": len(REQUIRED_FILES)},
        "json_check": json_check,
        "top_level_constraints": tlc_check,
        "memory": memory_check,
        "chapter_files": chapter_file_check,
    }

    if json_out:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 人类可读输出
    print(f"\n{'=' * 60}")
    print(f"项目完整性校验报告")
    print(f"{'=' * 60}")
    print(f"项目: {pdir.name}")

    # 文件检查
    fc = result["file_check"]
    print(f"\n[文件结构] {fc['total_required'] - len(fc['missing'])}/{fc['total_required']} 份设定文件存在")
    if fc["missing"]:
        for m in fc["missing"]:
            print(f"  ! 缺失: {m}")

    # JSON检查
    jc = result["json_check"]
    if jc.get("exists"):
        print(f"\n[写作计划] version={jc.get('version')} | 状态={jc.get('status')} | 模式={jc.get('writing_mode')} | 章节={jc.get('chapter_count')}")
        if jc.get("errors"):
            for e in jc["errors"]:
                print(f"  ! {e}")
    else:
        print(f"\n[写作计划] 不存在")

    # 顶层约束
    tlc = result["top_level_constraints"]
    if tlc.get("exists"):
        print(f"\n[顶层约束] {tlc['filled_required']}/{tlc['total_required']} 必填项已填写")
        if tlc.get("errors"):
            for e in tlc["errors"]:
                print(f"  ! {e}")
        if tlc.get("warnings"):
            for w in tlc["warnings"]:
                print(f"  ~ {w}")
    else:
        print(f"\n[顶层约束] {tlc.get('errors', ['未找到'])[0]}")

    # 记忆目录
    mc = result["memory"]
    if mc["exists"]:
        print(f"\n[记忆系统] 阶段总结: {mc['phase_summaries']} | 章节记忆: {mc['chapter_memories']} | 快照: {'有' if mc['has_snapshot'] else '无'}")
    else:
        print(f"\n[记忆系统] memory/ 目录不存在")

    # 章节文件
    cf = result["chapter_files"]
    if cf.get("missing_required_files"):
        print(f"\n[章节文件] ! {len(cf['missing_required_files'])} 个已完成章节文件缺失:")
        for m in cf["missing_required_files"]:
            print(f"    {m}")
    if cf.get("wordcount_suspects"):
        for w in cf["wordcount_suspects"]:
            print(f"  ~ {w}")

    # 汇总
    print(f"\n{'-' * 60}")
    if grade == "pass":
        print(f"+ 校验通过 | 警告: {len(all_warnings)}")
    else:
        print(f"X 校验失败 | 错误: {len(all_errors)} | 警告: {len(all_warnings)}")
        for e in all_errors:
            print(f"  - {e}")
    print(f"{'-' * 60}")


def main():
    args = sys.argv[1:]
    if not args:
        print("用法:")
        print("  python check_project_integrity.py <项目目录>")
        print("  python check_project_integrity.py --json <项目目录>")
        return

    json_out = "--json" in args
    if json_out:
        args.remove("--json")

    validate_project(args[0], json_out)


if __name__ == "__main__":
    main()
