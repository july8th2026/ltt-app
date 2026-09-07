"""Mối nối giữa LTT và WanGP.

Tầng trên (`so_dang_ky`, `tac_vu`, `jobs`, `routes`) **chỉ** được import từ đây.
Nhập thẳng `httpx`, `shared.api` hay bất kỳ thứ gì của WanGP ở tầng trên là đi
vòng qua mối nối — và đi vòng là cách `wangp_client` cũ đã phình ra.
"""
from __future__ import annotations

from apps.lttvideo.cong.giao_uoc import LoiMay, May
from apps.lttvideo.cong.may_gia_lap import MayGiaLap
from apps.lttvideo.cong.may_that import MayThat

__all__ = ["LoiMay", "May", "MayGiaLap", "MayThat"]
