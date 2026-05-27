# -*- coding: utf-8 -*-
"""
Unified intelligence helpers for TCA-System V2.0.

This module is the runtime entry for answer evaluation fallback, error-streak
updates, L1/L2/L3 trigger arbitration, and experiment-group actions. The named
TriggerEngine class is re-exported by backend.core.trigger_rules and
backend.core.trigger_engine so older design-document references point to the
same implementation instead of competing engines.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


STANDARD_ANSWERS = {
    1: "A",
    2: "A",
    3: "60",
    4: "180",
    5: "A",
    6: "A",
    7: "A",
    8: "A",
    9: "A",
    10: "A",
}

QUESTION_TEXTS = {
    1: "题目1",
    2: "题目2",
    3: "已知三角形ABC中，∠A=50°，∠B=70°，求∠C度数。",
    4: "三角形三个内角的和是多少度？",
    5: "选择题：请选择正确选项。",
    6: "题目6",
    7: "题目7",
    8: "题目8",
    9: "题目9",
    10: "题目10",
}

KNOWLEDGE_POINTS = {
    3: "三角形内角和",
    4: "三角形内角和",
}

HELP_KEYWORD_WEIGHTS = {
    "完全不会": 3,
    "一点不会": 3,
    "还是不会": 3,
    "真的不会": 3,
    "不会": 2,
    "不懂": 2,
    "不理解": 2,
    "不明白": 2,
    "不知道": 2,
    "看不懂": 2,
    "卡住": 2,
    "没思路": 2,
    "太难": 2,
    "帮帮我": 3,
    "帮我": 2,
    "教我": 2,
    "怎么做": 2,
    "怎么解": 2,
    "求助": 3,
}

HELP_NEGATION_PATTERNS = [
    r"不是\s*不会",
    r"并不是\s*不会",
    r"不是\s*不懂",
    r"并不是\s*不懂",
    r"不是\s*不知道",
    r"不是完全\s*不会",
    r"不是很\s*难",
    r"不用(帮|提示|管)",
    r"先不用",
    r"我再试",
    r"让我再想",
    r"我自己来",
    r"我想自己",
    r"我会了",
    r"懂了",
    r"明白了",
    r"知道了",
]

ERROR_WEIGHTS = {
    "concept": 1.0,
    "step": 0.8,
    "format": 0.5,
    "calculation": 0.6,
    "none": 0.0,
}

GROUP_ERROR_MULTIPLIER = {
    "SA": 0.5,
    "EXP": 1.0,
    "AI-AUTO": 1.0,
    "TCA": 1.5,
}

ERROR_TYPE_THRESHOLDS = {
    "concept": 1.5,
    "step": 2.5,
    "format": 3.0,
    "calculation": 3.5,
    "none": 2.0,
}

TRIGGER_PRIORITY = {"L1": 3, "L2": 2, "L3": 1}


@dataclass
class EvaluationResult:
    correct: bool
    error_type: str
    score: float
    confidence: str | float
    key_mistake: str
    suggestion: str
    standard_answer: str

    def to_dict(self):
        return asdict(self)


def normalize_confidence(confidence: Any) -> float:
    if isinstance(confidence, (int, float)):
        return max(0.0, min(float(confidence), 1.0))
    text = str(confidence or "").strip().lower()
    return {"high": 0.9, "medium": 0.65, "low": 0.35}.get(text, 0.65)


def normalize_answer_text(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .replace(" ", "")
        .replace("°", "")
        .replace("度", "")
        .upper()
    )


def parse_number(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("°", "").replace("度", "")
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            denominator = float(right)
            if denominator == 0:
                return None
            return float(left) / denominator
        except ValueError:
            return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


class RuleEvaluator:
    """Local evaluator used as deterministic fallback when LLM is unavailable."""

    def evaluate(self, answer, question_id):
        student_answer = str(answer or "").strip()
        standard = STANDARD_ANSWERS.get(int(question_id or 0), "A")
        normalized = normalize_answer_text(student_answer)
        standard_normalized = normalize_answer_text(standard)

        if normalized and normalized == standard_normalized:
            return EvaluationResult(True, "none", 100, "high", "", "答案正确，继续保持。", standard)

        student_value = parse_number(student_answer)
        standard_value = parse_number(standard)
        if student_value is not None and standard_value is not None:
            diff = abs(student_value - standard_value)
            if diff <= 0.001:
                return EvaluationResult(True, "none", 100, "high", "", "数值正确。", standard)
            if diff <= max(abs(standard_value) * 0.1, 1):
                return EvaluationResult(
                    False,
                    "calculation",
                    70,
                    "medium",
                    "答案接近标准结果，但计算存在偏差。",
                    "请重新检查代入和计算过程。",
                    standard,
                )
            return EvaluationResult(
                False,
                "concept",
                35,
                "medium",
                "答案与关键结论差距较大，可能没有用到核心知识点。",
                "先回到题目中的已知条件，再列式求解。",
                standard,
            )

        if TriggerEngine.detect_help_keywords(student_answer)["triggered"]:
            return EvaluationResult(
                False,
                "concept",
                25,
                "medium",
                "学生表达了明显求助或理解困难。",
                "先写出已知条件，再确认要使用的知识点。",
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


class TriggerEngine:
    """Unified L1/L2/L3 trigger engine."""

    error_type_thresholds = ERROR_TYPE_THRESHOLDS

    @classmethod
    def should_trigger(cls, error_streak, message=None, time_spent=0):
        return cls.should_trigger_enhanced(error_streak, "none", message, time_spent)

    @classmethod
    def should_trigger_enhanced(cls, error_streak, error_type="none", message=None, time_spent=0, confidence="medium"):
        confidence_value = normalize_confidence(confidence)
        threshold = cls.error_type_thresholds.get(error_type, cls.error_type_thresholds["none"])
        if confidence_value < 0.45:
            threshold += 0.5

        l1 = {
            "triggered": error_type != "none" and float(error_streak or 0) >= threshold,
            "threshold": threshold,
            "current_value": float(error_streak or 0),
            "error_type": error_type,
            "confidence": round(confidence_value, 2),
        }
        l2 = cls.detect_help_keywords(message)
        l3_threshold = cls.get_stagnation_threshold(question_difficulty="medium")
        l3 = {
            "triggered": int(time_spent or 0) >= l3_threshold,
            "stagnation_seconds": int(time_spent or 0),
            "threshold": l3_threshold,
        }

        diagnosis = {"L1": l1, "L2": l2, "L3": l3}
        levels = [level for level, result in diagnosis.items() if result["triggered"]]
        levels.sort(key=lambda level: TRIGGER_PRIORITY[level], reverse=True)
        strength = cls.calculate_strength(levels, error_streak, l2.get("weight", 0), time_spent)
        urgency = cls.calculate_urgency(error_streak, time_spent, levels)

        return {
            "triggered": bool(levels),
            "trigger_level": "+".join(levels) if levels else "none",
            "trigger_strength": strength,
            "urgency": urgency,
            "diagnosis": diagnosis,
        }

    @staticmethod
    def detect_help_keywords(message):
        text = str(message or "").strip()
        compact = re.sub(r"\s+", "", text)
        rejected = any(re.search(pattern, compact) for pattern in HELP_NEGATION_PATTERNS)
        detected = []
        weight = 0
        for keyword, keyword_weight in HELP_KEYWORD_WEIGHTS.items():
            if keyword in compact:
                detected.append(keyword)
                weight += keyword_weight

        return {
            "triggered": bool(detected) and not rejected and weight >= 2,
            "detected_keywords": detected,
            "weight": weight,
            "rejected": rejected,
        }

    @classmethod
    def should_switch_by_error_type(cls, error_type, error_streak, confidence="medium"):
        threshold = cls.error_type_thresholds.get(error_type, cls.error_type_thresholds["none"])
        if normalize_confidence(confidence) < 0.45:
            threshold += 0.5
        return error_type != "none" and float(error_streak or 0) >= threshold

    @staticmethod
    def update_error_streak_with_score(previous_streak, score, error_type, last_error_type=None, confidence="medium"):
        if score >= 80:
            return 0.0
        increment = 0.5 if score >= 50 else 1.0
        if error_type and last_error_type == error_type and error_type != "none":
            increment += 0.5
        if normalize_confidence(confidence) < 0.45:
            increment *= 0.6
        return round(float(previous_streak or 0) + increment, 2)

    @staticmethod
    def get_stagnation_threshold(question_difficulty="medium"):
        return {"easy": 30, "medium": 60, "hard": 120}.get(question_difficulty, 60)

    @staticmethod
    def calculate_strength(levels, error_streak, help_weight, time_spent):
        score = len(levels)
        if "L1" in levels and float(error_streak or 0) >= 3:
            score += 1
        if "L2" in levels and int(help_weight or 0) >= 4:
            score += 1
        if "L3" in levels and int(time_spent or 0) >= 120:
            score += 1
        if score >= 4:
            return "HIGH"
        if score >= 2:
            return "MEDIUM"
        if score == 1:
            return "LOW"
        return "NONE"

    @staticmethod
    def calculate_urgency(error_streak, time_spent, levels):
        base = min(float(error_streak or 0) * 20, 60)
        base += min(int(time_spent or 0) / 3, 30)
        base += len(levels) * 10
        return round(min(base, 100), 1)

    @staticmethod
    def get_action_by_condition(condition, trigger):
        triggered = bool(trigger.get("triggered"))
        actions = {
            "SA": {"action": "log_only", "inject_explanation": False, "notify_teacher": False, "switch_agent": False},
            "EXP": {"action": "inject" if triggered else "observe", "inject_explanation": triggered, "notify_teacher": False, "switch_agent": False},
            "AI-AUTO": {"action": "switch" if triggered else "observe", "inject_explanation": False, "notify_teacher": False, "switch_agent": triggered},
            "TCA": {"action": "notify" if triggered else "observe", "inject_explanation": triggered, "notify_teacher": triggered, "switch_agent": False},
        }
        return actions.get(condition, actions["SA"])

    analyze_trigger = should_trigger_enhanced


TriggerEngineV2 = TriggerEngine


def get_student_profile(cursor, student_id):
    cursor.execute(
        "SELECT student_name, experiment_group, current_question, total_questions "
        "FROM student_assignments WHERE student_id = ?",
        (student_id,),
    )
    row = cursor.fetchone()
    if not row:
        return {"student_name": "", "experiment_group": "SA", "current_question": 1, "total_questions": 10}
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
        error_streak = 0.0
        consecutive_correct = (state["consecutive_correct"] or 0) + 1
        last_error_type = "none"
    else:
        weighted = TriggerEngine.update_error_streak_with_score(
            state["error_streak"] or 0,
            evaluation.score,
            evaluation.error_type,
            state["last_error_type"],
            evaluation.confidence,
        )
        group_weight = GROUP_ERROR_MULTIPLIER.get(experiment_group, 1.0)
        error_streak = round(weighted * group_weight, 2)
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
    return TriggerEngine.detect_help_keywords(message)


def detect_trigger(error_streak, error_type, message=None, time_spent=0, confidence="medium"):
    return TriggerEngine.should_trigger_enhanced(error_streak, error_type, message, time_spent, confidence)


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
            str(evaluation.confidence),
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
        "action": TriggerEngine.get_action_by_condition(experiment_group, trigger),
    }

    if experiment_group == "SA":
        decision["agent"] = "Guide"
        if current_agent != "Guide":
            cursor.execute(
                "UPDATE student_states SET current_agent = ?, updated_at = ? WHERE student_id = ?",
                ("Guide", datetime.now().isoformat(), student_id),
            )
        decision["mode_note"] = "SA组：仅记录评估，不注入解释，不自动切换。"
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
        decision["mode_note"] = "EXP组：触发后注入解释提示，不自动切换Agent。"
        return decision

    if experiment_group == "AI-AUTO":
        if current_agent == "Tutor" and consecutive_correct >= 3:
            decision["agent"] = "Guide"
            decision["switched"] = True
            decision["explanation"] = "系统提示：你已经连续表现稳定，系统已回切到Guide模式，接下来继续引导你自主思考。"
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
            decision["mode_note"] = "AI-AUTO组：连续正确后自动回到Guide。"
            return decision

        if trigger["triggered"] and current_agent != "Tutor":
            decision["agent"] = "Tutor"
            decision["switched"] = True
            decision["explanation"] = "系统提示：检测到学习困难，已切换为Tutor模式，接下来会给出更直接的分步提示。"
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
            decision["explanation"] = "系统提示：检测到学习困难，当前保持Tutor模式，继续提供分步提示。"
        decision["mode_note"] = "AI-AUTO组：触发后自动切换Agent，教师仅观察。"
        return decision

    if experiment_group == "TCA":
        decision["teacher_alert"] = trigger["triggered"]
        if trigger["triggered"]:
            decision["explanation"] = "系统提示：已通知教师端，教师可查看详情并决定是否干预。"
        decision["mode_note"] = "TCA组：触发后推送教师端，由教师决定是否干预。"
        return decision

    return decision
