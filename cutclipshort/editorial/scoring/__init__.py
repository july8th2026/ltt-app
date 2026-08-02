"""Scoring package — modular scoring dimensions for segment evaluation.

Each module provides a single scoring function that can be tested independently.
The segment_scorer.py orchestrator imports and combines them.

Modules:
- pacing: Duration fit, WPM, speech ratio, silence ratio
- visual: Person presence, motion, static penalty
- audio: Energy consistency, speech presence, music contamination
- density: Words per second, information density
- semantic_context: Topic alignment, narrative overlap, emotional spikes
- genre_cues: Genre-specific content detection
"""
