#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI废词 + 文风质量扫描脚本 (V2 - 专业网文作者视角)
覆盖：AI废词(6类词库) / "的"字密度 / 句式多样性 / 展示vs讲述 /
      感官丰富度 / 节奏波峰检测 / 段落呼吸感 / 叙述声音检测

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

# ── AI废词库（6类，覆盖网文高频问题词） ──
WASTE = {
    "高频虚词": [
        "此刻","见状","随即","不由得","不禁","霎时","倏然",
        "蓦然","恍然","赫然","陡然","骤然","旋即","继而",
        "未几","俄顷","倏忽","须臾","霎时间","一刹那",
    ],
    "空洞修饰": [
        "仿佛","宛如","犹如","恰似","恍若","好似",
        "油然而生","心潮澎湃","热血沸腾","百感交集",
        "五味杂陈","感慨万千","思绪万千","百转千回",
        "难以名状","不可言喻","无以言表","莫名其妙",
    ],
    "AI套话": [
        "彰显","诠释","赋能","映射","勾勒","铸就",
        "谱写了","书写了","绽放出","迸发出","如同一幅画卷",
        "宛如一首诗","宛若仙境","美不胜收","叹为观止",
        "令人叹服","令人折服","令人钦佩","令人震撼",
    ],
    "四字堆砌": [
        "波澜壮阔","惊心动魄","荡气回肠","扣人心弦",
        "如梦似幻","如诗如画","美轮美奂","巧夺天工",
        "气势磅礴","排山倒海","翻天覆地","日新月异",
        "惊世骇俗","震古烁今","前无古人","登峰造极",
        "炉火纯青","出神入化","鬼斧神工","天衣无缝",
    ],
    "情绪标签": [
        "心中一暖","心头一颤","心中一沉","心中一喜",
        "暗自思忖","暗自心惊","暗自庆幸","暗自恼怒",
        "不由自主","情不自禁","鬼使神差","身不由己",
        "义愤填膺","怒火中烧","悲痛欲绝","欣喜若狂",
        "心如刀割","肝肠寸断","魂飞魄散","魂不守舍",
    ],
    "过度修饰": [
        "绝美","倾国倾城","沉鱼落雁","闭月羞花",
        "剑眉星目","面如冠玉","目若朗星","唇红齿白",
        "冰肌玉骨","肤若凝脂","吹弹可破","明眸皓齿",
        "万丈光芒","璀璨夺目","熠熠生辉","耀眼夺目",
    ],
}

ALL_WASTE = []
for v in WASTE.values():
    ALL_WASTE.extend(v)

# ── 强写法替换建议 ──
REPLACE_SUGGESTIONS = {
    # -- 高频虚词 (20词) --
    "此刻": "删除，直接进入动作/场景，不要用时间标记词开场",
    "见状": "删除，直接写角色看到后的具体动作反应",
    "随即": "删除，直接衔接下一个动作，用句号或逗号连接",
    "不由得": "删除，直接写动作本身",
    "不禁": "删除，直接写动作本身",
    "霎时": "删除，用具体感官变化替代：光线一暗/声音断了/手一抖",
    "倏然": "删除，用具体动作替代：猛地/一下/身子一缩",
    "蓦然": "删除，用具体动作替代：停下脚步/转过头/手顿住",
    "恍然": "删除，直接写角色的具体反应动作",
    "赫然": "删除，用具体视觉冲击替代：一眼看到/撞进视线",
    "陡然": "删除，用具体动作替代：猛地/一下子/身子一僵",
    "骤然": "删除，用具体感官变化替代：声音断了/空气一沉",
    "旋即": "删除，直接衔接下一个动作",
    "继而": "删除，直接用句号连接两句话",
    "未几": "删除，直接写时间跳转场景",
    "俄顷": "删除，直接写下一个动作",
    "倏忽": "删除，用具体动作替代",
    "须臾": "删除，用具体动作替代：停了一拍/顿了两秒",
    "霎时间": "删除，用具体感官冲击替代",
    "一刹那": "删除，用具体动作/感官替代",
    # -- 空洞修饰 (16词) --
    "仿佛": "用具体比喻替代：像X一样/和X一个样/跟X似的",
    "宛如": "删除，用具体细节替代",
    "犹如": "删除，用具体比喻替代",
    "恰似": "删除，用具体比喻替代",
    "恍若": "删除，用具体比喻替代",
    "好似": "删除，用具体比喻替代",
    "油然而生": "删除，用一个具体动作替代：深吸一口气/攥紧了手",
    "心潮澎湃": "用生理反应替代：心跳加速/呼吸变粗/手心出汗",
    "热血沸腾": "用生理反应替代：太阳穴突突跳/攥紧拳头/牙关咬紧",
    "百感交集": "删除，用一个具体的情绪动作替代：嘴唇抖了一下/说不出话",
    "五味杂陈": "删除，用一个具体反应替代：喉头发紧/鼻子一酸",
    "感慨万千": "删除，用具体动作替代：叹了口气/点了根烟/沉默了很久",
    "思绪万千": "删除，用具体动作替代：盯着天花板/转着手里的杯子",
    "百转千回": "删除，用具体心理动作替代：想了想又咽回去/话到嘴边",
    "难以名状": "删除，用具体感官描写替代",
    "不可言喻": "删除，用具体感官描写替代",
    # -- AI套话 (17词) --
    "彰显": "删除，用具体场景/行为替代",
    "诠释": "删除，用具体动作替代",
    "赋能": "删除，这不是小说用语，直接删",
    "映射": "删除，用具体场景替代",
    "勾勒": "删除，用具体视觉描写替代",
    "铸就": "删除，用具体过程描写替代",
    "谱写了": "删除，用具体事件替代",
    "书写了": "删除，用具体事件替代",
    "绽放出": "删除，用具体视觉描写替代",
    "迸发出": "删除，用具体动作替代：猛地站起来/一拳砸在桌上",
    "如同一幅画卷": "删除，用具体场景细节替代",
    "宛如一首诗": "删除，用具体场景细节替代",
    "宛若仙境": "删除，用具体场景细节替代：雾气/光线/水声",
    "美不胜收": "删除，用2-3个具体视觉细节替代",
    "叹为观止": "删除，用具体视觉冲击+角色反应替代",
    "令人叹服": "删除，用具体行为结果替代",
    "令人折服": "删除，用具体行为结果替代",
    # -- 四字堆砌 (20词) --
    "波澜壮阔": "删除，用具体场景规模描写替代：人山人海/一眼望不到头",
    "惊心动魄": "删除，用具体紧张动作替代：手抖/心跳到嗓子眼",
    "荡气回肠": "删除，用具体情绪反应替代：说不出话/眼眶发热",
    "扣人心弦": "删除，用具体悬念细节替代",
    "如梦似幻": "删除，用具体光影/触感描写替代",
    "如诗如画": "删除，用2-3个具体场景细节替代",
    "美轮美奂": "删除，用具体建筑/装饰细节替代",
    "巧夺天工": "删除，用具体工艺细节替代",
    "气势磅礴": "删除，用具体规模描写替代：多少人/多大/多高",
    "排山倒海": "删除，用具体力量描写替代：地面在震/灰尘腾起",
    "翻天覆地": "删除，用具体变化描写替代",
    "日新月异": "删除，用具体变化对比替代",
    "惊世骇俗": "删除，用具体旁人反应替代",
    "震古烁今": "删除，用具体成就描写替代",
    "前无古人": "删除，用具体成就描写替代",
    "登峰造极": "删除，用具体技术细节替代",
    "炉火纯青": "删除，用具体技术动作描写替代",
    "出神入化": "删除，用具体技术动作描写替代",
    "鬼斧神工": "删除，用具体细节描写替代",
    "天衣无缝": "删除，用具体过程描写替代",
    # -- 情绪标签 (20词) --
    "心中一暖": "用具体动作替代：嘴角不自觉弯了/喉头一紧/眼眶发酸",
    "心头一颤": "用生理反应替代：手一抖/杯子差点掉了/呼吸停了一拍",
    "心中一沉": "用生理反应替代：胃像被攥住/呼吸一滞/后背发凉",
    "心中一喜": "用具体反应替代：眼睛亮了/嘴角翘起来/脚步加快",
    "暗自思忖": "删除，直接写思考内容或用停顿/皱眉等微表情替代",
    "暗自心惊": "用生理反应替代：后背一凉/手心冒汗/瞳孔缩了",
    "暗自庆幸": "用具体动作替代：悄悄松了口气/擦了把冷汗",
    "暗自恼怒": "用具体动作替代：咬了咬后槽牙/攥紧了拳头/鼻翼翕动",
    "不由自主": "删除，直接写动作本身",
    "情不自禁": "删除，直接写动作本身",
    "鬼使神差": "删除，直接写角色做出的具体动作",
    "身不由己": "删除，用具体困境描写替代",
    "义愤填膺": "用具体行为替代：拳头攥紧/太阳穴突突跳/牙关咬得咯咯响",
    "怒火中烧": "用具体行为替代：眼眶发红/青筋暴起/指甲掐进肉里",
    "悲痛欲绝": "用具体行为替代：蹲在地上/蜷成一团/发不出声",
    "欣喜若狂": "用具体行为替代：跳起来/跑了出去/笑得停不下来",
    "心如刀割": "用具体生理反应替代：胸口像被拧/喘不上气/手在抖",
    "肝肠寸断": "用具体行为替代：蹲下来抱住自己/说不出一句完整的话",
    "魂飞魄散": "用具体行为替代：腿一软/脑子一片空白/钉在原地",
    "魂不守舍": "用具体行为替代：叫了三声才听到/走路撞到门框",
    # -- 过度修饰 (20词) --
    "绝美": "删除，用具体五官特征描写替代",
    "倾国倾城": "删除，用具体五官特征+旁人反应替代",
    "沉鱼落雁": "删除，用具体五官+旁人行为替代：回头率/看呆了",
    "闭月羞花": "删除，用具体五官特征替代",
    "剑眉星目": "删除，用具体面部特征替代：眉骨很高/眼睛很亮",
    "面如冠玉": "删除，用具体肤色/质感描写替代",
    "目若朗星": "删除，用具体眼神描写替代：盯了多久/目光落在哪",
    "唇红齿白": "删除，用具体特征替代：嘴唇抿着/露出一颗虎牙",
    "冰肌玉骨": "删除，用具体触感描写替代：皮肤凉/骨头硌手",
    "肤若凝脂": "删除，用具体触感/视觉描写替代",
    "吹弹可破": "删除，用具体细节替代：一碰就红/掐一下就留印",
    "明眸皓齿": "删除，用具体眼睛/牙齿描写替代",
    "万丈光芒": "删除，用具体光源描写替代：灯/火/阳光",
    "璀璨夺目": "删除，用具体光源细节替代：闪得睁不开眼/晃了一下",
    "熠熠生辉": "删除，用具体材质/光源描写替代",
    "耀眼夺目": "删除，用具体光源描写替代",
}

def scan_waste(text):
    result = {}
    total = 0
    suggestions = []
    for cat, words in WASTE.items():
        found = {}
        for w in words:
            c = text.count(w)
            if c > 0:
                found[w] = c
                total += c
                if w in REPLACE_SUGGESTIONS:
                    suggestions.append({"word": w, "count": c, "suggest": REPLACE_SUGGESTIONS[w]})
        if found:
            result[cat] = found
    result["_total"] = total
    result["_suggestions"] = suggestions[:8]
    return result

def check_de(text):
    sents = [s.strip() for s in re.split(r"[。！？；\n]", text) if len(s.strip()) > 5]
    overloaded = []
    for s in sents:
        dc = s.count("的")
        if dc > 2:
            overloaded.append({"s": s[:80] + ("..." if len(s) > 80 else ""), "n": dc})
    total_de = text.count("的")
    cn_total = len(re.findall(r"[一-鿿]", text))
    ratio = round(total_de / max(cn_total, 1) * 100, 1)
    return {
        "total": total_de, "sents": len(sents),
        "density": round(total_de / max(len(sents), 1), 2),
        "ratio_pct": ratio,
        "overloaded": len(overloaded),
        "samples": overloaded[:5],
    }

def check_variety(text):
    sents = [s.strip() for s in re.split(r"[。！？；\n]", text) if len(s.strip()) > 3]
    # 连续同主语
    streaks = []
    streak = 1
    for i in range(1, len(sents)):
        if len(sents[i-1]) >= 2 and len(sents[i]) >= 2 and sents[i-1][:2] == sents[i][:2]:
            streak += 1
        else:
            if streak >= 3:
                streaks.append({"pos": i - streak, "len": streak, "subj": sents[i-1][:2]})
            streak = 1
    if streak >= 3:
        streaks.append({"pos": len(sents) - streak, "len": streak, "subj": sents[-1][:2]})
    # 超长句
    long_s = []
    for i, s in enumerate(sents):
        cn = len(re.findall(r"[\u4e00-\u9fff]", s))
        if cn > 80:
            long_s.append({"pos": i, "chars": cn, "preview": s[:60] + "..."})
    # 连续长度相近句
    len_similar = 0
    cn_lens = [len(re.findall(r"[\u4e00-\u9fff]", s)) for s in sents]
    for i in range(2, len(cn_lens)):
        if cn_lens[i-2] > 0 and cn_lens[i-1] > 0 and cn_lens[i] > 0:
            avg = (cn_lens[i-2] + cn_lens[i-1] + cn_lens[i]) / 3
            if all(abs(l - avg) / max(avg, 1) < 0.2 for l in [cn_lens[i-2], cn_lens[i-1], cn_lens[i]]):
                len_similar += 1
    return {
        "sents": len(sents),
        "repeated": streaks,
        "long_count": len(long_s),
        "long_samples": long_s[:3],
        "similar_length_streaks": len_similar,
    }

def check_tell(text):
    patterns = [
        (r"他.{0,5}(感到|觉得|感觉到|意识到)", "情绪直接陈述"),
        (r"她.{0,5}(心中|内心|心里).{0,10}(涌起|充满|感到|浮现)", "内心直接描写"),
        (r"(一种|一股).{0,10}(情感|感觉|情绪|暖流).{0,5}(涌上|袭来|充满|弥漫)", "抽象情感陈述"),
        (r"(他|她)是一个.{2,10}(的人|人)", "性格标签说明"),
        (r"(性格|为人).{0,5}(十分|非常|极其|很|相当)", "性格直接定性"),
        (r"目光.{0,3}(深邃|锐利|温柔|冰冷|犀利)", "目光万能修饰"),
        (r"嘴角.{0,3}(微微|轻轻|缓缓|不自觉).{0,3}(上扬|勾起|弯起)", "嘴角AI公式"),
        (r"空气.{0,5}(凝固|凝滞|仿佛|安静)", "空气万能句"),
    ]
    issues = []
    for pat, label in patterns:
        for m in re.finditer(pat, text):
            s = max(0, m.start() - 5)
            e = min(len(text), m.end() + 20)
            issues.append({"type": label, "snip": text[s:e].replace("\n", " ")})
    return {"count": len(issues), "samples": issues[:6]}

# ── 感官丰富度检测 ──
SENSE_PATTERNS = {
    "视觉": re.compile(r"(看到|望着|盯|瞧|瞄|瞥|瞅|目光|光线|灯光|阳光|月色|影子|颜色|红了|白了|暗了|亮了|黑了|闪着|反光|暗下来|亮起来|看不清|眯着眼|眨了眨眼|抬眼|低眉|侧目)"),
    "听觉": re.compile(r"(听到|声音|响了|叫了|喊了|吼了|哭了|笑了|铃声|钟声|鼓声|风声|雨声|脚步声|呼吸声|心跳声|轰鸣|寂静|安静|嘈杂|嗡嗡|叮叮|咔嗒|啪的一声|咚咚|嘶嘶|砰的一声|咳了|咳嗽|喘着|叹了口气|哼了一声|啧啧|咔嚓|沙沙|窸窣)"),
    "触觉": re.compile(r"(摸了|碰了|触到|握住|抓住|捏住|冷了|热了|凉了|烫了|痛了|疼了|痒了|麻了|粗糙|光滑|柔软|坚硬|潮湿|干燥|颤抖|出汗|流泪|流血|卡在|硌着|扎手|刺痛|刮着|蹭了|摁住|抠着|挠了|拧开|拽住|扯着|拖着|掐住|顶着|压着|挤着|磨着|含着|咬着|叼着|啃着|噎住|呛了|吞下|咽下)"),
    "嗅觉": re.compile(r"(闻到|嗅到|气味|香味|臭味|腥味|烟味|花香|泥土味|血腥味|消毒水|霉味|焦味|汗味|油烟味|发霉的|铁锈味|草木味|灰烬味|烧焦的|腐臭)"),
    "味觉": re.compile(r"(尝到|吃了|喝了|嚼着|咽下|吞下|苦味|甜味|咸味|辣味|酸味|涩味|淡而无味|鲜味|油腻|干渴|嘴唇|舌头|嘴里|口水|饭菜|汤里|茶水|酒味|馒头渣|嗓子|喉咙|噎住|呛了|反胃|恶心)"),
}

def check_senses(text):
    body = text
    counts = {}
    found_senses = []
    for name, pat in SENSE_PATTERNS.items():
        hits = len(pat.findall(body))
        counts[name] = hits
        if hits > 0:
            found_senses.append(name)
    # 场景段落检测（以空行分隔的段落）
    paragraphs = [p.strip() for p in body.split("\n\n") if len(p.strip()) > 50]
    thin_paras = 0
    for para in paragraphs:
        para_senses = sum(1 for name, pat in SENSE_PATTERNS.items() if pat.search(para))
        if para_senses < 2 and len(para) > 100:
            thin_paras += 1
    return {
        "found_senses": found_senses,
        "sense_count": len(found_senses),
        "counts": counts,
        "thin_paragraphs": thin_paras,
        "total_paragraphs": len(paragraphs),
    }

# ── 节奏波峰检测 ──
# 8类张力词库：暴力动作/紧迫感/反常不对/威胁危险/身体反应/紧迫对话/破门突入/武器威胁物
# 8类张力词库：暴力动作/紧迫感/反常不对/威胁危险/身体反应/紧迫对话/破门突入/武器威胁物
TENSION_MARKERS = re.compile(
    "突然|猛地|一下|猛然|骤然|瞬间|刹那|一把|一拳|一脚"
    "|摔|砸|砍|刺|捅|扎|射|炸|崩|碎|裂|断|塌"
    "|杀|死|血|尸|亡|伤|残|废"
    "|枪|刀|剑|刃|弹|箭|矛|斧|锤|棍|棒"
    "|爆炸|崩塌|碎裂|尖叫|惨叫|怒吼|咆哮|嘶吼"
    "|危机|危险|威胁|恐惧|害怕|绝望|崩溃|慌|颤"
    "|背叛|欺骗|谎言|真相|秘密|暴露|揭穿|揭发"
    "|反转|逆转|意外|变故|突变"
    "|踹|踢|撞|推|掐|摁|顶|挠|拧|拽|扯|拖"
    "|摸到|抓到|握住|掏出|拔出|抽出|摸出"
    "|绕到|闪到|冲到|扑到|逼到|逼近"
    "|冷的|冷冰|硬邦|利器|凶器"
    "|数到|倒计|最后|来不及|跑不掉|逃不掉|出不去"
    "|不开口|不说话|沉默|没有动|不动|站住|别动|不准动"
    "|不对|不对劲|有问题|出事|出问题|完了|糟了|坏了"
    "|低头|抬头|转头|回过头|扭头"
    "|嘴角一|冷笑|苦笑|嗤笑|咧嘴"
)

def check_tension(text):
    sents = [s.strip() for s in re.split(r"[。！？\n]", text) if len(s.strip()) > 5]
    if not sents:
        return {"peaks": 0, "troughs": 0, "score": 0, "wave": []}

    wave = []
    window = 2
    for i in range(0, len(sents), window):
        chunk = "。".join(sents[i:i+window])
        hits = len(TENSION_MARKERS.findall(chunk))
        wave.append(hits)

    # 波峰 = 比前后都高的点
    peaks = 0
    for i in range(1, len(wave) - 1):
        if wave[i] > wave[i-1] and wave[i] > wave[i+1] and wave[i] >= 1:
            peaks += 1
    # 开头高张力
    if wave and wave[0] >= 2:
        peaks += 1
    # 结尾高张力
    if wave and len(wave) > 1 and wave[-1] >= 1:
        peaks += 1

    return {
        "peaks": peaks,
        "wave_summary": wave[:20],
        "total_sents": len(sents),
    }

# ── 段落呼吸感检测 ──
def check_breathing(text):
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    dialog_heavy = 0
    long_paras = 0
    mono_paras = 0

    for p in paras:
        cn_len = len(re.findall(r"[\u4e00-\u9fff]", p))
        # 纯对话段（只有引号内容）
        if re.match(r'^[""「].*[""」]\s*$', p.strip()):
            dialog_heavy += 1
        # 超长段落（超过200中文字）
        if cn_len > 200:
            long_paras += 1

    # 连续纯对话段
    dialog_streak = 0
    max_dialog_streak = 0
    for p in paras:
        if '"' in p or '"' in p or '「' in p:
            dialog_streak += 1
            max_dialog_streak = max(max_dialog_streak, dialog_streak)
        else:
            dialog_streak = 0

    return {
        "total_paras": len(paras),
        "long_paras": long_paras,
        "max_dialog_streak": max_dialog_streak,
        "dialog_streak_over5": max_dialog_streak > 5,
    }

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
    senses = check_senses(body)
    tension = check_tension(body)
    breathing = check_breathing(body)

    issues = []
    if waste["_total"] > threshold:
        issues.append(f"AI废词 {waste['_total']} 次 (阈值 {threshold})")
    if de["overloaded"] > 3:
        issues.append(f'"的"过载 {de["overloaded"]} 句 (占比{de["ratio_pct"]}%)')
    if var["repeated"]:
        issues.append(f"连续同主语 {len(var['repeated'])} 处")
    if var["long_count"] > 2:
        issues.append(f"超长句 {var['long_count']} 个")
    if var["similar_length_streaks"] > 2:
        issues.append(f"连续长度相近句 {var['similar_length_streaks']} 处")
    if tell["count"] > 3:
        issues.append(f"直接陈述/公式化描写 {tell['count']} 处")
    if senses["sense_count"] < 3:
        issues.append(f"感官覆盖不足: 仅{senses['sense_count']}种 ({','.join(senses['found_senses'])})")
    if senses["thin_paragraphs"] > 2:
        issues.append(f"场景单薄段落 {senses['thin_paragraphs']}/{senses['total_paragraphs']}")
    if tension["peaks"] < 2:
        issues.append(f"张力波峰不足: {tension['peaks']}个 (需>=2)")
    if breathing["long_paras"] > 3:
        issues.append(f"超长段落 {breathing['long_paras']} 个")
    if breathing["dialog_streak_over5"]:
        issues.append(f"纯对话流: 连续{breathing['max_dialog_streak']}段对话无非对话内容")

    grade = "pass" if not issues else ("warn" if len(issues) <= 3 else "fail")
    score = max(0, 100 - len(issues) * 10)

    return {
        "file": str(p), "exists": True, "cn": cn,
        "grade": grade, "score": score, "issues": issues,
        "waste": waste, "de": de, "variety": var, "tell": tell,
        "senses": senses, "tension": tension, "breathing": breathing,
    }

def scan_all(directory, threshold=5):
    dp = Path(directory)
    if not dp.exists():
        print(f"错误: 目录不存在 - {directory}")
        return []
    return [scan_chapter(str(f), threshold) for f in sorted(dp.glob("第*.md"))]

def print_results(results, threshold=5):
    if not results:
        print("没有找到章节文件")
        return
    pw = nw = fw = 0
    print(f"\n{'='*60}\n 文风质量深度扫描 V2 (阈值: {threshold})\n{'='*60}")
    for r in results:
        if not r.get("exists"):
            print(f"\n  {r['file']}: {r.get('error','')}")
            continue
        g = r["grade"]
        sc = r.get("score", 0)
        if g == "pass": pw += 1; ic = "+"
        elif g == "warn": nw += 1; ic = "!"
        else: fw += 1; ic = "X"
        print(f"\n{ic} {Path(r['file']).name} | 中文: {r['cn']} | 评级: {g} | 评分: {sc}/100")
        for iss in r.get("issues", []):
            print(f"    - {iss}")

        # 废词详情
        wt = r.get("waste", {})
        if wt.get("_total", 0) > 0:
            for cat, words in wt.items():
                if cat.startswith("_"): continue
                print(f"    [{cat}] {', '.join(f'{w}({c})' for w,c in words.items())}")
            for sug in wt.get("_suggestions", []):
                print(f"    >> 替换建议: \"{sug['word']}\" x{sug['count']} -> {sug['suggest']}")

        # 感官
        ss = r.get("senses", {})
        print(f"    感官: {ss.get('sense_count',0)}/5 ({','.join(ss.get('found_senses',[]))})")
        if ss.get("thin_paragraphs", 0) > 0:
            print(f"    感官单薄段: {ss['thin_paragraphs']}/{ss.get('total_paragraphs',0)}")

        # 张力
        tn = r.get("tension", {})
        print(f"    张力波峰: {tn.get('peaks',0)} | 波形: {tn.get('wave_summary',[])}")

        # 呼吸
        br = r.get("breathing", {})
        if br.get("dialog_streak_over5"):
            print(f"    纯对话流: 连续{br['max_dialog_streak']}段")
        if br.get("long_paras", 0) > 3:
            print(f"    超长段落: {br['long_paras']}个")

        # 句式
        sv = r.get("variety", {})
        for s in sv.get("repeated", [])[:2]:
            print(f"    同主语'{s['subj']}' x{s['len']}")
        if sv.get("similar_length_streaks", 0) > 2:
            print(f"    长度相近句: {sv['similar_length_streaks']}处")

        # 讲述
        sn = r.get("tell", {})
        if sn.get("count", 0) > 0:
            print(f"    讲述/公式化: {sn['count']}处")
            for t in sn.get("samples", [])[:2]:
                print(f"      [{t['type']}] {t['snip']}")

    print(f"\n{'-'*60}")
    print(f"总计: {len(results)} | 通过: {pw} | 警告: {nw} | 不合格: {fw}")
    avg = sum(r.get("score", 0) for r in results if r.get("exists")) / max(pw + nw + fw, 1)
    print(f"平均评分: {avg:.0f}/100")
    print("-" * 60)

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
        threshold = int(args[idx + 1])
        args = args[:idx] + args[idx+2:]
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
