# -*- coding: utf-8 -*-
"""ECNU LLM API adapter.

The API is OpenAI-compatible. Credentials stay in .env and are never committed.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from agents.prompt_templates import EXP_EXTRA_PROMPT, GUIDE_PROMPT, TCA_EXTRA_PROMPT, TUTOR_PROMPT
from backend.core.intelligence import QUESTION_TEXTS
from config.settings import config


class ECNULlmClient:
    def __init__(self):
        self.enabled = bool(config.ECNU_LLM_ENABLED and config.ECNU_LLM_API_KEY)
        self.base_url = config.ECNU_LLM_BASE_URL.rstrip("/")
        self.api_key = config.ECNU_LLM_API_KEY
        self.timeout = config.ECNU_LLM_TIMEOUT

    def chat(self, system_prompt, messages, model, temperature=0.4, max_tokens=2048, timeout=None):
        if not self.enabled:
            return None

        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "temperature": temperature,
            "top_p": 0.9,
            "max_tokens": max_tokens,
            "stream": False,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            return None

    def chat_json(self, system_prompt, messages, model, temperature=0.1, max_tokens=600, timeout=None):
        raw = self.chat(
            system_prompt,
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None


def clean_math_text(text):
    """Convert common LaTeX fragments from model output into readable text."""
    if not text:
        return text
    cleaned = str(text)
    replacements = {
        "\\(": "",
        "\\)": "",
        "\\[": "",
        "\\]": "",
        "$": "",
        "^{\\circ}": "°",
        "^\\circ": "°",
        "\\angle": "∠",
        "\\circ": "°",
        "\\,": " ",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _agent_system_prompt(agent, experiment_group):
    prompt = TUTOR_PROMPT if agent == "Tutor" else GUIDE_PROMPT
    if experiment_group == "EXP":
        prompt += "\n\n" + EXP_EXTRA_PROMPT
    if experiment_group == "TCA":
        prompt += "\n\n" + TCA_EXTRA_PROMPT
    return prompt


def generate_agent_reply(agent, experiment_group, question_id, user_message, history=None, decision=None):
    client = ECNULlmClient()
    if not client.enabled:
        return None

    qid = int(question_id or 0)
    messages = [
        {
            "role": "user",
            "content": (
                f"当前题目：{QUESTION_TEXTS.get(qid, f'第 {qid} 题')}\n"
                f"实验组：{experiment_group}\n"
                f"当前Agent：{agent}\n"
                f"系统决策：{json.dumps(decision or {}, ensure_ascii=False)}"
            ),
        }
    ]

    for item in (history or [])[-6:]:
        role = "assistant" if item.get("type") == "assistant" else "user"
        messages.append({"role": role, "content": item.get("content", "")})

    messages.append({"role": "user", "content": user_message})
    model = config.ECNU_LLM_TUTOR_MODEL if agent == "Tutor" else config.ECNU_LLM_GUIDE_MODEL
    temperature = 0.3 if agent == "Tutor" else 0.4
    max_tokens = 520 if agent == "Tutor" else 360
    return clean_math_text(
        client.chat(
            _agent_system_prompt(agent, experiment_group),
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=8,
        )
    )


def evaluate_answer_with_llm(answer, question_id):
    """Compatibility wrapper. The formal evaluator lives in agents.evaluator."""
    from agents.evaluator import AnswerEvaluator

    return AnswerEvaluator().evaluate_with_llm(answer, question_id)
