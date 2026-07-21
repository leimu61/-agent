"""
如意学伴 · 学习数据记录器
统一记录用户所有学习行为：番茄、问答、快测、日记、计划变更、薄弱点
数据文件：memory/learning_data.json
"""
import json, os, sys
from datetime import datetime, date
from collections import defaultdict

DATA = os.path.join(os.path.dirname(__file__), '..', 'memory', 'learning_data.json')
os.makedirs(os.path.dirname(DATA), exist_ok=True)

def _load():
    try:
        with open(DATA, encoding='utf-8') as f: return json.load(f)
    except: return _default()

def _default():
    return {
        "user": {}, "daily": {}, "pomodoro": [],
        "questions": [], "quizzes": [], "journal": [],
        "weak_points": [], "plan_snapshots": [],
        "stats_cache": {}
    }

def _save(d): 
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def record(action: str, payload: dict = None) -> dict:
    """统一入口：record('pomodoro',{...}) / record('question',{...}) 等"""
    d = _load()
    today = date.today().isoformat()
    d.setdefault("daily", {}).setdefault(today, {})
    daily = d["daily"][today]

    if action == "pomodoro":
        d["pomodoro"].append(payload)
        daily.setdefault("pomodoro", []).append(payload)

    elif action == "question":
        payload["asked_at"] = datetime.now().isoformat()
        payload.setdefault("understood", None)
        d["questions"].append(payload)
        daily.setdefault("questions", []).append(payload)

    elif action == "quiz":
        payload["taken_at"] = datetime.now().isoformat()
        d["quizzes"].append(payload)
        daily.setdefault("quizzes", []).append(payload)

    elif action == "journal":
        payload["written_at"] = datetime.now().isoformat()
        d["journal"].append(payload)
        daily.setdefault("journal", []).append(payload)

    elif action == "weak_point":
        wp = payload
        wp["logged_at"] = datetime.now().isoformat()
        # merge: increment count if same topic
        for existing in d["weak_points"]:
            if existing.get("topic") == wp.get("topic") and existing.get("subject") == wp.get("subject"):
                existing["count"] = existing.get("count", 1) + 1
                existing["last"] = wp["logged_at"]
                _save(d)
                return {"ok": True, "merged": True}
        wp["count"] = 1
        d["weak_points"].append(wp)
        daily.setdefault("weak_points", []).append(wp)

    elif action == "plan_snapshot":
        payload["snapshot_at"] = datetime.now().isoformat()
        d["plan_snapshots"].append(payload)

    elif action == "user_profile":
        d["user"] = payload

    else:
        return {"error": f"unknown action: {action}"}

    _save(d)
    return {"ok": True}

def stats() -> dict:
    """计算全量统计指标"""
    d = _load()
    today = date.today().isoformat()
    pomo = d.get("pomodoro", [])
    questions = d.get("questions", [])
    quizzes = d.get("quizzes", [])
    wp = d.get("weak_points", [])
    daily = d.get("daily", {})

    # 番茄统计
    pomo_today = [p for p in pomo if p.get("started_at","")[:10] == today]
    comp = sum(1 for p in pomo_today if p.get("completed"))
    inter = sum(1 for p in pomo_today if p.get("interrupted"))
    mins = sum(p.get("effective_minutes", 0) for p in pomo)

    # 问答统计
    q_today = [q for q in questions if q.get("asked_at","")[:10] == today]
    q_total = len(questions)
    q_understand = sum(1 for q in questions if q.get("understood"))

    # 快测统计
    quiz_all = [q for q in quizzes]
    quiz_today = [q for q in quizzes if q.get("taken_at","")[:10] == today]
    quiz_scores = [q.get("score", 0) for q in quiz_all if "score" in q]
    quiz_avg = round(sum(quiz_scores) / max(len(quiz_scores), 1), 1)

    # 薄弱点
    wp_sorted = sorted(wp, key=lambda x: x.get("count", 0), reverse=True)
    wp_top = {w["topic"]: w["count"] for w in wp_sorted[:5]}

    # 日记
    journal_days = len(set(j.get("written_at","")[:10] for j in d.get("journal",[])))

    return {
        "today": today,
        "pomodoro": {"total": len(pomo), "today": len(pomo_today), "completed": comp, "interrupted": inter, "total_minutes": mins},
        "questions": {"total": q_total, "today": len(q_today), "understood_rate": round(q_understand/max(q_total,1), 2)},
        "quizzes": {"total": len(quiz_all), "today": len(quiz_today), "avg_score": quiz_avg},
        "weak_points": wp_top,
        "journal": {"total": len(d.get("journal",[])), "days": journal_days},
        "records_total": len(pomo) + q_total + len(quiz_all) + len(d.get("journal",[])),
        "_meta": {"source": "learning_data.json", "data_is_real": len(pomo) + q_total > 0}
    }

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False, indent=2))
    else:
        payload = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
        r = record(cmd, payload)
        print(json.dumps(r, ensure_ascii=False))
