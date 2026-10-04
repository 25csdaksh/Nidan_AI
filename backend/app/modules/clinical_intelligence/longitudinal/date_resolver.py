import re
from datetime import datetime, timezone
from typing import Optional, Tuple
from pydantic import BaseModel


class DateResolutionResult(BaseModel):
    resolved_date: Optional[datetime] = None
    source: str  # REPORT_DATE, TEST_DATE, DOCUMENT_DATE, UPLOAD_TIMESTAMP, UNKNOWN
    confidence: str  # HIGH, MEDIUM, LOW
    raw_date_str: Optional[str] = None


class ObservationDateResolver:
    """Demographic-safe and multi-pattern medical observation date resolver."""

    DATE_PATTERNS = [
        # YYYY-MM-DD or YYYY/MM/DD
        (r"\b(20\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b", "%Y-%m-%d"),
        # DD-MM-YYYY or DD/MM/YYYY
        (r"\b(0[1-9]|[12]\d|3[01])[-/.](0[1-9]|1[0-2])[-/.](20\d{2})\b", "%d-%m-%Y"),
        # DD-Mon-YYYY (e.g., 15-Aug-2026 or 15 Aug 2026)
        (r"\b(0[1-9]|[12]\d|3[01])[\s-]([A-Za-z]{3})[\s-](20\d{2})\b", "%d-%b-%Y"),
        # Month DD, YYYY (e.g., August 15, 2026)
        (r"\b([A-Za-z]{3,9})\s+(0[1-9]|[12]\d|3[01]),\s+(20\d{2})\b", "%B %d, %Y"),
    ]

    @classmethod
    def resolve_date(
        cls,
        document_text: Optional[str] = None,
        document_metadata: Optional[dict] = None,
        document_created_at: Optional[datetime] = None,
    ) -> DateResolutionResult:
        if document_text:
            # 1. Look for explicit Report Date patterns
            report_match = re.search(
                r"(?:report\s+date|date\s+of\s+report|reported\s+on|result\s+date)\s*[:\-]?\s*([A-Za-z0-9\s,/\-]+)",
                document_text,
                re.IGNORECASE,
            )
            if report_match:
                parsed = cls._parse_date_snippet(report_match.group(1))
                if parsed:
                    return DateResolutionResult(
                        resolved_date=parsed,
                        source="REPORT_DATE",
                        confidence="HIGH",
                        raw_date_str=report_match.group(1).strip(),
                    )

            # 2. Look for Collection / Test Date patterns
            test_match = re.search(
                r"(?:collection\s+date|collected\s+on|sample\s+date|specimen\s+date|test\s+date)\s*[:\-]?\s*([A-Za-z0-9\s,/\-]+)",
                document_text,
                re.IGNORECASE,
            )
            if test_match:
                parsed = cls._parse_date_snippet(test_match.group(1))
                if parsed:
                    return DateResolutionResult(
                        resolved_date=parsed,
                        source="TEST_DATE",
                        confidence="HIGH",
                        raw_date_str=test_match.group(1).strip(),
                    )

            # 3. Scan first 500 characters of document text for any standard date header
            header_text = document_text[:600]
            for pattern, date_fmt in cls.DATE_PATTERNS:
                m = re.search(pattern, header_text)
                if m:
                    parsed = cls._try_parse_datetime(m.group(0), date_fmt)
                    if parsed:
                        return DateResolutionResult(
                            resolved_date=parsed,
                            source="REPORT_DATE",
                            confidence="MEDIUM",
                            raw_date_str=m.group(0),
                        )

        # 4. Fallback to document metadata creation date
        if document_metadata:
            for mkey in ("document_date", "creation_date", "report_date", "test_date", "date"):
                if mkey in document_metadata and document_metadata[mkey]:
                    meta_date = cls._parse_date_snippet(str(document_metadata[mkey]))
                    if meta_date:
                        return DateResolutionResult(
                            resolved_date=meta_date,
                            source="DOCUMENT_DATE",
                            confidence="MEDIUM",
                            raw_date_str=str(document_metadata[mkey]),
                        )

        # 5. Technical fallback to upload timestamp
        if document_created_at:
            return DateResolutionResult(
                resolved_date=document_created_at,
                source="UPLOAD_TIMESTAMP",
                confidence="LOW",
                raw_date_str=document_created_at.isoformat(),
            )

        return DateResolutionResult(
            resolved_date=None,
            source="UNKNOWN",
            confidence="LOW",
            raw_date_str=None,
        )

    @classmethod
    def _parse_date_snippet(cls, text: str) -> Optional[datetime]:
        clean = text.strip()
        for pattern, date_fmt in cls.DATE_PATTERNS:
            m = re.search(pattern, clean)
            if m:
                dt = cls._try_parse_datetime(m.group(0), date_fmt)
                if dt:
                    return dt
        return None

    @classmethod
    def _try_parse_datetime(cls, date_str: str, fmt: str) -> Optional[datetime]:
        normalized = date_str.replace("/", "-").replace(".", "-").strip()
        try:
            # Try formatting standard date string
            if fmt == "%Y-%m-%d":
                parts = normalized.split("-")
                return datetime(int(parts[0]), int(parts[1]), int(parts[2]), tzinfo=timezone.utc)
            elif fmt == "%d-%m-%Y":
                parts = normalized.split("-")
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]), tzinfo=timezone.utc)
            elif fmt == "%d-%b-%Y":
                return datetime.strptime(normalized, "%d-%b-%Y").replace(tzinfo=timezone.utc)
            elif fmt == "%B %d, %Y":
                return datetime.strptime(date_str.strip(), "%B %d, %Y").replace(tzinfo=timezone.utc)
        except Exception:
            pass
        return None
