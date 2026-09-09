import re
import json
import os
import torch
import numpy as np
from ..tuong_thich.log import info, error

# Compile regex once for performance
# Priority 1: PREFIX pattern - số 3-4 chữ số đầu tên file (e.g. "111-scene_id-121.mp4" → 111)
# Priority 2: SCENE_ID pattern (fallback) - số sau scene_id- (e.g. "scene_id-53.mp4" → 53)
PREFIX_PATTERN = re.compile(r'^(\d{3,4})-scene', re.IGNORECASE)
SCENE_ID_PATTERN = re.compile(r'scene_?id[-_](\d+)(?:-(\d+))?', re.IGNORECASE)


def build_sequential_timeline(cfg, segments, clips, out_json):
    """
    Build timeline by matching scene_id in segments with scene_id in video filenames.

    This is a DIRECT mapping approach - no semantic matching, no similarity scores.
    Simply matches segment scene_id (S0001, S0002, ...) with video filename scene_id.

    Args:
        cfg: Config dict
        segments: List of segments with scene_id field (may contain "feat" embeddings)
        clips: List of video clips with name/file (may contain "feat" embeddings)
        out_json: Output path for timeline.json

    Returns:
        timeline: List of timeline entries
    """
    # Check if we should save embeddings
    save_embeddings = cfg.get("timeline", {}).get("save_embeddings", False)

    # Auto-enable if transitions require embeddings
    transitions_cfg = cfg.get("transitions", {})
    if transitions_cfg.get("enable", False) and transitions_cfg.get("require_embeddings", False):
        if not save_embeddings:
            info("auto_enabling_save_embeddings", reason="transitions.require_embeddings=true")
            save_embeddings = True

    # Validate inputs
    if not segments:
        raise ValueError("No segments provided for timeline matching")
    if not clips:
        raise ValueError("No clips available for timeline matching")

    info("building_sequential_timeline_by_scene_id",
         segments=len(segments),
         clips=len(clips),
         save_embeddings=save_embeddings)

    timeline = []
    
    # Build mapping: scene_id → clip (with priority)
    # Parse logic (đồng bộ với scene_validator.py):
    #   Priority 1: PREFIX (3-4 số đầu tên file trước "-scene") → dùng làm scene_id
    #   Priority 2: scene_id-XX (fallback) → dùng khi không có PREFIX
    #   Suffix handling: 001-scene_id-1.mp4 (suffix=0) > 001-scene_id-1-2.mp4 (suffix=2)
    scene_to_clip = {}
    scene_to_priority = {}  # Track priority for replacement

    for clip in clips:
        filename = clip.get("name", "")
        scene_num = None
        parse_source = None  # Track which pattern was used (for logging)

        # Priority 1: Try PREFIX first (e.g. "111-scene_id-121.mp4" → 111)
        prefix_match = PREFIX_PATTERN.search(filename)
        if prefix_match:
            scene_num = int(prefix_match.group(1))
            parse_source = "prefix"
        else:
            # Priority 2: Fallback to scene_id-XX
            sid_match = SCENE_ID_PATTERN.search(filename)
            if sid_match:
                scene_num = int(sid_match.group(1))
                parse_source = "scene_id"

        if scene_num is None:
            # Cannot parse scene_id from filename - skip
            info("clip_skipped_no_scene_id", filename=filename)
            continue

        # Extract suffix for within-scene priority (e.g. -2, -3 variants)
        # Only relevant when parse_source == "scene_id" (suffix after scene_id number)
        suffix = 0
        if parse_source == "scene_id":
            sid_match2 = SCENE_ID_PATTERN.search(filename)
            if sid_match2 and sid_match2.group(2):
                suffix = int(sid_match2.group(2))

        scene_id = f"S{scene_num:04d}"  # Format: S0001, S0002, ...

        # Priority rule: Lower suffix number = higher priority
        # Only replace if new clip has better (lower) priority
        current_priority = scene_to_priority.get(scene_id, 999)

        if suffix < current_priority:
            scene_to_clip[scene_id] = clip
            scene_to_priority[scene_id] = suffix

            # DEBUG: Log replacements
            if suffix > 0:
                info("clip_priority_replaced",
                     scene_id=scene_id,
                     new_clip=filename,
                     new_priority=suffix,
                     old_priority=current_priority if current_priority != 999 else None)

        # DEBUG: Log first few mappings
        if len(scene_to_clip) <= 5:
            info("mapped_scene",
                 scene_id=scene_id,
                 clip=filename,
                 parse_source=parse_source,
                 priority=suffix,
                 clip_path=clip.get("file", ""))
    
    info("scene_mapping_built", total_scenes=len(scene_to_clip))
    
    # Match segments to clips by scene_id - STRICT MODE
    # Rule: scene_id MUST match exactly, NO fallbacks, NO cyclic
    missing_scenes = []

    for i, seg in enumerate(segments):
        seg_scene_id = seg.get("scene_id", "")

        # STRICT: Only direct match allowed
        if seg_scene_id in scene_to_clip:
            clip = scene_to_clip[seg_scene_id]
            match_type = "scene_id_direct"

            # Build timeline entry
            segment_data = {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg.get("text", ""),
                "type": seg.get("type", "speech"),
                "scene_id": seg_scene_id,
                "index": seg.get("index", i + 1)
            }

            clip_data = {
                "file": clip["file"],
                "name": clip.get("name", "")
            }

            # Conditionally add embeddings
            if save_embeddings:
                # Add segment text embedding (if exists)
                if "feat" in seg:
                    feat = seg["feat"]
                    if isinstance(feat, torch.Tensor):
                        # Efficient conversion: detach → cpu → numpy → list
                        feat_np = feat.detach().cpu().numpy()
                        segment_data["embedding"] = feat_np.tolist()
                        del feat_np  # Explicit cleanup
                    elif isinstance(feat, np.ndarray):
                        segment_data["embedding"] = feat.tolist()
                    else:
                        segment_data["embedding"] = feat

                # Add clip image embedding (if exists)
                if "feat" in clip:
                    feat = clip["feat"]
                    if isinstance(feat, torch.Tensor):
                        # Efficient conversion: detach → cpu → numpy → list
                        feat_np = feat.detach().cpu().numpy()
                        clip_data["embedding"] = feat_np.tolist()
                        del feat_np  # Explicit cleanup
                    elif isinstance(feat, np.ndarray):
                        clip_data["embedding"] = feat.tolist()
                    else:
                        clip_data["embedding"] = feat

            entry = {
                "segment": segment_data,
                "clip": clip_data,
                "scene_id": seg_scene_id,
                "match_type": match_type
            }
            timeline.append(entry)
        else:
            # ERROR: Missing video for this scene_id
            text = seg.get("text", "")
            text_preview = text[:50] + "..." if len(text) > 50 else text

            missing_scenes.append({
                "segment_index": i,
                "scene_id": seg_scene_id,
                "text": text_preview
            })

            # Log error immediately
            info("error_missing_video_for_scene",
                 segment_index=i,
                 scene_id=seg_scene_id,
                 text_preview=text_preview)
    
    # CRITICAL ERROR if any videos are missing
    if missing_scenes:
        error_msg = f"CRITICAL: Missing {len(missing_scenes)} videos for segments!\n"
        error_msg += f"Required: {len(segments)} videos | Found: {len(scene_to_clip)} videos\n"
        error_msg += "\nMissing scene_ids:\n"
        for miss in missing_scenes[:10]:  # Show first 10
            error_msg += f"  - {miss['scene_id']} (segment {miss['segment_index']}): {miss['text']}\n"

        if len(missing_scenes) > 10:
            error_msg += f"  ... and {len(missing_scenes) - 10} more\n"

        # Log detailed error
        info("error_video_count_mismatch",
             required_segments=len(segments),
             found_videos=len(scene_to_clip),
             missing_count=len(missing_scenes),
             missing_scenes=[m['scene_id'] for m in missing_scenes])

        # Raise error to stop pipeline
        raise ValueError(error_msg)

    # Save timeline (only if all videos found)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)

    # Log file size
    file_size_kb = os.path.getsize(out_json) / 1024

    info("sequential_timeline_done",
         entries=len(timeline),
         segments=len(segments),
         clips=len(scene_to_clip),
         status="all_matched",
         embeddings_saved=save_embeddings,
         file_size_kb=round(file_size_kb, 2))

    return timeline