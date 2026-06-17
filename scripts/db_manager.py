#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite 查询加速层
小说创作项目的结构化存储，用于数据量增长后的高速查询。

设计原则：
- JSON/Markdown 为主数据源，SQLite 为查询加速层（缓存）
- 所有写入操作幂等（UPSERT），可反复执行不产生重复
- 数据库位于 {项目目录}/data/novel.db
- Agent 通过预定义查询读写，无需手写 SQL

用法:
  python db_manager.py init <项目目录>                        # 初始化
  python db_manager.py sync <项目目录>                        # 全量同步
  python db_manager.py sync <项目目录> --chapter <N>          # 同步单章
  python db_manager.py query <项目目录> <查询名> [参数...]     # 预定义查询
  python db_manager.py sql <项目目录> "SELECT ..."            # 原始SQL(只读)
  python db_manager.py export <项目目录>                      # 导出统计JSON

可用查询见 main() 输出。
"""

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import fix_console_encoding, extract_body, count_cn, count_vis, load_plan

fix_console_encoding()

DB_NAME = "novel.db"
DB_DIR = "data"

# ══════════════════════════════════════════════════════════════
# Schema（8张表 + 10个索引）
# ══════════════════════════════════════════════════════════════

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- 1. 项目元数据（单行表，含五项顶层约束）
CREATE TABLE IF NOT EXISTS project (
    id                  INTEGER PRIMARY KEY CHECK (id=1),
    novel_name          TEXT,
    project_path        TEXT,
    total_chapters      INTEGER,
    min_words           INTEGER DEFAULT 3000,
    status              TEXT DEFAULT 'planning',
    writing_mode        TEXT,
    opening_background  TEXT,
    story_ending        TEXT,
    volume_outline      TEXT,
    ability_path        TEXT,
    growth_cost         TEXT,
    core_conflict       TEXT,
    conflict_escalation TEXT,
    created_at          TEXT,
    updated_at          TEXT
);

-- 2. 章节表（核心，连接评分/文风/记忆的中枢）
CREATE TABLE IF NOT EXISTS chapters (
    chapter_number       INTEGER PRIMARY KEY,
    title                TEXT,
    file_path            TEXT,
    volume               TEXT,
    status               TEXT DEFAULT 'pending',
    word_count_cn        INTEGER,
    word_count_vis       INTEGER,
    word_count_pass      INTEGER DEFAULT 0,
    retry_count          INTEGER DEFAULT 0,
    -- 8维度评分
    score_opening        INTEGER,
    score_senses         INTEGER,
    score_voice          INTEGER,
    score_info_release   INTEGER,
    score_emotion        INTEGER,
    score_tension        INTEGER,
    score_breathing      INTEGER,
    score_naturalness    INTEGER,
    score_total          INTEGER,
    score_grade          TEXT,
    -- 文风指标
    style_waste_total    INTEGER DEFAULT 0,
    style_de_overloaded  INTEGER DEFAULT 0,
    style_de_ratio_pct   REAL,
    style_tell_count     INTEGER DEFAULT 0,
    style_sense_count    INTEGER DEFAULT 0,
    style_tension_peaks  INTEGER DEFAULT 0,
    style_long_paras     INTEGER DEFAULT 0,
    style_dialog_streak  INTEGER DEFAULT 0,
    style_grade          TEXT,
    style_score          INTEGER,
    -- 大纲规划（从卷纲同步，供创作时快速查询）
    outline_core_event   TEXT,
    outline_hook         TEXT,
    outline_characters   TEXT,
    outline_scenes       TEXT,
    created_at           TEXT,
    updated_at           TEXT
);

-- 3. 伏笔表
CREATE TABLE IF NOT EXISTS foreshadowing (
    fs_id            TEXT PRIMARY KEY,
    content          TEXT,
    fs_type          TEXT,
    planted_chapter  INTEGER,
    resolve_chapter  INTEGER,
    status           TEXT DEFAULT '活跃',
    is_orphan        INTEGER DEFAULT 0,
    created_at       TEXT,
    updated_at       TEXT
);

-- 4. 人物表
CREATE TABLE IF NOT EXISTS characters (
    char_id          TEXT PRIMARY KEY,
    char_name        TEXT,
    char_type        TEXT,
    personality_core TEXT,
    fatal_flaw       TEXT,
    speaking_style   TEXT,
    first_chapter    INTEGER,
    last_chapter     INTEGER,
    raw_profile      TEXT,
    created_at       TEXT,
    updated_at       TEXT
);

-- 5. 角色出场记录
CREATE TABLE IF NOT EXISTS character_appearances (
    char_id          TEXT NOT NULL,
    chapter_number   INTEGER NOT NULL,
    role_in_chapter  TEXT,
    state_change     TEXT,
    PRIMARY KEY (char_id, chapter_number)
);

-- 6. 章节记忆（L2层，每章150-300字结构化摘要）
CREATE TABLE IF NOT EXISTS chapter_memory (
    chapter_number      INTEGER PRIMARY KEY,
    scene_location      TEXT,
    scene_time          TEXT,
    scene_mood          TEXT,
    core_event          TEXT,
    new_info            TEXT,
    relationship_change TEXT,
    suspense_closed     TEXT,
    suspense_opened     TEXT,
    suspense_active     TEXT,
    hook_scene          TEXT,
    hook_mood           TEXT,
    hook_suspense       TEXT,
    hook_unfinished     TEXT,
    foreshadow_planted  TEXT,
    foreshadow_resolved TEXT,
    foreshadow_advanced TEXT,
    raw_content         TEXT,
    created_at          TEXT,
    updated_at          TEXT
);

-- 7. 阶段总结（L1层，每10章压缩一次）
CREATE TABLE IF NOT EXISTS phase_summary (
    phase_number     INTEGER PRIMARY KEY,
    start_chapter    INTEGER,
    end_chapter      INTEGER,
    plot_summary     TEXT,
    character_arcs   TEXT,
    foreshadow_stats TEXT,
    suspense_status  TEXT,
    world_snapshot   TEXT,
    ending_anchor    TEXT,
    raw_content      TEXT,
    created_at       TEXT,
    updated_at       TEXT
);

-- 8. 修订日志
CREATE TABLE IF NOT EXISTS revision_log (
    revision_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_type    TEXT,
    target_file      TEXT,
    target_chapter   INTEGER,
    description      TEXT,
    before_hash      TEXT,
    after_hash       TEXT,
    created_at       TEXT
);

-- 索引（覆盖高频查询场景）
CREATE INDEX IF NOT EXISTS idx_ch_status    ON chapters(status);
CREATE INDEX IF NOT EXISTS idx_ch_score     ON chapters(score_total);
CREATE INDEX IF NOT EXISTS idx_ch_style     ON chapters(style_grade);
CREATE INDEX IF NOT EXISTS idx_ch_volume    ON chapters(volume);
CREATE INDEX IF NOT EXISTS idx_fs_status    ON foreshadowing(status);
CREATE INDEX IF NOT EXISTS idx_fs_resolve   ON foreshadowing(resolve_chapter);
CREATE INDEX IF NOT EXISTS idx_fs_plant     ON foreshadowing(planted_chapter);
CREATE INDEX IF NOT EXISTS idx_ch_type      ON characters(char_type);
CREATE INDEX IF NOT EXISTS idx_ap_char      ON character_appearances(char_id);
CREATE INDEX IF NOT EXISTS idx_ap_chapter   ON character_appearances(chapter_number);
CREATE INDEX IF NOT EXISTS idx_rev_type     ON revision_log(revision_type);
"""


# ══════════════════════════════════════════════════════════════
# 连接管理
# ══════════════════════════════════════════════════════════════

def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def _db_path(project_dir):
    return Path(project_dir) / DB_DIR / DB_NAME

def _conn(project_dir):
    p = _db_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db(project_dir):
    c = _conn(project_dir)
    c.executescript(SCHEMA_SQL)
    c.commit(); c.close()
    return str(_db_path(project_dir))


# ══════════════════════════════════════════════════════════════
# 同步：JSON/Markdown → SQLite（幂等UPSERT）
# ══════════════════════════════════════════════════════════════

def _extract_field(text, field_name):
    m = re.search(rf"-?\s*{re.escape(field_name)}[：:]\s*(.+?)(?:\n|$)", text)
    return m.group(1).strip() if m else None

def _extract_section(text, heading):
    """提取 Markdown 中某个 heading 下的正文到下一个同级 heading。"""
    pattern = rf"##\s*{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else None

def _sync_project_meta(conn, plan):
    tlc = plan.get("topLevelConstraints", {})
    conn.execute("""
        INSERT INTO project (id,novel_name,project_path,total_chapters,min_words,
            status,writing_mode,opening_background,story_ending,volume_outline,
            ability_path,growth_cost,core_conflict,conflict_escalation,created_at,updated_at)
        VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            novel_name=excluded.novel_name, total_chapters=excluded.total_chapters,
            status=excluded.status, writing_mode=excluded.writing_mode,
            opening_background=excluded.opening_background, story_ending=excluded.story_ending,
            volume_outline=excluded.volume_outline, ability_path=excluded.ability_path,
            growth_cost=excluded.growth_cost, core_conflict=excluded.core_conflict,
            conflict_escalation=excluded.conflict_escalation, updated_at=excluded.updated_at
    """, (
        plan.get("novelName"), plan.get("projectPath"),
        plan.get("totalChapters"), plan.get("minWordsPerChapter", 3000),
        plan.get("status"), plan.get("writingMode"),
        tlc.get("openingBackground"), tlc.get("storyEnding"),
        tlc.get("volumeOutline"), tlc.get("abilityPath"),
        tlc.get("growthCost"), tlc.get("coreConflict"),
        tlc.get("conflictEscalation"), plan.get("createdAt"), _now(),
    ))

def _sync_chapters(conn, plan, pdir, target_chapter=None):
    now = _now()
    for ch in plan.get("chapters", []):
        cn = ch.get("chapterNumber")
        if target_chapter is not None and cn != target_chapter:
            continue
        fp = ch.get("filePath", "")
        full = pdir / fp
        wc_cn = wc_vis = None
        if full.exists():
            body = extract_body(full)
            wc_cn = count_cn(body)
            wc_vis = count_vis(body)
        conn.execute("""
            INSERT INTO chapters (chapter_number,title,file_path,status,
                word_count_cn,word_count_vis,word_count_pass,retry_count,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(chapter_number) DO UPDATE SET
                title=excluded.title, file_path=excluded.file_path, status=excluded.status,
                word_count_cn=excluded.word_count_cn, word_count_vis=excluded.word_count_vis,
                word_count_pass=excluded.word_count_pass, retry_count=excluded.retry_count,
                updated_at=excluded.updated_at
        """, (cn, ch.get("title"), fp, ch.get("status"),
              wc_cn, wc_vis, 1 if ch.get("wordCountPass") else 0,
              ch.get("retryCount", 0), now, now))

def _sync_foreshadowing(conn, pdir):
    fs_file = None
    for cand in [pdir / "02-大纲" / "伏笔布局.md"]:
        if cand.exists(): fs_file = cand; break
    if not fs_file:
        for f in pdir.rglob("*伏笔*"):
            if f.is_file(): fs_file = f; break
    if not fs_file: return
    text = fs_file.read_text("utf-8")
    # 解析 Markdown 表格
    rows = re.findall(r"^\|(.+)\|$", text, re.MULTILINE)
    headers = []; done = False; now = _now()
    for raw in rows:
        cells = [c.strip() for c in raw.split("|") if c.strip()]
        if all(re.match(r"^[-:]+$", c) for c in cells): continue
        if not done and any(kw in "".join(cells) for kw in ["伏笔ID","ID","埋设","揭晓","状态"]):
            headers = [c.lower() for c in cells]; done = True; continue
        if not done or len(cells) < 4: continue
        e = {}
        for i, h in enumerate(headers):
            if i >= len(cells): break
            if "id" in h or "编号" in h: e["id"] = cells[i]
            elif "埋设" in h: e["planted"] = cells[i]
            elif "内容" in h or "描述" in h: e["content"] = cells[i]
            elif "类型" in h: e["type"] = cells[i]
            elif "揭晓" in h or "预计" in h or "回收" in h: e["resolve"] = cells[i]
            elif "状态" in h: e["status"] = cells[i]
        fs_id = e.get("id", "")
        if not fs_id: continue
        plant = resolve = None
        m = re.search(r"(\d+)", e.get("planted", ""))
        if m: plant = int(m.group(1))
        m = re.search(r"(\d+)", e.get("resolve", ""))
        if m: resolve = int(m.group(1))
        st = e.get("status", "活跃")
        conn.execute("""
            INSERT INTO foreshadowing (fs_id,content,fs_type,planted_chapter,resolve_chapter,
                status,is_orphan,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(fs_id) DO UPDATE SET
                content=excluded.content, status=excluded.status,
                is_orphan=excluded.is_orphan, updated_at=excluded.updated_at
        """, (fs_id, e.get("content"), e.get("type"), plant, resolve, st, 0, now, now))
    # 回退：列表格式
    if not done:
        for line in text.split("\n"):
            m = re.match(r"^[-*]\s*(F?\d+[.:：])\s*(.+?)(?:\(第(\d+)章", line.strip())
            if m:
                fs_id = m.group(1).rstrip(".:：")
                conn.execute("""
                    INSERT INTO foreshadowing (fs_id,content,status,created_at,updated_at)
                    VALUES (?,?,?,?,?)
                    ON CONFLICT(fs_id) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at
                """, (fs_id, m.group(2).strip(), "活跃", now, now))
    # 计算孤儿伏笔
    completed = set()
    for ch in conn.execute("SELECT chapter_number FROM chapters WHERE status='completed'").fetchall():
        completed.add(ch[0])
    conn.execute("UPDATE foreshadowing SET is_orphan=0")
    conn.execute("""
        UPDATE foreshadowing SET is_orphan=1
        WHERE resolve_chapter IN (SELECT chapter_number FROM chapters WHERE status='completed')
          AND status NOT IN ('已回收','已揭晓','完成','closed','resolved')
    """)

def _sync_characters(conn, pdir):
    char_dir = pdir / "01-人物卡"
    if not char_dir.exists(): return
    now = _now()
    type_map = {"主角.md":"主角","重要角色.md":"重要角色","次要角色.md":"次要角色",
                "重要反派.md":"重要反派","次要反派.md":"次要反派"}
    for fname, ctype in type_map.items():
        fp = char_dir / fname
        if not fp.exists(): continue
        raw = fp.read_text("utf-8")
        for m in re.finditer(r"###\s+(.+)", raw):
            name = m.group(1).strip()
            cid = f"{ctype}_{name}"
            conn.execute("""
                INSERT INTO characters (char_id,char_name,char_type,raw_profile,created_at,updated_at)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(char_id) DO UPDATE SET raw_profile=excluded.raw_profile, updated_at=excluded.updated_at
            """, (cid, name, ctype, raw[:3000], now, now))

def _sync_memory(conn, pdir):
    mem_dir = pdir / "memory"
    if not mem_dir.exists(): return
    now = _now()
    # 章节记忆 L2
    for mf in sorted(mem_dir.glob("ch-*-memory.md")):
        m = re.search(r"ch-(\d+)-memory", mf.name)
        if not m: continue
        cn = int(m.group(1))
        raw = mf.read_text("utf-8")
        conn.execute("""
            INSERT INTO chapter_memory (chapter_number,
                scene_location,scene_time,scene_mood,core_event,new_info,
                hook_scene,hook_mood,hook_suspense,hook_unfinished,
                foreshadow_planted,foreshadow_resolved,foreshadow_advanced,
                raw_content,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(chapter_number) DO UPDATE SET
                scene_mood=excluded.scene_mood, core_event=excluded.core_event,
                hook_suspense=excluded.hook_suspense, raw_content=excluded.raw_content,
                updated_at=excluded.updated_at
        """, (cn,
              _extract_field(raw,"位置"), _extract_field(raw,"时间"),
              _extract_field(raw,"氛围"), _extract_field(raw,"核心事件"),
              _extract_field(raw,"新信息"),
              _extract_field(raw,"结尾场景"), _extract_field(raw,"结尾情绪"),
              _extract_field(raw,"结尾悬念"), _extract_field(raw,"未完成动作"),
              _extract_field(raw,"埋设"), _extract_field(raw,"回收"),
              _extract_field(raw,"推进"),
              raw[:2000], now, now))
    # 阶段总结 L1
    for sf in sorted(mem_dir.glob("phase-*-summary.md")):
        m = re.search(r"phase-(\d+)-summary", sf.name)
        if not m: continue
        pn = int(m.group(1))
        raw = sf.read_text("utf-8")
        start = (pn-1)*10+1; end = pn*10
        conn.execute("""
            INSERT INTO phase_summary (phase_number,start_chapter,end_chapter,
                plot_summary,character_arcs,foreshadow_stats,suspense_status,
                world_snapshot,ending_anchor,raw_content,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(phase_number) DO UPDATE SET
                plot_summary=excluded.plot_summary, raw_content=excluded.raw_content,
                updated_at=excluded.updated_at
        """, (pn, start, end,
              _extract_section(raw,"剧情主线推进"),
              _extract_section(raw,"人物弧光进展"),
              _extract_section(raw,"伏笔总览"),
              _extract_section(raw,"悬念线状态"),
              _extract_section(raw,"世界状态快照"),
              _extract_section(raw,"阶段结尾锚点"),
              raw[:3000], now, now))

def sync_project(project_dir, target_chapter=None):
    """全量同步 JSON/Markdown → SQLite。target_chapter 非空时仅同步指定章节。"""
    pdir = Path(project_dir)
    c = _conn(pdir)
    c.executescript(SCHEMA_SQL)
    plan = load_plan(pdir)
    if plan:
        _sync_project_meta(c, plan)
        _sync_chapters(c, plan, pdir, target_chapter)
    if target_chapter is None:
        _sync_foreshadowing(c, pdir)
        _sync_characters(c, pdir)
        _sync_memory(c, pdir)
    c.commit(); c.close()
    return str(_db_path(pdir))


# ══════════════════════════════════════════════════════════════
# 评分/文风结果写入（供 score_chapter / check_ai_style 调用）
# ══════════════════════════════════════════════════════════════

def update_chapter_scores(project_dir, ch_num, score_result, style_result=None):
    c = _conn(project_dir); now = _now()
    d = score_result.get("dimensions", {})
    c.execute("""
        UPDATE chapters SET
            score_opening=?,score_senses=?,score_voice=?,score_info_release=?,
            score_emotion=?,score_tension=?,score_breathing=?,score_naturalness=?,
            score_total=?,score_grade=?,updated_at=?
        WHERE chapter_number=?
    """, (d.get("开篇吸引力",{}).get("score"), d.get("感官沉浸度",{}).get("score"),
          d.get("人物声音辨识度",{}).get("score"), d.get("信息释放节奏",{}).get("score"),
          d.get("情绪感染力",{}).get("score"), d.get("张力曲线",{}).get("score"),
          d.get("段落呼吸感",{}).get("score"), d.get("文风自然度",{}).get("score"),
          score_result.get("total"), score_result.get("grade"), now, ch_num))
    if style_result:
        c.execute("""
            UPDATE chapters SET
                style_waste_total=?,style_de_overloaded=?,style_de_ratio_pct=?,
                style_tell_count=?,style_sense_count=?,style_tension_peaks=?,
                style_long_paras=?,style_dialog_streak=?,
                style_grade=?,style_score=?,updated_at=?
            WHERE chapter_number=?
        """, (style_result.get("waste",{}).get("_total",0),
              style_result.get("de",{}).get("overloaded",0),
              style_result.get("de",{}).get("ratio_pct",0),
              style_result.get("tell",{}).get("count",0),
              style_result.get("senses",{}).get("sense_count",0),
              style_result.get("tension",{}).get("peaks",0),
              style_result.get("breathing",{}).get("long_paras",0),
              style_result.get("breathing",{}).get("max_dialog_streak",0),
              style_result.get("grade"), style_result.get("score"), now, ch_num))
    c.commit(); c.close()

def log_revision(project_dir, rtype, target_file, target_chapter, desc, before="", after=""):
    c = _conn(project_dir)
    c.execute("INSERT INTO revision_log (revision_type,target_file,target_chapter,description,before_hash,after_hash,created_at) VALUES (?,?,?,?,?,?,?)",
              (rtype, target_file, target_chapter, desc, before[:500], after[:500], _now()))
    c.commit(); c.close()


# ══════════════════════════════════════════════════════════════
# 预定义查询（Agent 直接调用，返回 list[dict]）
# ══════════════════════════════════════════════════════════════

Q = {
    # ── 章节状态 ──
    "chapters_by_status":
        "SELECT chapter_number,title,status,word_count_cn,score_total,score_grade FROM chapters WHERE status=? ORDER BY chapter_number",
    "chapters_pending":
        "SELECT chapter_number,title FROM chapters WHERE status='pending' ORDER BY chapter_number LIMIT ?",
    "chapters_low_score":
        "SELECT chapter_number,title,score_total,score_grade,score_opening,score_senses,score_voice,score_info_release,score_emotion,score_tension,score_breathing,score_naturalness FROM chapters WHERE score_total IS NOT NULL AND score_total<? ORDER BY score_total",
    "chapters_style_issues":
        "SELECT chapter_number,title,style_grade,style_score,style_waste_total,style_de_overloaded,style_tell_count,style_sense_count,style_tension_peaks FROM chapters WHERE style_grade IN ('warn','fail') ORDER BY style_score",
    "chapters_wordcount_fail":
        "SELECT chapter_number,title,word_count_cn,retry_count FROM chapters WHERE word_count_pass=0 AND status='completed' ORDER BY chapter_number",

    # ── 创作辅助（核心加速查询） ──
    "next_chapter_to_write":
        "SELECT chapter_number,title,outline_core_event,outline_hook,outline_characters FROM chapters WHERE status IN ('pending','failed') ORDER BY chapter_number LIMIT 1",
    "chapter_context":
        "SELECT c.chapter_number,c.title,c.status,c.word_count_cn,c.score_total,c.score_grade,c.outline_core_event,c.outline_hook,cm.scene_location,cm.scene_mood,cm.core_event,cm.hook_suspense,cm.hook_unfinished FROM chapters c LEFT JOIN chapter_memory cm ON c.chapter_number=cm.chapter_number WHERE c.chapter_number=?",
    "recent_context":
        "SELECT c.chapter_number,c.title,cm.core_event,cm.scene_mood,cm.hook_suspense,cm.hook_unfinished FROM chapters c LEFT JOIN chapter_memory cm ON c.chapter_number=cm.chapter_number WHERE c.chapter_number BETWEEN ? AND ? ORDER BY c.chapter_number",
    "latest_memory":
        "SELECT chapter_number,scene_location,scene_mood,core_event,hook_scene,hook_mood,hook_suspense,hook_unfinished FROM chapter_memory ORDER BY chapter_number DESC LIMIT ?",
    "latest_phase_summary":
        "SELECT phase_number,start_chapter,end_chapter,plot_summary,ending_anchor FROM phase_summary ORDER BY phase_number DESC LIMIT 1",
    "active_foreshadowing_for_chapter":
        "SELECT fs_id,content,fs_type,planted_chapter FROM foreshadowing WHERE (planted_chapter=? OR planted_chapter IS NULL) AND status='活跃' ORDER BY planted_chapter",

    # ── 伏笔 ──
    "foreshadowing_active":
        "SELECT fs_id,content,fs_type,planted_chapter,resolve_chapter FROM foreshadowing WHERE status='活跃' ORDER BY planted_chapter",
    "foreshadowing_orphans":
        "SELECT fs_id,content,planted_chapter,resolve_chapter FROM foreshadowing WHERE is_orphan=1 ORDER BY resolve_chapter",
    "foreshadowing_by_chapter":
        "SELECT fs_id,content,status FROM foreshadowing WHERE planted_chapter=? OR resolve_chapter=?",
    "foreshadowing_stats":
        "SELECT status,COUNT(*) as count FROM foreshadowing GROUP BY status",
    "foreshadowing_unresolved":
        "SELECT fs_id,content,planted_chapter,resolve_chapter FROM foreshadowing WHERE status='活跃' AND resolve_chapter<=? ORDER BY resolve_chapter",

    # ── 人物 ──
    "characters_all":
        "SELECT char_id,char_name,char_type FROM characters ORDER BY char_type,char_name",
    "characters_by_type":
        "SELECT char_id,char_name FROM characters WHERE char_type=?",
    "character_appearances":
        "SELECT ca.chapter_number,ca.role_in_chapter,ca.state_change FROM character_appearances ca WHERE ca.char_id=? ORDER BY ca.chapter_number",

    # ── 记忆 ──
    "phase_summaries":
        "SELECT phase_number,start_chapter,end_chapter,plot_summary FROM phase_summary ORDER BY phase_number",
    "memory_stats":
        "SELECT (SELECT COUNT(*) FROM chapter_memory) as memories, (SELECT COUNT(*) FROM phase_summary) as summaries, (SELECT COUNT(*) FROM chapters WHERE status='completed') as completed",

    # ── 统计 ──
    "stats_overview":
        "SELECT COUNT(*) as total, SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed, SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending, SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed, SUM(word_count_cn) as total_words, ROUND(AVG(word_count_cn)) as avg_words, ROUND(AVG(score_total),1) as avg_score, SUM(CASE WHEN score_grade='S' THEN 1 ELSE 0 END) as S, SUM(CASE WHEN score_grade='A' THEN 1 ELSE 0 END) as A, SUM(CASE WHEN score_grade='B' THEN 1 ELSE 0 END) as B, SUM(CASE WHEN score_grade='C' THEN 1 ELSE 0 END) as C, SUM(CASE WHEN score_grade='D' THEN 1 ELSE 0 END) as D FROM chapters",
    "stats_dimensions":
        "SELECT ROUND(AVG(score_opening),1) as opening, ROUND(AVG(score_senses),1) as senses, ROUND(AVG(score_voice),1) as voice, ROUND(AVG(score_info_release),1) as info_release, ROUND(AVG(score_emotion),1) as emotion, ROUND(AVG(score_tension),1) as tension, ROUND(AVG(score_breathing),1) as breathing, ROUND(AVG(score_naturalness),1) as naturalness FROM chapters WHERE score_total IS NOT NULL",
    "stats_foreshadowing":
        "SELECT COUNT(*) as total, SUM(CASE WHEN status='活跃' THEN 1 ELSE 0 END) as active, SUM(CASE WHEN status IN ('已回收','已揭晓','完成') THEN 1 ELSE 0 END) as resolved, SUM(is_orphan) as orphans FROM foreshadowing",

    # ── 修订 ──
    "revisions_recent":
        "SELECT revision_id,revision_type,target_file,target_chapter,description,created_at FROM revision_log ORDER BY created_at DESC LIMIT ?",
    "revisions_by_type":
        "SELECT revision_id,target_file,target_chapter,description,created_at FROM revision_log WHERE revision_type=? ORDER BY created_at DESC",

    # ── 顶层约束 ──
    "top_constraints":
        "SELECT opening_background,story_ending,volume_outline,ability_path,growth_cost,core_conflict,conflict_escalation FROM project WHERE id=1",
}

def query(project_dir, name, params=None):
    if name not in Q:
        return {"error": f"未知查询: {name}", "available": sorted(Q.keys())}
    c = _conn(project_dir)
    try:
        rows = c.execute(Q[name], params or ()).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        return {"error": str(e)}
    finally:
        c.close()

def raw_query(project_dir, sql, params=None):
    if not sql.strip().upper().startswith("SELECT"):
        return {"error": "仅支持 SELECT"}
    c = _conn(project_dir)
    try:
        rows = c.execute(sql, params or ()).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        return {"error": str(e)}
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]
    if not args:
        print("用法:")
        print("  python db_manager.py init <目录>                # 初始化数据库")
        print("  python db_manager.py sync <目录> [--chapter N]  # 同步(全量/单章)")
        print("  python db_manager.py query <目录> <查询名> [参数] # 预定义查询")
        print("  python db_manager.py sql <目录> \"SELECT ...\"   # 原始SQL(只读)")
        print("\n可用查询:")
        for k in sorted(Q.keys()): print(f"  {k}")
        return

    cmd = args[0]
    if cmd == "init":
        print(f"数据库: {init_db(args[1])}")
    elif cmd == "sync":
        ch = None
        if "--chapter" in args:
            idx = args.index("--chapter")
            ch = int(args[idx+1])
        print(f"已同步: {sync_project(args[1], ch)}")
    elif cmd == "query":
        params = args[3:] if len(args) > 3 else None
        print(json.dumps(query(args[1], args[2], params), ensure_ascii=False, indent=2))
    elif cmd == "sql":
        print(json.dumps(raw_query(args[1], args[2]), ensure_ascii=False, indent=2))
    else:
        print(f"未知命令: {cmd}")

if __name__ == "__main__":
    main()