"""Adapter từng nền tảng. Hợp đồng: base.py. Tra adapter theo registry: `tao(nen_id)`."""
from __future__ import annotations

import importlib

from platform_core.i18n import _ as _t


def tao(nen_id: str):
    """Instance adapter của nền đã BẬT (`NenTang.adapter` = tên module trong gói này).

    Một nguồn cho cả web (dựng lại URL chuẩn từ id — chống URL giả mạo) lẫn worker.
    """
    from apps.video_crawler import nen_tang
    ten = nen_tang.lay_nen_bat(nen_id).adapter
    mod = importlib.import_module(f"apps.video_crawler.adapters.{ten}")
    for v in vars(mod).values():
        if isinstance(v, type) and getattr(v, "nen_tang", None) == nen_id and hasattr(v, "tai"):
            return v()
    raise RuntimeError(_t("adapter {ten!r} không khai lớp cho nền {nen_id!r}").format(ten=ten, nen_id=nen_id))
