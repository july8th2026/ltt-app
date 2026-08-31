"""Phép kiểm cho chính BỘ ĐO — thước đo mà không ai đo lại là thước đo sai được.

## Vì sao tệp này tồn tại

Ngày 31/08/2026, `voice_sidecar/do_chat_luong.py` và các công cụ quanh nó lộ ra
**ba lỗi của chính chúng** trong một buổi, và cả ba đều **không làm chương trình
dừng** — chúng chỉ làm con số sai:

  1. `do_ben_dau_chim` đọc khoá `doc_lai` trong khi bộ đo trả `doc_lai_duoc`.
     Kết quả: `-1.0` ở **mọi** phép, và bảng đó đọc y hệt *"dấu chìm không bền
     chút nào"*. Thứ cứu nó là **dòng đối chứng**: tệp nguyên vẹn cũng `-1.0`
     ⇒ thủ phạm là phép đo, không phải dấu.
  2. Hai lớp `io.TextIOWrapper` trên cùng một `stdout.buffer`: lớp thứ hai thay
     chỗ lớp thứ nhất, lớp thứ nhất bị thu hồi và **đóng buffer**. Cả hai cùng
     chết sau khi đã đo xong.
  3. `condition_on_previous_text=True` (mặc định Whisper) khiến ASR **bỏ hẳn một
     đoạn giữa** audio dài. Bản ghi chỉ phủ 74,5 % văn bản trong khi phần cuối
     khớp hoàn hảo, CER báo 29,9 %. Kết luận *"ghép làm giảm chất lượng"* rút ra
     từ đó sẽ **sai**.

⭐ Điểm chung: một bộ đo hỏng không kêu. Nó trả về một con số, và con số đó đi
   thẳng vào tài liệu. Nên bộ đo cần bánh cóc **hơn** mã sản phẩm, không phải ít
   hơn.

## Phạm vi

Chạy trong venv nền tảng (có numpy + scipy, **không** có soundfile/pyloudnorm/
perth/librosa — chúng ở `vieneu-venv`). Nên tệp này kiểm phần **thuần tín hiệu
và thuần logic**; phần cần model được kiểm bằng đối chứng ngay trong công cụ.
"""
from __future__ import annotations

import numpy as np
import pytest

SR = 48_000


def _sin(giay: float, hz: float = 220.0, bien: float = 0.5):
    t = np.arange(int(SR * giay)) / SR
    return (np.sin(2 * np.pi * hz * t) * bien).astype(np.float32)


# ═══════════════════════════════════════════ toàn vẹn tín hiệu ═══════════════

def test_do_tin_hieu_bat_dung_dinh_va_vo_tieng():
    from voice_sidecar.do_chat_luong import NGUONG_CHAM_TRAN, do_tin_hieu

    # Sóng sin ở 0,5 → đỉnh mẫu 0,5, không có mẫu nào chạm trần.
    kq = do_tin_hieu(_sin(1.0, bien=0.5), SR)
    assert kq["dinh_mau"] == pytest.approx(0.5, abs=0.01)
    assert kq["so_mau_cham_tran"] == 0

    # Cắt cứng ở 1,0 → rất nhiều mẫu chạm trần.
    vo = np.clip(_sin(1.0, bien=2.0), -1.0, 1.0)
    kq2 = do_tin_hieu(vo, SR)
    assert kq2["so_mau_cham_tran"] > 0, (
        f"cat cung o 1,0 ma khong bat duoc mau nao >= {NGUONG_CHAM_TRAN}")
    assert kq2["ty_le_cham_tran"] > 0.01


def test_do_tin_hieu_bat_dung_dc_offset():
    from voice_sidecar.do_chat_luong import do_tin_hieu

    sach = do_tin_hieu(_sin(1.0), SR)
    assert abs(sach["dc_offset"]) < 0.001, "song sin thuan phai gan 0"

    lech = do_tin_hieu((_sin(1.0) + 0.2).astype(np.float32), SR)
    assert lech["dc_offset"] == pytest.approx(0.2, abs=0.01)


def test_do_tin_hieu_tep_rong_khong_no():
    """Một tệp 0 mẫu là một kết quả, không phải một ngoại lệ."""
    from voice_sidecar.do_chat_luong import do_tin_hieu

    kq = do_tin_hieu(np.zeros(0, dtype=np.float32), SR)
    assert "loi" in kq


# ═══════════════════════════════════════════ khoảng lặng ═════════════════════

def test_do_khoang_lang_tach_im_DAU_CUOI_khoi_im_GIUA():
    """Im ở hai đầu là bình thường; im ở GIỮA mới là đứt quãng."""
    from voice_sidecar.do_chat_luong import do_khoang_lang

    wav = np.concatenate([
        np.zeros(int(SR * 0.4), np.float32),   # im đầu
        _sin(0.5), np.zeros(int(SR * 0.7), np.float32), _sin(0.5),
        np.zeros(int(SR * 0.3), np.float32),   # im cuối
    ])
    kq = do_khoang_lang(wav, SR)
    assert kq["im_dau_s"] == pytest.approx(0.4, abs=0.06)
    assert kq["im_cuoi_s"] == pytest.approx(0.3, abs=0.06)
    assert kq["im_giua_dai_nhat_s"] == pytest.approx(0.7, abs=0.06)
    assert kq["so_khoang_lang_giua"] == 1


# ═══════════════════════════════════════════ so khớp văn bản ═════════════════

def test_ti_le_sai_dau_do_RIENG_dau_thanh():
    """⭐ Chỉ số riêng cho tiếng Việt: "má/mà/mã/mạ" khác nghĩa hoàn toàn.

    Một CER 3 % gồm toàn lỗi dấu tệ hơn hẳn một CER 3 % gồm lỗi phụ âm cuối.
    """
    from voice_sidecar.do_chat_luong import _chi_dau, _levenshtein

    goc = _chi_dau("má mà mã mạ")
    assert goc, "cau nay co bon dau thanh, khong duoc ra rong"
    sai_dau = _chi_dau("ma ma ma ma")
    assert _levenshtein(goc, sai_dau) == len(goc), (
        "bo het dau ma khoang cach khong bang so dau — phep do khong nhin dau")

    # Đổi phụ âm mà giữ nguyên dấu ⇒ tỉ lệ sai dấu KHÔNG đổi.
    giu_dau = _chi_dau("bá bà bã bạ")
    assert _levenshtein(goc, giu_dau) == 0, (
        "doi phu am ma ti le sai dau cung doi — no dang do lan ca chu")


def test_chuan_hoa_so_khop_bo_qua_hoa_thuong_va_dau_cau():
    from voice_sidecar.do_chat_luong import _chuan_hoa_so_khop as ch

    assert ch("Xin chào, bạn!") == ch("xin chào bạn")


# ═══════════════════════════════════════════ phán quyết ══════════════════════

def test_phan_quyet_CHI_phan_xu_muc_co_nguong_co_nguon():
    """🔴 Nguyên tắc trung tâm của cả bộ đo.

    CER, tương đồng người nói và trôi giọng **chỉ so sánh được**, chưa hiệu
    chuẩn. Cho chúng vào phán quyết là biến một bảng màu xanh thành một lời nói
    dối: `apps/qualitylab` của chính kho này đã học đúng bài đó.
    """
    from voice_sidecar.do_chat_luong import phan_quyet

    kq = {
        "hop_dong": {"giay": 8.0, "sample_rate": SR, "so_kenh": 1},
        "tin_hieu": {"true_peak_dbtp": -3.0, "ty_le_cham_tran": 0.0,
                     "so_mau_cham_tran": 0, "lufs": -18.0, "dc_offset": 0.0},
        "khoang_lang": {"im_giua_dai_nhat_s": 0.4},
        "watermark": {"co": True, "doc_lai_duoc": 1.0},
        # Ba muc "chi so sanh duoc" — co tinh dat gia tri RAT XAU:
        "de_hieu": {"co": True, "cer": 0.99, "chua_hieu_chuan": True},
        "giu_giong": {"co": True, "cosine": 0.01, "chua_hieu_chuan": True},
        "troi_giong": {"co": True, "cosine_thap_nhat": 0.01,
                       "chua_hieu_chuan": True},
    }
    pq = phan_quyet(kq)
    assert pq["ket_luan"] == "DAT", (
        f"CER 99 % va tuong dong 0,01 KHONG duoc lam hong phan quyet — chung "
        f"chua hieu chuan. Ket luan: {pq['ket_luan']}")

    # Nhưng một mục CÓ nguồn xấu thì phải HỎNG.
    kq["tin_hieu"]["true_peak_dbtp"] = -0.2      # vuot tran EBU R128
    assert phan_quyet(kq)["ket_luan"] == "HONG", (
        "dinh that -0,2 dBTP vuot tran -1,0 ma van DAT")


# ═══════════════════════════════════════ ba lỗi của chính bộ đo ══════════════

def test_khong_module_nao_boc_lai_stdout_bang_TextIOWrapper():
    """🔴 Hai lớp bọc trên cùng một buffer sẽ ĐÓNG buffer đó.

    Khi module thứ hai gán một `TextIOWrapper` mới đè lên cùng `sys.stdout.buffer`,
    wrapper của module thứ nhất mất tham chiếu, bị thu hồi, và đóng buffer bên
    dưới. Cả hai cùng chết với `ValueError: I/O operation on closed file` — **sau
    khi đã đo xong**, ở dòng `print` đầu tiên. Một thông điệp không hề nhắc tới
    mã hoá, tức nó giấu cả nguyên nhân lẫn nơi xảy ra.

    `reconfigure()` sửa tại chỗ, không tạo đối tượng mới, gọi hai lần vô hại.
    """
    import pathlib
    import re

    goc = pathlib.Path(__file__).resolve().parents[1]
    xau = []
    for duong in list((goc / "voice_sidecar").glob("*.py")) + \
            list((goc / "tools").glob("do_*.py")) + \
            list((goc / "tools").glob("*giong*.py")):
        text = duong.read_text(encoding="utf-8")
        for i, dong in enumerate(text.splitlines(), 1):
            if dong.lstrip().startswith("#"):
                continue
            if re.search(r"sys\.stdout\s*=\s*io\.TextIOWrapper", dong):
                xau.append(f"{duong.relative_to(goc)}:{i}")
    assert not xau, (
        "Nhung cho sau gan mot TextIOWrapper MOI de len sys.stdout:\n  "
        + "\n  ".join(xau) +
        "\nDung `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`.")


def test_asr_tat_condition_on_previous_text():
    """🔴 Mặc định `True` của Whisper BỎ HẲN một đoạn giữa audio dài.

    Đo 31/08/2026: bản 2.907 ký tự, bản ghi lại chỉ phủ 74,5 % văn bản trong khi
    **phần cuối khớp hoàn hảo** — tức chữ bị BỎ, không phải đọc SAI. CER báo
    29,9 %, và mọi kết luận về chất lượng rút ra từ đó đều sai.
    """
    import inspect

    from voice_sidecar import do_chat_luong

    # ⛔ Đọc MÃ của `_asr`, và bỏ dòng chú thích. Bản đầu quét cả tệp, và nó
    #    XANH cả khi đã gỡ cờ ra — vì chính đoạn chú thích giải thích lỗi cũng
    #    chứa chuỗi `condition_on_previous_text=False`. Một bánh cóc khớp vào
    #    lời văn giải thích chính nó là một bánh cóc không bao giờ đỏ.
    dong = inspect.getsource(do_chat_luong._asr).splitlines()
    ma = chr(10).join(d for d in dong if not d.lstrip().startswith("#"))
    assert "condition_on_previous_text=False" in ma, (
        "`_asr` khong tat `condition_on_previous_text`. Tren audio dai va lap "
        "noi dung, Whisper se sinh vong lap roi bo han mot doan — va no bo o "
        "GIUA, nen ban ghi van ket thuc dung cho, trong y het mot ban day du.")


def test_de_hieu_bao_TI_LE_PHU_de_CER_khong_danh_lua_duoc():
    """Không có tỉ lệ phủ thì một bản ghi mất 25 % ở giữa vẫn cho CER trông
    bình thường, và người đọc sẽ quy tội cho TTS."""
    import inspect

    from voice_sidecar import do_chat_luong

    ma = inspect.getsource(do_chat_luong.do_de_hieu)
    assert "ty_le_phu" in ma, (
        "`do_de_hieu` khong bao ty le phu. Hai CER chi so duoc voi nhau khi hai "
        "luot phu xap xi nhau — thieu no thi con so tu do mat nghia.")


def test_do_ben_dau_chim_luon_co_DOI_CHUNG_AM():
    """🔴 Một bảng toàn `1.0` có ĐÚNG HAI cách đọc.

    Dấu chìm rất bền, hoặc bộ dò luôn trả lời "có". Hai cách đọc cho **cùng một
    bảng số**, và chỉ đối chứng ÂM — audio chưa từng đi qua bộ đóng dấu — mới
    tách được chúng.

    Chính dòng đối chứng đó đã bắt được một lỗi thật cùng ngày: bản đầu đọc
    nhầm tên khoá kết quả, cho ra `-1.0` ở mọi phép. Không có nó, kết luận
    *"dấu chìm không bền chút nào"* đã đi thẳng vào tài liệu.
    """
    from voice_sidecar.do_ben_dau_chim import PHEP

    ma = [p[0] for p in PHEP]
    doi_chung = [m for m in ma if m.startswith("DOI_CHUNG")]
    assert doi_chung, (
        f"khong co phep DOI_CHUNG nao trong {ma}. Mot bang toan 1.0 khong phan "
        f"biet duoc 'dau ben' voi 'bo do luon noi co'.")
    assert ma[0].startswith("DOI_CHUNG"), (
        "doi chung phai in TRUOC — nguoi doc phai thay no truoc khi doc phan "
        "con lai, khong phai tim no o cuoi bang")


def test_moi_nguong_phan_quyet_deu_co_nguon_ghi_ngay_canh():
    """Một ngưỡng không có nguồn thì không được phán quyết — nó phải báo số."""
    import pathlib

    text = (pathlib.Path(__file__).resolve().parents[1]
            / "voice_sidecar" / "do_chat_luong.py").read_text(encoding="utf-8")
    dau = text.find("# ── ngưỡng CÓ NGUỒN")
    assert dau > 0, "mat khoi khai bao nguong co nguon"
    khoi = text[dau:text.find("# ═══", dau)]
    for ten in ("TRAN_TRUE_PEAK_DBTP", "LUFS_MUC_TIEU", "NGUONG_CHAM_TRAN",
                "DC_OFFSET_TOI_DA", "KHOANG_LANG_GIUA_TOI_DA_S"):
        assert ten in khoi, (
            f"`{ten}` khong nam trong khoi 'nguong CO NGUON'. Moi nguong tham "
            f"gia phan quyet deu phai co nguon ghi ngay canh no.")


# ═══════════════════════════ phan loai loi: ai duoc thu lai ══════════════════

def test_loi_HA_TANG_phai_duoc_thu_lai_con_loi_NGUOI_GOI_thi_khong():
    """🔴 Hồi quy thật, do commit `c8634b8` của chính phiên này gây ra.

    Cho `LoiGiongNoi` kế thừa `LoiNguoiGoi` là **đúng** cho "giọng này không
    phải của bạn" — chạy lại y hệt sẽ hỏng y hệt. Nhưng nhánh `LoiSidecar` cũng
    ném `LoiGiongNoi`, và nhánh đó gồm: mạng chập chờn, cổng trả 5xx, cổng đang
    khởi động lại sau deploy.

    Hệ quả: thông điệp nói *"Vui lòng thử lại sau"* trong khi nền tảng đã quyết
    **không bao giờ thử lại**. Ca thường gặp nhất là ca tệ nhất — mỗi lần deploy
    khởi động lại `LTTStudioVoice`, mọi job đang bay hỏng vĩnh viễn thay vì được
    xếp lại vài giây sau.

    ⭐ Chính docstring của `LoiNguoiGoi` đã cảnh báo đúng điều này. Phép kiểm
       này biến lời cảnh báo đó thành thứ máy đọc được.
    """
    from platform_core.job_runner import _provider_failure_kind
    from platform_core.jobs import LoiNguoiGoi

    from apps.ltt_voice.features import DangBanTam, LoiGiongNoi, LoiHaTang

    # Lỗi của NGƯỜI GỌI: không thử lại.
    assert issubclass(LoiGiongNoi, LoiNguoiGoi)
    assert _provider_failure_kind(LoiGiongNoi("x"), provider_state="")[0] \
        == "loi_nguoi_goi"

    # Lỗi HẠ TẦNG: PHẢI thử lại.
    assert not issubclass(LoiHaTang, LoiNguoiGoi), (
        "`LoiHaTang` ke thua `LoiNguoiGoi` — do la toan bo hoi quy ma lop nay "
        "sinh ra de sua")
    assert _provider_failure_kind(LoiHaTang("x"), provider_state="")[0] != \
        "loi_nguoi_goi", "cong giong truc trac ma khong duoc thu lai"

    # Máy bận: xếp lại, cũng không phải lỗi khách.
    assert not issubclass(DangBanTam, LoiNguoiGoi)


def test_nhanh_LoiSidecar_khong_duoc_nem_LoiGiongNoi():
    """Chốt đúng chỗ đã sai, để nó không lặng lẽ quay lại."""
    import inspect

    from apps.ltt_voice import features

    dong = inspect.getsource(features._goi_va_dich_loi).splitlines()
    ma = chr(10).join(d for d in dong if not d.lstrip().startswith("#"))
    i = ma.find("except sidecar_client.LoiSidecar")
    assert i > 0, "mat nhanh xu ly LoiSidecar"
    nhanh = ma[i:]
    assert "raise LoiHaTang(" in nhanh, (
        "nhanh `LoiSidecar` phai nem `LoiHaTang`. Nem `LoiGiongNoi` o day la "
        "noi voi khach 'vui long thu lai sau' roi tu quyet khong thu lai.")
