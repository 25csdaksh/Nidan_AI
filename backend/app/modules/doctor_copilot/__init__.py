"""
Doctor AI Copilot Module for NIDAN AI.
Provides evidence-grounded clinical decision support assistance to clinicians.
"""
from app.modules.doctor_copilot.models import CopilotSession, CopilotMessage, CopilotFeedback
from app.modules.doctor_copilot.router import router as doctor_copilot_router
from app.modules.doctor_copilot.service import DoctorCopilotService

__all__ = [
    "CopilotSession",
    "CopilotMessage",
    "CopilotFeedback",
    "doctor_copilot_router",
    "DoctorCopilotService",
]
