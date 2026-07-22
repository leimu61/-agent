"""
番茄钟计时器 — 自动追踪学习时长

记录学生在各科目/知识点上的真实学习时长，替代手动填时间。

用法:
    python pomodoro.py start "数据结构" "线性表"
    python pomodoro.py pause
    python pomodoro.py resume
    python pomodoro.py stop
    python pomodoro.py status
    python pomodoro.py today            # 今日学习分布
    python pomodoro.py week             # 本周统计

状态存储: ~/.hermes/pomodoro_state.json（当前计时状态）
会话记录: 通过 stdout 输出 JSON，由 Hermes 存入 Memory
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path


# 状态文件路径
STATE_FILE = Path(os.path.expanduser("~/.hermes/pomodoro_state.json"))


def load_state() -> dict:
    """加载当前计时状态"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"status": "idle"}  # idle | running | paused


def save_state(state: dict):
    """保存计时状态"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def format_duration(minutes: float) -> str:
    """格式化时长"""
    if minutes < 1:
        return f"{int(minutes * 60)}秒"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}小时{mins}分钟"
    return f"{mins}分钟"


def cmd_start(subject: str, topic: str = "") -> dict:
    """开始计时"""
    state = load_state()
    if state["status"] in ("running", "paused"):
        return {
            "success": False,
            "message": f"当前已有计时在进行中（{state['status']}）：{state.get('subject','')} {state.get('topic','')}，请先 stop",
        }

    now = datetime.now().isoformat()
    state = {
        "status": "running",
        "subject": subject,
        "topic": topic,
        "started_at": now,
        "paused_at": None,
        "total_paused_seconds": 0,
        "sessions": [],  # 暂停段记录
    }
    save_state(state)

    return {
        "success": True,
        "action": "start",
        "subject": subject,
        "topic": topic,
        "started_at": now,
        "message": f"🍅 开始学习：{subject}" + (f" · {topic}" if topic else "") + "\n⏱ 计时中...",
    }


def cmd_pause() -> dict:
    """暂停计时"""
    state = load_state()
    if state["status"] != "running":
        return {"success": False, "message": f"当前状态为 {state['status']}，无法暂停"}

    now = datetime.now()
    paused_at = now.isoformat()
    state["status"] = "paused"
    state["paused_at"] = paused_at
    state["sessions"].append({
        "started": state.get("last_resume", state["started_at"]),
        "ended": paused_at,
    })

    # 计算已学习时长
    total_seconds = calc_elapsed(state)
    save_state(state)

    return {
        "success": True,
        "action": "pause",
        "subject": state["subject"],
        "topic": state.get("topic", ""),
        "elapsed_minutes": round(total_seconds / 60, 1),
        "elapsed_display": format_duration(total_seconds / 60),
        "message": f"⏸ 已暂停 | 已学习：{format_duration(total_seconds / 60)}",
    }


def cmd_resume() -> dict:
    """继续计时"""
    state = load_state()
    if state["status"] != "paused":
        return {"success": False, "message": f"当前状态为 {state['status']}，无法继续"}

    now = datetime.now().isoformat()
    state["status"] = "running"
    state["last_resume"] = now

    # 累计暂停时长
    if state.get("paused_at"):
        paused_dt = datetime.fromisoformat(state["paused_at"])
        state["total_paused_seconds"] = state.get("total_paused_seconds", 0) + (
            datetime.now() - paused_dt
        ).total_seconds()
    state["paused_at"] = None
    save_state(state)

    return {
        "success": True,
        "action": "resume",
        "subject": state["subject"],
        "topic": state.get("topic", ""),
        "message": "▶ 继续计时中...",
    }


def calc_elapsed(state: dict) -> float:
    """计算净学习时长（秒）"""
    started = datetime.fromisoformat(state["started_at"])
    now = datetime.now()

    total_seconds = (now - started).total_seconds()
    total_seconds -= state.get("total_paused_seconds", 0)

    if state["status"] == "paused" and state.get("paused_at"):
        paused_dt = datetime.fromisoformat(state["paused_at"])
        total_seconds -= (now - paused_dt).total_seconds()

    return max(0, total_seconds)


def cmd_stop() -> dict:
    """结束计时，返回本次学习记录"""
    state = load_state()
    if state["status"] not in ("running", "paused"):
        return {"success": False, "message": "当前没有进行中的计时"}

    # 计算净学习时长
    total_seconds = calc_elapsed(state)
    total_minutes = round(total_seconds / 60, 1)

    subject = state.get("subject", "")
    topic = state.get("topic", "")

    # 生成会话记录（由 Hermes 存入 Memory）
    session_record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "started_at": state["started_at"],
        "ended_at": datetime.now().isoformat(),
        "subject": subject,
        "topic": topic,
        "duration_minutes": total_minutes,
        "duration_display": format_duration(total_minutes),
        "had_pauses": len(state.get("sessions", [])) > 0,
        "pause_count": len(state.get("sessions", [])),
    }

    # 清除状态
    save_state({"status": "idle"})

    # 番茄钟评价
    if total_minutes >= 50:
        badge = "🔥 深度学习！超过50分钟"
    elif total_minutes >= 25:
        badge = "🍅 一个标准番茄钟完成"
    elif total_minutes >= 10:
        badge = "💪 短时高效"
    else:
        badge = "📝 碎片学习"

    return {
        "success": True,
        "action": "stop",
        "session": session_record,
        "badge": badge,
        "message": (
            f"⏹ 计时结束！\n"
            f"📚 {subject}" + (f" · {topic}" if topic else "") + f"\n"
            f"⏱ 学习时长：{format_duration(total_minutes)}\n"
            f"{badge}\n\n"
            f"💾 请将 session 数据保存到 Memory 的 pomodoro_sessions 中"
        ),
    }


def cmd_status() -> dict:
    """查看当前计时状态"""
    state = load_state()
    if state["status"] == "idle":
        return {
            "success": True,
            "status": "idle",
            "message": "⏹ 当前没有进行中的番茄钟",
        }

    total_seconds = calc_elapsed(state)
    emoji = {"running": "🍅", "paused": "⏸"}.get(state["status"], "❓")

    return {
        "success": True,
        "status": state["status"],
        "subject": state.get("subject", ""),
        "topic": state.get("topic", ""),
        "elapsed_minutes": round(total_seconds / 60, 1),
        "elapsed_display": format_duration(total_seconds / 60),
        "started_at": state.get("started_at", ""),
        "message": (
            f"{emoji} {'计时中' if state['status'] == 'running' else '已暂停'}\n"
            f"📚 {state.get('subject', '')}" + (f" · {state.get('topic', '')}" if state.get('topic') else "") + f"\n"
            f"⏱ 已学习：{format_duration(total_seconds / 60)}"
        ),
    }


def cmd_today(sessions: list = None) -> dict:
    """今日学习分布统计"""
    if sessions is None:
        return {"success": False, "message": "请从 Memory 的 pomodoro_sessions 中传入今日数据"}

    today = datetime.now().strftime("%Y-%m-%d")
    today_sessions = [s for s in sessions if s.get("date") == today]

    subject_times = {}
    total = 0
    for s in today_sessions:
        subj = s.get("subject", "未分类")
        mins = s.get("duration_minutes", 0)
        subject_times[subj] = subject_times.get(subj, 0) + mins
        total += mins

    bars = []
    for subj, mins in sorted(subject_times.items(), key=lambda x: -x[1]):
        pct = round(mins / total * 100) if total > 0 else 0
        bar_len = max(1, pct // 5)
        bars.append({"subject": subj, "minutes": round(mins, 1), "percentage": pct, "bar": "█" * bar_len})

    return {
        "success": True,
        "date": today,
        "total_minutes": round(total, 1),
        "total_display": format_duration(total),
        "session_count": len(today_sessions),
        "breakdown": bars,
        "message": (
            f"📊 今日学习分布 | 总计：{format_duration(total)}\n"
            + "\n".join(
                f"  {b['bar']} {b['subject']}: {format_duration(b['minutes'])}（{b['percentage']}%）"
                for b in bars
            )
        ) if bars else "📊 今日暂无学习记录",
    }


def cmd_week(sessions: list = None) -> dict:
    """本周统计"""
    if sessions is None:
        return {"success": False, "message": "请从 Memory 中传入本周数据"}

    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())
    week_start_str = week_start.strftime("%Y-%m-%d")

    week_sessions = [s for s in sessions if s.get("date", "") >= week_start_str]

    daily_totals = {}
    subject_totals = {}
    total = 0
    for s in week_sessions:
        day = s.get("date", "")
        mins = s.get("duration_minutes", 0)
        daily_totals[day] = daily_totals.get(day, 0) + mins
        subj = s.get("subject", "未分类")
        subject_totals[subj] = subject_totals.get(subj, 0) + mins
        total += mins

    return {
        "success": True,
        "week_start": week_start_str,
        "total_minutes": round(total, 1),
        "total_display": format_duration(total),
        "total_sessions": len(week_sessions),
        "daily": daily_totals,
        "by_subject": {k: round(v, 1) for k, v in sorted(subject_totals.items(), key=lambda x: -x[1])},
        "message": (
            f"📊 本周学习统计（{week_start_str} 起）\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⏱ 总计：{format_duration(total)}\n"
            f"📝 学习次数：{len(week_sessions)}\n\n"
            + "\n".join(
                f"📅 {day}: {format_duration(mins)}"
                for day, mins in sorted(daily_totals.items())
            )
        ),
    }


# ── Hermes Tool 入口 ──────────────────────────────────────────

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        # 命令行模式
        if len(sys.argv) < 2:
            print(json.dumps({"error": "用法: pomodoro.py <start|pause|resume|stop|status|today|week> [参数...]"}, ensure_ascii=False))
            return
        cmd = sys.argv[1]
        args = sys.argv[2:]
        input_data = {"command": cmd}
        if cmd == "start" and args:
            input_data["subject"] = args[0]
            input_data["topic"] = args[1] if len(args) > 1 else ""

    cmd = input_data.get("command", "")

    if cmd == "start":
        result = cmd_start(
            subject=input_data.get("subject", "未指定"),
            topic=input_data.get("topic", ""),
        )
    elif cmd == "pause":
        result = cmd_pause()
    elif cmd == "resume":
        result = cmd_resume()
    elif cmd == "stop":
        result = cmd_stop()
    elif cmd == "status":
        result = cmd_status()
    elif cmd == "today":
        result = cmd_today(input_data.get("sessions", []))
    elif cmd == "week":
        result = cmd_week(input_data.get("sessions", []))
    else:
        result = {"success": False, "message": f"未知命令: {cmd}，支持: start/pause/resume/stop/status/today/week"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
