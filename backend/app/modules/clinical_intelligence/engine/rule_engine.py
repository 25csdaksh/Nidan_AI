from typing import Any, Dict, List, Optional
from app.modules.clinical_intelligence.rules.base import BaseClinicalRule, RuleEvaluationResult
from app.modules.clinical_intelligence.rules.abnormality import LabAbnormalityRule
from app.modules.clinical_intelligence.rules.critical import CriticalValueRule
from app.modules.clinical_intelligence.rules.deficiency import DeficiencyDetectionRule
from app.modules.clinical_intelligence.rules.patterns import MultiMarkerPatternRule


class ClinicalRuleEngine:
    """Deterministic, auditable clinical rule orchestration engine."""

    def __init__(self, rules: Optional[List[BaseClinicalRule]] = None):
        if rules is not None:
            self.rules = rules
        else:
            self.rules = [
                LabAbnormalityRule(),
                CriticalValueRule(),
                DeficiencyDetectionRule(),
                MultiMarkerPatternRule(),
            ]

    def register_rule(self, rule: BaseClinicalRule) -> None:
        self.rules.append(rule)

    def get_rule_metadata(self) -> List[Dict[str, Any]]:
        return [
            {
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "rule_version": r.rule_version,
                "rule_type": r.rule_type,
                "applicable_analytes": r.applicable_analytes,
                "severity": r.severity,
                "source": r.source,
                "source_version": r.source_version,
                "enabled": r.enabled,
            }
            for r in self.rules
        ]

    def evaluate_all(self, context: Dict[str, Any]) -> List[RuleEvaluationResult]:
        all_results: List[RuleEvaluationResult] = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            rule_results = rule.evaluate(context)
            for res in rule_results:
                if res.is_triggered:
                    all_results.append(res)
        return all_results
