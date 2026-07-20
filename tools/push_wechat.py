"""
如意学伴 · 微信推送脚本
支持：早报、晚报、番茄钟全流程推送
"""
import json, sys, urllib.request

WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=e07869d0-167e-409d-8646-7ed5082d6e00"

def _send(md: str) -> dict:
    data = json.dumps({"msgtype": "markdown", "markdown": {"content": md}}).encode()
    req = urllib.request.Request(WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

# ── 基础推送 ─────────────────────
def morning(): return _send('## 📚 如意学伴 · 今日早报\n> 新的一天，开始学习吧！\n\n🍅 说「开启番茄」开始专注~')
def evening(): return _send("## 🌙 如意学伴 · 今日晚报\n> 今天辛苦了！\n\n💤 早点休息，明天继续加油！")

# ── 番茄钟推送 ─────────────────────
def pomo_start(subject, count):
    return _send(f"## 🍅 开始专注\n\n📚 **{subject}**\n⏰ 25 分钟\n🏆 今日第 **{count}** 个\n\n💪 专注模式已开启！")

def pomo_end(count, mins, streak):
    return _send(f"## 🍅 时间到！\n\n⏰ 25 分钟完成！\n☕ 休息 5 分钟~\n\n🏆 今日 {count} 个 | {mins} 分钟 | 🔥 连续 {streak} 个")

def pomo_interrupt(subject, mins, reason):
    """番茄中断推送，差异化文案"""
    if "疲惫" in reason or "累" in reason:
        tip = "💤 累了就休息，明天减少同类任务时长~"
    elif "难" in reason or "不懂" in reason:
        tip = "📚 已记录薄弱点，后续计划会增加前置复习"
    else:
        tip = "📝 有空时补上就好，别给自己太大压力~"
    return _send(f"## ⏸ 番茄中断\n\n📚 **{subject}** 提前终止\n⏰ 有效专注：**{mins} 分钟**\n📝 原因：{reason}\n\n{tip}")

def pomo_abandon(subject):
    return _send(f"## ❌ 番茄作废\n\n📚 **{subject}** 本轮放弃\n\n💪 没关系，休息一下重新开始~")

def pomo_break_end(): return _send("## ☕ 休息完毕\n\n💪 5 分钟到了，准备下一轮！")
def pomo_longbreak(n, mins): return _send(f"## 🍅 {n} 个番茄完成！\n\n🏆 {mins} 分钟\n☕ 长休息 20 分钟~")
def pomo_badge(name): return _send(f"## 🏅 新勋章！\n\n🎉 **{name}**\n恭喜解锁番茄成就！")
def pomo_fatigue(count): return _send(f"## ⚠️ 专注提醒\n\n今日已中断 **{count}** 次\n\n💡 建议休息一会儿，调整状态再继续~")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    a2, a3, a4 = (sys.argv[i] if len(sys.argv) > i else "" for i in [2, 3, 4])
    r = {"morning": morning, "evening": evening,
         "pomo_start":  lambda: pomo_start(a2, int(a3 or "1")),
         "pomo_end":    lambda: pomo_end(int(a2 or "0"), int(a3 or "0"), 0),
         "pomo_interrupt": lambda: pomo_interrupt(a2, int(a3 or "0"), a4),
         "pomo_abandon": lambda: pomo_abandon(a2),
         "pomo_break":  pomo_break_end,
         "pomo_longbreak": lambda: pomo_longbreak(int(a2 or "4"), int(a3 or "100")),
         "pomo_badge":  lambda: pomo_badge(a2),
         "pomo_fatigue": lambda: pomo_fatigue(int(a2 or "3")),
    }.get(mode, morning)()
    print(json.dumps(r, ensure_ascii=False))
