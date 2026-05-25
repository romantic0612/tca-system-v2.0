# -*- coding: utf-8 -*-
"""
Core intelligence helpers for TCA-System V2.0.

This module keeps the first production-ready intelligent loop deliberately
small: rule evaluation, error tracking, trigger detection, and group-specific
agent decisions. It can later be replaced by an LLM evaluator without changing
the API layer contract.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime


STANDARD_ANSWERS = {
    1: "A",
    2: "A",
    3: "60",
    4: "180",
    5: "A",
}

QUESTION_TEXTS = {
    1: "题目1",
    2: "题目2",
    3: "已知三角形ABC中，∠A=50°，∠B=70°，求∠C度数。",
    4: "三角形三个内角的和是多少度？",
    5: "题目5",
}

HELP_KEYWORDS = [
    "不会", "不懂", "不知道", "不明白", "不理解", "怎么做", "怎么解",
    "帮帮我", "教我", "卡住", "没思路", "看不懂", "太难", "放弃",
]

REJECT_HELP_KEYWORDS = [
    "我再试试", "让我再", "不用", "先不用", "我自己", "想自己",
    "再想想", "知道了", "明白了", "懂了", "会了",
]

ERROR_WEIGHTS = {
    "concept": 1.0,
    "step": 0.8,
    "calculation": 0.6,
    "format": 0.5,
    "none": 0.0,
}

GROUP_ERROR_MULTIPLIER = {
    "SA": 0.5,
    "EXP": 1.0,
    "AI-AUTO": 1.0,
    "TCA": 1.5,
}

ERROR_THRESHOLDS = {
    "concept": 1.5,
    "step": 2.5,
    "calculation": 3.5,
    "format": 2.0,
    "none": 2.5,
}


@dataclass
class EvaluationResult:
    correct: bool
    error_type: str
    score: float
    confidence: str
    key_mistake: str
    suggestion: str
    standard_answer: str

    def to_dict(self):
        return asdict(self)


class RuleEvaluator:
    def evaluate(self, answer, question_id):
        student_answer = str(answer or "").strip()
        standard = STANDARD_ANSWERS.get(int(question_id), "A")
        normalized = student_answer.replace(" ", "").upper()
        standard_normalized = standard.replace(" ", "").upper()

        if normalized == standard_normalized:
            return EvaluationResult(
                correct=True,
                error_type="none",
                score=100,
                confidence="high",
                key_mistake="",
                suggestion="答案正确，继续保持。",
                standard_answer=standard,
            )

        try:
            student_value = float(student_answer)
            standard_value = float(standard)
            diff = abs(student_value - standard_value)
            if diff <= 0.001:
                return EvaluationResult(True, "none", 100, "high", "", "数值正确。", standard)
            if diff <= max(abs(standard_value) * 0.1, 1):
                return EvaluationResult(
                    False,
                    "calculation",
                    70,
                    "medium",
                    "数值接近标准答案，但计算存在偏差。",
                    "请重新检查代入和计算过程。",
                    standard,
                )
            return EvaluationResult(
                False,
                "concept",
                35,
                "medium",
                "答案与关键结论差距较大。",
                "先回到题目中的核心概念，再列式求解。",
                standard,
            )
        except (TypeError, ValueError):
            pass

        if any(token in student_answer for token in ["?", "？", "不会", "不知道"]):
            return EvaluationResult(
                False,
                "concept",
                25,
                "medium",
                "答案表现出概念理解或起步困难。",
                "先写出已知条件，再确定要用的知识点。",
                standard,
            )

        return EvaluationResult(
            False,
            "format",
            45,
            "low",
            "答案格式或选项不符合标准答案。",
            "请检查答案格式，并确认是否填入了最终结果。",
            standard,
        )


def get_student_profile(cursor, student_id):
    cursor.execute(
        "SELECT student_name, experiment_group, current_question, total_questions "
        "FROM student_assignments WHERE student_id = ?",
        (student_id,),
    )
    row = cursor.fetchone()
    if not row:
        return {
            "student_name": "",
            "experiment_group": "SA",
            "current_question": 1,
            "total_questions": 10,
        }
    return {
        "student_name": row["student_name"] or "",
        "experiment_group": row["experiment_group"] or "SA",
        "current_question": row["current_question"] or 1,
        "total_questions": row["total_questions"] or 10,
    }


def ensure_student_state(cursor, student_id):
    cursor.execute("SELECT * FROM student_states WHERE student_id = ?", (student_id,))
    row = cursor.fetchone()
    if row:
        return row

    cursor.execute(
        "INSERT OR IGNORE INTO student_states (student_id, last_response_time) VALUES (?, ?)",
        (student_id, datetime.now().isoformat()),
    )
    cursor.execute("SELECT * FROM student_states WHERE student_id = ?", (student_id,))
    return cursor.fetchone()


def update_error_state(cursor, student_id, experiment_group, evaluation):
    state = ensure_student_state(cursor, student_id)
    current_agent = state["current_agent"] or "Guide"
    now = datetime.now().isoformat()

    if evaluation.correct:
        error_streak = max((state["error_streak"] or 0) - 1.0, 0)
        consecutive_correct = (state["consecutive_correct"] or 0) + 1
        last_error_type = "none"
    else:
        base_weight = ERROR_WEIGHTS.get(evaluation.error_type, 0.8)
        group_weight = GROUP_ERROR_MULTIPLIER.get(experiment_group, 1.0)
        same_type_bonus = 0.5 if state["last_error_type"] == evaluation.error_type else 0
        error_streak = (state["error_streak"] or 0) + base_weight * group_weight + same_type_bonus
        consecutive_correct = 0
        last_error_type = evaluation.error_type

    cursor.execute(
        """
        UPDATE student_states
        SET error_streak = ?, last_error_type = ?, consecutive_correct = ?,
            total_interactions = COALESCE(total_interactions, 0) + 1,
            last_response_time = ?, updated_at = ?
        WHERE student_id = ?
        """,
        (error_streak, last_error_type, consecutive_correct, now, now, student_id),
    )
    return {
        "current_agent": current_agent,
        "error_streak": error_streak,
        "last_error_type": last_error_type,
        "consecutive_correct": consecutive_correct,
    }


def detect_help_keywords(message):
    text = str(message or "")
    detected = [keyword for keyword in HELP_KEYWORDS if keyword in text]
    rejected = any(keyword in text for keyword in REJECT_HELP_KEYWORDS)
    return {
        "triggered": bool(detected) and not rejected,
        "detected_keywords": detected,
        "rejected": rejected,
    }


def detect_trigger(error_streak, error_type, message=None, time_spent=0):
    l1_threshold = ERROR_THRESHOLDS.get(error_type, ERROR_THRESHOLDS["none"])
    l1 = {
        "triggered": error_type != "none" and error_streak >= l1_threshold,
        "threshold": l1_threshold,
        "current_value": error_streak,
        "error_type": error_type,
    }
    l2 = detect_help_keywords(message)
    l3_threshold = 300
    l3 = {
        "triggered": int(time_spent or 0) >= l3_threshold,
        "stagnation_seconds": int(time_spent or 0),
        "threshold": l3_threshold,
    }

    diagnosis = {"L1": l1, "L2": l2, "L3": l3}
    levels = [level for level, result in diagnosis.items() if result["triggered"]]
    strength = {0: "NONE", 1: "LOW", 2: "MEDIUM", 3: "HIGH"}.get(len(levels), "HIGH")
    return {
        "triggered": bool(levels),
        "trigger_level": "+".join(levels) if levels else "none",
        "trigger_strength": strength,
        "diagnosis": diagnosis,
    }


def record_evaluation(cursor, student_id, question_id, answer, evaluation):
    cursor.execute(
        """
        INSERT INTO evaluation_records
        (student_id, question_id, student_answer, standard_answer, is_correct,
         error_type, score, confidence, key_mistake, suggestion, evaluated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student_id,
            question_id,
            answer,
            evaluation.standard_answer,
            1 if evaluation.correct else 0,
            evaluation.error_type,
            evaluation.score,
            evaluation.confidence,
            evaluation.key_mistake,
            evaluation.suggestion,
            datetime.now().isoformat(),
        ),
    )


def record_trigger(cursor, student_id, trigger, error_type, error_streak):
    if not trigger["triggered"]:
        return None

    diagnosis_json = json.dumps(trigger["diagnosis"], ensure_ascii=False)
    detected_keywords = trigger["diagnosis"].get("L2", {}).get("detected_keywords", [])
    cursor.execute(
        """
        INSERT INTO trigger_events
        (student_id, trigger_level, error_type, error_streak_value,
         stagnation_seconds, detected_keywords, trigger_strength, diagnosis_result, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student_id,
            trigger["trigger_level"],
            error_type,
            error_streak,
            trigger["diagnosis"].get("L3", {}).get("stagnation_seconds", 0),
            json.dumps(detected_keywords, ensure_ascii=False),
            trigger["trigger_strength"],
            diagnosis_json,
            datetime.now().isoformat(),
        ),
    )
    return cursor.lastrowid


def apply_group_strategy(cursor, student_id, experiment_group, current_agent, trigger, trigger_event_id, consecutive_correct=0):
    decision = {
        "agent": current_agent or "Guide",
        "switched": False,
        "explanation": None,
        "teacher_alert": False,
        "mode_note": "",
    }

    if experiment_group == "SA":
        decision["agent"] = "Guide"
        if current_agent != "Guide":
            cursor.execute(
                "UPDATE student_states SET current_agent = ?, updated_at = ? WHERE student_id = ?",
                ("Guide", datetime.now().isoformat(), student_id),
            )
        decision["mode_note"] = "SA组：仅记录评估，不显示解释，不自动切换。"
        return decision

    if experiment_group == "EXP":
        decision["agent"] = "Guide"
        if current_agent != "Guide":
            cursor.execute(
                "UPDATE student_states SET current_agent = ?, updated_at = ? WHERE student_id = ?",
                ("Guide", datetime.now().isoformat(), student_id),
            )
        if trigger["triggered"]:
            decision["explanation"] = "系统提示：我发现你可能卡在关键概念上。先写出已知条件，再一步步推导。"
        decision["mode_note"] = "EXP组：提供解释提示，不自动切换。"
        return decision

    if experiment_group == "AI-AUTO":
        if current_agent == "Tutor" and consecutive_correct >= 3:
            decision["agent"] = "Guide"
            decision["switched"] = True
            decision["explanation"] = "系统提示：你已经连续几轮表现稳定，系统已回切为 Guide 模式，接下来会继续引导你自主思考。"
            cursor.execute(
                "UPDATE student_states SET current_agent = ?, last_trigger_level = ?, updated_at = ? WHERE student_id = ?",
                ("Guide", "recovery", datetime.now().isoformat(), student_id),
            )
            cursor.execute(
                """
                INSERT INTO agent_switches
                (student_id, from_agent, to_agent, switch_reason, triggered_by, trigger_event_id, created_at)
                VALUES (?, ?, ?, ?, 'auto_recovery', ?, ?)
                """,
                (student_id, "Tutor", "Guide", "consecutive_correct>=3", trigger_event_id, datetime.now().isoformat()),
            )
            decision["mode_note"] = "AI-AUTO组：连续正确后自动回切 Guide。"
            return decision

        if trigger["triggered"] and current_agent != "Tutor":
            decision["explanation"] = "系统提示：检测到学习困难，已切换为 Tutor 模式，接下来会给出更直接的分步提示。"
            decision["agent"] = "Tutor"
            decision["switched"] = True
            cursor.execute(
                "UPDATE student_states SET current_agent = ?, last_trigger_level = ?, updated_at = ? WHERE student_id = ?",
                ("Tutor", trigger["trigger_level"], datetime.now().isoformat(), student_id),
            )
            cursor.execute(
                """
                INSERT INTO agent_switches
                (student_id, from_agent, to_agent, switch_reason, triggered_by, trigger_event_id, created_at)
                VALUES (?, ?, ?, ?, 'auto', ?, ?)
                """,
                (student_id, current_agent, "Tutor", trigger["trigger_level"], trigger_event_id, datetime.now().isoformat()),
            )
        elif trigger["triggered"]:
            decision["explanation"] = "系统提示：检测到学习困难，当前保持 Tutor 模式，继续给你更直接的分步提示。"
        decision["mode_note"] = "AI-AUTO组：触发后自动切换 Agent。"
        return decision

    if experiment_group == "TCA":
        decision["teacher_alert"] = trigger["triggered"]
        decision["mode_note"] = "TCA组：触发后推送教师端，由教师决定是否干预。"
        return decision

    return decision
