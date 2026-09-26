# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.
"""M-02 CHO NOI — `giai_doan_qc_ai` THUC SU hoi VLM ve tung cho noi cua BAN RA.

🔑 `test_2120` goi thang `qc_ai.cac_cho_noi` / `qc_ai.doc_hinh` voi tham so
   tuong minh; no khong chung minh rang GIAI DOAN truyen chung vao. Va do dung
   la hinh dang cua M-02: ba manh (`loi_nhac_hinh`, `doc_hinh`, `tu_qc_hinh`)
   deu co test xanh tu pha 19, deu **khong co nguoi goi**, va bao cao pha 19 goi
   dung ten no — *"The repair loop is planned, not yet driven."*

⇒ Bai nay chay HET CHUOI voi `LTT_ASV_QC_AI=1` roi doc bao cao da luu. Mot
  `so_cho_noi: 0` hay mot `khong_kha_dung` o preset CAT la mot phep do chet
  lang le, va no phai lam bai nay DO.
"""
from __future__ import annotations

import json

import pytest

from apps.auto_scan_video import (features, giai_doan_qc_ai as gdqa,
                                  pipeline, qc_ai)
from platform_core.storage import get_storage
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests.test_402_asv_mach_doc_gia import (_chay_het_hang_doi, _tao_run,  # noqa: F401
                                             asr_gia, db, dich_gia, giong_gia,
                                             kho_tam)
from tests.test_440_asv_v4_long_tieng import _cat_canh_le, _nhieu_canh, _run_cat


#: 🔴 **Do dai NGUON toi thieu de mot CHO NOI co the ton tai** (b4, 25/09).
#:
#:    Tu khi phep cat chuyen xuong giai doan 2, `ke_cat` ap hai luat cung:
#:
#:        TRAN_CAT_TI_LE  = 0,05   cat khong qua 5 % tong do dai
#:        TOI_THIEU_GIAY  = 0,20   ngan hon the thi khong dang mot cho noi
#:
#:    ⇒ Mau 3 giay mac dinh cho ngan sach cat 0,15 s — DUOI muc toi thieu, nen
#:      tren no ⛔ khong mot cho noi nao co the ton tai. Voi canh 1 giay
#:      (`_nhieu_canh`), nguon phai dai >= 20 giay de mot canh cat duoc.
#:
#: ⭐ 24 giay: ngan sach 1,2 s ⇒ nhan DUNG mot canh 1 giay, va khai ra phan con
#:    lai. `ban_ghi_gia()` chi sinh thoai trong [0; 2,8) nen moi canh tu giay 3
#:    tro di ⛔ khong co loi thoai — dung luat *"CHI cat vung khong co thoai"*.
#:
#: ⛔ ⛔ KHONG noi tran de mau 3 giay vua: vuot tran la tin hieu tieu chi sai,
#:    ⛔ khong phai rang tran chat (chu du an chot 25/09).
NGUON_CO_CHO_NOI_S = 24.0


@pytest.fixture()
def bat_qc_ai(monkeypatch):
    monkeypatch.setenv(gdqa.BIEN_BAT, "1")


def _bao_cao(phien, run) -> dict:
    gd = features.giai_doan_theo_ten(phien, run.id, pipeline.QC_AI)
    assert gd is not None and gd.status == "succeeded", (
        "qc_ai: %s %s" % (getattr(gd, "status", None), getattr(gd, "error", "")))
    khoa = next(k for k in (gd.outputs or {}).get("khoa_asset") or []
                if k.endswith(".json"))
    with get_storage().open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def test_preset_CAT_hoi_VLM_ve_TUNG_cho_noi_cua_ban_ra(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia,
        bat_qc_ai):
    """🔴 **Bai nay la cai M-02 thieu.** Mot `so_cho_noi: 0` o preset CAT nghia
    la lop QC hinh dang chay ma khong nhin gi — dung trang thai truoc 23/09,
    chi khac la nay no co ten."""
    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)
    run = _run_cat(db, kho_tam, tmp_path, duration_s=NGUON_CO_CHO_NOI_S)
    _chay_het_hang_doi(db)
    db.expire_all()

    bc = _bao_cao(db, run)
    tt = bc["hinh_tom_tat"]
    assert "khong_kha_dung" not in tt, tt
    assert tt["so_cho_noi"] > 0, "preset CAT ma khong co cho noi nao de soat"
    # ⭐ Bat bien: moi cho noi hoac co phan quyet, hoac co mot dong ly do.
    assert tt["du_phu"] is True, tt
    assert tt["so_co_phan_quyet"] == tt["so_cho_noi"], tt

    # Moi phan quyet phai mang DU thu de doi chieu lai: moc tren ban ra, canh bi
    # bo (don vi sua), va so khung DA THUC SU gui di.
    assert len(bc["hinh"]) == tt["so_cho_noi"]
    for pq in bc["hinh"]:
        assert pq["so_khung"] == qc_ai.KHUNG_MOI_CHO_NOI, pq
        assert pq["moc_giay"] >= 0.0
        assert pq["ma_cat"], "cho noi khong doi nguoc ra canh nao — khong sua duoc"
        assert pq["ma_canh"] in pq["ma_cat"]
        assert 0.0 <= pq["do_tin"] <= 1.0


def test_preset_GIU_HINH_KHONG_hoi_cau_nao_va_NOI_RO_vi_sao(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia, bat_qc_ai):
    """⭐ Khong canh nao bi cat ⇒ khong cho noi nao ⇒ khong mot dong token.

    ⛔ Nhung bao cao phai NOI RA dieu do. Mot `so_cho_noi: 0` khong kem ly do
       doc giong het mot lan chay da soat va khong thay gi.
    """
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    tt = _bao_cao(db, run)["hinh_tom_tat"]
    assert tt["so_cho_noi"] == 0
    assert tt["ly_do"], "so_cho_noi = 0 ma khong noi vi sao"


def test_phan_quyet_hinh_di_toi_stage_outputs_cho_vong_sua(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia,
        bat_qc_ai):
    """🔑 `jobs._qc_hinh` doc `stage.outputs`, KHONG mo kho — `_advance` chay o
    moi luot cua moi lan chay. Khoa phai co mat ke ca khi rong."""
    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)
    run = _run_cat(db, kho_tam, tmp_path, duration_s=NGUON_CO_CHO_NOI_S)
    _chay_het_hang_doi(db)
    db.expire_all()

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.QC_AI)
    o = gd.outputs or {}
    assert "qc_hinh_khong_dat" in o
    assert o["qc_hinh_la_tu_van"] is True
    assert o["qc_hinh_so_cho_noi"] > 0

    from apps.auto_scan_video.jobs import _qc_hinh
    theo_ten = {s.stage: s for s in features.cac_giai_doan(db, run)}
    assert _qc_hinh(theo_ten) == o["qc_hinh_khong_dat"]


def test_cho_noi_HONG_van_ve_run_DONE_chu_khong_giet_lan_chay(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia,
        bat_qc_ai):
    """⛔ Mot lop QC CHU QUAN khong duoc giet mot lan chay. `qc` (tat dinh) moi
    la cong phat hanh; neu `_soat_hinh` nem thi mot model dong bong lam hong
    mot ban ra da qua het muoi tam dung sai."""
    from apps.auto_scan_video import ai

    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)

    goc = ai.goi_tinh_tien

    def hong(db_, run_, thao_tac, messages, **kw):
        if thao_tac.ma == ai.QC_HINH.ma:
            raise ai.AiError("gia lap: may B tu choi")
        return goc(db_, run_, thao_tac, messages, **kw)

    monkeypatch.setattr(ai, "goi_tinh_tien", hong)
    monkeypatch.setattr(gdqa.ai, "goi_tinh_tien", hong, raising=False)

    run = _run_cat(db, kho_tam, tmp_path, duration_s=NGUON_CO_CHO_NOI_S)
    _chay_het_hang_doi(db)
    db.expire_all()

    tt = _bao_cao(db, run)["hinh_tom_tat"]
    assert tt["so_co_phan_quyet"] == 0
    assert tt["so_hong"] == tt["so_cho_noi"] > 0
    # ⭐ Va bat bien do phu VAN dung: khong cho noi nao bien mat khong dau vet.
    assert tt["du_phu"] is True
    assert features.giai_doan_theo_ten(db, run.id, pipeline.QC_AI).status \
        == "succeeded"


def test_thieu_mot_khung_thi_KHONG_HOI_chu_khong_hoi_bang_mot_anh(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia,
        bat_qc_ai):
    """🔴 Mot chuyen tiep khong nhin duoc tu MOT phia.

    `canh.rut_khung` chiu duoc mot khung hong vi nguoi goi dau tien cua no
    (`doc_canh`) mo ta MOT canh. O day thi khong: hoi bang mot buc anh se cho
    ra mot phan quyet **trong nhu that** ve mot chuyen tiep model chua nhin
    thay. Phai ra `thieu_khung`, khong ra `dat=true`.
    """
    from apps.auto_scan_video import canh as canh_mod

    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)
    # `_soat_hinh` nhap `canh` ben trong ham, nen va tren chinh MODULE la du
    # — va do la cach va dung: khong co ban sao thu hai nao de sot.
    goc = canh_mod.rut_khung
    monkeypatch.setattr(canh_mod, "rut_khung",
                        lambda duong, moc, **kw: goc(duong, list(moc)[:1], **kw))

    run = _run_cat(db, kho_tam, tmp_path, duration_s=NGUON_CO_CHO_NOI_S)
    _chay_het_hang_doi(db)
    db.expire_all()

    tt = _bao_cao(db, run)["hinh_tom_tat"]
    assert tt["so_co_phan_quyet"] == 0, "hoi bang MOT anh ve mot chuyen tiep"
    assert tt["so_hong"] == tt["so_cho_noi"] > 0
    assert tt["du_phu"] is True


def test_cho_noi_HONG_sinh_vong_sua_NHAM_DUNG_CHO_va_CO_TRAN(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia,
        bat_qc_ai):
    """🔴 **Nửa thứ hai của M-02: vòng sửa có nhắm đúng chỗ, và có trần không.**

    Bật cờ gate (⛔ **chỉ trong bài này** — sản phẩm vẫn tư vấn; `test_2120` §4
    chốt mặc định), rồi cho model chấm **mọi** chỗ nối là hỏng. Đó là trường hợp
    tệ nhất có thật: một chỗ nối hỏng **không sửa được** (hai cảnh hai bên vốn là
    hai cảnh khác nhau) thì mọi vòng sửa đều cho ra đúng phán quyết cũ.

    Hai mệnh đề, và cả hai đo được từ SỔ CÁI:
      1. vòng sửa **nhắm đúng** `edit_plan`, với đúng mã cảnh — không phải một
         lần chạy lại mù;
      2. nó chạy **đúng một** vòng (`VONG_SUA_TOI_DA`) rồi thôi — không quay.

    ⚠️ Bài này **không** chốt `run.status == "done"`. Lý do là một khiếm khuyết
       KHÁC, có trước và không liên quan tới M-02: xem `M-09` trong `LOI_TONG.md`
       — mọi vòng sửa chạy lại `voice_synthesis` đều chết vì `database is
       locked`. Đối chứng: ép `qc_ngu_nghia` chấm hỏng (đường `dich_sai`, có từ
       M-01, không đụng gì tới làn này) cho ra **đúng cùng một lỗi**. Chốt
       `done` ở đây sẽ là chốt một mệnh đề của làn khác vào một bài của làn này.
    """
    from apps.auto_scan_video import ai, jobs, su_dung, sua_chua as sc

    monkeypatch.setattr(sc, "QC_HINH_LA_TU_VAN", False)
    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)

    goc = ai.goi_tinh_tien
    # 🔑 Ghi lai MOI luot goi: `(thao tac, item_key)`. Day la cach duy nhat o
    #    khuon thu nay de chung minh vong sua **hoi lai that** — khuon dung ban
    #    gia cua `goi_tinh_tien` nen khong co dong so cai nao cho `edit_plan`.
    da_goi: list[tuple[str, str]] = []

    def moi_cho_noi_deu_hong(db_, run_, thao_tac, messages, **kw):
        da_goi.append((thao_tac.ma, str(kw.get("item_key") or "")))
        if thao_tac.ma == ai.QC_HINH.ma:
            return {"noi_dung": json.dumps(
                {"dat": False, "do_tin": 0.95,
                 "ly_do": "cat giua mot dong tac"}, ensure_ascii=False),
                "provider": "gia", "model": "gia", "su_dung": None,
                "finish_reason": "stop", "suy_nghi": ""}
        return goc(db_, run_, thao_tac, messages, **kw)

    monkeypatch.setattr(ai, "goi_tinh_tien", moi_cho_noi_deu_hong)
    monkeypatch.setattr(gdqa.ai, "goi_tinh_tien", moi_cho_noi_deu_hong,
                        raising=False)

    run = _run_cat(db, kho_tam, tmp_path, duration_s=NGUON_CO_CHO_NOI_S)
    so_job = _chay_het_hang_doi(db)
    db.expire_all()

    # (2) CO TRAN — dem bang SO CAI (`UNIQUE(run_id, ma_dispatch)`), khong bang
    #     mot bien trong bo nho: mot bien khong song qua mot lan worker chet, va
    #     hai luot `advance` chay chong nhau co the cung tang no.
    vong = [d for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                        item_key=jobs.DON_VI_SUA)
            if d.nang_luc == jobs.NANG_LUC_VONG_SUA]
    assert len(vong) == 1 == sc.VONG_SUA_TOI_DA
    # ...va khuon thu co tran 200 job. Cham tran do la dau hieu cua mot vong
    #    quay, chu khong phai mot lan chay dai.
    assert so_job < 200, "vong sua quay: cham tran job cua chinh khuon thu"

    # (1) NHAM DUNG CHO: `cat_sai` -> `edit_plan`, mang MA CANH that, va KHONG
    #     keo theo mot giai doan nao khac vao ke hoach sua.
    ke = dict(vong[0].ghi_chu or {})
    assert list(ke["giai_doan_sua"]) == ["edit_plan"], ke["giai_doan_sua"]
    ma_canh = ke["giai_doan_sua"]["edit_plan"]
    assert ma_canh and all(m.startswith("canh_") for m in ma_canh), ma_canh
    assert {k["loai"] for k in ke["khiem_khuyet"]} == {sc.CAT_SAI}

    # 🔴 **26/09/2026 — MENH DE THU BA DOI CHIEU, va no la mot SU THAT SAN PHAM
    #    phai duoc noi ra chu khong duoc de im.**
    #
    #    Ban cu chot: *vong sua da HOI LAI THAT* — mot but toan `doc_canh` mang
    #    hau to `:sua1` chung minh mot luot goi VLM MOI da xay ra cho dung canh
    #    do, voi mot cau KHAC (muoi vong sua trong van tay), vi hoi y nguyen cau
    #    cu thi model tra loi y nhu cu (M-07 cua duong GIONG).
    #
    # ⭐ Tu 26/09 `edit_plan` phan quyet bang **phep do tat dinh** (B1 §9b), nen:
    #      · ⛔ KHONG con luot goi nao — `doc_canh` phai RONG;
    #      · ⛔ KHONG con don vi tinh tien theo canh;
    #      · va vong sua `cat_sai` cho ra **DUNG phan quyet cu** — tat dinh nghia
    #        la cung dau vao cho cung ket qua.
    #
    # ⚠️ **Tuc vong sua `cat_sai` nay hom nay la MOT VONG VO HIEU QUA.** Do la he
    #    qua truc tiep cua §9b (*"tat dinh thang khon, vi cat la thao tac KHONG
    #    DAO DUOC tren ban giao khach"*) — mot y kien khac cho cung mot video la
    #    dung thu khong ai giai thich duoc cho khach. Cai vong nay chi lay lai
    #    y nghia neu sau nay co mot nac VLM **tuy chon** (§9b, doan cuoi).
    doc_canh = {k for t, k in da_goi if t == ai.DOC_CANH.ma}
    assert doc_canh == set(), (
        f"edit_plan lai goi VLM: {sorted(doc_canh)} — xem test_3912 §1")

    from apps.auto_scan_video import features
    for m in ma_canh:
        assert features.don_vi_theo_khoa(db, run.id, pipeline.EDIT_PLAN,
                                         m) is None, (
            "edit_plan lai mo don vi tinh tien theo canh")


def test_lat_cat_vong_HINH_nhuong_roi_NOI_TIEP_khong_hoi_lai(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia,
        bat_qc_ai):
    """🔑 **Vòng hình là một vòng lặp model DÀI — nó phải đi qua `lat_cat`.**

    Một phim 120 phút cho hàng trăm chỗ nối × ~22 s/chỗ nối (đo thật) ⇒ không
    vừa một job. `lat_cat` nhường trước khi chạm trần rồi nối tiếp bằng job
    mới; điều kiện đúng đắn là **mỗi chỗ nối chỉ được hỏi MỘT lần** qua tất cả
    các lượt, vì mỗi lần hỏi là một lần trả tiền.

    ⛔ Và hai vòng (nghĩa + hình) dùng **CHUNG một con trỏ**: lô nghĩa chiếm
       `0..so_lo-1`, chỗ nối hình chiếm `so_lo..`. Bài này ép trần nhỏ để con
       trỏ phải đi qua ranh giới đó.
    """
    from apps.auto_scan_video import ai, canh as canh_mod, features, lat_cat

    # 🔴 **BAY canh KHONG DEU NHAU — va su khong deu ay la do TRAN 5 %.**
    #
    #    Ban truoc dung bay canh DEU: `_cat_canh_le` bo canh chi so LE nen bon
    #    canh duoc giu, khong lien nhau => BA cho noi. Tu b4 (25/09) phep cat
    #    phai lot qua `ke_cat.TRAN_CAT_TI_LE` = 5 %, va bay canh DEU ⛔ khong the:
    #
    #        n canh deu, moi canh T/n; nhan k canh  =>  k·T/n <= 0,05·T
    #        <=>  k <= 0,05·n         (⛔ do dai nguon TRIET TIEU — n moi quyet)
    #
    #    ⇒ Ba cho noi doi n >= 60 canh, va 60 canh lam khuon nay tran 200 job
    #      (moi canh mot loi goi `DOC_CANH`, cong vong nhuong cua dong ho gia).
    #
    # ⭐ Loi giai la canh KHONG DEU — va do cung la hinh dang THAT: canh bi de
    #    nghi bo thuong la canh **ngan** (chuyen canh, hieu ung, khung den). Ba
    #    canh CAT dai 0,3 s (>= `TOI_THIEU_GIAY`), tong 0,9 s <= ngan sach 1,2 s.
    #    Bon canh GIU chia phan con lai.
    #
    # ⛔ ⛔ KHONG noi tran de bay canh deu vua: vuot tran la tin hieu tieu chi sai
    #    (chu du an chot 25/09), va mot bai kiem noi tran de xanh la mot bai kiem
    #    do mot san pham KHAC voi san pham dang chay.
    CAT_S = 0.3

    def bay_canh(duong, *, thoi_luong, hoi_huy=None, **kw):
        t = float(thoi_luong)
        # 7 canh: chi so LE bi `_cat_canh_le` cat => ba canh ngan.
        giu_s = (t - 3 * CAT_S) / 4.0
        moc, ds = 0.0, []
        for i in range(7):
            dai = CAT_S if i % 2 else giu_s
            ket = min(t, moc + dai)
            ds.append(canh_mod.Canh("canh_%04d" % (i + 1), moc, ket,
                                    ((moc + ket) / 2.0,)))
            moc = ket
        return canh_mod.ChiMucCanh(tuple(ds), t)

    monkeypatch.setattr(canh_mod, "phan_tich", bay_canh)
    from apps.auto_scan_video import giai_doan_ban_bien_tap as _gdbbt
    monkeypatch.setattr(_gdbbt.canh_mod, "phan_tich", bay_canh, raising=False)
    _cat_canh_le(monkeypatch)

    # Đồng hồ giả: mỗi lượt gọi model "tốn" 200 s, trần `qc_ai` ép còn 600 s.
    gio = {"t": 1000.0}
    monkeypatch.setattr(lat_cat, "dong_ho", lambda: gio["t"])
    that = lat_cat.tran_giai_doan
    monkeypatch.setattr(
        lat_cat, "tran_giai_doan",
        lambda ten: 600 if ten == pipeline.QC_AI else that(ten))

    goc = ai.goi_tinh_tien
    da_goi: list[str] = []

    def dem(db_, run_, thao_tac, messages, **kw):
        if thao_tac.ma in (ai.QC_HINH.ma, ai.QC_NGU_NGHIA.ma):
            gio["t"] += 200.0
            da_goi.append(f"{thao_tac.ma}:{kw.get('item_key')}")
        return goc(db_, run_, thao_tac, messages, **kw)

    monkeypatch.setattr(ai, "goi_tinh_tien", dem)
    monkeypatch.setattr(gdqa.ai, "goi_tinh_tien", dem, raising=False)

    run = _run_cat(db, kho_tam, tmp_path, duration_s=NGUON_CO_CHO_NOI_S)
    _chay_het_hang_doi(db)
    db.expire_all()

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.QC_AI)
    assert gd.status == "succeeded", (gd.status, gd.error)

    # 🔴 **Phải THỰC SỰ đã nhường ít nhất một lần** — nếu không, bài này xanh
    #    mà không đo gì (trần ép quá rộng, hoặc con trỏ không được dùng).
    hinh = [k for k in da_goi if k.startswith(ai.QC_HINH.ma)]
    assert len(hinh) >= 2, da_goi
    tt = _bao_cao(db, run)["hinh_tom_tat"]
    assert tt["so_co_phan_quyet"] == len(hinh)

    # ⛔ MỖI chỗ nối đúng MỘT lần hỏi, qua tất cả các lượt nối tiếp. Đây là
    #    mệnh đề đắt nhất: hỏi lại một chỗ nối đã hỏi là trả tiền hai lần.
    assert len(set(hinh)) == len(hinh), sorted(hinh)
    hop_le = {f"{ai.QC_HINH.ma}:hinh_{j:03d}" for j in range(tt["so_cho_noi"])}
    assert set(hinh) <= hop_le, (sorted(hinh), sorted(hop_le))

    # ⚠️ **Bất biến độ phủ vẫn đúng qua nhiều lượt**: mỗi chỗ nối hoặc có phán
    #    quyết, hoặc có một dòng lý do. (Phim mẫu của khuôn thử dài 3 s nên chỗ
    #    nối cuối nằm sát cuối bản ra và `ffmpeg` không rút đủ hai khung — đúng
    #    theo luật "một chuyển tiếp không nhìn được từ MỘT phía".)
    assert tt["du_phu"] is True, tt
    assert tt["so_co_phan_quyet"] + tt["so_hong"] == tt["so_cho_noi"]
