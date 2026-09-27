"""tables/__init__.py — package CSDL cua PROMPT AI OMMI.

Tach tu mot tep 385 dong (2026-09-26, spec pha 1 muc R-4). Tep nay CHI
re-export — khong dinh nghia lop nao — de `from apps.prompt_ai_ommi.tables
import X` cu van chay nguyen sau khi tach thanh package.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.tables.tai_nguyen import (
    RESOURCE_KINDS, OmmiResource, OmmiResourceVariant, OmmiTag,
    OmmiResourceTag, OmmiCollection, OmmiCollectionItem, OmmiResourceUsage)
from apps.prompt_ai_ommi.tables.thu_vien import (
    OmmiMetaPrompt, OmmiPromptSnippet, OmmiPromptVersion, OmmiStyle,
    OmmiImageTemplate, OmmiStoryboardFramework, OmmiSample, OmmiProfile)
from apps.prompt_ai_ommi.tables.kich_ban import (
    OmmiStoryboard, OmmiScene, OmmiSceneVersion)
from apps.prompt_ai_ommi.tables.binding import OmmiBinding
from apps.prompt_ai_ommi.tables.handoff import OmmiHandoff
from apps.prompt_ai_ommi.tables.brief import OmmiBrief
from apps.prompt_ai_ommi.tables.canh import OmmiCanh
from apps.prompt_ai_ommi.tables.iteration import OmmiIteration
from apps.prompt_ai_ommi.tables.nhan_vat import (
    OmmiBackground, OmmiCharacter, OmmiFaceEmbedding, OmmiOutfit, OmmiPose)
from apps.prompt_ai_ommi.tables.chia_se import OmmiShareCode

__all__ = [
    "RESOURCE_KINDS", "OmmiResource", "OmmiResourceVariant", "OmmiTag",
    "OmmiResourceTag", "OmmiCollection", "OmmiCollectionItem",
    "OmmiResourceUsage", "OmmiMetaPrompt", "OmmiPromptSnippet",
    "OmmiPromptVersion", "OmmiStyle",
    "OmmiImageTemplate", "OmmiStoryboardFramework", "OmmiSample",
    "OmmiProfile",
    "OmmiStoryboard", "OmmiScene",
    "OmmiSceneVersion", "OmmiBinding", "OmmiHandoff",
    "OmmiBrief", "OmmiCanh", "OmmiIteration",
    "OmmiBackground", "OmmiCharacter", "OmmiFaceEmbedding", "OmmiOutfit",
    "OmmiPose", "OmmiShareCode",
]
