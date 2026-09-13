"""Tầng khớp clip của App `video_assembly`, đo trên job THẬT của bot legacy.

Bộ mẫu ở `tests/golden/parity_video_khop_clip/` là **4 lượt job thật** đã chạy
trên production, chỉ giữ `transcript.json` và **tên** tệp clip — tầng này không
mở video, nên chép 5,7 GB `.mp4` không thêm một bit thông tin nào.

🔴 Phát hiện đổi hành vi, đo được: bản chuyển nguyên vẹn cho **ba kết quả khác
   nhau từ ba thứ tự đầu vào** trên `mau_03` — **115/125 cảnh đổi clip**. Thứ tự
   ấy đến từ `clip_sampling.py:75`, `os.listdir()` **không** `sorted()`. Tức đầu
   ra của bot phụ thuộc thứ tự thư mục của hệ tệp.

⭐ Khác hẳn `random.uniform` bên App `transcript`. Cái kia **ngẫu nhiên có chủ
   đích**. Cái này thì mã **đã có** cơ chế phân định (`suffix`) và chú thích của
   nó nói rõ ý định — `001-scene_id-1.mp4 (suffix=0) > 001-scene_id-1-2.mp4
   (suffix=2)` — nhưng `suffix` chỉ được tính ở nhánh `scene_id`, còn tên thật
   trên production đều có tiền tố nên đi nhánh `prefix` và `suffix` **luôn bằng
   0**. Luật `suffix < current_priority` không bao giờ cắn.

⇒ Bản sửa sắp xếp đầu vào theo `(số cảnh, hậu tố, tên)`. Nó làm đúng hai việc:
  kết quả hết phụ thuộc thứ tự, **và** người thắng là clip gốc chứ không phải
  biến thể — tức đúng ý định mà chú thích kia đã viết ra.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from apps.video_assembly.services.engine import sequential_timeline as st
from apps.video_assembly.services.tuong_thich.paths import safe_name

GOC = pathlib.Path(__file__).resolve().parent / "golden" / "parity_video_khop_clip"


def _mau() -> list[pathlib.Path]:
    return sorted(d for d in GOC.iterdir() if d.is_dir())


def _doc(d: pathlib.Path) -> tuple[list[dict], list[str]]:
    seg = json.loads((d / "transcript.json").read_text(encoding="utf-8"))
    ten = json.loads((d / "ten_clip.json").read_text(encoding="utf-8"))
    return seg, ten


def _chay(seg, ten, tmp_path):
    return st.build_sequential_timeline(
        {}, seg, [{"name": n, "file": n} for n in ten],
        str(tmp_path / "timeline.json"))


def _bam(x) -> str:
    return hashlib.sha256(
        json.dumps(x, sort_keys=True, default=str).encode()).hexdigest()


def _thu_tu(ten: list[str]) -> list[list[str]]:
    """Bốn thứ tự đầu vào — tăng, giảm, và hai lần xáo có gieo cố định."""
    import random
    return [sorted(ten), sorted(ten, reverse=True),
            random.Random(1).sample(ten, len(ten)),
            random.Random(9).sample(ten, len(ten))]


def test_bo_mau_phu_du_BON_TRUONG_HOP() -> None:
    st_ = json.loads((GOC / "so_tay.json").read_text(encoding="utf-8"))
    cap = {c["ten"]: c for c in st_["cap"]}
    assert len(cap) == 4 == len(_mau())
    assert cap["mau_02_khong_co_clip"]["so_clip"] == 0
    assert cap["mau_03_nhieu_clip_mot_canh"]["so_clip"] > \
        cap["mau_03_nhieu_clip_mot_canh"]["so_canh"]
    assert cap["mau_01_mot_doi_mot_nho"]["so_clip"] == \
        cap["mau_01_mot_doi_mot_nho"]["so_canh"]
    for c in cap.values():
        assert len(c["bam_id_nguon"]) == 64
        assert not c["ten"].startswith("row")     # Drive id khong duoc lot ra


@pytest.mark.parametrize("d", [p for p in _mau()
                               if "khong_co_clip" not in p.name
                               and "thieu_mot_canh" not in p.name],
                         ids=lambda p: p.name)
def test_ket_qua_KHONG_phu_thuoc_thu_tu_dau_vao(d, tmp_path) -> None:
    seg, ten = _doc(d)
    assert len({_bam(_chay(seg, t, tmp_path)) for t in _thu_tu(ten)}) == 1


def test_DOI_CHUNG_bo_sap_xep_di_thi_ket_qua_LECH_ngay(tmp_path, monkeypatch) -> None:
    """Không có nửa này thì phép kiểm trên có thể xanh vì lý do khác hẳn.

    Vô hiệu hoá khoá sắp xếp (trả hằng số ⇒ `sorted` giữ nguyên thứ tự vào) là
    tái hiện đúng hành vi bản gốc. Kết quả phải **lệch** — nếu không thì phép
    kiểm trên không đo cái nó nói nó đo.
    """
    d = GOC / "mau_03_nhieu_clip_mot_canh"
    seg, ten = _doc(d)
    monkeypatch.setattr(st, "_khoa_sap_xep", lambda clip: 0)
    assert len({_bam(_chay(seg, t, tmp_path)) for t in _thu_tu(ten)}) > 1


def test_clip_GOC_thang_bien_the__dung_y_dinh_ma_chu_thich_da_viet(tmp_path) -> None:
    seg, ten = _doc(GOC / "mau_03_nhieu_clip_mot_canh")
    tl = _chay(seg, ten, tmp_path)
    chon = {e["scene_id"]: json.dumps(e.get("clip", e.get("video", "")),
                                      ensure_ascii=False) for e in tl}
    # `002-scene_id-2.mp4` (goc) va `002-scene_id-2-2.mp4` (bien the) cung canh.
    assert "002-scene_id-2.mp4" in ten and "002-scene_id-2-2.mp4" in ten
    assert "002-scene_id-2.mp4" in chon["S0002"]
    assert "002-scene_id-2-2.mp4" not in chon["S0002"]


def test_THIEU_clip_thi_NEM_LOI_neu_dich_danh_canh(tmp_path) -> None:
    """Thiếu một cảnh phải **nổ**, không được im lặng dựng một video hụt."""
    seg, ten = _doc(GOC / "mau_04_thieu_mot_canh")
    with pytest.raises(ValueError) as e:
        _chay(seg, ten, tmp_path)
    assert "S0069" in str(e.value), "loi khong noi canh nao thieu"


def test_KHONG_co_clip_nao_thi_NEM_LOI(tmp_path) -> None:
    seg, ten = _doc(GOC / "mau_02_khong_co_clip")
    assert ten == []
    with pytest.raises(ValueError):
        _chay(seg, ten, tmp_path)


def test_safe_name_GIU_NGUYEN_tien_to_ma_tang_khop_clip_doc() -> None:
    """Ràng buộc nối tầng bảo mật với tầng khớp clip.

    ⛔ Bản vá path traversal **không** được thay tên tệp bằng UUID: chế độ
       `sequential` khớp cảnh bằng **tiền tố tên tệp**. Đo trên job thật:
       `mau_03` có 240 clip cho 125 cảnh, tên dạng `002-scene_id-2-2.mp4` — mất
       tiền tố là mất toàn bộ ánh xạ.
    """
    for n in ("001-scene_id-1.mp4", "002-scene_id-2-2.mp4", "0123-scene_id-99.mp4"):
        assert safe_name(n) == n
        assert st.PREFIX_PATTERN.search(safe_name(n)), n
    # ...nhung duong dan an trong ten thi phai bi chan.
    assert "/" not in safe_name("../../etc/passwd")
    assert chr(92) not in safe_name(".." + chr(92) + "windows" + chr(92) + "x.mp4")
