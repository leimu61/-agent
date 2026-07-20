"""
如意学伴 · 微信推送脚本
由 Hermes Cron 定时调用，读取 Memory 学习数据并推送到企业微信
"""
import json, os, sys, urllib.request

WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=e07869d0-167e-409d-8646-7ed5082d6e00"

def send_markdown(content: str):
    data = json.dumps({"msgtype": "markdown", "markdown": {"content": content}}).encode()
    req = urllib.request.Request(WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

def morning_report():
    """早报：今日学习任务"""
    msg = """## 📚 如意学伴 · 今日早报
> 新的一天，开始学习吧！

**📅 今日任务：**
- 数据结构：线性表（2h）
- 操作系统：进程管理（2h）
- 🔄 艾宾浩斯复习：链表回顾（0.5h）

💬 完成某项后，回来打卡更新进度~"""
    return send_markdown(msg)

def evening_report():
    """晚报：今日总结"""
    msg = """## 🌙 如意学伴 · 今日晚报
> 今天辛苦了！

**📊 今日完成：**
- 任务完成率：--
- 学习时长：--
- 连续打卡：--

💤 早点休息，明天继续加油！"""
    return send_markdown(msg)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    r = morning_report() if mode == "morning" else evening_report()
    print(json.dumps(r, ensure_ascii=False))
