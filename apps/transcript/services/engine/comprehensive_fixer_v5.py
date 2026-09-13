"""
COMPREHENSIVE FIXER V5 - STRICT (BILINGUAL SAFE)
Goals:
- Avoid over-merging (max_segment_duration)
- Merge incomplete sentences BUT keep timestamps stable (timestamp fix optional)
- Merge words when merging speech segments (critical for word-level pipeline)
- Terminology dict: caller may clear it for EN to avoid corrupting English
- Hallucination removal: consecutive duplicate sentence detection
- Proper noun capitalization (Vietnamese)
- External correction files for easy maintenance
"""

from __future__ import annotations

import os
import re
import json
from typing import List, Dict, Any, Optional


class ComprehensiveTranscriptFixerV5:
    def __init__(
        self,
        max_segment_duration: float = 30.0,
        *,
        enable_hallucination_removal: bool = False,
        enable_sentence_completion: bool = True,
        enable_timestamp_fix: bool = False,
        hallucination_similarity_threshold: float = 0.80,
        debug_print: bool = False,
    ):
        self.max_segment_duration = float(max_segment_duration)
        self.enable_hallucination_removal = bool(enable_hallucination_removal)
        self.enable_sentence_completion = bool(enable_sentence_completion)
        self.enable_timestamp_fix = bool(enable_timestamp_fix)
        self.hallucination_similarity_threshold = float(hallucination_similarity_threshold)
        self.debug_print = bool(debug_print)

        # Vietnamese terminology dictionary (caller should disable for EN)
        self.terminology_fixes = {
            "chieu dinh": "triều đình",
            "chiều đỉnh": "triều đình",
            "chiều đình": "triều đình",
            "trieu dinh": "triều đình",
            "triệu định": "triều đình",
            "chieu dai": "triều đại",
            "chiều đại": "triều đại",
            "trieu dai": "triều đại",
            "triệu đại": "triều đại",
            "doi chu": "đổi chủ",
            "đội chủ": "đổi chủ",
            "thanh chung": "thanh trừng",
            "thanh chừng": "thanh trừng",
            "thanh trung": "thanh trừng",
            "phan lich": "phản nghịch",
            "phản lịch": "phản nghịch",
            "phan nghich": "phản nghịch",
            "giai giac": "phân tán",
            "giải giác": "phân tán",
            "phan tan": "phân tán",
            "tuong lanh": "tướng lĩnh",
            "tương lẫn": "tướng lĩnh",
            "tuong linh": "tướng lĩnh",
            "tro thanh": "trở thành",
            "trợ thành": "trở thành",
            "so sach": "sử sách",
            "sở sách": "sử sách",
            "su tu": "xử tử",
            "sử tử": "xử tử",
            "nghe lan": "nghe lệnh",
            "nghe lận": "nghe lệnh",
            "cam quan": "cầm quân",
            "chinh dia": "chính địa",
            "chính đĩa": "chính địa",
            "nghi la": "nghịch lý",
            "nghịch lã": "nghịch lý",
            "Quy an": "Quyền",
            "Quy án": "Quyền",
        }

        # Load external corrections (merge, file takes precedence)
        ext = self._load_external_json("vi_corrections.json")
        if ext:
            self.terminology_fixes.update(ext)

        # English corrections (loaded separately, applied when lang=en)
        self.en_corrections = self._load_external_json("en_corrections.json") or {}

        # Load proper noun map
        self.proper_nouns = self._load_external_json("vi_proper_nouns.json") or {}

        # simple punctuation set for checking completion
        self._end_punct = set(".!?," + ";:")

        # Vietnamese/English connector words that indicate incomplete sentence
        # Include BOTH diacritics and non-diacritics versions for Vietnamese
        _vi_connectors = [
            "và", "va", "hay", "hoặc", "hoac", "nhưng", "nhung", "mà", "ma", "nên", "nen", "vì", "vi",
            "của", "cua", "với", "voi", "từ", "tu", "cho", "về", "ve", "tại", "tai", "trong",
            "một", "mot", "hai", "các", "cac", "những", "nhung", "mọi", "moi",
            "phải", "phai", "cần", "can", "sẽ", "se", "đã", "da", "đang", "dang",
            "là", "la", "có", "co", "được", "duoc", "bị", "bi", "giữ", "giu",
            "rất", "rat", "khá", "kha", "hơn", "hon",
            "ông", "ong", "bà", "ba", "họ", "ho",
            "như", "nhu", "nào", "nao",
        ]
        _en_connectors = [
            "and", "or", "but", "so", "because", "with", "from", "to", "of", "in", "on", "at",
        ]
        self._incomplete_tail_words = set(_vi_connectors + _en_connectors)

    def set_language(self, lang: str):
        """Switch correction dicts based on detected language."""
        lang = (lang or "").strip().lower()
        if lang == "en":
            self.terminology_fixes = dict(self.en_corrections) if self.en_corrections else {}
            self.proper_nouns = {}
        elif lang != "vi":
            self.terminology_fixes = {}
            self.proper_nouns = {}
        # vi: keep defaults (already loaded)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _load_external_json(self, filename: str) -> Optional[Dict[str, str]]:
        """Load a JSON dict file from same directory as this module."""
        try:
            path = os.path.join(os.path.dirname(__file__), filename)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return None

    @staticmethod
    def _normalize_for_compare(text: str) -> str:
        """Normalize text for comparison: lowercase, strip punct, collapse spaces."""
        t = (text or "").strip().lower()
        t = re.sub(r"[^\w\s]", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _text_similarity(self, a: str, b: str) -> float:
        """Word-overlap similarity ratio between two texts. Returns 0.0-1.0."""
        na = self._normalize_for_compare(a)
        nb = self._normalize_for_compare(b)
        if not na or not nb:
            return 0.0
        wa = set(na.split())
        wb = set(nb.split())
        shared = len(wa & wb)
        total = len(wa) + len(wb)
        if total == 0:
            return 0.0
        return 2.0 * shared / total

    # ------------------------------------------------------------
    # Public
    # ------------------------------------------------------------
    def process(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(segments, list):
            return {"segments": [], "stats": {"input_segments": 0, "output_segments": 0}}

        stats = {
            "input_segments": len(segments),
            "output_segments": 0,
            "encoding_fixed": 0,
            "proper_nouns_fixed": 0,
            "hallucinations_removed": 0,
            "sentences_completed": 0,
            "prevented_over_merge": 0,
            "gaps_fixed": 0,
        }

        if self.debug_print:
            print("\n" + "=" * 80)
            print("COMPREHENSIVE FIXER V5 (STRICT)")
            print(f"max_segment_duration={self.max_segment_duration}")
            print(f"hallucination_removal={self.enable_hallucination_removal}")
            print(f"sentence_completion={self.enable_sentence_completion}")
            print(f"timestamp_fix={self.enable_timestamp_fix}")
            print("=" * 80)

        # 1) terminology/encoding fixes (safe only if dict is correct language)
        segments = self._fix_encoding(segments, stats)

        # 2) proper noun capitalization (Vietnamese only, safe to skip if dict empty)
        segments = self._capitalize_proper_nouns(segments, stats)

        # 3) hallucination removal — consecutive duplicate sentence detection
        if self.enable_hallucination_removal:
            segments = self._remove_hallucinations(segments, stats)

        # 4) sentence completion merge with max_duration limit + merge words
        if self.enable_sentence_completion:
            segments = self._complete_sentences_merge_words(segments, stats)

        # 5) timestamp fix (OFF by default to avoid drifting)
        if self.enable_timestamp_fix:
            segments = self._fix_timestamps_light(segments, stats)

        # 6) add metadata (optional keys - upstream may ignore)
        segments = self._add_metadata(segments)

        stats["output_segments"] = len(segments)
        return {"segments": segments, "stats": stats}

    # ------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------
    def _fix_encoding(self, segments: List[Dict[str, Any]], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply terminology corrections on WORDS first, then rebuild text from words.
        This ensures text and words stay in sync (no desync).
        Falls back to text-only fix if segment has no words.
        """
        if not self.terminology_fixes:
            return segments

        for seg in segments:
            if seg.get("type") != "speech":
                continue

            words = seg.get("words")
            if isinstance(words, list) and words:
                # Fix on word level: join words → apply fixes → re-split back
                original_joined = " ".join(str(w.get("word", "")) for w in words)
                fixed_joined = original_joined
                for wrong, correct in self.terminology_fixes.items():
                    if wrong in fixed_joined:
                        fixed_joined = fixed_joined.replace(wrong, correct)

                if fixed_joined != original_joined:
                    # Re-distribute corrected words back to word dicts
                    new_word_texts = fixed_joined.split()
                    if len(new_word_texts) == len(words):
                        for w, new_text in zip(words, new_word_texts):
                            w["word"] = new_text
                    # Rebuild segment text from corrected words
                    seg["text"] = " ".join(w.get("word", "") for w in words)
                    stats["encoding_fixed"] += 1
            else:
                # Fallback: text-only fix (no words available)
                text = seg.get("text", "")
                if not isinstance(text, str):
                    continue
                original = text
                for wrong, correct in self.terminology_fixes.items():
                    if wrong in text:
                        text = text.replace(wrong, correct)
                if text != original:
                    seg["text"] = text
                    stats["encoding_fixed"] += 1

        return segments

    def _remove_hallucinations(self, segments: List[Dict[str, Any]], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Two-layer hallucination detection:
        1. Consecutive duplicate sentences (Whisper loop in silence regions)
        2. Intra-segment word repetition (original V5 check)
        """
        if not segments:
            return segments

        cleaned: List[Dict[str, Any]] = []
        prev_norm = ""

        for seg in segments:
            if seg.get("type") != "speech":
                cleaned.append(seg)
                continue

            text = seg.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue

            cur_norm = self._normalize_for_compare(text)

            # Layer 1: consecutive duplicate — same or very similar text as previous speech
            if prev_norm and cur_norm:
                sim = self._text_similarity(text, prev_norm)
                if sim >= self.hallucination_similarity_threshold:
                    stats["hallucinations_removed"] += 1
                    # don't update prev_norm — keep comparing against the original
                    continue

            # Layer 2: intra-segment word repetition (>= 6 words, < 25% unique)
            words = text.split()
            if len(words) >= 6:
                unique_ratio = len(set(w.lower() for w in words)) / len(words)
                if unique_ratio < 0.25:
                    stats["hallucinations_removed"] += 1
                    continue

            cleaned.append(seg)
            prev_norm = text  # store ORIGINAL text for next comparison

        return cleaned

    def _capitalize_proper_nouns(self, segments: List[Dict[str, Any]], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Capitalize proper nouns on WORDS first, then rebuild text.
        Keeps text and words in sync.
        """
        if not self.proper_nouns:
            return segments

        for seg in segments:
            if seg.get("type") != "speech":
                continue

            words = seg.get("words")
            if isinstance(words, list) and words:
                # Fix on word level
                original_joined = " ".join(str(w.get("word", "")) for w in words)
                fixed_joined = original_joined
                for wrong_lower, correct in self.proper_nouns.items():
                    pattern = re.escape(wrong_lower)
                    fixed_joined = re.sub(pattern, correct, fixed_joined, flags=re.IGNORECASE)

                if fixed_joined != original_joined:
                    new_word_texts = fixed_joined.split()
                    if len(new_word_texts) == len(words):
                        for w, new_text in zip(words, new_word_texts):
                            w["word"] = new_text
                    seg["text"] = " ".join(w.get("word", "") for w in words)
                    stats["proper_nouns_fixed"] += 1
            else:
                # Fallback: text-only
                text = seg.get("text", "")
                if not isinstance(text, str):
                    continue
                original = text
                for wrong_lower, correct in self.proper_nouns.items():
                    pattern = re.escape(wrong_lower)
                    text = re.sub(pattern, correct, text, flags=re.IGNORECASE)
                if text != original:
                    seg["text"] = text
                    stats["proper_nouns_fixed"] += 1

        return segments

    def _is_incomplete_sentence(self, text: str) -> bool:
        t = (text or "").strip()
        if not t:
            return False
        last = t[-1]
        if last in self._end_punct:
            return False

        parts = t.split()
        if not parts:
            return False
        last_word = parts[-1].strip().lower()
        if last_word in self._incomplete_tail_words:
            return True

        return False  # default: don't assume incomplete — only merge when truly incomplete (ends with connector word)

    def _should_merge(self, cur: Dict[str, Any], nxt: Dict[str, Any]) -> bool:
        if cur.get("type") != "speech" or nxt.get("type") != "speech":
            return False

        cur_text = (cur.get("text", "") or "").strip()
        nxt_text = (nxt.get("text", "") or "").strip()
        if not cur_text or not nxt_text:
            return False

        merged_duration = float(nxt.get("end", 0.0)) - float(cur.get("start", 0.0))
        if merged_duration > self.max_segment_duration:
            return False

        gap = float(nxt.get("start", 0.0)) - float(cur.get("end", 0.0))
        # Small gap helps
        small_gap = (gap >= -0.05 and gap < 0.5)

        # If current incomplete => merge
        if self._is_incomplete_sentence(cur_text):
            return True

        # If next starts lowercase => merge (often continuation)
        if nxt_text and nxt_text[0].islower():
            return True

        # Removed: unconditional small_gap merge was too aggressive
        # Only merge when sentence is genuinely incomplete or next starts lowercase
        return False

    def _merge_words(self, w1: Any, w2: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if isinstance(w1, list):
            for w in w1:
                if isinstance(w, dict) and "start" in w and "end" in w and "word" in w:
                    out.append(w)
        if isinstance(w2, list):
            for w in w2:
                if isinstance(w, dict) and "start" in w and "end" in w and "word" in w:
                    out.append(w)
        return out

    def _complete_sentences_merge_words(self, segments: List[Dict[str, Any]], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        if len(segments) < 2:
            return segments

        max_passes = 5
        for _ in range(max_passes):
            merged_this_pass = False
            completed: List[Dict[str, Any]] = []
            i = 0

            while i < len(segments):
                cur = dict(segments[i])

                if i + 1 < len(segments) and cur.get("type") == "speech":
                    nxt = segments[i + 1]

                    if self._should_merge(cur, nxt):
                        # prevent over-merge already checked in _should_merge
                        cur_text = (cur.get("text", "") or "").strip()
                        nxt_text = (nxt.get("text", "") or "").strip()

                        cur["text"] = (cur_text + " " + nxt_text).strip()
                        cur["end"] = float(nxt.get("end", cur.get("end", 0.0)))

                        # merge words
                        cur["words"] = self._merge_words(cur.get("words"), nxt.get("words"))

                        stats["sentences_completed"] += 1
                        merged_this_pass = True
                        i += 2
                        completed.append(cur)
                        continue
                    else:
                        # if would be incomplete but blocked by duration -> count prevented
                        cur_text = (cur.get("text", "") or "").strip()
                        if self._is_incomplete_sentence(cur_text):
                            merged_duration = float(nxt.get("end", 0.0)) - float(cur.get("start", 0.0))
                            if merged_duration > self.max_segment_duration:
                                stats["prevented_over_merge"] += 1

                completed.append(cur)
                i += 1

            segments = completed
            if not merged_this_pass:
                break

        return segments

    def _fix_timestamps_light(self, segments: List[Dict[str, Any]], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Light timestamp fix:
        - If small positive gap (<3s): extend prev.end to current.start
        - If overlap: split midpoint
        NOTE: OFF by default in bilingual mode (recommended).
        """
        if not segments:
            return segments

        fixed: List[Dict[str, Any]] = []
        for i, seg in enumerate(segments):
            if i == 0:
                fixed.append(dict(seg))
                continue

            prev = fixed[-1]
            cur = dict(seg)

            try:
                gap = float(cur.get("start", 0.0)) - float(prev.get("end", 0.0))
            except Exception:
                fixed.append(cur)
                continue

            if gap > 0.05 and gap < 3.0:
                prev["end"] = float(cur.get("start", prev.get("end", 0.0)))
                stats["gaps_fixed"] += 1
            elif gap < -0.01:
                mid = (float(prev.get("end", 0.0)) + float(cur.get("start", 0.0))) / 2.0
                prev["end"] = mid
                cur["start"] = mid
                stats["gaps_fixed"] += 1

            fixed.append(cur)

        return fixed

    def _add_metadata(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add lightweight metadata (optional keys).
        Upstream pipeline may ignore extra keys; if you want zero extra keys,
        you can remove this step or keep but segment.py later will project schema.
        """
        for i, seg in enumerate(segments, 1):
            seg.setdefault("index", i)
            seg.setdefault("scene_id", f"S{i:04d}")
            try:
                seg["duration"] = round(float(seg.get("end", 0.0)) - float(seg.get("start", 0.0)), 2)
            except Exception:
                seg["duration"] = 0.0
        return segments

    # ------------------------------------------------------------
    # Optional validate tool (debug)
    # ------------------------------------------------------------
    def validate(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        report = {"total_segments": len(segments), "issues": [], "warnings": [], "valid": True}
        for i, seg in enumerate(segments):
            try:
                st = float(seg.get("start", 0.0))
                en = float(seg.get("end", 0.0))
            except Exception:
                report["issues"].append(f"idx={i}: invalid start/end")
                report["valid"] = False
                continue

            if en <= st:
                report["issues"].append(f"idx={i}: end<=start")
                report["valid"] = False

            if i > 0:
                prev = segments[i - 1]
                try:
                    gap = st - float(prev.get("end", 0.0))
                except Exception:
                    gap = 0.0
                if gap > 1.0:
                    report["warnings"].append(f"idx={i}: large gap {gap:.2f}s")

            if seg.get("type") == "speech":
                txt = (seg.get("text", "") or "").strip()
                if txt and txt[-1] not in ".!?,;:":
                    report["warnings"].append(f"idx={i}: incomplete sentence")

                if (en - st) > self.max_segment_duration + 5.0:
                    report["warnings"].append(f"idx={i}: very long segment {(en-st):.1f}s")

        return report


def fix_and_validate_v5(input_path: str, output_path: str, validation_path: Optional[str] = None, max_duration: float = 30.0):
    with open(input_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    fixer = ComprehensiveTranscriptFixerV5(max_segment_duration=max_duration)
    result = fixer.process(segments)

    validation = fixer.validate(result["segments"])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result["segments"], f, ensure_ascii=False, indent=2)

    if validation_path:
        with open(validation_path, "w", encoding="utf-8") as f:
            json.dump(validation, f, ensure_ascii=False, indent=2)

    return result["stats"], validation
