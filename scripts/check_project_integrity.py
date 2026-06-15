#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
写作计划JSON + 项目完整性校验脚本
检查14份设定文件、JSON结构、顶层约束、记忆系统。

用法:
  python check_project_integrity.py <项目目录>
  python check_project_integrity.py --json <项目目录>
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import fix_console_encoding, load_plan

fix_console_encoding()

REQUIRED_FILES = [
    "00-世界观.md",
    "01-人物卡/主角.md", "01-人物卡/重要角色.md", "01-人物卡/次要角色.md",
    "01-人物卡/重要反派.md", "01-人物卡/次要反派.md",
    "02-大纲/卷纲.md", "02-大纲/时间线.md", "02-大纲/伏笔布局.md",
    "02-大纲/进阶条件.md", "02-大纲/成长体系.md", "02-大纲/境界功法.md",
    "03-写作计划.json",
]

REQUIRED_TLC = ["openingBackground","storyEnding","volumeOutline","abilityPath","coreConflict"]
OPTIONAL_TLC = ["growthCost","conflictEscalation"]
VALID_CH_STATUS = {"pending","in_progress","completed","failed","draft"}
VALID_MODES = {"serial","subagent-parallel","agent-teams",None}
VALID_PROJ_STATUS = {"planning","in_progress","validating","completed"}

def check_files(pdir):
    return [r for r in REQUIRED_FILES if not (pdir / r).exists()]

def check_json(pdir):
    plan = load_plan(pdir)
    if plan is None:
        return {"exists": False, "errors": ["文件不存在或JSON解析失败"]}
    errs = []
    for k in ["novelName","totalChapters","status","chapters"]:
        if k not in plan: errs.append(f"缺少字段: {k}")
    if plan.get("status") not in VALID_PROJ_STATUS: errs.append(f"无效状态: {plan.get('status')}")
    if plan.get("writingMode") not in VALID_MODES: errs.append(f"无效模式: {plan.get('writingMode')}")
    chs = plan.get("chapters", [])
    if not isinstance(chs, list): errs.append("chapters应为数组")
    elif not chs: errs.append("chapters为空")
    else:
        nums = []
        for i, ch in enumerate(chs):
            if "chapterNumber" not in ch: errs.append(f"ch[{i}]缺chapterNumber")
            else: nums.append(ch["chapterNumber"])
            if "status" not in ch: errs.append(f"ch[{i}]缺status")
            elif ch["status"] not in VALID_CH_STATUS: errs.append(f"ch[{i}]无效状态: {ch['status']}")
            if "filePath" not in ch: errs.append(f"ch[{i}]缺filePath")
        if nums and nums != list(range(1, len(nums)+1)):
            errs.append(f"章节号不连续: 期望1-{len(nums)}, 实际{nums[:5]}...")
    return {"exists": True, "errors": errs, "version": plan.get("version"),
            "total": plan.get("totalChapters"), "status": plan.get("status"),
            "mode": plan.get("writingMode"), "count": len(chs)}

def check_tlc(pdir):
    plan = load_plan(pdir)
    if plan is None: return {"exists": False, "errors": ["写作计划不存在"]}
    tlc = plan.get("topLevelConstraints")
    if tlc is None: return {"exists": False, "errors": ["缺少topLevelConstraints (V2必需)"]}
    if not isinstance(tlc, dict): return {"exists": True, "errors": ["topLevelConstraints应为对象"]}
    errs = []; warns = []; filled = 0
    for k in REQUIRED_TLC:
        v = tlc.get(k)
        if v is None or (isinstance(v, str) and not v.strip()): errs.append(f"必填项为空: {k}")
        else: filled += 1
    for k in OPTIONAL_TLC:
        v = tlc.get(k)
        if v is None or (isinstance(v, str) and not v.strip()): warns.append(f"可选项为空: {k}")
    return {"exists": True, "errors": errs, "warnings": warns, "filled": filled,
            "total": len(REQUIRED_TLC),
            "preview": {k: str(tlc.get(k,""))[:60] for k in REQUIRED_TLC + OPTIONAL_TLC}}

def check_memory(pdir):
    md = pdir / "memory"
    if not md.exists(): return {"exists": False}
    return {"exists": True, "summaries": len(list(md.glob("phase-*-summary.md"))),
            "memories": len(list(md.glob("ch-*-memory.md"))),
            "snapshot": (md / "snapshot.json").exists()}

def check_chapter_files(pdir, chapters):
    missing = []; suspects = []
    for ch in chapters:
        fp = pdir / ch.get("filePath", "")
        if not fp.exists():
            if ch.get("status") in ("completed","in_progress"): missing.append(ch.get("filePath","?"))
        elif ch.get("status") == "completed" and fp.stat().st_size < 1000:
            suspects.append(f"{ch.get('filePath')}: 仅{fp.stat().st_size}字节")
    return {"missing": missing, "suspects": suspects}

def validate(project_dir, json_out=False):
    pdir = Path(project_dir)
    if not pdir.exists(): print(f"错误: 目录不存在 - {project_dir}"); return
    missing = check_files(pdir)
    jc = check_json(pdir)
    tlc = check_tlc(pdir)
    mc = check_memory(pdir)
    cf = {"missing": [], "suspects": []}
    plan = load_plan(pdir)
    if plan: cf = check_chapter_files(pdir, plan.get("chapters", []))
    errs = [f"缺少: {m}" for m in missing] + jc.get("errors",[]) + tlc.get("errors",[]) + [f"文件缺失: {m}" for m in cf.get("missing",[])]
    warns = tlc.get("warnings",[]) + cf.get("suspects",[])
    grade = "pass" if not errs else "fail"
    r = {"project": str(pdir), "grade": grade, "errors": errs, "warnings": warns,
         "files": {"missing": missing, "total": len(REQUIRED_FILES)}, "json": jc,
         "tlc": tlc, "memory": mc, "chapters": cf}
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2)); return
    print(f"\n{'='*56}\n 项目完整性校验\n{'='*56}")
    fc = r["files"]
    print(f"\n[文件] {fc['total']-len(fc['missing'])}/{fc['total']} 份存在")
    for m in fc["missing"]: print(f"  ! 缺失: {m}")
    if jc.get("exists"):
        print(f"\n[计划] v{jc.get('version')} | {jc.get('status')} | {jc.get('mode')} | {jc.get('count')}章")
        for e in jc.get("errors",[]): print(f"  ! {e}")
    else: print("\n[计划] 不存在")
    if tlc.get("exists"):
        print(f"\n[顶层约束] {tlc['filled']}/{tlc['total']} 必填已填写")
        for e in tlc.get("errors",[]): print(f"  ! {e}")
        for w in tlc.get("warnings",[]): print(f"  ~ {w}")
    else: print(f"\n[顶层约束] {tlc.get('errors',['未找到'])[0]}")
    if mc.get("exists"):
        print(f"\n[记忆] 总结: {mc['summaries']} | 记忆: {mc['memories']} | 快照: {'有' if mc['snapshot'] else '无'}")
    else: print("\n[记忆] memory/ 不存在")
    if cf.get("missing"):
        print(f"\n[章节] ! {len(cf['missing'])} 个已完成章节文件缺失:")
        for m in cf["missing"]: print(f"    {m}")
    print(f"\n{'-'*56}")
    if grade == "pass": print(f"+ 通过 | 警告: {len(warns)}")
    else:
        print(f"X 失败 | 错误: {len(errs)} | 警告: {len(warns)}")
        for e in errs: print(f"  - {e}")
    print("-" * 56)

def main():
    args = sys.argv[1:]
    if not args: print("用法: python check_project_integrity.py [--json] <项目目录>"); return
    json_out = "--json" in args
    if json_out: args.remove("--json")
    validate(args[0], json_out)

if __name__ == "__main__":
    main()