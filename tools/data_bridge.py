"""
如意学伴 · 数据桥
从 learning_data.json + tomato_state.json 读取全量学习数据
"""
import json, os, sys
from datetime import date, timedelta
from collections import defaultdict

LEARNING = os.path.join(os.path.dirname(__file__), '..', 'memory', 'learning_data.json')
TOMATO   = os.path.join(os.path.dirname(__file__), '..', 'memory', 'tomato_state.json')

def load_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f: return json.load(f)
    except: return default or {}

def compute_stats() -> dict:
    """从 learning_data.json + tomato_state.json 计算全量统计"""
    ld = load_json(LEARNING, {"pomodoro":[],"questions":[],"quizzes":[],"journal":[],"weak_points":[]})
    t  = load_json(TOMATO, {"history":[],"today":[]})

    # 合并番茄数据（优先 learning_data，fallback tomato_state）
    pomo_records = ld.get("pomodoro", [])
    if not pomo_records:
        pomo_records = t.get("history", [])
    if not pomo_records and "pomodoro" in ld:
        pomo_records = ld["pomodoro"]

    questions = ld.get("questions", [])
    quizzes = ld.get("quizzes", [])
    journals = ld.get("journal", [])
    weak_pts = ld.get("weak_points", [])
    now = date.today()
    week_start = now - timedelta(days=now.weekday())

    # ── 周维度数据 ──
    week_days = [(week_start + timedelta(days=i)).isoformat() for i in range(7)]
    week_labels = ['周一','周二','周三','周四','周五','周六','周日']
    daily_completion = defaultdict(float)
    daily_completed = defaultdict(int)
    daily_interrupted = defaultdict(int)
    subject_minutes = defaultdict(float)
    interrupt_reasons = defaultdict(int)

    for r in pomo_records:
        d = r.get("started_at", "")[:10]
        if d in week_days:
            if r.get("completed"):
                daily_completed[d] += 1
            elif r.get("interrupted"):
                daily_interrupted[d] += 1
            daily_completion[d] += r.get("effective_minutes", 0)
            subject_minutes[r.get("subject", "未知")] += r.get("effective_minutes", 0)
            if r.get("interrupt_reason"):
                interrupt_reasons[r.get("interrupt_reason")] += 1

    # ── 本周完成率数据（兼容 visualize.py 格式）─
    completion_rates = []
    hours_data = []
    pomo_completed = []
    pomo_interrupted = []
    for d in week_days:
        total = daily_completed[d] + daily_interrupted[d]
        rate = daily_completed[d] / max(total, 1)
        completion_rates.append(round(rate, 2))
        hours_data.append(round(daily_completion[d] / 60, 1))
        pomo_completed.append(daily_completed[d])
        pomo_interrupted.append(daily_interrupted[d])

    # ── 科目分布 ──
    subjects = dict(sorted(subject_minutes.items(), key=lambda x: -x[1]))
    pomo_subjects = {k: int(v//25) for k, v in subjects.items()}

    # ── 薄弱点（从番茄中断原因提取"太难"类）─
    weak = {}
    for rsn, cnt in interrupt_reasons.items():
        if any(kw in rsn for kw in ['难', '不懂', '太复杂']):
            weak[rsn] = cnt

    # ── 中断率 ──
    total_today = daily_completed[now.isoformat()] + daily_interrupted[now.isoformat()]
    interrupt_rate = round(daily_interrupted[now.isoformat()] / max(total_today, 1), 2)

    # ── 番茄总数 ──
    total_pomos = sum(pomo_completed) + sum(pomo_interrupted)

    return {
        "completion": completion_rates if any(c > 0 for c in completion_rates) else [0.5]*7,
        "hours": hours_data if any(h > 0 for h in hours_data) else [2]*7,
        "subjects": subjects if subjects else {"数据结构": 4, "高数": 2},
        "pomo_subjects": pomo_subjects if pomo_subjects else {"数据结构": 2, "高数": 1},
        "weak": weak if weak else {"红黑树": 1, "极限": 2},
        # 新增：问答/快测/日记统计
        "questions_total": len(questions),
        "quizzes_total": len(quizzes),
        "quiz_avg_score": round(sum(q.get("score", 0) for q in quizzes) / max(len(quizzes), 1), 1) if quizzes else 0,
        "journal_days": len(set(j.get("written_at","")[:10] for j in journals)),
        "weak_points_count": len(weak_pts),
        # 番茄
        "pomo_completed": pomo_completed,
        "pomo_interrupted": pomo_interrupted,
        "interrupt_rate": interrupt_rate,
        "total_pomos": total_pomos,
        "week_labels": week_labels,
        "_meta": {
            "source": "learning_data.json + tomato_state.json",
            "total_records": len(pomo_records) + len(questions) + len(quizzes) + len(journals),
            "data_is_real": len(pomo_records) + len(questions) > 0
        }
    }

if __name__ == "__main__":
    stats = compute_stats()
    out = sys.argv[1] if len(sys.argv) > 1 else None
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"✅ 数据已导出到 {out}")
        print(f"   番茄: {stats['total_pomos']}个 | 问答: {stats['questions_total']}次 | 快测: {stats['quizzes_total']}次")
        print(f"   日记: {stats['journal_days']}天 | 薄弱点: {stats['weak_points_count']}个")
    else:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
