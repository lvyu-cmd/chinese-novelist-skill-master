#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
伏笔追踪表校验脚本
扫描 02-大纲/伏笔布局.md 中的伏笔表格，检查孤儿伏笔和状态统计。

用法:
  python check_foreshadowing.py <项目目录>
  python check_foreshadowing.py --json <项目目录>
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import fix_console_encoding, load_plan

fix_console_encoding()

def find_fs_file(project_dir):
    p = Path(project_dir)
    for candidate in [p / "02-大纲" / "伏笔布局.md"]:
        if candidate.exists(): return candidate
    for f in p.rglob("*伏笔*"):
        if f.is_file(): return f
    return None

def parse_table(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    entries = []
    rows = re.findall(r"^\|(.+)\|$", content, re.MULTILINE)
    headers = []
    header_done = False
    for raw in rows:
        cells = [c.strip() for c in raw.split("|") if c.strip()]
        if all(re.match(r"^[-:]+$", c) for c in cells): continue
        if not header_done and any(kw in "".join(cells) for kw in ["伏笔ID","ID","埋设","揭晓","状态"]):
            headers = [c.lower() for c in cells]; header_done = True; continue
        if not header_done or len(cells) < 4: continue
        e = {"_raw": cells}
        for i, h in enumerate(headers):
            if i >= len(cells): break
            if "id" in h or "编号" in h: e["id"] = cells[i]
            elif "埋设" in h: e["planted"] = cells[i]
            elif "内容" in h or "描述" in h: e["content"] = cells[i]
            elif "类型" in h: e["type"] = cells[i]
            elif "揭晓" in h or "预计" in h or "回收" in h: e["resolve"] = cells[i]
            elif "状态" in h: e["status"] = cells[i]
        if e.get("id") or e.get("content"):
            e.setdefault("status", "活跃"); e.setdefault("resolve", "")
            entries.append(e)
    if not entries:
        for line in content.split("\n"):
            m = re.match(r"^[-*]\s*(F?\d+[.:：])\s*(.+?)(?:\(第(\d+)章", line.strip())
            if m:
                entries.append({"id": m.group(1).rstrip(".:："), "content": m.group(2).strip(),
                                "resolve": m.group(3) or "", "status": "活跃"})
    return entries

def get_completed(project_dir):
    done = set()
    plan = load_plan(project_dir)
    if plan:
        for ch in plan.get("chapters", []):
            if ch.get("status") == "completed": done.add(ch.get("chapterNumber", 0))
    if not done:
        for f in Path(project_dir).glob("第*章*.md"):
            m = re.search(r"第(\d+)章", f.name)
            if m: done.add(int(m.group(1)))
    return done

def check_orphans(entries, completed):
    orphans = []
    for e in entries:
        rs = e.get("resolve", ""); st = e.get("status", "").lower()
        if not rs or st in ("已回收","已揭晓","完成","closed","resolved"): continue
        m = re.search(r"(\d+)", rs)
        if m:
            ch = int(m.group(1))
            if ch in completed:
                orphans.append({"id": e.get("id","?"), "content": e.get("content","")[:50],
                                "ch": ch, "reason": f"预计第{ch}章揭晓, 该章已完成但状态仍为「{st}」"})
    return orphans

def stats(entries):
    s = {"total": len(entries), "by_status": {}, "by_type": {}}
    for e in entries:
        st = e.get("status","未知"); tp = e.get("type","未分类")
        s["by_status"][st] = s["by_status"].get(st, 0) + 1
        s["by_type"][tp] = s["by_type"].get(tp, 0) + 1
    return s

def validate(project_dir, json_out=False):
    pdir = Path(project_dir)
    if not pdir.exists(): print(f"错误: 目录不存在 - {project_dir}"); return
    fsf = find_fs_file(pdir)
    if not fsf: print("未找到伏笔布局文件"); return
    entries = parse_table(fsf)
    completed = get_completed(pdir)
    orphans = check_orphans(entries, completed)
    st = stats(entries)
    r = {"project": str(pdir), "file": str(fsf), "stats": st, "orphans": orphans, "orphan_count": len(orphans)}
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2)); return
    print(f"\n{'='*56}\n 伏笔追踪表校验\n{'='*56}")
    print(f"项目: {pdir.name} | 文件: {fsf.name}")
    print(f"已完成章节: {sorted(completed) if completed else '无'}")
    print(f"\n伏笔: {st['total']} 条")
    for k, v in st["by_status"].items(): print(f"  [{k}]: {v}")
    if orphans:
        print(f"\n! 孤儿伏笔: {len(orphans)} 条")
        for o in orphans: print(f"  - [{o['id']}] {o['content']}... {o['reason']}")
    else:
        print("\n+ 无孤儿伏笔")
    print(f"{'-'*56}")

def main():
    args = sys.argv[1:]
    if not args: print("用法: python check_foreshadowing.py [--json] <项目目录>"); return
    json_out = "--json" in args
    if json_out: args.remove("--json")
    validate(args[0], json_out)

if __name__ == "__main__":
    main()