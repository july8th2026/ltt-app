import json, re
from ..tuong_thich.log import info

END_PUNCT = re.compile(r"[\.\!\?…]+$")

def make_segments(cfg: dict, whisper_segments: list[dict], out_json: str):
    wcfg = cfg.get("whisper", {})
    min_s = float(wcfg.get("min_segment_s", 3.0))
    max_s = float(wcfg.get("max_segment_s", 5.0))
    merge_short = float(wcfg.get("merge_if_shorter_s", 1.5))
    split_long = float(wcfg.get("split_if_longer_s", 8.0))

    # Build a continuous stream from whisper segments then slice into 3-5s chunks,
    # while preferring punctuation boundaries when possible.
    merged = []
    buf_text = ""
    buf_start = None
    buf_end = None

    def flush():
        nonlocal buf_text, buf_start, buf_end
        if buf_start is None:
            return
        text = buf_text.strip()
        if text:
            merged.append({"start": float(buf_start), "end": float(buf_end), "text": text})
        buf_text = ""
        buf_start = None
        buf_end = None

    for s in whisper_segments:
        if buf_start is None:
            buf_start = s["start"]
        buf_end = s["end"]
        buf_text += (s["text"] + " ")

        dur = buf_end - buf_start
        # If too short, keep accumulating
        if dur < min_s:
            continue
        # If in target range, flush
        if min_s <= dur <= max_s:
            flush()
            continue
        # If long, try flush at punctuation; else split hard later.
        if dur > max_s:
            # if last chunk ends with punctuation, flush
            if END_PUNCT.search(s["text"].strip()):
                flush()
            else:
                # don't let buffer grow too huge
                if dur >= split_long:
                    flush()

    flush()

    # Merge very short segments (<merge_short) into next
    out = []
    i = 0
    while i < len(merged):
        cur = merged[i]
        dur = cur["end"] - cur["start"]
        if dur < merge_short and i+1 < len(merged):
            nxt = merged[i+1]
            out.append({
                "start": cur["start"],
                "end": nxt["end"],
                "text": (cur["text"] + " " + nxt["text"]).strip()
            })
            i += 2
        else:
            out.append(cur)
            i += 1

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    info("segments_done", segments=len(out))
    return out
