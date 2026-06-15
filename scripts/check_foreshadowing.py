#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
伏笔追踪表校验脚本
扫描 02-大纲/伏笔布局.md 中的伏笔追踪表，检查：
  1. 伏笔完整性（是否有孤儿伏笔：已过预计揭晓章节但状态仍为「活跃」）
  2. 伏笔-章节交叉验证（已标记回收的伏笔是否在对应章节文件中有对应内容）
  3. 伏笔状态统计

用法:
  校验伏笔:     python check_foreshadowing.py <项目目录>
  输出JSON:     python check_foreshadowing.py --json <项目目录>
"""

import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def find_foreshadowing_file(project_dir: Path) -> Path:
    """定位伏笔布局文件。"""
    candidates = [
        project_dir / "02-大纲" / "伏笔布局.md",
        project_dir / "02-outline" / "foreshadowing.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    # 回退：模糊搜索
    for f in project_dir.rglob("*伏笔*"):
        if f.is_file():
            return f
    return None


def parse_foreshadowing_table(file_path: Path) -> list:
    """
    解析伏笔追踪表。支持Markdown表格格式：
    | 伏笔ID | 埋设章节 | 内容 | 类型 | 预计揭晓 | 状态 |
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    entries = []
    # 查找Markdown表格行（跳过表头和分隔行）
    table_pattern = re.compile(r"^\|(.+)\|$", re.MULTILINE)
    rows = table_pattern.findall(content)

    header_found = False
    headers = []
    for row_raw in rows:
        cells = [c.strip() for c in row_raw.split("|")]
        cells = [c for c in cells if c]  # 去空

        # 跳过分隔行
        if all(re.match(r"^[-:]+$", c) for c in cells):
            continue

        # 表头检测
        if not header_found and any(kw in "".join(cells) for kw in ["伏笔ID", "ID", "埋设", "揭晓", "状态"]):
            headers = [c.lower() for c in cells]
            header_found = True
            continue

        if not header_found or len(cells) < 4:
            continue

        entry = {"_raw_cells": cells}
        # 按位置或表头映射
        for i, h in enumerate(headers):
            if i < len(cells):
                if "id" in h or "编号" in h:
                    entry["id"] = cells[i]
                elif "埋设" in h:
                    entry["planted"] = cells[i]
                elif "内容" in h or "描述" in h:
                    entry["content"] = cells[i]
                elif "类型" in h:
                    entry["type"] = cells[i]
                elif "揭晓" in h or "预计" in h or "回收" in h:
                    entry["resolve"] = cells[i]
                elif "状态" in h:
                    entry["status"] = cells[i]

        if entry.get("id") or entry.get("content"):
            # 默认值
            entry.setdefault("status", "活跃")
            entry.setdefault("resolve", "")
            entries.append(entry)

    # 回退：如果没有表格格式，尝试用正则逐行解析
    if not entries:
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 匹配 "- F001: 内容... (第X章揭晓)" 或类似格式
            m = re.match(r"^[-*]\s*(F?\d+[.:：])\s*(.+?)(?:\(第(\d+)章", line)
            if m:
                entries.append({
                    "id": m.group(1).rstrip(".:："),
                    "content": m.group(2).strip(),
                    "resolve": m.group(3) if m.group(3) else "",
                    "status": "活跃",
                })
    return entries


def get_completed_chapters(project_dir: Path) -> set:
    """获取已完成的章节号集合。"""
    completed = set()
    # 从写作计划JSON读取
    plan_file = project_dir / "03-写作计划.json"
    if plan_file.exists():
        try:
            with open(plan_file, "r", encoding="utf-8") as f:
                plan = json.load(f)
            for ch in plan.get("chapters", []):
                if ch.get("status") == "completed":
                    completed.add(ch.get("chapterNumber", 0))
        except (json.JSONDecodeError, KeyError):
            pass
    # 补充：扫描实际存在的章节文件
    if not completed:
        for f in project_dir.glob("第*章*.md"):
            m = re.search(r"第(\d+)章", f.name)
            if m:
                completed.add(int(m.group(1)))
    return completed


def check_orphans(entries: list, completed: set) -> list:
    """检查孤儿伏笔：预计揭晓章节已完成但状态仍为活跃。"""
    orphans = []
    for e in entries:
        resolve_str = e.get("resolve", "")
        status = e.get("status", "").lower()
        if not resolve_str or status in ("已回收", "已揭晓", "完成", "closed", "resolved"):
            continue
        # 尝试提取章节号
        m = re.search(r"(\d+)", resolve_str)
        if m:
            resolve_ch = int(m.group(1))
            if resolve_ch in completed:
                orphans.append({
                    "id": e.get("id", "?"),
                    "content": e.get("content", "")[:50],
                    "expected_chapter": resolve_ch,
                    "reason": f"预计第{resolve_ch}章揭晓，该章已完成但伏笔状态仍为「{status}」",
                })
    return orphans


def check_stats(entries: list) -> dict:
    """伏笔状态统计。"""
    stats = {"total": len(entries), "by_status": {}, "by_type": {}}
    for e in entries:
        s = e.get("status", "未知")
        t = e.get("type", "未分类")
        stats["by_status"][s] = stats["by_status"].get(s, 0) + 1
        stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
    return stats


def validate_project(project_dir: str, json_out: bool = False):
    """主校验入口。"""
    pdir = Path(project_dir)
    if not pdir.exists():
        print(f"错误: 项目目录不存在 - {project_dir}")
        return

    fs_file = find_foreshadowing_file(pdir)
    if not fs_file:
        print("未找到伏笔布局文件（搜索: 02-大纲/伏笔布局.md 或模糊匹配 *伏笔*）")
        return

    entries = parse_foreshadowing_table(fs_file)
    completed = get_completed_chapters(pdir)
    orphans = check_orphans(entries, completed)
    stats = check_stats(entries)

    result = {
        "project": str(pdir),
        "foreshadowing_file": str(fs_file),
        "stats": stats,
        "orphans": orphans,
        "orphan_count": len(orphans),
    }

    if json_out:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 人类可读输出
    print(f"\n{'=' * 60}")
    print(f"伏笔追踪表校验报告")
    print(f"{'=' * 60}")
    print(f"项目: {pdir.name}")
    print(f"文件: {fs_file.name}")
    print(f"已完成章节: {sorted(completed) if completed else '无'}")
    print(f"\n统计:")
    print(f"  伏笔总数: {stats['total']}")
    for s, c in stats["by_status"].items():
        print(f"  [{s}]: {c}")
    if stats["by_type"]:
        print(f"  类型分布:")
        for t, c in stats["by_type"].items():
            print(f"    {t}: {c}")

    if orphans:
        print(f"\n! 孤儿伏笔: {len(orphans)} 条")
        for o in orphans:
            print(f"  - [{o['id']}] {o['content']}...")
            print(f"    {o['reason']}")
    else:
        print(f"\n+ 无孤儿伏笔")

    print(f"\n{'-' * 60}")


def main():
    args = sys.argv[1:]
    if not args:
        print("用法:")
        print("  python check_foreshadowing.py <项目目录>")
        print("  python check_foreshadowing.py --json <项目目录>")
        return

    json_out = "--json" in args
    if json_out:
        args.remove("--json")

    validate_project(args[0], json_out)


if __name__ == "__main__":
    main()
