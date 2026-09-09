import json, torch
from ..tuong_thich.log import info

def match_timeline(cfg: dict, segments: list[dict], clips: list[dict], out_json: str):
    ccfg = cfg.get("clip", {})
    reuse_max = int(ccfg.get("reuse_max_times", 3))
    prefer_unused = bool(ccfg.get("prefer_unused", True))

    # DEBUG: Log matching start
    info("matching_timeline_semantic",
         segments=len(segments),
         clips=len(clips),
         reuse_max=reuse_max,
         prefer_unused=prefer_unused)

    if not clips:
        raise ValueError("Không có clip nào để matching (tất cả đã bị filter?)")
    if not segments:
        raise ValueError("Không có segment nào để matching")

    # Validate all clips/segments have embeddings
    missing_feat_clips = [c.get("name", "?") for c in clips if c.get("feat") is None]
    if missing_feat_clips:
        raise ValueError(f"Thiếu embeddings cho {len(missing_feat_clips)} clips: {missing_feat_clips[:5]}")
    missing_feat_segs = [i for i, s in enumerate(segments) if s.get("feat") is None]
    if missing_feat_segs:
        raise ValueError(f"Thiếu embeddings cho {len(missing_feat_segs)} segments")

    # Build matrix of similarities segment x clip
    clip_feats = torch.cat([c["feat"] for c in clips], dim=0)  # (N, D)
    timeline=[]
    
    for idx, s in enumerate(segments):
        sfeat = s["feat"].unsqueeze(0)  # (1, D)
        sims = torch.matmul(sfeat, clip_feats.T).squeeze(0)     # (N,)
        order = torch.argsort(sims, descending=True).tolist()

        chosen = None
        # pass 1: prefer unused
        if prefer_unused:
            for idx_c in order:
                if clips[idx_c]["used"] == 0:
                    chosen = idx_c
                    break
        # pass 2: allow reuse up to max
        if chosen is None:
            for idx_c in order:
                if clips[idx_c]["used"] < reuse_max:
                    chosen = idx_c
                    break
        # final fallback: best
        if chosen is None:
            chosen = order[0]

        clips[chosen]["used"] += 1
        
        # DEBUG: Log first 3 matches
        if idx < 3:
            info("segment_matched",
                 segment_index=idx,
                 clip_name=clips[chosen].get("name", ""),
                 clip_path=clips[chosen].get("file", ""),
                 similarity=round(float(sims[chosen].item()), 3),
                 clip_used_count=clips[chosen]["used"])
        
        timeline.append({
            "segment": {"start": s["start"], "end": s["end"], "text": s["text"]},
            "clip": {"file": clips[chosen]["file"], "name": clips[chosen]["name"]},  # Uses relative path
            "similarity": float(sims[chosen].item())
        })
    
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)
    
    info("match_done", segments=len(segments), clips=len(clips))
    return timeline