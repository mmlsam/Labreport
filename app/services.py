from __future__ import annotations

import json
import random
from pathlib import Path

from docx import Document
from docx.shared import RGBColor
from flask import current_app
from openai import OpenAI
from openai import OpenAIError


KEYWORDS = {
    "实验目的": 10,
    "实验原理": 10,
    "实验内容": 10,
    "程序": 10,
    "结果": 10,
    "总结": 10,
    "心得": 10,
}


def evaluate_report(docx_path: Path, model: str | None = None, api_key: str | None = None) -> tuple[float, str]:
    """Evaluate a report using the configured LLM when possible, fallback otherwise."""

    document = Document(docx_path)
    full_text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    if model and api_key:
        try:
            score, feedback = _evaluate_with_chatgpt(full_text, model, api_key)
            return score, feedback
        except Exception as exc:  # noqa: BLE001
            _log_evaluation_failure(exc)

    return _keyword_based_evaluation(full_text)


def annotate_report(docx_path: Path, score: float, feedback: str, output_path: Path) -> Path:
    document = Document(docx_path)
    if document.paragraphs:
        target_paragraph = document.paragraphs[0].insert_paragraph_before()
    else:
        target_paragraph = document.add_paragraph()

    score_run = target_paragraph.add_run(f"成绩：{score}分")
    score_run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
    score_run.font.bold = True

    target_paragraph.add_run().add_break()

    feedback_run = target_paragraph.add_run(f"评语：{feedback}")
    feedback_run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
    feedback_run.font.bold = True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
    return output_path


def _evaluate_with_chatgpt(report_text: str, model: str, api_key: str) -> tuple[float, str]:
    truncated_text = report_text.strip()
    if not truncated_text:
        truncated_text = "（学生提交的报告内容为空，请返回0分并提示补充完整的报告。）"
    else:
        truncated_text = truncated_text[:8000]

    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "你是一名严谨的大学C语言实验课程教师，需要根据实验报告客观评分并给出改进建议。",
            },
            {
                "role": "user",
                "content": (
                    "请阅读以下学生实验报告内容，从0到100分给出客观得分，并提供不少于40字的中文评语，"
                    "同时指出优点与需要改进的地方。\n\n报告内容：\n" + truncated_text
                ),
            },
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = completion.choices[0].message.content.strip()
    data = json.loads(content)
    score = float(data.get("score"))
    feedback = str(data.get("feedback", "")).strip()
    if not feedback:
        raise ValueError("LLM返回的评语为空")

    score = max(0.0, min(round(score, 1), 100.0))
    return score, feedback


def _keyword_based_evaluation(full_text: str) -> tuple[float, str]:
    score = 60
    matched_sections: list[str] = []
    for keyword, weight in KEYWORDS.items():
        if keyword in full_text:
            score += weight
            matched_sections.append(keyword)
    score = min(score + random.uniform(-5, 5), 100)
    score = round(score, 1)

    if matched_sections:
        feedback = f"报告结构完整，涵盖：{', '.join(matched_sections)}，请继续保持。"
    else:
        feedback = "建议补充实验目的、过程、结果等内容，让报告更加完整。"
    return score, feedback


def _log_evaluation_failure(exc: Exception) -> None:
    if isinstance(exc, OpenAIError):
        message = f"调用OpenAI接口失败：{exc}"
    else:
        message = f"LLM评测异常：{exc}"
    try:
        current_app.logger.exception(message)
    except RuntimeError:
        pass
