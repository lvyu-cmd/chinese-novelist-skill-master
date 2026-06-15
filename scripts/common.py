#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公共工具模块 - 编码修复/Markdown清理/正文提取/字数统计/计划读取"""

import json
import re
import sys
from pathlib import Path

# ── 控制台编码修复（幂等安全） ──
_encoding_fixed = False

def fix_console_encoding():
    global _encoding_fixed
    if _encoding_fixed: return
    _encoding_fixed = True
    if sys.platform == "win32":
        import io
        try:
            if hasattr(sys.stdout, "buffer"):
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
            if hasattr(sys.stderr, "buffer"):
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        except (ValueError, AttributeError): pass

# ── Markdown 清理 ──
_MD_RULES = [
    (re.compile(r"#{1,6}\s*"), ""),
    (re.compile(r"\*\*(.*?)\*\*"), r"\1"),
    (re.compile(r"\*(.*?)\*"), r"\1"),
    (re.compile(r"~~(.*?)~~"), r"\1"),
    (re.compile(r"(.*?)"), r"\1"),
    (re.compile(r"\[(.*?)\]\(.*?\)"), r"\1"),
    (re.compile(r"^>\s*", re.MULTILINE), ""),
    (re.compile(r"^---+$", re.MULTILINE), ""),
]

def strip_md(text):
    for pat, repl in _MD_RULES:
        text = pat.sub(repl, text)
    return text

# ── 正文提取 ──
def extract_body(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("#") and "章" in line.strip():
            start = i + 1
            break
    return "\n".join(lines[start:])

# ── 字数统计 ──
_CN_RE = re.compile(r"[\u4e00-\u9fff]")
_VIS_RE = re.compile(r"\S")

def count_cn(text):
    return len(_CN_RE.findall(strip_md(text)))

def count_vis(text):
    return len(_VIS_RE.findall(strip_md(text)))

# ── 章节文件发现 ──
def find_chapters(directory, pattern="第*.md"):
    return sorted(Path(directory).glob(pattern))

# ── 写作计划读取 ──
def load_plan(project_dir):
    f = Path(project_dir) / "03-写作计划.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None