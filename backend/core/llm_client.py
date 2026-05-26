# -*- coding: utf-8 -*-
"""
ECNU LLM API adapter.

The API is OpenAI-compatible. Keep credentials outside source code and enable
calls only when ECNU_LLM_API_KEY is available.
"""

import json
import re
import urllib.error
import urllib.request

from config.settings import config
from backend.core.intelligence import EvaluationResult, QUESTION_TEXTS, STANDARD_ANSWERS


GUIDE_PROMPT = """
你是初中数学学习引导老师，擅长苏格拉底式提问。

核心原则：
1. 不直接给最终答案。
2. 不长篇解释，不直接告诉学生“为什么这样做”。
3. 用提问引导学生观察已知条件、目标和下一步。
4. 语气温和鼓励，学生挫败时先共情再继续。
5. 每次回复尽量以开放式问题结尾。
6. 不使用 LaTeX、Markdown 数学公式或反斜杠转义；角和度数直接写成 ∠A=50°。
""".strip()


TUTOR_PROMPT = """
你是经验丰富的初中数学辅导老师，适合学生多次出错时分步精讲。

工作方式：
1. 先温和过渡，肯定学生已经尝试。
2. 点明可能卡住的原因，但不要直接替学生完成所有作答。
3. 分步讲解，每步后询问理解情况。
4. 讲解结束后追加一个元认知问题：现在你能回顾一下刚才哪里卡住了吗？
5. 不使用 LaTeX、Markdown 数学公式或反斜杠转义；角和度数直接写成 ∠A=50°。
""".strip()


EXP_EXTRA_PROMPT = """
当前学生属于 EXP 组。学生明确表达不懂或连续出错时，可以提供 1-2 句通俗解释，
然后立刻回到提问模式。
""".strip()


TCA_EXTRA_PROMPT = """
当前学生属于 TCA 组。教师可能会覆盖系统行为。回复需要保持克制，
优先帮助教师可控干预链路，不主动宣称已经替教师做决定。
""".strip()


EVALUATOR_PROMPT = """
你是初中数学答案评估助手，负责客观判断学生解答是否正确。

只输出严格 JSON，不要额外文字。格式如下：
{
  "correct": true,
  "error_type": "calculation|concept|step|format|none",
  "score": 0,
  "confidence": 0.0,
  "key_mistake": "核心错误描述",
  "suggestion": "简短建议"
}

评估规则：
- 正确只做简短肯定，error_type 为 none。
- 错误只指出错误类型和核心问题，不直接泄露标准答案。
""".strip()


class ECNULlmClient:
    def __init__(self):
        self.enabled = bool(config.ECNU_LLM_ENABLED and config.ECNU_LLM_API_KEY)
        self.base_url = config.ECNU_LLM_BASE_URL.rstrip("/")
        self.api_key = config.ECNU_LLM_API_KEY
        self.timeout = config.ECNU_LLM_TIMEOUT

    def chat(self, system_prompt, messages, model, temperature=0.4, max_tokens=2048):
        if not self.enabled:
            return None

        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "temperature": temperature,
            "top_p": 0.90,
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
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            return None


def _question_context(question_id):
    qid = int(question_id or 0)
    return {
        "question_text": QUESTION_TEXTS.get(qid, f"第 {qid} 题"),
        "standard_answer": STANDARD_ANSWERS.get(qid, ""),
    }


def clean_math_text(text):
    """Convert common LaTeX fragments from model output into readable text."""
    if not text:
        return text
    cleaned = str(text)
    cleaned = cleaned.replace("\\(", "").replace("\\)", "")
    cleaned = cleaned.replace("\\[", "").replace("\\]", "")
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace("\\angle", "∠")
    cleaned = cleaned.replace("\\circ", "°")
    cleaned = cleaned.replace("\\,", " ")
    cleaned = cleaned.replace("^°", "°").replace("^{°}", "°")
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

    context = _question_context(question_id)
    messages = [
        {
            "role": "user",
            "content": (
                f"当前题目：{context['question_text']}\n"
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
    temperature = 0.30 if agent == "Tutor" else 0.40
    return clean_math_text(client.chat(
        _agent_system_prompt(agent, experiment_group),
        messages,
        model=model,
        temperature=temperature,
        max_tokens=2048,
    ))


def evaluate_answer_with_llm(answer, question_id):
    client = ECNULlmClient()
    if not client.enabled:
        return None

    context = _question_context(question_id)
    content = (
        f"题目：{context['question_text']}\n"
        f"标准答案：{context['standard_answer']}\n"
        f"学生答案：{answer}\n"
        "请按指定 JSON 格式评估。"
    )
    raw = client.chat(
        EVALUATOR_PROMPT,
        [{"role": "user", "content": content}],
        model=config.ECNU_LLM_EVALUATOR_MODEL,
        temperature=0.10,
        max_tokens=300,
    )
    if not raw:
        return None

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return None

    error_type = data.get("error_type") or "none"
    if error_type not in ["calculation", "concept", "step", "format", "none"]:
        error_type = "format"

    return EvaluationResult(
        correct=bool(data.get("correct")),
        error_type=error_type,
        score=float(data.get("score", 0)),
        confidence=str(data.get("confidence", "medium")),
        key_mistake=data.get("key_mistake", ""),
        suggestion=data.get("suggestion", ""),
        standard_answer=context["standard_answer"],
    )
