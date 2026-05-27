# -*- coding: utf-8 -*-
"""LLM-backed answer evaluator with deterministic local safeguards."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.core.intelligence import EvaluationResult, QUESTION_TEXTS, RuleEvaluator, STANDARD_ANSWERS, parse_number
from backend.core.llm_client import ECNULlmClient
from config.settings import config


EVALUATOR_PROMPT = """
你是初中数学答案评估助手，负责客观判断学生答案是否正确。

只输出严格 JSON，不要额外文字。格式如下：
{
  "correct": true,
  "error_type": "calculation|concept|step|format|none|unknown",
  "score": 0,
  "confidence": 0.0,
  "key_mistake": "核心错误描述",
  "suggestion": "简短建议"
}

评估规则：
- 等价答案应判为正确。
- 正确时 error_type 为 none，score >= 80。
- 如果只是算错，error_type 为 calculation。
- 如果没有用到关键知识点或明显不理解，error_type 为 concept。
- 如果思路方向有偏但部分合理，error_type 为 step。
- 如果内容不是可评分答案或格式不明确，error_type 为 format。
""".strip()

HELP_KEYWORDS = [
    "完全不会",
    "一点不会",
    "还是不会",
    "真的不会",
    "不会",
    "不懂",
    "不理解",
    "不明白",
    "不知道",
    "看不懂",
    "卡住",
    "没思路",
    "太难",
    "帮帮我",
    "帮我",
    "教教我",
    "教我",
    "怎么做",
    "怎么解",
    "可以提示",
    "求助",
]


def _confidence_to_label(value: Any) -> str:
    if isinstance(value, (int, float)):
        if value >= 0.75:
            return "high"
        if value >= 0.45:
            return "medium"
        return "low"
    text = str(value or "").lower()
    return text if text in {"high", "medium", "low"} else "medium"


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().lower()
    if text in {"true", "yes", "1", "正确", "对", "是"}:
        return True
    if text in {"false", "no", "0", "错误", "错", "否"}:
        return False
    return False


class AnswerEvaluator:
    """Evaluate an answer using local equivalence first, then ECNU LLM."""

    VALID_ERROR_TYPES = {"calculation", "concept", "step", "format", "none", "unknown"}

    def __init__(self):
        self.local = RuleEvaluator()

    def _looks_like_answer(self, text: str) -> bool:
        compact = re.sub(r"\s+", "", str(text or ""))
        if not compact:
            return False

        math_patterns = [
            r"\d",
            r"[x-zX-Z]",
            r"[+\-*/=]",
            r"[≈≠≤≥<>]",
            r"解[:：]",
            r"(答案|结果|所以|得)[:：]?",
            r"^[是与否对错]",
        ]
        if any(re.search(pattern, compact) for pattern in math_patterns):
            return True

        matched_chars = sum(len(keyword) for keyword in HELP_KEYWORDS if keyword in compact)
        return not (matched_chars > 0 and matched_chars / max(len(compact), 1) > 0.5)

    def _skipped_result(self, question_id: int) -> EvaluationResult:
        return EvaluationResult(
            False,
            "unknown",
            0,
            0.5,
            "输入更像提问、求助或情绪表达，已跳过答案评分。",
            "请在答题框提交最终答案，问题讨论放在消息框。",
            STANDARD_ANSWERS.get(int(question_id or 0), ""),
            True,
        )

    def _unknown_result(self, question_id: int) -> EvaluationResult:
        return EvaluationResult(
            False,
            "unknown",
            0,
            0.5,
            "评估结果解析失败。",
            "请重新提交更清晰的答案。",
            STANDARD_ANSWERS.get(int(question_id or 0), ""),
        )

    def _get_evaluator_prompt(self) -> str:
        try:
            from agents.prompt_templates import get_evaluator_prompt

            return get_evaluator_prompt()
        except (ImportError, AttributeError):
            return EVALUATOR_PROMPT

    def _local_equivalence(self, answer: str, question_id: int) -> EvaluationResult | None:
        standard = STANDARD_ANSWERS.get(int(question_id or 0), "")
        if not standard:
            return None
        answer_value = parse_number(answer)
        standard_value = parse_number(standard)
        if answer_value is not None and standard_value is not None and abs(answer_value - standard_value) <= 0.001:
            return EvaluationResult(True, "none", 100, "high", "", "答案正确，继续保持。", standard)
        compact_answer = str(answer or "").strip().replace(" ", "").upper()
        compact_standard = str(standard or "").strip().replace(" ", "").upper()
        if compact_answer and compact_answer == compact_standard:
            return EvaluationResult(True, "none", 100, "high", "", "答案正确，继续保持。", standard)
        return None

    def evaluate_with_llm(self, answer: str, question_id: int) -> EvaluationResult | None:
        if not self._looks_like_answer(answer):
            return self._skipped_result(question_id)

        client = ECNULlmClient()
        if not client.enabled:
            return self._local_equivalence(answer, question_id)

        qid = int(question_id or 0)
        prompt = (
            f"题目：{QUESTION_TEXTS.get(qid, f'第 {qid} 题')}\n"
            f"标准答案：{STANDARD_ANSWERS.get(qid, '')}\n"
            f"学生答案：{answer}\n"
            "请按指定 JSON 格式评估。"
        )
        system_prompt = self._get_evaluator_prompt()
        try:
            if hasattr(client, "chat_json"):
                data = client.chat_json(
                    system_prompt,
                    [{"role": "user", "content": prompt}],
                    model="ecnu-max",
                    temperature=0.1,
                    max_tokens=600,
                )
            else:
                raw = client.chat(
                    system_prompt,
                    [{"role": "user", "content": prompt}],
                    model=config.ECNU_LLM_EVALUATOR_MODEL,
                    temperature=0.1,
                    max_tokens=300,
                )
                data = self._parse_json_response(raw or "")
        except (TypeError, ValueError, json.JSONDecodeError):
            return self._unknown_result(qid)

        if not data:
            return self._unknown_result(qid)
        return self._validate_result(data, qid)

    def evaluate(self, answer: str, question_id: int) -> EvaluationResult:
        return self.evaluate_with_llm(answer, question_id) or self.local.evaluate(answer, question_id)

    def _parse_json_response(self, raw: str) -> dict[str, Any] | None:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("No JSON object found in evaluator response.")

    def _validate_result(self, data: dict[str, Any], question_id: int) -> EvaluationResult:
        error_type = str(data.get("error_type") or "unknown").lower()
        if error_type not in self.VALID_ERROR_TYPES:
            error_type = "unknown"
        correct = _parse_bool(data.get("correct", False))
        if correct:
            error_type = "none"

        try:
            score = float(data.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(score, 100))

        try:
            confidence = float(data.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(confidence, 1.0))

        return EvaluationResult(
            correct=correct,
            error_type=error_type,
            score=score,
            confidence=confidence,
            key_mistake=str(data.get("key_mistake") or ""),
            suggestion=str(data.get("suggestion") or ""),
            standard_answer=STANDARD_ANSWERS.get(question_id, ""),
        )
