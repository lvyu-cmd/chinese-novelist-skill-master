#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节质量深度评分脚本
从专业网文作者视角，对章节进行8维度深度评分。
每个维度0-10分，总分0-80分。输出评分报告+改进建议。

用法:
  python score_chapter.py <章节文件> [--json]
  python score_chapter.py --all <目录> [--json]
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import fix_console_encoding, extract_body, count_cn

fix_console_encoding()

# ── 评分维度定义 ──
DIMENSIONS = [
    "开篇吸引力",
    "感官沉浸度",
    "人物声音辨识度",
    "信息释放节奏",
    "情绪感染力",
    "张力曲线",
    "段落呼吸感",
    "文风自然度",
]

# ── 维度1：开篇吸引力 ──
def score_opening(text):
    sents = [s.strip() for s in re.split(r"[。！？\n]", text) if len(s.strip()) > 3]
    first_500 = text[:500]
    issues = []
    score = 10

    # 检查前500字是否有冲突/悬念/异常（与TENSION_MARKERS对齐的8类词库）
    conflict_markers = re.compile(
        r"(突然|猛地|一下|猛然|骤然|瞬间|刹那|一把|一拳|一脚"
        r"|摔|砸|砍|刺|捅|扎|炸|崩|碎|裂"
        r"|杀|死|血|伤"
        r"|枪|刀|剑|刃|弹|箭"
        r"|踹|踢|撞|推|掐|摁|顶|挠|拧|拽|扯|拖"
        r"|摸到|抓到|握住|掏出|拔出|抽出|摸出"
        r"|绕到|闪到|冲到|扑到|逼到|逼近"
        r"|冷的|利器|凶器"
        r"|数到|来不及|跑不掉|逃不掉"
        r"|不对|不对劲|出事|完了|糟了|坏了"
        r"|秘密|真相|反常|奇怪|意外|危机|危险|威胁"
        r"|不能|不行|不要|住手|站住|别动"
        r"|冷笑|苦笑|嗤笑|咧嘴)"
    )
    hits = len(conflict_markers.findall(first_500))
    if hits == 0:
        score -= 4
        issues.append("前500字无冲突/悬念/异常标记")

    # 检查是否以静态/抽象虚词开头（AI典型废词开场）
    static_openers = re.compile(r"^(此刻|顿时|霎时|随即|继而|俄顷|须臾|倏忽|蓦然|赫然|陡然|骤然|倏然|旋即|未几|霎时间|一刹那|恍然)")
    if static_openers.match(first_500.strip()):
        score -= 3
        issues.append("以AI虚词开头，静态抽象，缺乏吸引力")
    # 检查是否以对话/动作开场
    elif first_500.strip().startswith(('"', '"', '「', '*')):
        score += 0  # 好的开场
    elif re.match(r"^(今天|这天|那天|清晨|早晨|晚上|深夜|阳光|月光|天气)", first_500.strip()):
        score -= 3
        issues.append("以天气/时间描述开头，缺乏吸引力")

    # 检查是否有环境信息倾倒
    env_sentences = len(re.findall(r"(位于|坐落于|建于|创建于|成立|年代|历史|背景|传说)", first_500))
    if env_sentences > 2:
        score -= 2
        issues.append(f"前500字有{env_sentences}处信息倾倒")

    return max(0, score), issues

# ── 维度2：感官沉浸度 ──
def score_senses(text):
    from check_ai_style import SENSE_PATTERNS
    counts = {}
    found = []
    for name, pat in SENSE_PATTERNS.items():
        h = len(pat.findall(text))
        counts[name] = h
        if h > 0: found.append(name)
    issues = []
    score = len(found) * 2  # 每种感官2分

    if len(found) < 3:
        issues.append(f"仅覆盖{len(found)}种感官 ({','.join(found)})，建议补充")
    if counts.get("视觉", 0) > 0 and counts.get("听觉", 0) == 0:
        issues.append("视觉偏重，建议补充听觉/触觉细节")
    if counts.get("嗅觉", 0) == 0 and counts.get("味觉", 0) == 0:
        issues.append("缺少嗅觉/味觉，场景缺少生活气息")

    # 场景段落感官密度
    paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80]
    thin = 0
    for para in paras:
        ps = sum(1 for _, pat in SENSE_PATTERNS.items() if pat.search(para))
        if ps < 2 and len(para) > 100:
            thin += 1
    if thin > len(paras) * 0.4 and len(paras) > 2:
        score -= 2
        issues.append(f"{thin}/{len(paras)}个场景段落感官单薄")

    return max(0, min(10, score)), issues

# ── 维度3：人物声音辨识度 ──
def score_voice(text):
    dialogs = re.findall(r'[""「](.*?)[""」]', text)
    if not dialogs:
        return 3, ["全文无对话"]

    issues = []
    score = 6  # 基础分

    # 检查是否有角色标签（说话人区分）
    speech_tags = re.findall(r'(他|她|[^\s""「」]{1,4})\s*(?:说|道|问|答|喊|叫|笑|叹|吼|低声道|轻声道)', text)
    unique_speakers = set(s for s in speech_tags if len(s) <= 4)
    if len(unique_speakers) >= 3:
        score += 2
    elif len(unique_speakers) >= 2:
        score += 1

    # 检查对话是否有潜台词（不只是信息传递）
    info_only = 0
    for d in dialogs[:10]:
        if re.match(r"^(我|你|他|她).{0,5}(是|在|有|要|会|能|去|来)", d.strip()):
            info_only += 1
    if info_only > len(dialogs[:10]) * 0.5:
        score -= 2
        issues.append(f"对话偏信息传递型 ({info_only}/{min(len(dialogs),10)})，缺少潜台词")

    # 检查是否有口语化表达
    colloquial = len(re.findall(r"(嘛|呗|呗|呢|啊|呀|哦|嗯|哎|嘿|哼|切|靠|我去|什么鬼|搞什么|怎么回事|得了|算了|行了|好了|得了吧|拉倒吧)", text))
    if colloquial >= 3:
        score += 1
    elif colloquial == 0:
        issues.append("对话缺少口语化表达，偏书面")
        score -= 1

    return max(0, min(10, score)), issues

# ── 维度4：信息释放节奏 ──
def score_info_release(text):
    score = 7
    issues = []

    # 检查是否有大段信息倾倒（连续陈述句无对话/动作打断）
    sents = [s.strip() for s in re.split(r"[。！？\n]", text) if len(s.strip()) > 5]
    info_dump_streak = 0
    max_dump = 0
    for s in sents:
        is_info = bool(re.search(r"(是|属于|分为|包括|由|组成|共有|共有|共有)", s))
        has_dialog = '"' in s or '"' in s or '「' in s
        has_action = bool(re.search(r"(走|跑|拿|放|看|听|转|站|坐|躺|伸|握|推|拉|打开|关上)", s))
        if is_info and not has_dialog and not has_action:
            info_dump_streak += 1
            max_dump = max(max_dump, info_dump_streak)
        else:
            info_dump_streak = 0
    if max_dump > 5:
        score -= 3
        issues.append(f"信息倾倒: 连续{max_dump}句纯陈述无动作/对话打断")
    elif max_dump > 3:
        score -= 1
        issues.append(f"轻微信息倾倒: 连续{max_dump}句纯陈述")

    # 检查是否有「直接告诉读者」而非暗示
    direct_tell = len(re.findall(r"(原来|其实|事实上|实际上|众所周知|很明显|显然|当然)", text))
    if direct_tell > 3:
        score -= 2
        issues.append(f"直接告知读者{direct_tell}次，建议用场景/线索暗示替代")

    return max(0, min(10, score)), issues

# ── 维度5：情绪感染力 ──
def score_emotion(text):
    from check_ai_style import WASTE
    score = 7
    issues = []

    # 检查情绪标签词（弱写法）
    emotion_labels = WASTE.get("情绪标签", [])
    label_count = sum(text.count(w) for w in emotion_labels)
    if label_count > 3:
        score -= 3
        issues.append(f"情绪标签词{label_count}个，建议用具体动作/细节替代")
    elif label_count > 1:
        score -= 1
        issues.append(f"情绪标签词{label_count}个")

    # 检查是否有共鸣锚点
    anchors = len(re.findall(r"(不公平|凭什么|为什么|没人|不懂|不信|不理解|不甘|差一点|就差|如果当初|要是|早知道)", text))
    if anchors >= 2:
        score += 2
    elif anchors >= 1:
        score += 1
    else:
        issues.append("缺少共鸣锚点（不公平感/被误解/不甘心等）")

    # 检查情绪变化（不是全程一种情绪）
    positive = len(re.findall(r"(笑|开心|高兴|欢喜|温暖|感动|希望|幸福|甜蜜|满足)", text))
    negative = len(re.findall(r"(哭|痛|苦|恨|怒|怕|绝望|悲伤|孤独|恐惧|焦虑)", text))
    if positive > 0 and negative > 0:
        score += 1  # 有情绪温差
    elif positive == 0 and negative == 0:
        issues.append("缺少明确的情绪锚点")

    return max(0, min(10, score)), issues

# ── 维度6：张力曲线 ──
def score_tension(text):
    from check_ai_style import check_tension
    result = check_tension(text)
    peaks = result.get("peaks", 0)
    issues = []
    score = min(peaks * 3, 9)  # 每个波峰3分，上限9分

    if peaks < 2:
        issues.append(f"张力波峰仅{peaks}个，需>=2")

    # 检查结尾是否有钩子
    last_200 = text[-200:]
    hook_markers = len(re.findall(
        r"(突然|忽然|但是|然而|只是|没想到|门|电话|声音|消息|发现|看见|看到|出现"
        r"|转身|回头|开口|笑了|不对|冷的|顶|掏出|拔出|逼近|站住)", last_200))
    if hook_markers > 0:
        score += 1
    else:
        issues.append("结尾200字缺少钩子标记")
        score -= 1

    return max(0, min(10, score)), issues

# ── 维度7：段落呼吸感 ──
def score_breathing(text):
    from check_ai_style import check_breathing
    result = check_breathing(text)
    issues = []
    score = 7

    if result.get("dialog_streak_over5"):
        score -= 3
        issues.append(f"纯对话流: 连续{result['max_dialog_streak']}段")
    elif result.get("max_dialog_streak", 0) > 3:
        score -= 1
        issues.append(f"对话连续{result['max_dialog_streak']}段，建议穿插非对话内容")

    if result.get("long_paras", 0) > 3:
        score -= 2
        issues.append(f"超长段落{result['long_paras']}个，网文读者视觉疲劳")

    # 检查段落长度变化
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    lens = [len(re.findall(r"[\u4e00-\u9fff]", p)) for p in paras]
    lens = [l for l in lens if l > 0]
    if lens:
        avg = sum(lens) / len(lens)
        variance = sum((l - avg) ** 2 for l in lens) / len(lens)
        cv = (variance ** 0.5) / max(avg, 1)
        if cv < 0.3 and len(lens) >= 4:
            score -= 1
            issues.append("段落长度变化不足，节奏单调")

    return max(0, min(10, score)), issues

# ── 维度8：文风自然度 ──
def score_naturalness(text):
    from check_ai_style import scan_waste, check_de, check_variety, check_tell
    score = 10
    issues = []

    wt = scan_waste(text)
    if wt["_total"] > 5:
        score -= 3
        issues.append(f"AI废词{wt['_total']}个")
    elif wt["_total"] > 2:
        score -= 1

    de = check_de(text)
    if de["overloaded"] > 5:
        score -= 2
        issues.append(f'"的"过载{de["overloaded"]}句')
    elif de["overloaded"] > 3:
        score -= 1

    var = check_variety(text)
    if var["repeated"]:
        score -= min(3, len(var["repeated"]))
        issues.append(f"连续同主语{len(var['repeated'])}处")
    if var["similar_length_streaks"] > 2:
        score -= 1
        issues.append(f"句式长度单调{var['similar_length_streaks']}处")

    tell = check_tell(text)
    if tell["count"] > 3:
        score -= 2
        issues.append(f"公式化描写{tell['count']}处")

    return max(0, min(10, score)), issues

# ── 综合评分 ──
def score_chapter(file_path):
    p = Path(file_path)
    if not p.exists():
        return {"file": str(p), "exists": False, "error": f"文件不存在"}

    body = extract_body(p)
    cn = count_cn(body)

    scorers = [
        score_opening, score_senses, score_voice, score_info_release,
        score_emotion, score_tension, score_breathing, score_naturalness,
    ]

    results = {}
    total = 0
    all_issues = []
    for dim, scorer in zip(DIMENSIONS, scorers):
        sc, iss = scorer(body)
        results[dim] = {"score": sc, "issues": iss}
        total += sc
        for i in iss:
            all_issues.append(f"[{dim}] {i}")

    grade = "S" if total >= 70 else "A" if total >= 60 else "B" if total >= 50 else "C" if total >= 40 else "D"

    return {
        "file": str(p), "exists": True, "cn": cn,
        "total": total, "max": 80, "grade": grade,
        "dimensions": results, "all_issues": all_issues,
    }

def score_all(directory):
    dp = Path(directory)
    if not dp.exists():
        print(f"错误: 目录不存在 - {directory}")
        return []
    return [score_chapter(str(f)) for f in sorted(dp.glob("第*.md"))]

def print_scores(results):
    if not results:
        print("没有找到章节文件")
        return

    print(f"\n{'='*64}")
    print(f" 章节质量深度评分报告 (8维度, 满分80)")
    print(f"{'='*64}")

    for r in results:
        if not r.get("exists"):
            print(f"\n  {r['file']}: {r.get('error','')}")
            continue

        g = r["grade"]
        t = r["total"]
        print(f"\n  [{g}] {Path(r['file']).name} | 中文: {r['cn']} | 总分: {t}/80")
        print(f"  {'─'*56}")

        for dim in DIMENSIONS:
            d = r["dimensions"][dim]
            bar = "#" * d["score"] + "." * (10 - d["score"])
            print(f"  {bar} {d['score']:>2}/10  {dim}")
            for iss in d["issues"][:2]:
                print(f"           -> {iss}")

    # 汇总
    valid = [r for r in results if r.get("exists")]
    if valid:
        avg = sum(r["total"] for r in valid) / len(valid)
        print(f"\n{'─'*64}")
        print(f" 总计: {len(valid)} 章 | 平均: {avg:.1f}/80")
        grade_dist = {}
        for r in valid:
            grade_dist[r["grade"]] = grade_dist.get(r["grade"], 0) + 1
        print(f" 评级分布: {' '.join(f'{g}:{c}' for g,c in sorted(grade_dist.items()))}")
        print(f"{'─'*64}")

def main():
    args = sys.argv[1:]
    if not args:
        print("用法: python score_chapter.py [--json] [--all] <目标>")
        return
    json_out = "--json" in args
    if json_out: args.remove("--json")
    is_all = "--all" in args
    if is_all: args.remove("--all")
    if is_all:
        results = score_all(args[0])
    else:
        results = [score_chapter(args[0])]
    if json_out:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_scores(results)

if __name__ == "__main__":
    main()
