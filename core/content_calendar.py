"""
Content calendar CSV import (Sprint D2).

Why this exists:
  Filling Google Sheet rows by hand is the slowest part of operating the
  bot. A user with 20 pages doing 60 posts/week is editing 60 rows/week —
  error-prone, slow, no version control. CSV import lets them prep
  content offline (Excel / Notion / their CRM) and bulk-push.

This module:
  • Reads a CSV file in our standard column shape.
  • Validates each row: required fields, schedule format, platform value.
  • Returns (parsed_rows, errors). Caller decides whether to push to Sheet.

The push-to-Sheet step lives elsewhere; this module is import-side only
so it has zero Google API dependency and is fully unit-testable.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


_REQUIRED_FIELDS = ["video_url"]   # only video_url is hard-required
_ALLOWED_PLATFORMS = {"facebook", "tiktok", ""}
_DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S",
]


@dataclass
class CalendarRow:
    """One row in the import CSV after validation."""
    video_url:     str
    title:         str = ""
    description:   str = ""
    target_page:   str = ""
    schedule_time: str = ""
    platform:      str = "facebook"
    post_type:     str = "feed"
    comment:       str = ""
    thumbnail_url: str = ""
    keywords:      str = ""

    # TikTok-specific (only used when platform=tiktok)
    tiktok_account:          str = ""
    tiktok_privacy_level:    str = ""
    tiktok_is_ai_generated:  str = ""

    def to_sheet_dict(self) -> dict:
        """Format as a dict ready to write into the Sheet — column names
        match the bot's col_* config keys when keys are 1:1."""
        return {
            "video_url":           self.video_url,
            "title":               self.title,
            "description":         self.description,
            "target_page":         self.target_page,
            "schedule_time":       self.schedule_time,
            "platform":            self.platform,
            "post_type":           self.post_type,
            "comment":             self.comment,
            "thumbnail_url":       self.thumbnail_url,
            "keywords":            self.keywords,
            "tiktok_account":      self.tiktok_account,
            "tiktok_privacy_level": self.tiktok_privacy_level,
            "tiktok_is_ai_generated": self.tiktok_is_ai_generated,
        }


@dataclass
class ImportResult:
    rows:   list[CalendarRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def import_csv(path: str) -> ImportResult:
    """Parse a CSV at *path* into CalendarRow objects. Soft-validates each
    row; rows with hard errors are added to errors[] and skipped."""
    res = ImportResult()
    if not path or not os.path.exists(path):
        res.errors.append(f"File không tồn tại: {path}")
        return res

    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                res.errors.append("CSV trống hoặc thiếu header row")
                return res
            for line_no, raw in enumerate(reader, start=2):
                err = _validate(raw)
                if err:
                    res.errors.append(f"Dòng {line_no}: {err}")
                    continue
                res.rows.append(_normalise(raw))
    except UnicodeDecodeError:
        res.errors.append("CSV không phải UTF-8 — re-save file với UTF-8 encoding")
    except Exception as exc:
        res.errors.append(f"Lỗi đọc file: {exc}")

    return res


# ─── Validation ──────────────────────────────────────────────────────────────

def _validate(row: dict) -> Optional[str]:
    """Return an error string if the row is invalid; None when OK."""
    for f_name in _REQUIRED_FIELDS:
        if not (row.get(f_name) or "").strip():
            return f"thiếu field '{f_name}'"
    platform = (row.get("platform") or "").strip().lower()
    if platform not in _ALLOWED_PLATFORMS:
        return f"platform='{platform}' không hợp lệ (chỉ chấp nhận facebook/tiktok)"
    schedule = (row.get("schedule_time") or "").strip()
    if schedule and not _parse_datetime(schedule):
        return (
            f"schedule_time='{schedule}' format sai — chấp nhận YYYY-MM-DD HH:MM[:SS] "
            f"hoặc DD/MM/YYYY HH:MM"
        )
    return None


def _parse_datetime(s: str) -> Optional[datetime]:
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# ─── Normalisation ──────────────────────────────────────────────────────────

def _normalise(row: dict) -> CalendarRow:
    """Convert raw CSV dict → CalendarRow with sensible defaults."""
    return CalendarRow(
        video_url             = (row.get("video_url")     or "").strip(),
        title                 = (row.get("title")         or "").strip(),
        description           = (row.get("description")   or "").strip(),
        target_page           = (row.get("target_page")   or "").strip(),
        schedule_time         = (row.get("schedule_time") or "").strip(),
        platform              = (row.get("platform")      or "facebook").strip().lower(),
        post_type             = (row.get("post_type")     or "feed").strip().lower(),
        comment               = (row.get("comment")       or "").strip(),
        thumbnail_url         = (row.get("thumbnail_url") or "").strip(),
        keywords              = (row.get("keywords")      or "").strip(),
        tiktok_account        = (row.get("tiktok_account") or "").strip(),
        tiktok_privacy_level  = (row.get("tiktok_privacy_level") or "").strip(),
        tiktok_is_ai_generated = (row.get("tiktok_is_ai_generated") or "").strip(),
    )
