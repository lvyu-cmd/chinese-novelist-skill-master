#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI废词 + 文风质量扫描脚本
扫描章节中的AI高频废词、"的"字密度、句式多样性、展示vs讲述。

用法:
  python check_ai_style.py <章节文件> [--threshold N]
  python check_ai_style.py --all <目录> [--threshold N]
  python check_ai_style.py --json [--all] <目标> [--threshold N]
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import fix_console_encoding, extract_body, count_cn

fix_console_encoding()

# ── AI废词库（4类） ──
WASTE = {
    "高频虚词": ["此刻","见状","随即","不由得","不禁","霎时","倏然","蓦然","恍然","赫然","陡然","骤然"],
    "空洞修饰": ["仿佛","宛如","犹如","恰似","恍若","好似","油然而生","心潮澎湃","热血沸腾","百感交集","五味杂陈","感慨万千","思绪万千"],
    "AI套话": ["彰显","诠释","赋能","映射","勾勒","铸就","谱写了","书写了","绽放出","迸发出","如同一幅画卷","宛如一首诗"],
    "四字堆砌": ["波澜壮阔","惊心动魄","荡气回肠","扣人心弦","如梦似幻","如诗如画","美轮美奂","巧夺天工","气势磅礴","排山倒海","翻天覆地","日新月异"],
}

def scan_waste(text):
    result = {}
    total = 0
    for cat, words in WASTE.items():
        found = {}
        for w in words:
            c = text.count(w)
            if c > 0: found[w] = c; total += c
        if found: result[cat] = found
    result["_total"] = total
    return result

def check_de(text):
    sents = [s.strip() for s in re.split(r"[。！？；\n]", text) if len(s.strip()) > 5]
    overloaded = []
    for s in sents:
        dc = s.count("的")
        if dc > 2:
            overloaded.append({"s": s[:60] + ("..." if len(s) > 60 else ""), "n": dc})
    total_de = text.count("的")
    return {"total": total_de, "sents": len(sents), "density": round(total_de / max(len(sents), 1), 2),
            "overloaded": len(overloaded), "samples": overloaded[:5]}

def check_variety(text):
    sents = [s.strip() for s in re.split(r"[。！？；\n]", text) if len(s.strip()) > 3]
    streaks = []
    streak = 1
    for i in range(1, len(sents)):
        if len(sents[i-1]) >= 2 and len(sents[i]) >= 2 and sents[i-1][:2] == sents[i][:2]:
            streak += 1
        else:
            if streak >= 3: streaks.append({"pos": i - streak, "len": streak, "subj": sents[i-1][:2]})
            streak = 1
    if streak >= 3: streaks.append({"pos": len(sents) - streak, "len": streak, "subj": sents[-1][:2]})
    long_s = []
    for i, s in enumerate(sents):
        cn = len(re.findall(r"[\u4e00-\u9fff]", s))
        if cn > 80: long_s.append({"pos": i, "chars": cn, "preview": s[:60] + "..."})
    return {"sents": len(sents), "repeated": streaks, "long_count": len(long_s), "long_samples": long_s[:3]}

def check_tell(text):
    patterns = [
        (r"他.{0,5}(感到|觉得|感觉到|意识到)", "情绪直接陈述"),
        (r"她.{0,5}(心中|内心|心里).{0,10}(涌起|充满|感到)", "内心直接描写"),
        (r"(一种|一股).{0,10}(情感|感觉|情绪).{0,5}(涌上|袭来|充满)", "抽象情感陈述"),
        (r"(他|她)是一个.{2,10}(的人|人)", "性格标签说明"),
    ]
    issues = []
    for pat, label in patterns:
        for m in re.finditer(pat, text):
            s = max(0, m.start() - 5)
            e = min(len(text), m.end() + 15)
            issues.append({"type": label, "snip": text[s:e].replace("\n", " ")})
    return {"count": len(issues), "samples": issues[:5]}

def scan_chapter(file_path, threshold=5):
    p = Path(file_path)
    if not p.exists():
        return {"file": str(p), "exists": False, "error": f"文件不存在: {file_path}"}
    body = extract_body(p)
    cn = count_cn(body)
    waste = scan_waste(body)
    de = check_de(body)
    var = check_variety(body)
    tell = check_tell(body)
    issues = []
    if waste["_total"] > threshold: issues.append(f"AI废词 {waste['_total']} 次 (阈值 {threshold})")
    if de["overloaded"] > 3: issues.append(f'"的"过载 {de["overloaded"]} 句')
    if var["repeated"]: issues.append(f"连续同主语 {len(var['repeated'])} 处")
    if var["long_count"] > 2: issues.append(f"超长句 {var['long_count']} 个")
    if tell["count"] > 3: issues.append(f"直接陈述 {tell['count']} 处")
    grade = "pass" if not issues else ("warn" if len(issues) <= 2 else "fail")
    return {"file": str(p), "exists": True, "cn": cn, "grade": grade, "issues": issues,
            "waste": waste, "de": de, "variety": var, "tell": tell}

def scan_all(directory, threshold=5):
    dp = Path(directory)
    if not dp.exists():
        print(f"错误: 目录不存在 - {directory}"); return []
    return [scan_chapter(str(f), threshold) for f in sorted(dp.glob("第*.md"))]

def print_results(results, threshold=5):
    if not results:
        print("没有找到章节文件"); return
    pw = nw = fw = 0
    print(f"\n{'='*56}\n AI废词 + 文风扫描 (阈值: {threshold})\n{'='*56}")
    for r in results:
        if not r.get("exists"):
            print(f"\n  {r['file']}: {r.get('error','')}"); continue
        g = r["grade"]
        if g == "pass": pw += 1; ic = "+"
        elif g == "warn": nw += 1; ic = "!"
        else: fw += 1; ic = "X"
        print(f"\n{ic} {Path(r['file']).name} | 中文: {r['cn']} | {g}")
        for iss in r.get("issues", []):
            print(f"    - {iss}")
        wt = r.get("waste", {})
        if wt.get("_total", 0) > 0:
            for cat, words in wt.items():
                if cat.startswith("_"): continue
                print(f"    [{cat}] {', '.join(f'{w}({c})' for w,c in words.items())}")
        de = r.get("de", {})
        if de.get("overloaded", 0) > 0:
            print(f"    的字: {de['total']}个/{de['sents']}句, 过载{de['overloaded']}句")
        sv = r.get("variety", {})
        for s in sv.get("repeated", []):
            print(f"    同主语'{s['subj']}' x{s['len']}")
        sn = r.get("tell", {})
        if sn.get("count", 0) > 0:
            print(f"    讲述: {sn['count']}处")
            for t in sn.get("samples", [])[:2]:
                print(f"      [{t['type']}] {t['snip']}")
    print(f"\n{'-'*56}")
    print(f"总计: {len(results)} | 通过: {pw} | 警告: {nw} | 不合格: {fw}")
    print("-" * 56)

def main():
    args = sys.argv[1:]
    if not args:
        print("用法: python check_ai_style.py [--json] [--all] <目标> [--threshold N]")
        return
    json_out = "--json" in args
    if json_out: args.remove("--json")
    is_all = "--all" in args
    if is_all: args.remove("--all")
    threshold = 5
    if "--threshold" in args:
        idx = args.index("--threshold")
        threshold = int(args[idx + 1]); args = args[:idx] + args[idx+2:]
    if is_all:
        results = scan_all(args[0], threshold)
    else:
        results = [scan_chapter(args[0], threshold)]
    if json_out:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_results(results, threshold)

if __name__ == "__main__":
    main()