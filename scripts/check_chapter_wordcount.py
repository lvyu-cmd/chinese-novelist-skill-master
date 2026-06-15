#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节字数检查脚本
检查指定章节文件的中文字符数，低于阈值时提示扩充。

用法:
  python check_chapter_wordcount.py <章节文件> [最小字数]
  python check_chapter_wordcount.py --all <目录> [最小字数]
  python check_chapter_wordcount.py --json [--all] <目标> [最小字数]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import fix_console_encoding, extract_body, count_cn, count_vis, find_chapters

fix_console_encoding()

def check_chapter(file_path, min_words=3000):
    p = Path(file_path)
    if not p.exists():
        return {"file": str(p), "exists": False, "cn": 0, "vis": 0,
                "status": "error", "msg": f"文件不存在: {file_path}"}
    body = extract_body(p)
    cn = count_cn(body)
    vis = count_vis(body)
    ok = cn >= min_words
    return {"file": str(p), "exists": True, "cn": cn, "vis": vis,
            "status": "pass" if ok else "fail",
            "msg": f"中文: {cn} | 总字符: {vis}" + (" (达标)" if ok else f" (不足, 需 {min_words})")}

def check_all(directory, min_words=3000):
    dp = Path(directory)
    if not dp.exists():
        print(f"错误: 目录不存在 - {directory}")
        return []
    return [check_chapter(str(f), min_words) for f in find_chapters(dp)]

def print_results(results, min_words=3000):
    if not results:
        print("没有找到章节文件")
        return {"total": 0, "passed": 0, "failed": 0, "words": 0}
    words = 0
    p = f = 0
    print(f"\n{'='*56}\n 章节字数检查 (阈值: {min_words})\n{'='*56}")
    for r in results:
        if not r["exists"]:
            print(f"\n  {r['file']}: {r['msg']}")
            continue
        words += r["cn"]
        if r["status"] == "pass":
            p += 1; icon = "+"
        else:
            f += 1; icon = "!"
        print(f"\n{icon} {Path(r['file']).name} | {r['msg']}")
    print(f"\n{'-'*56}")
    print(f"总计: {len(results)} 章 | 达标: {p} | 不足: {f} | 中文字: {words:,}")
    print("-" * 56)
    if f:
        print(f"! {f} 章不足 {min_words} 字")
    return {"total": len(results), "passed": p, "failed": f, "words": words}

def main():
    args = sys.argv[1:]
    if not args:
        print("用法: python check_chapter_wordcount.py [--json] [--all] <目标> [最小字数]")
        return
    json_out = "--json" in args
    if json_out: args.remove("--json")
    is_all = "--all" in args
    if is_all: args.remove("--all")
    min_w = 3000
    if len(args) > 1:
        try: min_w = int(args[1])
        except ValueError: pass
    if is_all:
        results = check_all(args[0], min_w)
    else:
        results = [check_chapter(args[0], min_w)]
    if json_out:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_results(results, min_w)

if __name__ == "__main__":
    main()