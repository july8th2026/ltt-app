"""Feedback store — persists user accept/reject decisions with clip metadata.

Stores decisions in a single JSON file per app installation.
Each record captures the clip's score breakdown + user decision.

Schema:
    {
        "version": 2,
        "total_accepted": 42,
        "total_rejected": 18,
        "records": [
            {
                "timestamp": "2024-01-15T10:30:00",
                "decision": "accepted",
                "genre": "talking_head",
                "scores": {"hook": 0.82, "pacing": 0.91, ...},
                "clip_intent": "hook",
                "duration": 32.5,
                "composite": 0.78
            }
        ]
    }
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MAX_RECORDS = 500  # Rolling window — keep last 500 decisions


class FeedbackStore:
    """Persists user accept/reject decisions for preference learning."""

    def __init__(self, store_path: Path) -> None:
        self._path = store_path
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("version") == 2:
                    return data
                logger.info("Feedback store version mismatch, starting fresh")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load feedback store: %s", e)
        return {"version": 2, "total_accepted": 0, "total_rejected": 0, "records": []}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)
        except OSError as e:
            logger.error("Failed to save feedback store: %s", e)

    def record_decision(
        self,
        decision: str,
        clip_data: dict[str, Any],
    ) -> None:
        """Record an accept/reject decision with clip metadata.

        Args:
            decision: "accepted" or "rejected"
            clip_data: Candidate dict from GUI (must have score_breakdown, score, etc.)
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "genre": clip_data.get("strategy_name", "unknown"),
            "clip_intent": clip_data.get("clip_intent", "unknown"),
            "composite": float(clip_data.get("score", 0)) / 100.0,
            "duration": float(clip_data.get("duration", 0)),
            "hook_type": clip_data.get("hook_type", ""),
            "risk_level": clip_data.get("risk_level", "low"),
            "has_speech": clip_data.get("has_speech", True),
            "scores": clip_data.get("score_breakdown", {}),
        }

        # Also extract individual scores if breakdown not available
        if not record["scores"]:
            record["scores"] = {
                "hook": float(clip_data.get("hook_score", 0)) / 100.0,
                "pacing": float(clip_data.get("pacing_score", 0)) / 100.0,
                "completeness": float(clip_data.get("completeness_score", 0)) / 100.0,
                "visual": float(clip_data.get("visual_score", 0)) / 100.0,
                "audio": float(clip_data.get("audio_score", 0)) / 100.0,
            }

        self._data["records"].append(record)

        if decision == "accepted":
            self._data["total_accepted"] = self._data.get("total_accepted", 0) + 1
        else:
            self._data["total_rejected"] = self._data.get("total_rejected", 0) + 1

        # Rolling window
        if len(self._data["records"]) > _MAX_RECORDS:
            self._data["records"] = self._data["records"][-_MAX_RECORDS:]

        self._save()
        logger.debug(
            "Feedback recorded: %s (composite=%.2f, intent=%s)",
            decision, record["composite"], record["clip_intent"],
        )

    def record_accepted(self, clip_data: dict[str, Any]) -> None:
        self.record_decision("accepted", clip_data)

    def record_rejected(self, clip_data: dict[str, Any]) -> None:
        self.record_decision("rejected", clip_data)

    @property
    def total_decisions(self) -> int:
        return self._data.get("total_accepted", 0) + self._data.get("total_rejected", 0)

    @property
    def total_accepted(self) -> int:
        return self._data.get("total_accepted", 0)

    @property
    def total_rejected(self) -> int:
        return self._data.get("total_rejected", 0)

    @property
    def records(self) -> list[dict[str, Any]]:
        return self._data.get("records", [])

    def get_accepted_records(self) -> list[dict[str, Any]]:
        return [r for r in self.records if r["decision"] == "accepted"]

    def get_rejected_records(self) -> list[dict[str, Any]]:
        return [r for r in self.records if r["decision"] == "rejected"]
