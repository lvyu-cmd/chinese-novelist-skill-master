#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本质感润色建议生成脚本
为修订模式分支2（文本质感润色打磨）生成具体的逐条润色建议。
不修改原文，只输出可执行的修改建议列表。

用法:
  python suggest_polish.py <章节文件> [--json]
  python suggest_polish.py --all <目录> [--json]
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import fix_console_encoding, extract_body, count_cn

fix_console_encoding()

# ── 润色建议生成器 ──

def find_waste_suggestions(text):
    """查找AI废词并生成替换建议。"""
    from check_ai_style import WASTE, REPLACE_SUGGESTIONS
    suggestions = []
    for cat, words in WASTE.items():
        for w in words:
            count = text.count(w)
            if count == 0: continue
            locs = []
            start = 0
            for _ in range(min(count, 3)):
                idx = text.find(w, start)
                if idx == -1: break
                ctx_start = max(0, idx - 10)
                ctx_end = min(len(text), idx + len(w) + 15)
                locs.append(text[ctx_start:ctx_end].replace("\n", " "))
                start = idx + len(w)
            sug = REPLACE_SUGGESTIONS.get(w, f"删除或替换为具体动作/细节描写")
            suggestions.append({
                "type": "废词替换", "word": w, "count": count,
                "suggest": sug, "contexts": locs,
            })
    return suggestions

def find_de_overload(text):
    """查找"的"字过载句子。"""
    sents = [s.strip() for s in re.split(r"[。！？\n]", text) if len(s.strip()) > 8]
    suggestions = []
    for s in sents:
        dc = s.count("的")
        if dc > 2:
            # 分析"的"的位置，建议拆分
            de_positions = [m.start() for m in re.finditer("的", s)]
            preview = s[:80] + ("..." if len(s) > 80 else "")
            if dc == 3:
                sug = f"拆分长定语：在第二个「的」处断句，改为两句话"
            else:
                sug = f"重构长句：{dc}个「的」堆积，拆成2-3个短句，每个短句最多1个「的」"
            suggestions.append({
                "type": "的字过载", "count": dc, "sentence": preview, "suggest": sug,
            })
    return suggestions[:5]

def find_tell_instances(text):
    """查找直接陈述/讲述，建议改为展示。"""
    patterns = [
        (r"他.{0,5}(感到|觉得|感觉到|意识到)(.{2,20})", "情绪直接陈述",
         lambda m: f"删除「{m.group(1)}」，改为具体动作：角色做了什么来表达这种感受？"),
        (r"她.{0,5}(心中|内心|心里).{0,5}(涌起|充满|浮现)(.{2,20})", "内心直接描写",
         lambda m: f"删除「{m.group(1)}{m.group(2)}」，用身体反应替代：手抖了？呼吸变了？眼眶红了？"),
        (r"(一种|一股).{0,5}(情感|感觉|情绪|暖流).{0,5}(涌上|袭来|充满)", "抽象情感堆砌",
         lambda m: "删除整个句子，用一个具体细节替代（比如：她把他的杯子悄悄续满了热水）"),
        (r"目光.{0,2}(深邃|锐利|温柔|冰冷|犀利|坚定|复杂)", "目光万能修饰",
         lambda m: f"删除「{m.group(1)}」，用目光的具体行为替代：盯了多久？移开了？眨了几下？瞳孔缩了？"),
        (r"嘴角.{0,2}(微微|轻轻|缓缓|不自觉).{0,2}(上扬|勾起|弯起)", "嘴角AI公式",
         lambda m: "删除公式化描写，改为角色具体的笑容方式：咧嘴/抿嘴/露出虎牙/只有一边嘴角动"),
        (r"空气.{0,3}(凝固|凝滞|仿佛).{0,5}(安静|沉默|寂静)", "空气万能句",
         lambda m: "删除，改为具体声源的消失或出现：空调嗡嗡声突然变得很响/谁的手机响了一下又挂了"),
    ]
    suggestions = []
    for pat, label, sug_fn in patterns:
        for m in re.finditer(pat, text):
            s = max(0, m.start() - 5)
            e = min(len(text), m.end() + 15)
            suggestions.append({
                "type": label,
                "original": text[s:e].replace("\n", " "),
                "suggest": sug_fn(m),
            })
    return suggestions[:8]

def find_rhythm_issues(text):
    """查找节奏问题。"""
    from check_ai_style import check_tension, check_breathing
    suggestions = []

    tn = check_tension(text)
    if tn["peaks"] < 2:
        suggestions.append({
            "type": "节奏单调",
            "original": f"张力波峰仅{tn['peaks']}个",
            "suggest": "在章节中部插入一个冲突/意外/新信息。可以是：一个新人物出现、一条坏消息、一个秘密被发现、一次误会升级",
        })

    br = check_breathing(text)
    if br.get("dialog_streak_over5"):
        suggestions.append({
            "type": "纯对话流",
            "original": f"连续{br['max_dialog_streak']}段纯对话",
            "suggest": "在第3段对话后插入非对话内容：一个微表情（皱眉/低头/转杯子）、一个环境细节（窗外的雨声/手机震动）、一个心理闪念",
        })

    # 检查结尾钩子
    last_200 = text[-200:]
    if not re.search(r"(突然|忽然|但是|然而|只是|没想到|门|电话|声音|消息|发现|看见|出现|转身|回头)", last_200):
        suggestions.append({
            "type": "结尾无力",
            "original": "最后200字缺少钩子标记",
            "suggest": "在章节最后一段加入钩子：一个新出现的人物/一封未拆的信/一句意味深长的话/一个反常细节",
        })

    return suggestions

def find_paragraph_issues(text):
    """查找段落问题。"""
    suggestions = []
    paras = [p.strip() for p in text.split("\n") if p.strip()]

    # 超长段落
    for i, p in enumerate(paras):
        cn = len(re.findall(r"[\u4e00-\u9fff]", p))
        if cn > 200:
            preview = p[:60] + "..."
            suggestions.append({
                "type": "超长段落",
                "original": f"第{i+1}段 ({cn}字): {preview}",
                "suggest": f"在{cn // 2}字左右的位置找一个自然断点（场景切换/视角转移/时间跳跃处）拆为两段",
            })
    return suggestions[:3]

def generate_suggestions(file_path):
    """生成单个章节的润色建议。"""
    p = Path(file_path)
    if not p.exists():
        return {"file": str(p), "exists": False, "error": "文件不存在"}

    body = extract_body(p)
    cn = count_cn(body)

    all_suggestions = []
    all_suggestions.extend(find_waste_suggestions(body))
    all_suggestions.extend(find_de_overload(body))
    all_suggestions.extend(find_tell_instances(body))
    all_suggestions.extend(find_rhythm_issues(body))
    all_suggestions.extend(find_paragraph_issues(body))

    # 按类型分组
    by_type = {}
    for s in all_suggestions:
        t = s["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(s)

    return {
        "file": str(p), "exists": True, "cn": cn,
        "total_suggestions": len(all_suggestions),
        "by_type": {k: len(v) for k, v in by_type.items()},
        "suggestions": all_suggestions,
    }

def generate_all(directory):
    dp = Path(directory)
    if not dp.exists():
        print(f"错误: 目录不存在 - {directory}")
        return []
    return [generate_suggestions(str(f)) for f in sorted(dp.glob("第*.md"))]

def print_suggestions(results):
    if not results:
        print("没有找到章节文件")
        return

    print(f"\n{'='*64}")
    print(f" 文本质感润色建议")
    print(f"{'='*64}")

    for r in results:
        if not r.get("exists"):
            print(f"\n  {r['file']}: {r.get('error','')}")
            continue

        sugs = r["suggestions"]
        by_type = r["by_type"]
        print(f"\n  {Path(r['file']).name} | 中文: {r['cn']} | 建议: {len(sugs)} 条")
        if by_type:
            print(f"  分布: {', '.join(f'{k}({v})' for k,v in by_type.items())}")

        for s in sugs[:12]:
            print(f"\n  [{s['type']}]")
            if "original" in s:
                print(f"    原文: {s['original']}")
            if "word" in s:
                print(f"    词语: \"{s['word']}\" x{s.get('count',1)}")
                if s.get("contexts"):
                    print(f"    上下文: ...{s['contexts'][0]}...")
            print(f"    建议: {s['suggest']}")

    # 汇总
    valid = [r for r in results if r.get("exists")]
    if valid:
        total_sugs = sum(r["total_suggestions"] for r in valid)
        print(f"\n{'─'*64}")
        print(f" 总计: {len(valid)} 章 | 润色建议: {total_sugs} 条")
        # 汇总类型分布
        type_total = {}
        for r in valid:
            for t, c in r.get("by_type", {}).items():
                type_total[t] = type_total.get(t, 0) + c
        if type_total:
            print(f" 类型分布:")
            for t, c in sorted(type_total.items(), key=lambda x: -x[1]):
                print(f"   {t}: {c}")
        print(f"{'─'*64}")

def main():
    args = sys.argv[1:]
    if not args:
        print("用法: python suggest_polish.py [--json] [--all] <目标>")
        return
    json_out = "--json" in args
    if json_out: args.remove("--json")
    is_all = "--all" in args
    if is_all: args.remove("--all")
    if is_all:
        results = generate_all(args[0])
    else:
        results = [generate_suggestions(args[0])]
    if json_out:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_suggestions(results)

if __name__ == "__main__":
    main()