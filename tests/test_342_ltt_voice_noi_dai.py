"""Đường văn bản dài: chia đoạn, ghép, và hai trần là hai thứ khác nhau.

Bộ ghép (`voice_sidecar/noi_dai.py`) chỉ dùng numpy nên chạy được trong venv nền
tảng — không cần torch, không cần model. Nhờ vậy nó kiểm được **logic ghép** mà
không phải nạp GPU, và phần cần GPU chỉ còn là phép đo chất lượng ở V10.
"""
from __future__ import annotations

import numpy as np
import pytest

SR = 48_000


def _tieng(giay: float, muc: float = 0.2) -> np.ndarray:
    """Một đoạn 'có tiếng': nhiễu ở mức cho trước. Không cần giống tiếng nói —
    bộ ghép chỉ phân biệt có tiếng / im theo RMS."""
    n = int(SR * giay)
    rng = np.random.default_rng(0)
    return (rng.standard_normal(n) * muc).astype(np.float32)


def _im(giay: float) -> np.ndarray:
    return np.zeros(int(SR * giay), dtype=np.float32)


def _doan(im_dau: float, tieng: float, im_cuoi: float, muc: float = 0.2):
    return np.concatenate([_im(im_dau), _tieng(tieng, muc), _im(im_cuoi)])


# ── trần ─────────────────────────────────────────────────────────────────────

def test_hai_tran_la_hai_hang_so_khac_nhau():
    """🔴 Gộp hai trần làm một là nguyên nhân gốc của việc văn bản dài bị TỪ CHỐI.

    `TRAN_MOI_LUOT_SINH` là "model đọc liền được bao nhiêu"; `TRAN_KY_TU_CONG_KHAI`
    là "khách gửi được bao nhiêu trong một lần". Một con số cho hai câu hỏi nghĩa
    là nới cái này bắt buộc nới cái kia — và một trong hai lần nới đó sẽ sai.
    """
    from apps.ltt_voice import tham_so_cong_khai as t

    assert hasattr(t, "TRAN_MOI_LUOT_SINH")
    assert hasattr(t, "TRAN_KY_TU_CONG_KHAI")
    assert t.TRAN_KY_TU_CONG_KHAI >= t.TRAN_MOI_LUOT_SINH, (
        "tran cua mot YEU CAU khong the nho hon tran cua mot LUOT SINH — "
        "nhu the thi khong yeu cau nao dung mot luot tron ven")


def test_van_ban_dai_duoc_chia_chu_khong_bi_tu_choi():
    from apps.ltt_voice import features
    from apps.ltt_voice.tham_so_cong_khai import TRAN_MOI_LUOT_SINH

    cau = "Đây là một câu thử có độ dài vừa phải để chia đoạn. "
    dai = cau * 120                       # ~6.000 ký tự
    yc = features.chuan_hoa({"text": dai})
    kq = features.chuan_bi_van_ban(yc, tran_moi_doan=TRAN_MOI_LUOT_SINH)

    assert len(kq.doan) > 1, "van ban 6.000 ky tu phai duoc chia thanh nhieu doan"
    assert all(len(d) <= TRAN_MOI_LUOT_SINH for d in kq.doan), (
        "moi doan phai lot tran mot luot sinh, neu khong cong se tra 413")
    # Không mất chữ: ghép các đoạn lại phải phủ hết nội dung đã chuẩn hoá.
    assert sum(len(d) for d in kq.doan) >= len(kq.da_chuan_hoa) * 0.98


# ── ghép ─────────────────────────────────────────────────────────────────────

def test_ghep_mot_doan_khong_dong_gi():
    from voice_sidecar import noi_dai

    w = _doan(0.2, 1.0, 0.3)
    ra, ho_so = noi_dai.ghep([w], SR)
    assert ho_so["so_doan"] == 1
    assert np.array_equal(ra, w), "mot doan thi khong co moi noi nao de sua"


def test_ghep_cat_im_hai_dau_nen_moi_noi_khong_bi_im_gap_doi():
    from voice_sidecar import noi_dai

    # Mỗi đoạn mang 0,5s im cuối + 0,5s im đầu -> nối thẳng là 1,0s im ở mối nối.
    ds = [_doan(0.5, 1.0, 0.5) for _ in range(3)]
    ra, ho_so = noi_dai.ghep(ds, SR)

    assert ho_so["so_doan"] == 3
    tho = sum(len(w) for w in ds) / SR
    assert len(ra) / SR < tho, (
        "ban ghep phai NGAN hon tong tho — im o moi noi da bi cat")

    # Khoảng lặng dài nhất trong bản ghép phải là nhịp nghỉ đã chọn, không phải
    # tổng hai khoảng im cộng lại.
    lang = noi_dai.khoang_lang_giua(ra, SR)
    if lang:
        assert max(lang) <= ho_so["nghi_s"] + 0.05, (
            f"con mot khoang lang {max(lang):.3f}s > nhip nghi "
            f"{ho_so['nghi_s']}s — im o moi noi chua bi cat het")


def test_nhip_nghi_lay_RANH_GIOI_CAU_chu_khong_phai_khe_tu():
    """🔴 Trung vị MỌI khoảng lặng là sai, và sai rất xa.

    ĐO THẬT 31/08/2026: bản 2.907 ký tự có **214** khoảng lặng giữa, trung vị
    **0,04 giây** — đó là khe giữa hai TỪ, không phải nghỉ giữa hai CÂU. Đặt
    0,04 s ở mối nối là nối gần như dính liền.

    Phép kiểm dựng đúng hình dạng đó: mỗi đoạn có hai câu (một ranh giới 0,40s)
    và **rất nhiều** khe từ 40 ms. Trung vị toàn bộ sẽ ra ~0,04; chỉ cách lấy
    `S − 1` khoảng dài nhất mới ra 0,40.
    """
    from voice_sidecar import noi_dai

    def hai_cau():
        manh = [_tieng(0.25)]
        for _ in range(8):                       # khe TU, 40 ms
            manh += [_im(0.04), _tieng(0.25)]
        manh += [_im(0.40)]                      # ranh gioi CAU
        manh += [_tieng(0.25)]
        for _ in range(8):
            manh += [_im(0.04), _tieng(0.25)]
        return np.concatenate(manh)

    ds = [hai_cau() for _ in range(3)]

    nghi, nguon = noi_dai.nhip_nghi(ds, SR, so_cau=[2, 2, 2])
    assert abs(nghi - 0.40) < 0.08, (
        f"do duoc {nghi:.3f}s, mong doi ~0.40 — dang lay nham khe tu")
    assert "ranh gioi cau" in nguon

    # Không biết số câu -> ước thô, và PHẢI tự khai là ước thô.
    nghi2, nguon2 = noi_dai.nhip_nghi(ds, SR)
    assert "UOC THO" in nguon2
    assert nghi2 == noi_dai.NGHI_LUI_S, (
        "uoc tho ra ~0,04s, ngan hon loi lui — phai dung loi lui chu khong "
        "dung mot con so chac chan sai")

    # Không có khoảng lặng giữa nào -> phải LUI, và phải NÓI là đã lui.
    nghi2, nguon2 = noi_dai.nhip_nghi([_tieng(1.0), _tieng(1.0)], SR)
    assert nghi2 == noi_dai.NGHI_LUI_S
    assert "lui" in nguon2, (
        "mot con so mac dinh trong giong het mot con so do duoc neu khong ai "
        "ghi lai no den tu dau")


def test_nhip_nghi_bi_kep_khi_ban_doc_co_quang_nghi_rat_dai():
    from voice_sidecar import noi_dai

    dai = np.concatenate([_tieng(0.5), _im(2.0), _tieng(0.5)])
    nghi, nguon = noi_dai.nhip_nghi([dai], SR)
    assert nghi == noi_dai.NGHI_TOI_DA_S
    assert "kep" in nguon


def test_can_do_to_keo_doan_lech_ve_gan_trung_vi():
    from voice_sidecar import noi_dai

    ds = [_doan(0.1, 1.0, 0.1, muc=0.20),
          _doan(0.1, 1.0, 0.1, muc=0.20),
          _doan(0.1, 1.0, 0.1, muc=0.14)]        # thấp hơn ~3,1 dB
    ra, chinh = noi_dai.can_do_to(ds, SR)

    assert chinh[2] > 0, "doan nho tieng phai duoc keo len"
    assert abs(chinh[0]) < 0.5 and abs(chinh[1]) < 0.5, (
        "hai doan dung muc trung vi thi gan nhu khong bi dong")
    assert all(abs(c) <= noi_dai.KEP_CHINH_DB + 1e-6 for c in chinh)


def test_can_do_to_khong_san_phang_mot_doan_co_y_nho_tieng():
    """⛔ Kẹp ±3 dB là để KHÔNG sửa thứ model cố ý làm."""
    from voice_sidecar import noi_dai

    ds = [_doan(0.1, 1.0, 0.1, muc=0.20),
          _doan(0.1, 1.0, 0.1, muc=0.20),
          _doan(0.1, 1.0, 0.1, muc=0.02)]        # thì thầm: thấp ~20 dB
    _, chinh = noi_dai.can_do_to(ds, SR)
    assert chinh[2] == pytest.approx(noi_dai.KEP_CHINH_DB), (
        "phai DUNG o vach kep, khong keo doan thi tham len bang phan con lai")


def test_ghep_bo_qua_doan_rong_ma_khong_no():
    from voice_sidecar import noi_dai

    ra, ho_so = noi_dai.ghep([_doan(0.1, 0.6, 0.1), np.zeros(0, np.float32)], SR)
    assert ho_so["so_doan"] == 1
    assert len(ra) > 0


def test_ghep_khong_bao_gio_vuot_tran_dinh_that():
    """🔴 Phép cân độ to có thể đẩy đỉnh vượt trần — bản ghép phải tự hạ lại.

    ĐO THẬT 31/08/2026: bản 4.920 ký tự (4 đoạn) ra **−0,65 dBTP**, vượt trần
    EBU R128 (−1,0), trong khi bản một đoạn cùng ngày là −1,10. Lỗi **không**
    lộ ra ở bản ngắn: một đoạn thì không có gì để cân, nên nó chỉ xuất hiện
    đúng ở cấu hình vừa mới xây — tức đúng chỗ chưa ai nhìn.
    """
    from voice_sidecar import noi_dai

    # Ba đoạn to gần trần + một đoạn nhỏ hơn ~3 dB (sẽ bị kéo lên kịch kẹp).
    ds = [_doan(0.1, 1.0, 0.1, muc=0.30) for _ in range(3)]
    ds.append(_doan(0.1, 1.0, 0.1, muc=0.21))
    for w in ds:                       # đẩy đỉnh sát trần
        w *= 0.85 / max(1e-9, float(np.max(np.abs(w))))

    ra, ho_so = noi_dai.ghep(ds, SR)
    tp = noi_dai.dinh_that(ra)
    assert tp <= noi_dai.TRAN_TRUE_PEAK_DBTP + 1e-6, (
        f"ban ghep ra {tp:.2f} dBTP, vuot tran "
        f"{noi_dai.TRAN_TRUE_PEAK_DBTP} — nguoi nghe se vo tieng o bo chuyen doi")
    assert "ha_tran_db" in ho_so, "phai KHAI da ha bao nhieu, khong ha am tham"


def test_ha_tran_giu_nguyen_tuong_quan_giua_cac_doan():
    """Hạ trần là hạ ĐỀU cả bản — không nén, không kẹp từng đoạn.

    Nén hay kẹp sẽ tạo méo mới đúng ở chỗ ồn nhất, và nó xoá luôn kết quả của
    phép cân độ to vừa làm ở bước trước.
    """
    from voice_sidecar import noi_dai

    ds = [_doan(0.1, 1.0, 0.1, muc=0.30), _doan(0.1, 1.0, 0.1, muc=0.30)]
    for w in ds:
        w *= 0.95 / max(1e-9, float(np.max(np.abs(w))))

    ra, ho_so = noi_dai.ghep(ds, SR)
    # ⛔ KHÔNG `pytest.skip` ở đây. Hai đoạn ở 0,95 đỉnh thì bản ghép **luôn**
    #    vượt trần, nên một nhánh bỏ qua ở đây là mã chết — và một test bị bỏ
    #    qua là một test không canh gì cả. Khẳng định thẳng rằng nó đã hạ.
    assert ho_so["ha_tran_db"] < 0, (
        f"lo nay phai cham tran (dinh truoc {ho_so.get('dinh_truoc_dbtp')} dBTP) "
        f"nhung `ha_tran_db` = {ho_so.get('ha_tran_db')} — phep kiem duoi day "
        f"se khong kiem gi ca")

    # Tỉ lệ RMS giữa nửa đầu và nửa sau phải gần như không đổi sau khi hạ.
    giua = len(ra) // 2
    ti = float(np.sqrt((ra[:giua].astype(np.float64) ** 2).mean())
               / max(1e-12, np.sqrt((ra[giua:].astype(np.float64) ** 2).mean())))
    assert 0.8 < ti < 1.25, (
        f"ti le RMS hai nua = {ti:.3f} — ha tran da lam meo tuong quan, "
        "gan nhu chac chan la da nen chu khong ha deu")


# ── giãn cách chờ tài nguyên ─────────────────────────────────────────────────

def test_gian_cach_cho_tai_nguyen_khai_theo_app():
    """🔴 Một hằng số toàn cục không phục vụ được cả job 5 giây lẫn job 5 phút.

    ĐO THẬT 31/08/2026, năm job LTT VOICE đồng thời trên một suất:

        làm việc thật : 4,75 – 5,42 giây  (ổn định, không chậm đi khi tải lên)
        xếp hàng      : 0,07 → 20,2 → 40,8 → 61,2 → 82,0 giây

    Bậc 20 giây **không phải** thời gian job trước chiếm GPU — nó nhả sau ~5
    giây. Đó là `GPU_RETRY_DELAY_S`: thời gian job sau chưa quay lại hỏi. GPU
    nằm không ~15 trong mỗi 20 giây, tức mất 75 % thông lượng — và mất ở chỗ
    không ai nhìn, vì mọi job vẫn `done` và vẫn đúng tiền.
    """
    from platform_core.job_runner import GPU_RETRY_DELAY_S, _cho_tai_nguyen
    from platform_core.registry import discover

    mf = next(i.manifest for i in discover() if i.manifest.slug == "ltt_voice")

    for jt in ("ltt_voice.synthesize", "ltt_voice.enroll"):
        khai = mf.cho_tai_nguyen_for(jt, default=GPU_RETRY_DELAY_S)
        assert khai < GPU_RETRY_DELAY_S, (
            f"{jt} khai {khai}s, khong nho hon mac dinh {GPU_RETRY_DELAY_S}s — "
            f"job nay lam viec ~5 giay nen 20 giay la lang phi")
        assert khai >= 2, (
            f"{jt} khai {khai}s: qua day. Moi luot hoi la mot vong CSDL; "
            f"1 giay bien hang doi thanh mot vong lap ban")
        assert _cho_tai_nguyen(jt) == khai, (
            "`job_runner` khong doc khai bao cua app — bo sung hop dong nay "
            "khong co tac dung gi")


def test_app_khong_khai_thi_giu_nguyen_mac_dinh_nen_tang():
    """⛔ Bổ sung hợp đồng phải TƯƠNG THÍCH NGƯỢC.

    App cũ không khai `cho_tai_nguyen_s` phải giữ đúng hành vi 20 giây như
    trước. Một "cải tiến" đổi ngầm hành vi của mọi app khác là một hồi quy.
    """
    from platform_core.job_runner import GPU_RETRY_DELAY_S, _cho_tai_nguyen
    from platform_core.registry import AppManifest, discover

    trong = AppManifest(slug="x", display_name="x", route_prefix="/x")
    assert trong.cho_tai_nguyen_for("x.y", default=GPU_RETRY_DELAY_S) == GPU_RETRY_DELAY_S

    khong_khai = [i.manifest for i in discover()
                  if not i.error and not i.manifest.cho_tai_nguyen_s
                  and i.manifest.job_types]
    assert khong_khai, "khong con app nao chua khai — phep kiem het nghia"
    jt = khong_khai[0].job_types[0]
    assert _cho_tai_nguyen(jt) == GPU_RETRY_DELAY_S, (
        f"{jt} khong khai gi ma bi doi giãn cách — do la mot hoi quy")
