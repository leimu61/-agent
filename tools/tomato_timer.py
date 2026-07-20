"""
如意学伴 · 番茄钟计时器
管理番茄状态持久化 — 启动/暂停/恢复/终止/统计
"""
import json, os, sys
from datetime import datetime, timedelta

TIMER_FILE = os.path.join(os.path.dirname(__file__), '..', 'memory', 'tomato_state.json')
os.makedirs(os.path.dirname(TIMER_FILE), exist_ok=True)

DEFAULT = {"active": None, "history": []}

def _load() -> dict:
    try:
        with open(TIMER_FILE, encoding='utf-8') as f:
            return json.load(f)
    except: return {**DEFAULT}

def _save(data: dict):
    with open(TIMER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def start(subject: str, duration: int = 25) -> dict:
    """启动新番茄"""
    data = _load()
    if data.get("active"):
        return {"error": f"已有进行中的番茄：{data['active']['subject']}，请先停止"}
    now = datetime.now().isoformat()
    tomato = {
        "subject": subject,
        "duration": duration,
        "started_at": now,
        "paused_at": None,
        "remaining_seconds": duration * 60,
        "status": "running",
        "interrupt_reason": None,
    }
    data["active"] = tomato
    if "today" not in data: data["today"] = []
    _save(data)
    return {"ok": True, "tomato": tomato}

def pause(reason: str = "") -> dict:
    """暂停番茄，保留剩余时间"""
    data = _load()
    t = data.get("active")
    if not t: return {"error": "没有进行中的番茄"}
    if t["status"] == "paused": return {"error": "已暂停"}
    elapsed = (datetime.now() - datetime.fromisoformat(t["started_at"])).total_seconds()
    t["paused_at"] = datetime.now().isoformat()
    t["remaining_seconds"] = max(0, t["duration"] * 60 - elapsed)
    t["status"] = "paused"
    t["interrupt_reason"] = reason
    _save(data)
    return {"ok": True, "tomato": t, "effective_minutes": round(elapsed / 60, 1)}

def resume() -> dict:
    """恢复暂停的番茄"""
    data = _load()
    t = data.get("active")
    if not t: return {"error": "没有进行中的番茄"}
    if t["status"] != "paused": return {"error": "番茄未暂停"}
    t["status"] = "running"
    t["paused_at"] = None
    t["interrupt_reason"] = None
    _save(data)
    return {"ok": True, "tomato": t}

def stop(reason: str = "", abandon: bool = False) -> dict:
    """终止番茄。abandon=True 作废，不计入有效时长"""
    data = _load()
    t = data.get("active")
    if not t: return {"error": "没有进行中的番茄"}
    now = datetime.now()
    elapsed_minutes = round((now - datetime.fromisoformat(t["started_at"])).total_seconds() / 60, 1)
    effective = 0 if abandon else min(elapsed_minutes, t["duration"])
    record = {
        "subject": t["subject"], "duration": t["duration"],
        "started_at": t["started_at"], "ended_at": now.isoformat(),
        "effective_minutes": effective,
        "completed": not abandon and elapsed_minutes >= t["duration"] * 0.9,
        "interrupted": not abandon and elapsed_minutes < t["duration"] * 0.9,
        "abandoned": abandon,
        "interrupt_reason": reason or t.get("interrupt_reason") or ("" if not abandon else "主动放弃"),
    }
    data["active"] = None
    data.setdefault("history", []).append(record)
    data.setdefault("today", []).append(record)
    _save(data)
    return {"ok": True, "record": record}

def status() -> dict:
    """当前番茄状态"""
    data = _load()
    t = data.get("active")
    if not t: return {"active": False}
    elapsed = (datetime.now() - datetime.fromisoformat(t["started_at"])).total_seconds()
    if t["status"] == "paused" and t["paused_at"]:
        elapsed = (datetime.fromisoformat(t["paused_at"]) - datetime.fromisoformat(t["started_at"])).total_seconds()
    return {"active": True, "tomato": t, "elapsed_seconds": int(elapsed), "remaining_seconds": max(0, t["remaining_seconds"] if t["status"]=="paused" else t["duration"]*60 - int(elapsed))}

def stats() -> dict:
    """番茄统计数据"""
    data = _load()
    today = data.get("today", [])
    completed = [r for r in today if r["completed"]]
    interrupted = [r for r in today if r["interrupted"]]
    abandoned = [r for r in today if r["abandoned"]]
    by_subject = {}
    for r in completed + interrupted:
        by_subject[r["subject"]] = by_subject.get(r["subject"], 0) + r["effective_minutes"]
    reasons = {}
    for r in interrupted:
        rsn = r.get("interrupt_reason", "未知")
        reasons[rsn] = reasons.get(rsn, 0) + 1
    return {
        "total_today": len(today),
        "completed": len(completed),
        "interrupted": len(interrupted),
        "abandoned": len(abandoned),
        "effective_minutes": sum(r["effective_minutes"] for r in completed+interrupted),
        "interrupt_rate": round(len(interrupted)/max(len(today),1), 2),
        "by_subject": by_subject,
        "interrupt_reasons": reasons,
    }

# ── CLI ─────────────────────────────
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    arg2 = sys.argv[2] if len(sys.argv) > 2 else ""
    arg3 = sys.argv[3] if len(sys.argv) > 3 else ""

    handlers = {
        "start": lambda: start(arg2, int(arg3 or "25")),
        "pause": lambda: pause(arg2),
        "resume": resume,
        "stop": lambda: stop(arg2, arg3 == "abandon"),
        "status": status,
        "stats": stats,
    }
    r = handlers.get(cmd, status)()
    print(json.dumps(r, ensure_ascii=False, indent=2))
