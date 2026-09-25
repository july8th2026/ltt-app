"""Pha 0.4 — chỉ số độ tin cậy ghi lời theo clip (taoclipngan).

`tin_cay_ghi_loi()` trong `apps/taoclipngan/features.py` biến confidence
từng từ của Whisper (đã có sẵn trong `speech.json` → `caption_segments`)
thành một chỉ số tin cậy cho MỖI clip, không tốn thêm lượt GPU. Đây là
đo TÍN NHIỆM từ confidence — KHÔNG phải WER (chưa có corpus tham chiếu
tiếng Việt chuẩn), nên tên hàm/nhãn UI đều nói thẳng "độ tin cậy ghi lời".

Không đọc trạng thái máy: mọi caption là dict tự dựng.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.taoclipngan.features import NGUONG_TU_YEUNGHI, tin_cay_ghi_loi


def _seg(words):
    """Một caption segment kiểu như `jobs.py` dựng: dict có khối `words`."""
    return {"start": 0.0, "end": 1.0, "text": " ".join(w["word"] for w in words),
            "speaker": "", "words": words}


def _w(word, conf):
    return {"word": word, "confidence": conf}


def test_trong_cho_clip_thanh_khoang():
    # Độ tin cậy cao, không từ nghi ngờ
    segs = [_seg([_w("xanh", 0.95), _w("màu", 0.9), _w("lá", 0.88)])]
    out = tin_cay_ghi_loi(segs, total_words=100)
    assert out is not None
    assert out["value"] == 0.91  # (0.95+0.9+0.88)/3 = 0.91
    assert out["words"] == 3
    assert out["low_words"] == 0
    assert out["low_ratio"] == 0.0
    assert out["total_words"] == 100


def test_dem_tu_di_hong_nguong():
    # Một từ dưới ngưỡng (0.5) → nghi ngờ
    segs = [_seg([_w("a", 0.9), _w("b", 0.3), _w("c", 0.5), _w("d", 0.2)])]
    out = tin_cay_ghi_loi(segs)
    assert out is not None
    assert out["low_words"] == 2          # 0.3 và 0.2 (0.5 KHÔNG < 0.5)
    assert out["low_ratio"] == 0.5
    assert out["value"] == round((0.9 + 0.3 + 0.5 + 0.2) / 4, 3)


def test_cho_clip_con_kho_block_words_tra_none():
    # Bản ghi cũ chưa có khối words → không giả số, trả None (UI ẩn)
    assert tin_cay_ghi_loi([{"start": 0, "end": 1, "text": "X", "speaker": ""}]) is None
    assert tin_cay_ghi_loi([]) is None
    assert tin_cay_ghi_loi(None) is None
    # Segment có words rỗng
    assert tin_cay_ghi_loi([{"words": [], "text": "X"}]) is None


def test_ngoi_mat_tu_khong_co_khoa_confidence():
    # Từ không có trường confidence (dict rác) bị bỏ qua, không crash
    segs = [_seg([_w("a", 0.9), {"word": "b"}, {"word": "c", "confidence": "rác"}])]
    out = tin_cay_ghi_loi(segs)
    assert out is not None
    assert out["words"] == 1               # chỉ từ "a" hợp lệ
    assert out["value"] == 0.9


def test_gop_nhieu_segment_dict():
    # Gộp từ confidence qua nhiều segment (đúng hợp đồng jobs.py: dict)
    segs = [_seg([_w("a", 1.0), _w("b", 0.0)]), _seg([_w("c", 0.6)])]
    out = tin_cay_ghi_loi(segs)
    assert out is not None
    assert out["words"] == 3
    assert out["low_words"] == 1           # chỉ "b"=0.0 (< 0.5)
    assert out["value"] == round((1.0 + 0.0 + 0.6) / 3, 3)


def test_nguong_hang_co_dung():
    assert NGUONG_TU_YEUNGHI == 0.5
