#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节字数检查脚本
检查指定章节文件的中文字符数，低于阈值时提示扩充。
支持单章检查、批量检查、自定义阈值。

用法:
  检查单个章节: python check_chapter_wordcount.py <章节文件> [最小字数]
  检查所有章节: python check_chapter_wordcount.py --all <目录> [最小字数]
  输出JSON格式: python check_chapter_wordcount.py --json <章节文件> [最小字数]
  批量JSON:     python check_chapter_wordcount.py --all --json <目录> [最小字数]
"""

import json
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def count_chinese_chars(text: str) -> int:
    """统计中文字符数（汉字），排除标点和Markdown标记。"""
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def count_total_chars(text: str) -> int:
    """统计所有可见字符数（含中文、英文、数字、标点）。"""
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    return len(re.findall(r"\S", text))


def extract_body(file_path: Path) -> str:
    """提取正文内容，跳过开头章节标题行。"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("#") and "章" in line:
            start = i + 1
            break
    return "\n".join(lines[start:])


def check_chapter(file_path: str, min_words: int = 3000) -> dict:
    """检查单个章节字数。"""
    path = Path(file_path)
    if not path.exists():
        return {"file": str(path), "exists": False, "chinese_count": 0,
                "total_count": 0, "status": "error", "message": f"文件不存在: {file_path}"}

    body = extract_body(path)
    cn = count_chinese_chars(body)
    total = count_total_chars(body)
    ok = cn >= min_words
    return {
        "file": str(path), "exists": True,
        "chinese_count": cn, "total_count": total,
        "status": "pass" if ok else "fail",
        "message": f"中文字数: {cn} | 总字符: {total}"
                    + (" (达标)" if ok else f" (不足，需至少 {min_words} 字)"),
    }


def check_all(directory: str, pattern: str = "第*.md", min_words: int = 3000) -> list:
    """批量检查目录下所有章节。"""
    dp = Path(directory)
    if not dp.exists():
        print(f"错误: 目录不存在 - {directory}")
        return []
    return [check_chapter(str(f), min_words) for f in sorted(dp.glob(pattern))]


def print_results(results: list, min_words: int = 3000) -> dict:
    """打印结果摘要，返回统计dict。"""
    if not results:
        print("没有找到章节文件")
        return {"total": 0, "passed": 0, "failed": 0, "total_words": 0}

    total_words = 0
    passed = failed = 0
    print(f"\n{'=' * 60}\n章节字数检查报告（阈值: {min_words}）\n{'=' * 60}")

    for r in results:
        if not r["exists"]:
            print(f"\n  {r['file']}\n   {r['message']}")
            continue
        total_words += r["chinese_count"]
        if r["status"] == "pass":
            passed += 1
            icon = "+"
        else:
            failed += 1
            icon = "!"
        print(f"\n{icon} {Path(r['file']).name} | {r['message']}")

    print(f"\n{'-' * 60}")
    print(f"总计: {len(results)} 章 | 达标: {passed} | 不足: {failed} | 总中文字: {total_words:,}")
    print("-" * 60)
    if failed:
        print(f"\n! {failed} 章不足 {min_words} 字，建议: 添加细节/对话/心理/背景描写")
    return {"total": len(results), "passed": passed, "failed": failed, "total_words": total_words}


def main():
    min_words = 3000
    json_out = False
    args = sys.argv[1:]

    if not args:
        print("用法:")
        print("  python check_chapter_wordcount.py <章节文件> [最小字数]")
        print("  python check_chapter_wordcount.py --all <目录> [最小字数]")
        print("  python check_chapter_wordcount.py --json <章节文件> [最小字数]")
        return

    if "--json" in args:
        json_out = True
        args.remove("--json")

    if args[0] == "--all":
        if len(args) < 2:
            print("错误: --all 需要指定目录")
            return
        directory = args[1]
        min_words = int(args[2]) if len(args) > 2 else 3000
        results = check_all(directory, min_words=min_words)
    else:
        file_path = args[0]
        min_words = int(args[1]) if len(args) > 1 else 3000
        results = [check_chapter(file_path, min_words)]

    if json_out:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_results(results, min_words)


if __name__ == "__main__":
    main()
