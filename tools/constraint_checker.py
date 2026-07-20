"""
计划约束校验器

对学习计划进行合理性校验：
- 日总时长不超过上限（默认 8h）
- 单科连续不超过 2h
- 超过上限时自动给出缩放建议

用法：
    python constraint_checker.py '{"daily_hours":4,"subjects":["数据结构","操作系统"],"days_until_exam":14}'

作为 Hermes Tool 注册：
    hermes tools register tools/constraint_checker.py
"""

import json
import sys


# 约束常量
MAX_DAILY_HOURS = 8       # 每日最大学习时长
MAX_CONTINUOUS_HOURS = 2  # 单科连续最大时长
MIN_DAILY_HOURS = 1       # 每日最小时长
MAX_SUBJECTS_PER_DAY = 4  # 每天最多科目数


def check_plan(
    daily_hours: float,
    subjects: list,
    days_until_exam: int = None,
    task_details: list = None,
) -> dict:
    """
    校验学习计划是否合理

    Args:
        daily_hours: 每日计划学习时长（小时）
        subjects: 科目列表
        days_until_exam: 距考试天数（可选）
        task_details: 详细任务列表（可选），格式：
            [{"subject": "数据结构", "hours": 2, "topic": "线性表"}, ...]

    Returns:
        {
            "valid": true/false,
            "warnings": [...],
            "suggestions": [...],
            "adjusted_hours": null or 建议调整后的数值
        }
    """
    warnings = []
    suggestions = []
    valid = True

    # 1. 日总时长校验
    if daily_hours > MAX_DAILY_HOURS:
        valid = False
        adjusted = MAX_DAILY_HOURS
        warnings.append(f"每日 {daily_hours}h 超过上限 {MAX_DAILY_HOURS}h")
        suggestions.append(f"建议将每日学习时长调整为 {adjusted}h")
    elif daily_hours < MIN_DAILY_HOURS:
        warnings.append(f"每日 {daily_hours}h 较少，建议至少 {MIN_DAILY_HOURS}h/天")

    # 2. 科目数量校验
    if len(subjects) > MAX_SUBJECTS_PER_DAY:
        valid = False
        warnings.append(f"每天 {len(subjects)} 科偏多，建议不超过 {MAX_SUBJECTS_PER_DAY} 科/天")
        suggestions.append(f"建议每天轮换 {MAX_SUBJECTS_PER_DAY} 科，其余隔天安排")

    # 3. 任务细节校验
    if task_details:
        # 3.1 单科连续时长
        subject_continuous = {}
        for task in task_details:
            subj = task.get("subject", "")
            hrs = task.get("hours", 0)
            subject_continuous[subj] = subject_continuous.get(subj, 0) + hrs

        for subj, hrs in subject_continuous.items():
            if hrs > MAX_CONTINUOUS_HOURS:
                warnings.append(f"{subj} 单日 {hrs}h，超过单科连续上限 {MAX_CONTINUOUS_HOURS}h")
                suggestions.append(f"建议将 {subj} 拆分为上下午两个时段，或减少至 {MAX_CONTINUOUS_HOURS}h")

        # 3.2 总时长一致性
        total = sum(t.get("hours", 0) for t in task_details)
        if total > MAX_DAILY_HOURS:
            valid = False
            ratio = MAX_DAILY_HOURS / total
            warnings.append(f"任务总时长 {total}h 超过上限 {MAX_DAILY_HOURS}h")
            suggestions.append(f"建议按 {ratio:.0%} 比例缩放各项任务时长")

    # 4. 距考试天数建议
    if days_until_exam is not None:
        if daily_hours <= 0:
            pass
        elif days_until_exam <= 0:
            warnings.append("考试日期已过或为今天，请确认日期是否正确")
        elif days_until_exam <= 3:
            suggestions.append(f"⚠️ 距考试仅 {days_until_exam} 天，建议每日至少 6h 集中冲刺")
        elif days_until_exam <= 7:
            suggestions.append(f"距考试 {days_until_exam} 天，进入冲刺阶段")
        else:
            total_available_hours = days_until_exam * daily_hours
            suggestions.append(f"备考期 {days_until_exam} 天，总可用 {total_available_hours}h，建议合理分配到各科")

    # 5. 无问题时
    if not warnings:
        warnings.append("✅ 计划校验通过，各项指标在合理范围内")

    return {
        "valid": valid,
        "warnings": warnings,
        "suggestions": suggestions,
        "daily_hours_input": daily_hours,
        "subjects_count": len(subjects),
        "days_until_exam": days_until_exam,
    }


def suggest_daily_split(daily_hours: float, subjects: list) -> list:
    """
    自动建议每日科目时间分配

    Args:
        daily_hours: 每日学习时长
        subjects: 科目列表

    Returns:
        建议的时间分配列表
    """
    if not subjects:
        return []

    # 简单均分，每科不超过2h
    per_subject = min(daily_hours / len(subjects), MAX_CONTINUOUS_HOURS)
    per_subject = round(per_subject, 1)

    plan = []
    remaining = daily_hours
    for i, subj in enumerate(subjects):
        if i == len(subjects) - 1:
            hours = round(remaining, 1)
        else:
            hours = per_subject
        remaining -= hours
        plan.append({"subject": subj, "hours": max(hours, 0.5)})

    return plan


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

    daily_hours = float(input_data.get("daily_hours", 0))
    subjects = input_data.get("subjects", [])
    days_until_exam = input_data.get("days_until_exam")
    task_details = input_data.get("task_details")

    result = check_plan(
        daily_hours=daily_hours,
        subjects=subjects,
        days_until_exam=days_until_exam,
        task_details=task_details,
    )

    # 附加自动分配建议
    if subjects:
        result["suggested_split"] = suggest_daily_split(daily_hours, subjects)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
