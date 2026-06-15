#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI废词扫描 + 文风质量检查脚本
扫描章节文件中的AI高频废词、句式问题、"的"字密度等文风指标。

用法:
  扫描单章:     python check_ai_style.py <章节文件>
  批量扫描:     python check_ai_style.py --all <目录>
  输出JSON:     python check_ai_style.py --json <章节文件>
  批量JSON:     python check_ai_style.py --all --json <目录>
  自定义阈值:   python check_ai_style.py <章节文件> --threshold 3
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── AI高频废词库 ──────────────────────────────────────────────
AI_WASTE_WORDS = {
    "高频虚词": [
        "此刻", "见状", "随即", "不由得", "不禁", "霎时", "倏然",
        "蓦然", "恍然", "赫然", "陡然", "骤然",
    ],
    "空洞修饰": [
        "仿佛", "宛如", "犹如", "恰似", "恍若", "好似",
        "油然而生", "心潮澎湃", "热血沸腾", "百感交集",
        "五味杂陈", "感慨万千", "思绪万千",
    ],
    "AI套话": [
        "彰显", "诠释", "赋能", "映射", "勾勒", "铸就",
        "谱写了", "书写了", "绽放出", "迸发出",
        "如同一幅画卷", "宛如一首诗",
    ],
    "四字堆砌": [
        "波澜壮阔", "惊心动魄", "荡气回肠", "扣人心弦",
        "如梦似幻", "如诗如画", "美轮美奂", "巧夺天工",
        "气势磅礴", "排山倒海", "翻天覆地", "日新月异",
    ],
}

# 所有废词平铺
ALL_WASTE_WORDS = []
for words in AI_WASTE_WORDS.values():
    ALL_WASTE_WORDS.extend(words)


def extract_body(file_path: Path) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("#") and "章" in line:
            start = i + 1
            break
    return "\n".join(lines[start:])


def scan_waste_words(text: str) -> dict:
    """扫描AI废词，返回分类统计。"""
    result = {}
    total_hits = 0
    for category, words in AI_WASTE_WORDS.items():
        found = {}
        for w in words:
            count = text.count(w)
            if count > 0:
                found[w] = count
                total_hits += count
        if found:
            result[category] = found
    result["_total_hits"] = total_hits
    return result


def check_de_density(text: str) -> dict:
    """检查"的"字密度：逐句分析，标记单句含"的"超过2个的句子。"""
    sentences = re.split(r"[。！？；\n]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    overloaded = []
    for s in sentences:
        de_count = s.count("的")
        if de_count > 2:
            overloaded.append({"sentence": s[:60] + ("..." if len(s) > 60 else ""), "de_count": de_count})
    total_de = text.count("的")
    total_sentences = len(sentences)
    density = round(total_de / max(total_sentences, 1), 2)
    return {
        "total_de": total_de,
        "total_sentences": total_sentences,
        "density_per_sentence": density,
        "overloaded_count": len(overloaded),
        "overloaded_samples": overloaded[:5],
    }


def check_sentence_variety(text: str) -> dict:
    """检查句式多样性：连续同主语短句、长句堆砌。"""
    sentences = re.split(r"[。！？；\n]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]

    # 连续同主语检查（连续3句以上主语相同）
    repeated_subject_streaks = []
    streak = 1
    for i in range(1, len(sentences)):
        prev_subj = sentences[i - 1][:2] if len(sentences[i - 1]) >= 2 else ""
        curr_subj = sentences[i][:2] if len(sentences[i]) >= 2 else ""
        if prev_subj and prev_subj == curr_subj:
            streak += 1
        else:
            if streak >= 3:
                repeated_subject_streaks.append({"position": i - streak, "length": streak, "subject": prev_subj})
            streak = 1
    if streak >= 3:
        repeated_subject_streaks.append({"position": len(sentences) - streak, "length": streak,
                                          "subject": sentences[-1][:2]})

    # 长句检查（单句超过80字）
    long_sentences = []
    for i, s in enumerate(sentences):
        cn_count = len(re.findall(r"[\u4e00-\u9fff]", s))
        if cn_count > 80:
            long_sentences.append({"position": i, "char_count": cn_count, "preview": s[:60] + "..."})

    return {
        "total_sentences": len(sentences),
        "repeated_subject_streaks": repeated_subject_streaks,
        "long_sentences_count": len(long_sentences),
        "long_sentences_samples": long_sentences[:3],
    }


def check_show_not_tell(text: str) -> dict:
    """检查「展示而非讲述」：标记直接陈述情绪/性格的句子。"""
    tell_patterns = [
        (r"他.{0,5}(感到|觉得|感觉到|意识到)", "情绪直接陈述"),
        (r"她.{0,5}(心中|内心|心里).{0,10}(涌起|充满|感到|感到)", "内心直接描写"),
        (r"(一种|一股).{0,10}(情感|感觉|情绪).{0,5}(涌上|袭来|充满)", "抽象情感陈述"),
        (r"(他|她)是一个.{2,10}(的人|人)", "性格标签式说明"),
        (r"(性格|为人).{0,5}(十分|非常|极其|很)", "性格直接定性"),
    ]
    issues = []
    for pattern, label in tell_patterns:
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - 5)
            end = min(len(text), m.end() + 15)
            snippet = text[start:end].replace("\n", " ")
            issues.append({"type": label, "snippet": snippet})
    return {"tell_count": len(issues), "samples": issues[:5]}


def scan_chapter(file_path: str, threshold: int = 5) -> dict:
    """综合扫描单个章节文风质量。"""
    path = Path(file_path)
    if not path.exists():
        return {"file": str(path), "exists": False, "error": f"文件不存在: {file_path}"}

    body = extract_body(path)
    cn_count = len(re.findall(r"[\u4e00-\u9fff]", body))

    waste = scan_waste_words(body)
    de = check_de_density(body)
    sentence = check_sentence_variety(body)
    show = check_show_not_tell(body)

    # 综合评级
    issues = []
    if waste["_total_hits"] > threshold:
        issues.append(f"AI废词命中 {waste['_total_hits']} 次（阈值 {threshold}）")
    if de["overloaded_count"] > 3:
        issues.append(f"\"的\"字过载句子 {de['overloaded_count']} 个")
    if sentence["repeated_subject_streaks"]:
        issues.append(f"连续同主语句 {len(sentence['repeated_subject_streaks'])} 处")
    if sentence["long_sentences_count"] > 2:
        issues.append(f"超长句子 {sentence['long_sentences_count']} 个")
    if show["tell_count"] > 3:
        issues.append(f"直接陈述 {show['tell_count']} 处")

    grade = "pass" if len(issues) == 0 else ("warn" if len(issues) <= 2 else "fail")

    return {
        "file": str(path),
        "exists": True,
        "chinese_count": cn_count,
        "grade": grade,
        "issues": issues,
        "waste_words": waste,
        "de_density": de,
        "sentence_variety": sentence,
        "show_not_tell": show,
    }


def scan_all(directory: str, pattern: str = "第*.md", threshold: int = 5) -> list:
    dp = Path(directory)
    if not dp.exists():
        print(f"错误: 目录不存在 - {directory}")
        return []
    return [scan_chapter(str(f), threshold) for f in sorted(dp.glob(pattern))]


def print_scan_results(results: list, threshold: int = 5):
    if not results:
        print("没有找到章节文件")
        return

    pass_count = warn_count = fail_count = 0
    print(f"\n{'=' * 60}\nAI废词 + 文风质量扫描报告（阈值: {threshold}）\n{'=' * 60}")

    for r in results:
        if not r.get("exists"):
            print(f"\n  {r['file']}: {r.get('error', '')}")
            continue

        grade = r["grade"]
        if grade == "pass":
            pass_count += 1
            icon = "+"
        elif grade == "warn":
            warn_count += 1
            icon = "!"
        else:
            fail_count += 1
            icon = "X"

        print(f"\n{icon} {Path(r['file']).name} | 中文: {r['chinese_count']}字 | 评级: {grade}")

        if r["issues"]:
            for iss in r["issues"]:
                print(f"    - {iss}")

        wt = r["waste_words"]
        if wt.get("_total_hits", 0) > 0:
            print(f"    废词分布:")
            for cat, words in wt.items():
                if cat.startswith("_"):
                    continue
                items = ", ".join(f"{w}({c})" for w, c in words.items())
                print(f"      [{cat}] {items}")

        de = r["de_density"]
        if de["overloaded_count"] > 0:
            print(f"    \"的\"字: 总{de['total_de']}个/{de['total_sentences']}句, 过载{de['overloaded_count']}句")

        sv = r["sentence_variety"]
        if sv["repeated_subject_streaks"]:
            for s in sv["repeated_subject_streaks"]:
                print(f"    句式: 连续同主语'{s['subject']}' x{s['length']} (位置{s['position']})")
        if sv["long_sentences_count"] > 0:
            print(f"    句式: 超长句 {sv['long_sentences_count']} 个")

        sn = r["show_not_tell"]
        if sn["tell_count"] > 0:
            print(f"    讲述: 直接陈述 {sn['tell_count']} 处")
            for s in sn["samples"][:2]:
                print(f"      [{s['type']}] {s['snippet']}")

    print(f"\n{'-' * 60}")
    print(f"总计: {len(results)} 章 | 通过: {pass_count} | 警告: {warn_count} | 不合格: {fail_count}")
    print("-" * 60)


def main():
    threshold = 5
    json_out = False
    args = sys.argv[1:]

    if not args:
        print("用法:")
        print("  python check_ai_style.py <章节文件> [--threshold N]")
        print("  python check_ai_style.py --all <目录> [--threshold N]")
        print("  python check_ai_style.py --json <章节文件>")
        return

    if "--json" in args:
        json_out = True
        args.remove("--json")
    if "--threshold" in args:
        idx = args.index("--threshold")
        threshold = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    if args[0] == "--all":
        directory = args[1] if len(args) > 1 else "."
        results = scan_all(directory, threshold=threshold)
    else:
        results = [scan_chapter(args[0], threshold)]

    if json_out:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_scan_results(results, threshold)


if __name__ == "__main__":
    main()
