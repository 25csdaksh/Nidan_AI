from typing import Dict, List, Tuple
from app.modules.doctor_copilot.schemas import ClaimItem, EvidenceItem, SupportLevel


class UnsupportedClaimDetector:
    """
    Validates evidence citations on generated claims.
    """

    def validate_claims(
        self,
        claims: List[ClaimItem],
        evidence_catalog: Dict[str, EvidenceItem],
    ) -> Tuple[List[ClaimItem], List[str]]:
        validated_claims: List[ClaimItem] = []
        issues: List[str] = []

        for claim in claims:
            if not claim.evidence_ids:
                validated_claims.append(
                    ClaimItem(
                        claim=claim.claim,
                        evidence_ids=[],
                        support_level=SupportLevel.UNSUPPORTED,
                        validation_note="No evidence IDs cited for this factual claim.",
                    )
                )
                issues.append(f"Uncited claim: '{claim.claim}'")
                continue

            # Verify that all cited evidence IDs exist in catalog
            missing_ids = [eid for eid in claim.evidence_ids if eid not in evidence_catalog]
            if missing_ids:
                validated_claims.append(
                    ClaimItem(
                        claim=claim.claim,
                        evidence_ids=[eid for eid in claim.evidence_ids if eid in evidence_catalog],
                        support_level=SupportLevel.PARTIALLY_SUPPORTED if len(missing_ids) < len(claim.evidence_ids) else SupportLevel.UNSUPPORTED,
                        validation_note=f"Cited unknown evidence IDs: {missing_ids}",
                    )
                )
                issues.append(f"Claim cited invalid evidence IDs {missing_ids}: '{claim.claim}'")
            else:
                validated_claims.append(
                    ClaimItem(
                        claim=claim.claim,
                        evidence_ids=claim.evidence_ids,
                        support_level=SupportLevel.SUPPORTED,
                        validation_note="Fully grounded in verified evidence.",
                    )
                )

        return validated_claims, issues
