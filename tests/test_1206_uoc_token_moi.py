"""multijob Task 7 — ước token prefill MỚI (nhận diện lượt tiếp của cùng hội thoại)."""
from __future__ import annotations

import pytest

from platform_core.llm import uoc_moi


def _uoc(ds):
    """Phép ước giả: 1.000 token mỗi tin nhắn."""
    return 1_000 * len(ds)


@pytest.fixture(autouse=True)
def _sach():
    uoc_moi.quen_het()
    yield
    uoc_moi.quen_het()


def _hoi_thoai(n):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"tin {i}"}
            for i in range(n)]


def test_luot_dau_la_toan_bo():
    assert uoc_moi.uoc_token_moi("u", _hoi_thoai(150), _uoc) == 150_000


def test_luot_tiep_chi_tinh_phan_moi():
    """Phiên agent 150K, lượt sau thêm 2 tin ⇒ chỉ 2.000 token mới — KHÔNG phải whale."""
    uoc_moi.uoc_token_moi("u", _hoi_thoai(150), _uoc)
    assert uoc_moi.uoc_token_moi("u", _hoi_thoai(152), _uoc) == 2_000


def test_tai_khoan_khac_khong_huong_cache_cua_nhau():
    uoc_moi.uoc_token_moi("a", _hoi_thoai(150), _uoc)
    assert uoc_moi.uoc_token_moi("b", _hoi_thoai(152), _uoc) == 152_000


def test_sua_tin_giua_hoi_thoai_thi_phan_sau_la_moi():
    """Tin nhắn thứ 10 đổi ⇒ cache từ đó trở đi vô hiệu (đúng hành vi llama.cpp)."""
    ht = _hoi_thoai(20)
    uoc_moi.uoc_token_moi("u", ht, _uoc)
    ht2 = list(ht)
    ht2[10] = {"role": "user", "content": "DA SUA"}
    assert uoc_moi.uoc_token_moi("u", ht2, _uoc) == 10_000


def test_gui_lai_y_het_la_khong_co_gi_moi():
    ht = _hoi_thoai(5)
    uoc_moi.uoc_token_moi("u", ht, _uoc)
    assert uoc_moi.uoc_token_moi("u", ht, _uoc) == 0


def test_nhieu_hoi_thoai_song_song_cua_mot_nguoi():
    a = [{"role": "user", "content": f"A{i}"} for i in range(30)]
    b = [{"role": "user", "content": f"B{i}"} for i in range(30)]
    uoc_moi.uoc_token_moi("u", a, _uoc)
    uoc_moi.uoc_token_moi("u", b, _uoc)
    assert uoc_moi.uoc_token_moi("u", a + [{"role": "user", "content": "A-moi"}], _uoc) == 1_000
