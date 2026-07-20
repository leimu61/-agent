"""
艾宾浩斯遗忘曲线复习日期计算器

基于艾宾浩斯遗忘曲线，根据首次学习日期计算最佳复习时间节点。
复习间隔：1天、2天、4天、7天、15天（可根据需要调整）

用法：
    python ebbinghaus.py --learned 2026-07-20 --topic "链表"

作为 Hermes Tool 注册：
    hermes tools register tools/ebbinghaus.py
"""

import json
import sys
from datetime import date, datetime, timedelta


# 艾宾浩斯复习间隔（天数）
EBBINGHAUS_INTERVALS = [1, 2, 4, 7, 15]

# 间隔对应的阶段名称
INTERVAL_LABELS = {
    1: "第1次复习（1天后）",
    2: "第2次复习（2天后）",
    4: "第3次复习（4天后）",
    7: "第4次复习（7天后）",
    15: "第5次复习（15天后）",
}


def calculate_review_dates(
    learned_date: str,
    topic: str,
    intervals: list = None,
) -> dict:
    """
    计算复习日期列表

    Args:
        learned_date: 首次学习日期，格式 YYYY-MM-DD
        topic: 知识点名称
        intervals: 自定义复习间隔（天数列表），默认使用标准艾宾浩斯间隔

    Returns:
        {
            "topic": "链表",
            "learned_date": "2026-07-20",
            "reviews": [
                {"date": "2026-07-21", "day": 1, "label": "第1次复习（1天后）"},
                {"date": "2026-07-22", "day": 2, "label": "第2次复习（2天后）"},
                ...
            ]
        }
    """
    if intervals is None:
        intervals = EBBINGHAUS_INTERVALS

    try:
        base_date = datetime.strptime(learned_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": f"日期格式错误：{learned_date}，请使用 YYYY-MM-DD 格式"}

    reviews = []
    for day_offset in intervals:
        review_date = base_date + timedelta(days=day_offset)
        reviews.append({
            "date": review_date.strftime("%Y-%m-%d"),
            "day": day_offset,
            "label": INTERVAL_LABELS.get(day_offset, f"第{len(reviews)+1}次复习"),
        })

    return {
        "topic": topic,
        "learned_date": learned_date,
        "reviews": reviews,
        "total_reviews": len(reviews),
    }


def calculate_batch(topics: list) -> list:
    """
    批量计算多个知识点的复习日期

    Args:
        topics: [
            {"learned_date": "2026-07-20", "topic": "链表"},
            {"learned_date": "2026-07-21", "topic": "栈"},
        ]

    Returns:
        [{...}, {...}]
    """
    results = []
    for item in topics:
        result = calculate_review_dates(
            learned_date=item["learned_date"],
            topic=item["topic"],
        )
        results.append(result)
    return results


def get_today_reviews(queue: list) -> list:
    """
    从复习队列中筛选今天需要复习的知识点

    Args:
        queue: 复习队列，格式同 calculate_review_dates 返回值列表

    Returns:
        今天需要复习的知识点列表
    """
    today = date.today().strftime("%Y-%m-%d")
    today_reviews = []

    for item in queue:
        for review in item.get("reviews", []):
            if review["date"] == today:
                today_reviews.append({
                    "topic": item["topic"],
                    "learned_date": item["learned_date"],
                    "review_stage": review["label"],
                })

    return today_reviews


# ── Hermes Tool 接口 ──────────────────────────────────────────
# Hermes 通过 JSON stdin 调用工具，工具输出 JSON stdout

def main():
    """Hermes Tool 入口：从 stdin 读取 JSON，输出 JSON 到 stdout"""
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        # 兼容命令行直接调用
        if len(sys.argv) >= 3:
            learned = sys.argv[1]
            topic = sys.argv[2]
            result = calculate_review_dates(learned, topic)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        print(json.dumps({"error": "无输入数据，请通过 stdin 传入 JSON 或使用命令行参数"}, ensure_ascii=False))
        return

    # 批量模式
    if isinstance(input_data, list):
        result = calculate_batch(input_data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 单条模式
    learned_date = input_data.get("learned_date", "")
    topic = input_data.get("topic", "未命名知识点")

    result = calculate_review_dates(learned_date, topic)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
