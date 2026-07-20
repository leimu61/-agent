"""
错题检索器

从学习 Memory 中检索与当前知识点相关的历史错题，
供答疑导师在讲解时自动提醒学生注意薄弱环节。

用法：
    python mistake_retriever.py '{"keyword":"红黑树"}'

作为 Hermes Tool 注册：
    hermes tools register tools/mistake_retriever.py
"""

import json
import sys
from datetime import date


def search_mistakes(
    keyword: str,
    weak_points: list = None,
    fuzzy: bool = True,
) -> dict:
    """
    在错题库中搜索相关错题

    Args:
        keyword: 搜索关键词（知识点名称）
        weak_points: 薄弱知识点列表，格式：
            [{"subject":"数据结构","topic":"红黑树","error_count":3,"last_error_date":"2026-07-19"}, ...]
            如果不传，返回空结果（实际使用时由 Hermes Memory 提供）
        fuzzy: 是否启用模糊匹配（默认 True）

    Returns:
        {
            "keyword": "红黑树",
            "matches": [...],
            "total_errors": 3,
            "suggestion": "..."
        }
    """
    if weak_points is None:
        weak_points = []

    matches = []

    for wp in weak_points:
        topic = wp.get("topic", "")
        subject = wp.get("subject", "")

        # 匹配逻辑
        is_match = False
        if fuzzy:
            # 模糊匹配：关键词出现在 topic 或 subject 中
            kw_lower = keyword.lower()
            if kw_lower in topic.lower() or kw_lower in subject.lower():
                is_match = True
            # 反向匹配：topic 中的词出现在 keyword 中
            for word in topic.split():
                if len(word) >= 2 and word.lower() in kw_lower:
                    is_match = True
                    break
        else:
            # 精确匹配
            if keyword == topic:
                is_match = True

        if is_match:
            matches.append({
                "subject": subject,
                "topic": topic,
                "error_count": wp.get("error_count", 0),
                "last_error_date": wp.get("last_error_date", "未知"),
                "next_review_date": wp.get("next_review_date"),
            })

    # 按错误次数降序
    matches.sort(key=lambda x: x["error_count"], reverse=True)

    total_errors = sum(m["error_count"] for m in matches)

    # 生成建议文本
    if matches:
        top = matches[0]
        if top["error_count"] >= 3:
            suggestion = f"⚠️ 「{top['topic']}」已累计错误 {top['error_count']} 次，属于高频薄弱点，建议重点讲解并安排额外练习"
        elif top["error_count"] >= 2:
            suggestion = f"📌 「{top['topic']}」之前错过 {top['error_count']} 次，建议在讲解时穿插易错提醒"
        else:
            suggestion = f"💡 「{top['topic']}」有过 1 次错误记录，可简单提及易错点"
    else:
        suggestion = "✅ 该知识点暂无历史错题记录"

    return {
        "keyword": keyword,
        "matches": matches,
        "match_count": len(matches),
        "total_errors": total_errors,
        "suggestion": suggestion,
    }


def get_weakest_points(weak_points: list, top_n: int = 3) -> list:
    """
    获取最薄弱的知识点 Top-N（按错误次数排序）

    Args:
        weak_points: 薄弱知识点列表
        top_n: 返回前 N 个

    Returns:
        排序后的薄弱点列表
    """
    sorted_points = sorted(weak_points, key=lambda x: x.get("error_count", 0), reverse=True)
    return sorted_points[:top_n]


def format_mistake_context(matches: list) -> str:
    """
    将匹配结果格式化为答疑导师可直接使用的提醒文本

    Args:
        matches: search_mistakes 返回的 matches 列表

    Returns:
        格式化的提醒文本
    """
    if not matches:
        return ""

    lines = ["\n⚠️ 历史错题提醒："]
    for i, m in enumerate(matches[:3], 1):  # 最多显示 3 条
        lines.append(f"  {i}. {m['subject']} · {m['topic']} — 错过 {m['error_count']} 次（最近：{m['last_error_date']}）")

    return "\n".join(lines)


# ── Hermes Tool 接口 ──────────────────────────────────────────

def main():
    """Hermes Tool 入口"""
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            print(json.dumps({"error": "无输入数据"}, ensure_ascii=False))
            return

    keyword = input_data.get("keyword", "")
    weak_points = input_data.get("weak_points", [])
    fuzzy = input_data.get("fuzzy", True)

    if not keyword:
        print(json.dumps({"error": "缺少 keyword 参数"}, ensure_ascii=False))
        return

    result = search_mistakes(keyword=keyword, weak_points=weak_points, fuzzy=fuzzy)

    # 附加格式化文本
    result["formatted_context"] = format_mistake_context(result["matches"])

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
