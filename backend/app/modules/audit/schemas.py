from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditLogBase(BaseModel):
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditLogCreate(AuditLogBase):
    actor_id: Optional[str] = None


class AuditLogResponse(AuditLogBase):
    id: str
    actor_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
