from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RuleEvaluationResult(BaseModel):
    is_triggered: bool
    finding_type: str
    analyte: Optional[str] = None
    value: Optional[str] = None
    normalized_value: Optional[float] = None
    unit: Optional[str] = None
    status: str
    severity: str
    title: str
    explanation: str
    clinical_association: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    rule_id: str
    rule_version: str
    reference_source: str = "KNOWLEDGE_BASE"
    reference_source_version: Optional[str] = None
    requires_review: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseClinicalRule(ABC):
    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        rule_version: str,
        rule_type: str,
        applicable_analytes: List[str],
        severity: str,
        source: str,
        source_version: str,
        enabled: bool = True,
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_version = rule_version
        self.rule_type = rule_type
        self.applicable_analytes = applicable_analytes
        self.severity = severity
        self.source = source
        self.source_version = source_version
        self.enabled = enabled

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> List[RuleEvaluationResult]:
        """Evaluate rule against provided context containing entities, patient data, and resolved ranges."""
        pass
