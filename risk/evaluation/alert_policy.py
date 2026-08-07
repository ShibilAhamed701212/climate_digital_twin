"""Alert Policy — deterministic rules for creating and managing alerts
from HazardAssessment severity.  Alerts NEVER calculate hazard — they
only react to already-computed assessments.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from risk.models.hazard import Alert, AlertStatus, HazardAssessment, Severity


class AlertPolicy:
    def __init__(self, config_path: str = "config/risk_config.yaml") -> None:
        self._policy: dict[str, str] = {
            "NONE": "no_alert",
            "LOW": "no_alert",
            "MODERATE": "watch",
            "HIGH": "active_warning",
            "SEVERE": "active_critical",
        }
        self._dedup_window_minutes: int = 60
        self._escalation_on: str = "SEVERE"
        self._resolve_on: set[str] = {"LOW", "NONE"}
        self._load_config(config_path)

    def _load_config(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            return
        try:
            with open(p) as f:
                cfg = yaml.safe_load(f) or {}
            alert_cfg = cfg.get("alerts", {})
            self._policy = alert_cfg.get("policy", self._policy)
            self._dedup_window_minutes = alert_cfg.get("dedup_window_minutes", 60)
            self._escalation_on = alert_cfg.get("escalation_on", "SEVERE")
            self._resolve_on = set(alert_cfg.get("resolve_on", ["LOW", "NONE"]))
        except Exception:
            pass

    def should_alert(self, severity: Severity) -> bool:
        action = self._policy.get(severity.value, "no_alert")
        return action != "no_alert"

    def alert_action(self, severity: Severity) -> str:
        return self._policy.get(severity.value, "no_alert")

    def evaluate(
        self,
        assessment: HazardAssessment,
        latest_active_alerts: list[Alert],
    ) -> Alert | None:
        if not self.should_alert(assessment.severity):
            return None

        severity_str = assessment.severity.value
        existing = self._find_matching(assessment, latest_active_alerts)
        now = datetime.now(UTC).isoformat()

        if existing is None:
            return Alert(
                assessment_id=assessment.assessment_id,
                location_id=assessment.location_id,
                hazard_type=assessment.hazard_type,
                severity=severity_str,
                status=AlertStatus.ACTIVE,
                reason=f"{severity_str} severity triggered: {assessment.hazard_type}",
            )

        if severity_str == self._escalation_on and existing.status != AlertStatus.ESCALATED:
            existing.status = AlertStatus.ESCALATED
            existing.updated_at = now
            existing.reason = f"Escalated to {severity_str}"
            return existing

        return None

    def resolve(
        self,
        assessment: HazardAssessment,
        active_alerts: list[Alert],
    ) -> list[Alert]:
        resolved: list[Alert] = []
        if assessment.severity.value not in self._resolve_on:
            return resolved
        now = datetime.now(UTC).isoformat()
        for alert in active_alerts:
            if alert.status in (AlertStatus.ACTIVE, AlertStatus.ESCALATED):
                alert.status = AlertStatus.RESOLVED
                alert.updated_at = now
                alert.reason = f"Severity downgraded to {assessment.severity.value}"
                resolved.append(alert)
        return resolved

    def _find_matching(self, assessment: HazardAssessment, alerts: list[Alert]) -> Alert | None:
        for a in alerts:
            if (
                a.location_id == assessment.location_id
                and a.hazard_type == assessment.hazard_type
                and a.status in (AlertStatus.ACTIVE, AlertStatus.ESCALATED)
            ):
                return a
        return None
