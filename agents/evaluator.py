# -*- coding: utf-8 -*-
"""LLM-backed answer evaluator with deterministic local safeguards."""

from __future__ import annotations

import json
import re
from typing import Any

from agents.prompt_templates import EVALUATOR_PROMPT
from backend.core.intelligence import EvaluationResult, QUESTION_TEXTS, RuleEvaluator, STANDARD_ANSWERS, parse_number
from backend.core.llm_client import ECNULlmClient
from config.settings import config


NON_ANSWER_PATTERNS = [
    r"^(我)?(不会|不懂|不知道|不理解|没思路|卡住了?)$",
    r"帮帮我",
    r"教教我",
    r"怎么做",
    r"怎么解",
    r"可以提示",
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


class AnswerEvaluator:
    """Evaluate an answer using local equivalence first, then ECNU LLM."""

    VALID_ERROR_TYPES = {"calculation", "concept", "step", "format", "none"}

    def __init__(self):
        self.local = RuleEvaluator()

    def _looks_like_answer(self, text: str) -> bool:
        compact = re.sub(r"\s+", "", str(text or ""))
        if not compact:
            return False
        if any(re.search(pattern, compact) for pattern in NON_ANSWER_PATTERNS):
            return False
        if re.search(r"(不是|并不是).*(不会|不懂|不知道)", compact):
            return False
        if re.search(r"\d|[A-Da-d]|∠|角|度|°|=", compact):
            return True
        return len(compact) <= 8

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
            return EvaluationResult(
                False,
                "format",
                0,
                "high",
                "输入更像求助或对话，不适合作为答案评分。",
                "请在答题框提交最终答案，问题讨论放在消息框。",
                STANDARD_ANSWERS.get(int(question_id or 0), ""),
            )

        local = self._local_equivalence(answer, question_id)
        if local:
            return local

        client = ECNULlmClient()
        if not client.enabled:
            return None

        qid = int(question_id or 0)
        prompt = (
            f"题目：{QUESTION_TEXTS.get(qid, f'第 {qid} 题')}\n"
            f"标准答案：{STANDARD_ANSWERS.get(qid, '')}\n"
            f"学生答案：{answer}\n"
            "请按指定 JSON 格式评估。"
        )
        raw = client.chat(
            EVALUATOR_PROMPT,
            [{"role": "user", "content": prompt}],
            model=config.ECNU_LLM_EVALUATOR_MODEL,
            temperature=0.1,
            max_tokens=360,
        )
        if not raw:
            return None

        data = self._parse_json_response(raw)
        if not data:
            return None
        return self._validate_result(data, qid)

    def evaluate(self, answer: str, question_id: int) -> EvaluationResult:
        return self.evaluate_with_llm(answer, question_id) or self.local.evaluate(answer, question_id)

    def _parse_json_response(self, raw: str) -> dict[str, Any] | None:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                return None
        return None

    def _validate_result(self, data: dict[str, Any], question_id: int) -> EvaluationResult:
        error_type = str(data.get("error_type") or "format").lower()
        if error_type not in self.VALID_ERROR_TYPES:
            error_type = "format"
        correct = bool(data.get("correct"))
        if correct:
            error_type = "none"

        try:
            score = float(data.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(score, 100))

        return EvaluationResult(
            correct=correct,
            error_type=error_type,
            score=score,
            confidence=_confidence_to_label(data.get("confidence", "medium")),
            key_mistake=str(data.get("key_mistake") or ""),
            suggestion=str(data.get("suggestion") or ""),
            standard_answer=STANDARD_ANSWERS.get(question_id, ""),
        )
