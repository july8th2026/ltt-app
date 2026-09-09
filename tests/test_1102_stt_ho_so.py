"""Service STT dùng chung: hồ sơ **có tên**, và cache không được lẫn hồ sơ.

## Ba mệnh đề, và vì sao đúng ba cái này

1. **Không có mặc định.** Một tên hồ sơ sai phải NÉM, không được rơi về một bộ
   tham số "hợp lý". Mặc định ngầm ở tầng này là một quyết định về **đầu ra của
   sản phẩm** mà không ai ký tên.

2. **Khoá cache phải gồm tên hồ sơ.** Bản legacy khoá theo `(hash, model, lang)`
   — đúng với chúng, vì mỗi bot chỉ có MỘT hồ sơ. Sáu hồ sơ dùng chung một thư
   mục cache thì thiếu tên hồ sơ là **trả kết quả của hồ sơ khác**: cùng audio,
   cùng model, cùng ngôn ngữ, khác `vad_filter`. Không ai phát hiện, vì kết quả
   trông hoàn toàn hợp lệ.

3. **`pause` chọn theo ngôn ngữ, và thiếu ngôn ngữ là LỖI.** `configs/` đang
   chạy khai `beam_size_vi=5 / beam_size_en=1`. Đoán bừa một bên vẫn ra kết quả
   hợp lệ — chỉ là khác đi. Đúng loại sai lặng lẽ mà cả tệp này chống.

⛔ Không chốt ở đây: giá trị cụ thể của từng tham số. Chúng đến từ `configs/`
   đang chạy và sẽ đổi khi production đổi; chốt chúng ở đây là dựng một bản sao
   thứ hai của cấu hình. Thứ **bất biến** là *hình dạng*: có tên, không lẫn,
   không đoán.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from platform_core.stt import ho_so, service


# ── 1. Không có mặc định ────────────────────────────────────────────────────

def test_ten_ho_so_la_khong_the_doan() -> None:
    with pytest.raises(ho_so.KhongCoHoSo):
        ho_so.lay("khong_ton_tai")
    with pytest.raises(ho_so.KhongCoHoSo):
        ho_so.lay("")


def test_lay_tra_BAN_SAO_khong_phai_ban_goc() -> None:
    """Bên gọi thêm `language=` vào là chuyện thường; một lần sửa tại chỗ sẽ
    làm hỏng mọi lượt sau trong cùng tiến trình."""
    a = ho_so.lay("transcript")
    a["beam_size"] = 999
    a.setdefault("vad_parameters", {})["min_silence_duration_ms"] = 1
    assert ho_so.lay("transcript")["beam_size"] != 999
    b = ho_so.lay("pause_vi")
    b["vad_parameters"]["min_silence_duration_ms"] = 1
    assert ho_so.lay("pause_vi")["vad_parameters"]["min_silence_duration_ms"] != 1


def test_transcript_KHONG_co_vad_filter() -> None:
    """Vắng mặt khác với `False`.

    `bot_transcript` chạy VAD riêng ở tầng trên. Truyền `vad_filter=False` cho
    faster-whisper KHÔNG tương đương với việc không truyền gì — nên phép kiểm
    hỏi về **sự vắng mặt của khoá**, không hỏi giá trị.
    """
    assert "vad_filter" not in ho_so.lay("transcript")
    assert ho_so.lay("transcript")["word_timestamps"] is True


def test_moi_ho_so_deu_khac_nhau_that_su() -> None:
    """Hai hồ sơ trùng nhau từng tham số thì một trong hai là thừa — và một hồ
    sơ thừa sẽ được ai đó "dọn", rồi bên gọi của nó đổi hành vi."""
    thay: dict[str, str] = {}
    for ten in ho_so.HO_SO:
        khoa = json.dumps(ho_so.lay(ten), sort_keys=True)
        assert khoa not in thay, f"`{ten}` trung het voi `{thay.get(khoa)}`"
        thay[khoa] = ten


# ── 2. `pause` là hàm của ngôn ngữ ──────────────────────────────────────────

def test_pause_doi_ngon_ngu_va_KHONG_doan() -> None:
    assert ho_so.ten_thuc("pause", "vi") == "pause_vi"
    assert ho_so.ten_thuc("pause", "en") == "pause_en"
    for thieu in (None, "", "fr"):
        with pytest.raises(ho_so.KhongCoHoSo):
            ho_so.ten_thuc("pause", thieu)


def test_hai_bien_the_pause_khac_nhau_o_dung_hai_tham_so() -> None:
    vi, en = ho_so.lay("pause", "vi"), ho_so.lay("pause", "en")
    khac = {k for k in set(vi) | set(en) if vi.get(k) != en.get(k)}
    assert khac == {"beam_size", "best_of"}, (
        "hai bien the `pause` chi duoc khac beam_size/best_of — moi tham so "
        f"khac them la mot thay doi hanh vi chua ai ky: {sorted(khac)}")


def test_ho_so_khong_theo_ngon_ngu_thi_bo_qua_ngon_ngu() -> None:
    assert ho_so.ten_thuc("video", "vi") == "video"
    assert ho_so.lay("video", "en") == ho_so.lay("video")


# ── 3. Cache không được lẫn hồ sơ ───────────────────────────────────────────

def test_khoa_cache_GOM_ten_ho_so(tmp_path: Path,
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """Cùng audio · cùng model · cùng ngôn ngữ · KHÁC hồ sơ ⇒ khác tệp cache.

    🔴 Đây là phép kiểm quan trọng nhất tệp này. Thiếu tên hồ sơ trong khoá,
       một lượt `video_eval` sẽ nhận lại kết quả của `video` — cùng ba thành
       phần kia, nhưng `vad_filter` ngược nhau. Kết quả trả về **hợp lệ về hình
       thức**, nên không có gì đỏ.
    """
    monkeypatch.setenv("LTT_STT_CACHE", str(tmp_path))
    a = service._tep_cache("BAM", "large-v3", "vi", "video")
    b = service._tep_cache("BAM", "large-v3", "vi", "video_eval")
    assert a != b


def test_cache_hong_KHONG_thanh_mot_luot_phien_am_rong(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Một tệp cache hỏng phải bị **bỏ qua**, không được đọc thành `segments=[]`.

    Đó là cách một lỗi hạ tầng (ghi dở vì mất điện) biến thành một lỗi nội dung
    mà không ai truy ngược được.
    """
    monkeypatch.setenv("LTT_STT_CACHE", str(tmp_path))
    assert service._hop_le({"language": "vi", "segments": []}) is True
    for xau in ({}, {"segments": []}, {"language": "vi"},
                {"language": "vi", "segments": "khong phai list"},
                [], None, "{}"):
        assert service._hop_le(xau) is False


def test_bam_theo_NOI_DUNG_khong_theo_duong_dan(tmp_path: Path) -> None:
    """Cùng một audio tới qua hai đường dẫn tạm khác nhau — chuyện xảy ra MỖI
    lượt trong một hàng đợi job — phải cho cùng một khoá."""
    a, b = tmp_path / "mot.wav", tmp_path / "hai.wav"
    a.write_bytes(b"RIFF-gia-lap")
    b.write_bytes(b"RIFF-gia-lap")
    khac = tmp_path / "ba.wav"
    khac.write_bytes(b"RIFF-khac-han")
    assert service.bam_audio(a) == service.bam_audio(b)
    assert service.bam_audio(a) != service.bam_audio(khac)


def test_thieu_tep_audio_bao_loi_cua_TA(tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """Không được để `FileNotFoundError` của thư viện lọt ra — bên gọi phân biệt
    lỗi tham số với lỗi runtime bằng lớp lỗi, không bằng chuỗi."""
    monkeypatch.setenv("LTT_STT_CACHE", str(tmp_path))
    with pytest.raises(service.LoiSTT):
        service.phien_am(tmp_path / "khong-co.wav", ten_ho_so="transcript")


# ── 4. Ranh giới ────────────────────────────────────────────────────────────

def test_stt_khong_import_apps_hay_server() -> None:
    """Cùng ranh giới mà `runtime_noi_bo` giữ: Core không biết App nào tồn tại."""
    goc = Path(__file__).resolve().parent.parent / "platform_core" / "stt"
    for tep in goc.glob("*.py"):
        van = tep.read_text(encoding="utf-8")
        for cam in ("from apps", "import apps", "from server", "import server"):
            assert cam not in van, f"{tep.name} import `{cam}`"


def test_hai_cho_goi_DA_CO_duoc_ghi_lai_nhung_khong_lan_vao_HO_SO() -> None:
    """`apps/autosubvideo` và `cutclipshort` đang chạy với hồ sơ riêng.

    Ghi lại để không ai tưởng chúng dùng chung; tách khỏi `HO_SO` để không ai
    vô tình migrate chúng — đổi đường gọi của một app đang phục vụ khách là đổi
    đầu ra của nó.
    """
    assert set(ho_so.HO_SO_DA_CO) & set(ho_so.HO_SO) == set()
    for ten in ho_so.HO_SO_DA_CO:
        with pytest.raises(ho_so.KhongCoHoSo):
            ho_so.lay(ten)
