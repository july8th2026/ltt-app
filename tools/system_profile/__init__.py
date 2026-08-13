"""Deterministic, secret-safe full-source system dossier builder."""

from .builder import build_profile, profile_path, source_files

__all__ = ["build_profile", "profile_path", "source_files"]
