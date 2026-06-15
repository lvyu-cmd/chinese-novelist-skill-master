#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全流程一键校验脚本
串联字数/文风/伏笔/完整性四模块，输出统一报告。

用法:
  python validate_all.py <项目目录>
  python validate_all.py --json <项目目录>
  python validate_all.py <项目目录> --min-words 3500 --threshold 3
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import fix_console_encoding, load_plan
from check_chapter_wordcount import check_all as wc_all
from check_ai_style import scan_all as style_all
from check_foreshadowing import find_fs_file, parse_table, get_completed, check_orphans, stats as fs_stats
from check_project_integrity import check_files, check_json, check_tlc, check_memory, check_chapter_files

fix_console_encoding()

def run(project_dir, min_words=3000, threshold=5, json_out=False):
    pdir = Path(project_dir)
    if not pdir.exists(): print(f"错误: 目录不存在 - {project_dir}"); return

    # 1. 字数
    wc = wc_all(str(pdir), min_words)
    wc_p = sum(1 for r in wc if r.get("status") == "pass")
    wc_f = sum(1 for r in wc if r.get("status") == "fail")
    wc_w = sum(r.get("cn", 0) for r in wc if r.get("exists"))

    # 2. 文风
    st = style_all(str(pdir), threshold)
    st_p = sum(1 for r in st if r.get("grade") == "pass")
    st_n = sum(1 for r in st if r.get("grade") == "warn")
    st_f = sum(1 for r in st if r.get("grade") == "fail")

    # 3. 伏笔
    fsf = find_fs_file(pdir)
    fs_entries = []; fs_orp = []; fs_st = {}
    if fsf:
        fs_entries = parse_table(fsf)
        comp = get_completed(pdir)
        fs_orp = check_orphans(fs_entries, comp)
        fs_st = fs_stats(fs_entries)

    # 4. 完整性
    missing = check_files(pdir)
    jc = check_json(pdir)
    tlc = check_tlc(pdir)
    mc = check_memory(pdir)
    cf = {"missing": [], "suspects": []}
    plan = load_plan(pdir)
    if plan: cf = check_chapter_files(pdir, plan.get("chapters", []))
    int_errs = len([f"缺少: {m}" for m in missing] + jc.get("errors",[]) + tlc.get("errors",[]) + [f"缺失: {m}" for m in cf.get("missing",[])])
    int_warns = len(tlc.get("warnings",[]) + cf.get("suspects",[]))

    # 总评
    overall = "pass"
    if wc_f > 0 or st_f > 0 or int_errs > 0: overall = "fail"
    elif st_n > 0 or fs_orp or int_warns > 0: overall = "warn"

    report = {
        "project": str(pdir), "overall": overall,
        "wordcount": {"total": len(wc), "passed": wc_p, "failed": wc_f, "words": wc_w},
        "style": {"total": len(st), "pass": st_p, "warn": st_n, "fail": st_f},
        "foreshadowing": {"total": fs_st.get("total",0), "orphans": len(fs_orp), "by_status": fs_st.get("by_status",{})},
        "integrity": {"errors": int_errs, "warnings": int_warns},
    }

    if json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2)); return

    gi = {"pass": "+", "warn": "!", "fail": "X"}
    print(f"\n{'='*60}\n  全流程校验报告\n{'='*60}")
    print(f"  项目: {pdir.name}")

    print(f"\n  [字数] {wc_p}/{len(wc)} 达标 | 中文字: {wc_w:,}")
    for r in wc:
        if r.get("status") == "fail": print(f"    ! {Path(r['file']).name}: {r['cn']}字")

    print(f"\n  [文风] 通过: {st_p} | 警告: {st_n} | 不合格: {st_f}")
    for r in st:
        if r.get("grade") != "pass" and r.get("exists"):
            print(f"    {'!' if r['grade']=='warn' else 'X'} {Path(r['file']).name}: {'; '.join(r.get('issues',[])[:2])}")

    print(f"\n  [伏笔] 总计: {fs_st.get('total',0)} | 孤儿: {len(fs_orp)}")
    for o in fs_orp[:3]: print(f"    ! [{o['id']}] {o['content']}...")

    print(f"\n  [完整性] 错误: {int_errs} | 警告: {int_warns}")
    if mc.get("exists"):
        print(f"    记忆: 总结{mc['summaries']} | 记忆{mc['memories']} | 快照{'有' if mc['snapshot'] else '无'}")

    print(f"\n{'-'*60}")
    print(f"  总评: [{gi.get(overall,'?')}] {overall.upper()}")
    print(f"{'-'*60}")

def main():
    args = sys.argv[1:]
    if not args: print("用法: python validate_all.py [--json] <目录> [--min-words N] [--threshold N]"); return
    json_out = "--json" in args
    if json_out: args.remove("--json")
    mw = 3000; th = 5
    if "--min-words" in args:
        i = args.index("--min-words"); mw = int(args[i+1]); args = args[:i] + args[i+2:]
    if "--threshold" in args:
        i = args.index("--threshold"); th = int(args[i+1]); args = args[:i] + args[i+2:]
    run(args[0], mw, th, json_out)

if __name__ == "__main__":
    main()