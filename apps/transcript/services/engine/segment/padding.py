"""
Segment Padding Logic

Fix short speech segments by "eating" adjacent silence
"""
from __future__ import annotations

from typing import Dict, List

from .text_utils import dur


def pad_short_speech_into_adjacent_silence(
    tl: List[Dict],
    *,
    min_s: float,
    max_s: float,
    min_silence_keep: float,
) -> List[Dict]:
    """
    Fix speech < min_s by expanding into adjacent silence
    
    AGGRESSIVE mode:
    - Can eat entire silence if needed
    - Drop silence if remaining < 0.3s
    - Clamp at max_s
    
    Priority: RIGHT then LEFT
    """
    if not tl:
        return tl

    def is_speech(x: Dict) -> bool:
        return str(x.get("type", "")).lower() == "speech"

    def is_silence(x: Dict) -> bool:
        return str(x.get("type", "")).lower() == "silence"

    tl = sorted(tl, key=lambda x: (float(x.get("start", 0.0)), float(x.get("end", 0.0)), x.get("type", "")))

    for i in range(len(tl)):
        seg = tl[i]
        if not is_speech(seg):
            continue

        st = float(seg.get("start", 0.0))
        en = float(seg.get("end", 0.0))
        d = en - st
        
        if d >= min_s - 1e-6:
            continue

        need = min_s - d
        if need <= 1e-9:
            continue

        max_add = max_s - d
        if max_add <= 1e-9:
            continue

        take_budget = min(need, max_add)

        # ========================================================
        # RIGHT - AGGRESSIVE: Eat entire silence if needed
        # ========================================================
        if i + 1 < len(tl) and is_silence(tl[i + 1]):
            sil = tl[i + 1]
            sst = float(sil.get("start", 0.0))
            sen = float(sil.get("end", 0.0))
            sil_d = sen - sst
            
            # UPDATED: No min_silence_keep check
            take = min(take_budget, sil_d)
            if take > 1e-9:
                seg["end"] = en + take
                sil["start"] = sst + take
                
                # Drop silence if remaining < 0.3s
                if (sen - (sst + take)) < 0.3:
                    sil["start"] = sil["end"]
                continue

        # ========================================================
        # LEFT - AGGRESSIVE
        # ========================================================
        if i - 1 >= 0 and is_silence(tl[i - 1]):
            sil = tl[i - 1]
            sst = float(sil.get("start", 0.0))
            sen = float(sil.get("end", 0.0))
            sil_d = sen - sst
            
            take = min(take_budget, sil_d)
            if take > 1e-9:
                seg["start"] = st - take
                sil["end"] = sen - take
                
                if ((sen - take) - sst) < 0.3:
                    sil["end"] = sil["start"]
                continue

    # ========================================================
    # Cleanup invalid segments
    # ========================================================
    cleaned: List[Dict] = []
    for s in tl:
        try:
            st = float(s.get("start", 0.0))
            en = float(s.get("end", 0.0))
        except Exception:
            continue
        if (en - st) >= 0.05:
            cleaned.append(s)
    
    return cleaned
