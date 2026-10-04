"""
Prompt package for NIDAN AI Doctor Copilot.
Includes strict CDSS system guardrails and prompt injection defenses.
"""
from app.modules.doctor_copilot.prompts.system_prompt import CDSS_SYSTEM_PROMPT, PROMPT_VERSION
from app.modules.doctor_copilot.prompts.clinical_summary_prompt import build_clinical_summary_prompt
from app.modules.doctor_copilot.prompts.question_answer_prompt import build_question_answer_prompt
from app.modules.doctor_copilot.prompts.comparison_prompt import build_comparison_prompt

__all__ = [
    "CDSS_SYSTEM_PROMPT",
    "PROMPT_VERSION",
    "build_clinical_summary_prompt",
    "build_question_answer_prompt",
    "build_comparison_prompt",
]
