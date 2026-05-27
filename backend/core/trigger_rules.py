# -*- coding: utf-8 -*-
"""Unified trigger engine public entry.

The project previously referenced trigger_rules.py and trigger_engine.py as two
separate implementations. Both files now re-export the same TriggerEngine from
backend.core.intelligence, so runtime logic has one source of truth.
"""

from agents.prompt_templates import EVALUATOR_PROMPT, EXP_EXTRA_PROMPT, GUIDE_PROMPT, TUTOR_PROMPT
from backend.core.intelligence import (
    ERROR_TYPE_THRESHOLDS,
    HELP_KEYWORD_WEIGHTS,
    TriggerEngine,
    TriggerEngineV2,
    detect_help_keywords,
    detect_trigger,
)


class PromptManager:
    GUIDE_PROMPT = GUIDE_PROMPT
    TUTOR_PROMPT = TUTOR_PROMPT
    EXP_ADDON = EXP_EXTRA_PROMPT
    EVALUATOR_PROMPT = EVALUATOR_PROMPT

    @classmethod
    def get_prompt(cls, condition="SA", agent_mode="Guide"):
        prompt = cls.TUTOR_PROMPT if agent_mode == "Tutor" else cls.GUIDE_PROMPT
        if condition == "EXP":
            prompt += "\n\n" + cls.EXP_ADDON
        return prompt

    @classmethod
    def get_evaluator_prompt(cls):
        return cls.EVALUATOR_PROMPT


def analyze_trigger(error_streak, error_type="none", message=None, time_spent=0, confidence="medium"):
    return TriggerEngine.should_trigger_enhanced(error_streak, error_type, message, time_spent, confidence)
