"""
如意学伴 · 微信推送脚本
支持：早报、晚报、番茄钟通知
"""
import json, sys, urllib.request

WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=e07869d0-167e-409d-8646-7ed5082d6e00"

def send_markdown(content: str) -> dict:
    data = json.dumps({"msgtype": "markdown", "markdown": {"content": content}}).encode()
    req = urllib.request.Request(WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

def morning_report():
    msg = """## 📚 如意学伴 · 今日早报
> 新的一天，开始学习吧！

**📅 今日任务：**
- 数据结构：线性表（2h）
- 操作系统：进程管理（2h）
- 🔄 艾宾浩斯复习：链表回顾（0.5h）

🍅 建议：每 25 分钟一个番茄钟，说"开启番茄"开始~

💬 完成某项后，回来打卡更新进度~"""
    return send_markdown(msg)

def evening_report():
    msg = """## 🌙 如意学伴 · 今日晚报
> 今天辛苦了！

**📊 今日完成：**
- 任务完成率：--
- 学习时长：--
- 连续打卡：--
- 🍅 番茄完成：--个

💤 早点休息，明天继续加油！"""
    return send_markdown(msg)

def pomodoro_start(subject: str, count: int):
    msg = f"""## 🍅 番茄钟 · 开始专注

📚 科目：**{subject}**
⏰ 计时：**25 分钟**
🏆 今日第 **{count}** 个番茄

💪 专注模式已开启，25 分钟内不回消息！"""
    return send_markdown(msg)

def pomodoro_end(count: int, minutes: int, streak: int):
    msg = f"""## 🍅 番茄钟 · 时间到！

⏰ **25 分钟**专注完成！
☕ 休息 5 分钟，起身走走，喝点水~

🏆 今日：**{count}** 个番茄 | 累计：**{minutes}** 分钟
🔥 连续完成：**{streak}** 个"""
    return send_markdown(msg)

def pomodoro_break_end():
    msg = """## ☕ 休息完毕

💪 5 分钟休息结束，准备开始下一轮番茄！
说"开启番茄"继续专注~"""
    return send_markdown(msg)

def pomodoro_long_break(pomo_count: int, total_minutes: int):
    msg = f"""## 🍅 恭喜完成 {pomo_count} 个番茄！

🏆 累计专注：**{total_minutes}** 分钟
☕ 建议长休息：**20 分钟**

💡 长时间专注后让大脑休息一下~
   起来走动、喝水、远眺窗外。"""
    return send_markdown(msg)

def pomodoro_badge(badge_name: str, badge_emoji: str):
    msg = f"""## 🏅 获得新勋章！

{emoji} **{badge_name}**

恭喜解锁番茄成就，继续加油！"""
    return send_markdown(msg)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    arg2 = sys.argv[2] if len(sys.argv) > 2 else ""
    arg3 = sys.argv[3] if len(sys.argv) > 3 else ""

    handlers = {
        "morning": morning_report,
        "evening": evening_report,
        "pomo_start": lambda: pomodoro_start(arg2, int(arg3 or "1")),
        "pomo_end": lambda: pomodoro_end(int(arg2 or "0"), int(arg3 or "0"), 0),
        "pomo_break": pomodoro_break_end,
        "pomo_longbreak": lambda: pomodoro_long_break(int(arg2 or "4"), int(arg3 or "100")),
        "pomo_badge": lambda: pomodoro_badge(arg2, arg3),
    }
    r = handlers.get(mode, morning_report)()
    print(json.dumps(r, ensure_ascii=False))
