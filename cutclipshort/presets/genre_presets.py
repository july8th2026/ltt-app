"""Genre preset registry.

Maps each genre to its default analysis, editorial, and render config.
"""

from __future__ import annotations

from typing import Any

from cutclipshort.types import Genre

# ── Genre Presets ────────────────────────────────────────────────────────

GENRE_PRESETS: dict[str, dict[str, Any]] = {
    Genre.TALKING_HEAD.value: {
        "display_name": "Talking Head",
        "description": "Single speaker, face-to-camera content",
        "strategy": "talking_head",
        "analysis": {
            "scene_threshold": 30.0,
            "min_scene_len_sec": 2.0,
        },
        "editorial": {
            "min_clip_duration_sec": 15.0,
            "max_clip_duration_sec": 60.0,
            "target_clip_count": 5,
            "hook_priority": "speech_energy",
            "cut_on": "sentence_boundary",
        },
        "render": {
            "default_color": "original",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
    Genre.PODCAST.value: {
        "display_name": "Podcast",
        "description": "Long-form conversation, multiple speakers",
        "strategy": "podcast",
        "analysis": {
            "scene_threshold": 35.0,
            "min_scene_len_sec": 3.0,
        },
        "editorial": {
            "min_clip_duration_sec": 20.0,
            "max_clip_duration_sec": 60.0,
            "target_clip_count": 8,
            "hook_priority": "topic_start",
            "cut_on": "topic_boundary",
        },
        "render": {
            "default_color": "original",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
    Genre.INTERVIEW.value: {
        "display_name": "Interview",
        "description": "Q&A format, two or more speakers",
        "strategy": "interview",
        "analysis": {
            "scene_threshold": 28.0,
            "min_scene_len_sec": 2.0,
        },
        "editorial": {
            "min_clip_duration_sec": 20.0,
            "max_clip_duration_sec": 60.0,
            "target_clip_count": 5,
            "hook_priority": "question_answer",
            "cut_on": "speaker_change",
        },
        "render": {
            "default_color": "clear_fresh",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
    Genre.HIGHLIGHT_REEL.value: {
        "display_name": "Highlight Reel",
        "description": "Action, sports, high-energy content",
        "strategy": "highlight_reel",
        "analysis": {
            "scene_threshold": 20.0,
            "min_scene_len_sec": 1.0,
        },
        "editorial": {
            "min_clip_duration_sec": 10.0,
            "max_clip_duration_sec": 30.0,
            "target_clip_count": 8,
            "hook_priority": "motion_peak",
            "cut_on": "scene_change",
        },
        "render": {
            "default_color": "cinematic",
            "speed_factor": 1.0,
            "caption_default": False,
        },
    },
    Genre.STORYTELLING.value: {
        "display_name": "Storytelling",
        "description": "Narrative content with dramatic arcs",
        "strategy": "storytelling",
        "analysis": {
            "scene_threshold": 25.0,
            "min_scene_len_sec": 2.0,
        },
        "editorial": {
            "min_clip_duration_sec": 20.0,
            "max_clip_duration_sec": 60.0,
            "target_clip_count": 5,
            "hook_priority": "tension_peak",
            "cut_on": "narrative_beat",
        },
        "render": {
            "default_color": "cinematic",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
    Genre.COMEDY.value: {
        "display_name": "Comedy",
        "description": "Setup-punchline, reaction content",
        "strategy": "comedy",
        "analysis": {
            "scene_threshold": 25.0,
            "min_scene_len_sec": 1.5,
        },
        "editorial": {
            "min_clip_duration_sec": 10.0,
            "max_clip_duration_sec": 45.0,
            "target_clip_count": 8,
            "hook_priority": "punchline",
            "cut_on": "laugh_pause",
        },
        "render": {
            "default_color": "clear_fresh",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
    Genre.EDUCATION.value: {
        "display_name": "Education",
        "description": "Tutorial, lesson, how-to content",
        "strategy": "education",
        "analysis": {
            "scene_threshold": 30.0,
            "min_scene_len_sec": 3.0,
        },
        "editorial": {
            "min_clip_duration_sec": 20.0,
            "max_clip_duration_sec": 60.0,
            "target_clip_count": 5,
            "hook_priority": "key_concept",
            "cut_on": "lesson_segment",
        },
        "render": {
            "default_color": "clear_fresh",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
    Genre.NEWS_COMMENTARY.value: {
        "display_name": "News Commentary",
        "description": "Hot takes, reactions, opinion content",
        "strategy": "news_commentary",
        "analysis": {
            "scene_threshold": 25.0,
            "min_scene_len_sec": 2.0,
        },
        "editorial": {
            "min_clip_duration_sec": 15.0,
            "max_clip_duration_sec": 45.0,
            "target_clip_count": 6,
            "hook_priority": "hot_take",
            "cut_on": "opinion_boundary",
        },
        "render": {
            "default_color": "original",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
    Genre.REVIEW.value: {
        "display_name": "Review",
        "description": "Product review, verdict, comparison",
        "strategy": "review",
        "analysis": {
            "scene_threshold": 25.0,
            "min_scene_len_sec": 2.0,
        },
        "editorial": {
            "min_clip_duration_sec": 15.0,
            "max_clip_duration_sec": 60.0,
            "target_clip_count": 5,
            "hook_priority": "verdict",
            "cut_on": "topic_segment",
        },
        "render": {
            "default_color": "clear_fresh",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },

    # ── Entertainment genres ──────────────────────────────────────────

    Genre.NATURE.value: {
        "display_name": "Thiên nhiên",
        "description": "Visual-first nature, wildlife, landscape content",
        "strategy": "nature",
        "analysis": {
            "scene_threshold": 20.0,
            "min_scene_len_sec": 2.0,
        },
        "editorial": {
            "min_clip_duration_sec": 15.0,
            "max_clip_duration_sec": 45.0,
            "target_clip_count": 6,
            "hook_priority": "visual_impact",
            "cut_on": "scene_change",
        },
        "render": {
            "default_color": "cinematic",
            "speed_factor": 1.0,
            "caption_default": False,
        },
    },
    Genre.HISTORY.value: {
        "display_name": "Lịch sử",
        "description": "Documentary, historical narrative content",
        "strategy": "history",
        "analysis": {
            "scene_threshold": 25.0,
            "min_scene_len_sec": 2.5,
        },
        "editorial": {
            "min_clip_duration_sec": 20.0,
            "max_clip_duration_sec": 55.0,
            "target_clip_count": 5,
            "hook_priority": "curiosity",
            "cut_on": "narrative_beat",
        },
        "render": {
            "default_color": "original",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
    Genre.ACTION.value: {
        "display_name": "Hành động",
        "description": "High-energy action, sports, gaming",
        "strategy": "action",
        "analysis": {
            "scene_threshold": 15.0,
            "min_scene_len_sec": 1.0,
        },
        "editorial": {
            "min_clip_duration_sec": 10.0,
            "max_clip_duration_sec": 40.0,
            "target_clip_count": 8,
            "hook_priority": "motion_peak",
            "cut_on": "scene_change",
        },
        "render": {
            "default_color": "original",
            "speed_factor": 1.0,
            "caption_default": False,
        },
    },
    Genre.KIDS_MUSIC.value: {
        "display_name": "Nhạc thiếu nhi",
        "description": "Children's music, sing-along, dance",
        "strategy": "kids_music",
        "analysis": {
            "scene_threshold": 25.0,
            "min_scene_len_sec": 2.0,
        },
        "editorial": {
            "min_clip_duration_sec": 15.0,
            "max_clip_duration_sec": 45.0,
            "target_clip_count": 5,
            "hook_priority": "chorus",
            "cut_on": "music_boundary",
        },
        "render": {
            "default_color": "clear_fresh",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
    Genre.ANIMATION.value: {
        "display_name": "Hoạt hình",
        "description": "Animated content, cartoon, character-driven",
        "strategy": "animation",
        "analysis": {
            "scene_threshold": 20.0,
            "min_scene_len_sec": 1.5,
        },
        "editorial": {
            "min_clip_duration_sec": 15.0,
            "max_clip_duration_sec": 50.0,
            "target_clip_count": 6,
            "hook_priority": "story_beat",
            "cut_on": "scene_change",
        },
        "render": {
            "default_color": "original",
            "speed_factor": 1.0,
            "caption_default": True,
        },
    },
}


def get_genre_preset(genre: str | Genre) -> dict[str, Any]:
    """Get preset for a genre. Falls back to talking_head."""
    key = genre.value if isinstance(genre, Genre) else genre
    return dict(GENRE_PRESETS.get(key, GENRE_PRESETS[Genre.TALKING_HEAD.value]))


def list_genres() -> list[dict[str, str]]:
    """List all genres with name, display_name, description."""
    return [
        {
            "name": name,
            "display_name": preset["display_name"],
            "description": preset["description"],
        }
        for name, preset in GENRE_PRESETS.items()
    ]
