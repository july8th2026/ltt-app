"""Auto Scan Video V4 — BAN BIEN TAP (EditPlan), pha 12.

**§1 vi tri trong chuoi** — 🔴 **DAO CHIEU 26/09/2026** (B1 §9a): buoc nay xuong
     **GIAI DOAN 2**, chay SAU `render`. Ly do cu (`V4-R07`: *"dung dich nhung
     cau thuoc canh se bi cat"*) het dung khi GD1 giu nguyen hinh va xuat MP4
     full do dai — ⛔ khong con canh nao bi cat trong GD1 de tiet kiem. Cai duoc:
     phan quyet va phep cat dung tren **cung mot dong ho**. Cai gia: tra tien
     tieng cho <= 5 % se bi bo.

**§2 `localize_preserve_picture` KHONG BAO GIO cat** — `THAO_TAC_CHO_PHEP` cua no
     la mot tuple RONG. Do la loi hua san pham, khong phai mot mac dinh mem.

**§3 canh CO LOI THOAI kho bi cat hon** — mot canh khong thoai bi cat nham thi
     khan gia mat mot canh; mot canh co thoai bi cat nham thi **mach truyen dut**
     — nguoi xem nghe mot cau tra loi cho mot cau hoi khong con.

**§4 tat dinh** — cung bang chung => cung ban. Mot ban doi giua hai lan chay tren
     cung du lieu la mot san pham khach khong the giai thich duoc.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import ban_bien_tap as bt, canh as cn, hieu_canh as hc
from apps.auto_scan_video import pipeline
from apps.auto_scan_video.hop_dong_v4 import (PRESET_CAT_THONG_MINH,
                                              PRESET_GIU_HINH, THAO_TAC_CAT,
                                              THAO_TAC_GIU)

GIU_HINH, CAT = PRESET_GIU_HINH, PRESET_CAT_THONG_MINH


def _ci(so=6, dai=10.0) -> cn.ChiMucCanh:
    return cn.ChiMucCanh(
        tuple(cn.Canh(f"canh_{i:04d}", i * dai, (i + 1) * dai) for i in range(so)),
        so * dai)


def _h(i, de_xuat="bo", do_tin=0.9) -> hc.HieuCanh:
    return hc.HieuCanh(f"canh_{i:04d}", de_xuat=de_xuat, do_tin=do_tin)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Vi tri trong chuoi — ban bien tap dung TRUOC moi thu tra tien
# ══════════════════════════════════════════════════════════════════════════════

def test_edit_plan_dung_SAU_render_chu_khong_truoc_content_process():
    """🔴 **26/09/2026 — KY VONG DAO CHIEU** (B1 §9a). Y dinh cu con nguyen o
    `test_doi_ban_KHONG_lam_vo_hieu_ASR_hay_tach_tieng` duoi.

    Ly do CU (`V4-R07`, pha 12): *"dung dich nhung cau thuoc canh se bi cat"*.
    Ly do do **het dung** khi chu du an chot kien truc hai giai doan — GD1 giu
    nguyen hinh va xuat MP4 **full do dai**, nen ⛔ khong con canh nao bi cat
    trong GD1 de tiet kiem.

    ⭐ Va vi tri moi xoa mot LOP LOI: o vi tri cu, buoc nay phan quyet tren truc
       thoi gian NGUON con `ke_cat`/`image_finish` cat tren truc BAN RA. Chay sau
       `render` thi chi con MOT dong ho.

    ⚠️ Cai gia: tra tien tieng cho phan se bi bo, <= 5 % (`ke_cat.TRAN_CAT_TI_LE`).
    """
    ten = [g.ten for g in pipeline.CHUOI]
    assert ten.index(pipeline.EDIT_PLAN) > ten.index(pipeline.CONTENT_PROCESS)
    assert ten.index(pipeline.EDIT_PLAN) > ten.index(pipeline.RENDER)
    assert ten.index(pipeline.EDIT_PLAN) < ten.index(pipeline.IMAGE_FINISH)


def test_edit_plan_phu_thuoc_TRUC_TIEP_vao_render():
    """Khong chi dung sau — phai **an theo**, de dieu phoi vien khong nop no khi
    `render` chua `succeeded`.

    ⭐ Va chieu con lai cung phai dung: `image_finish` an theo `edit_plan`, neu
       khong thi hai buoc nop duoc CUNG LUC va `image_finish` cat 0 khung im lang.
    """
    assert pipeline.RENDER in pipeline.THEO_TEN[pipeline.EDIT_PLAN].sau
    assert pipeline.EDIT_PLAN in pipeline.THEO_TEN[pipeline.IMAGE_FINISH].sau


def test_moi_giai_doan_CAT_deu_o_HA_NGUON_cua_edit_plan():
    """🔴 **26/09 — KY VONG DOI CHIEU.** Y dinh cu: *khong THAO TAC nao an theo
    ban bien tap duoc bat dau truoc khi ban do hop le.*

    O vi tri cu, thu an theo la cac buoc **TRA TIEN** (`content_process`,
    `voice_synthesis`). Tu 26/09 chung dung TRUOC, va thu an theo la cac buoc
    **CAT** — `image_finish` va moi cong chat luong do tep DA CAT.
    """
    ha = set(pipeline.ha_nguon_cua(pipeline.EDIT_PLAN))
    for an_theo in (pipeline.IMAGE_FINISH, pipeline.QC, pipeline.QC_DO_LUONG,
                    pipeline.QC_AI):
        assert an_theo in ha, f"{an_theo} khong an theo ban bien tap"


def test_doi_ban_KHONG_lam_vo_hieu_ASR_hay_tach_tieng():
    """Yeu cau 7: doi ban chi vo hieu HA NGUON, khong dung toi thuong nguon.

    ⭐ Tu 26/09 bat bien nay MANH hon han: ca duong long tieng (`content_process`,
       `voice_synthesis`, `timing_align`, `compose`, `render`) nam THUONG NGUON,
       nen doi ban bien tap ⛔ khong con lam chay lai mot lan tra tien nao.
    """
    ha = set(pipeline.ha_nguon_cua(pipeline.EDIT_PLAN))
    for thuong_nguon in (pipeline.MEDIA_PREPARE, pipeline.AUDIO_PREPARE,
                         pipeline.TRANSCRIBE, pipeline.CONTENT_PROCESS,
                         pipeline.VOICE_SYNTHESIS, pipeline.RENDER):
        assert thuong_nguon not in ha, (
            f"{thuong_nguon} bi vo hieu khi doi ban — do la chay lai mot lan "
            f"da tra tien vi mot quyet dinh hinh anh")


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Giu nguyen hinh: khong bao gio cat
# ══════════════════════════════════════════════════════════════════════════════

def test_giu_hinh_giu_MOI_canh():
    b = bt.lap_ban(preset=GIU_HINH, chi_muc=_ci(8))
    assert len(b.cac_ma_giu) == 8 and b.cac_ma_cat == ()
    assert b.ghi_chu.get("bat_bien_giu_hinh") is True


def test_giu_hinh_KHONG_doc_y_kien_cua_VLM():
    """⛔ Preset nay khong duoc phep cat, nen mot y kien ve viec nen cat gi la
    mot y kien khong duoc dung toi. Doc no se tao mot duong ma mot ban sua sau
    co the vo tinh mo ra."""
    de_nghi_bo_het = [_h(i, "bo", 1.0) for i in range(6)]
    b = bt.lap_ban(preset=GIU_HINH, chi_muc=_ci(6), hieu_canh=de_nghi_bo_het)
    assert b.cac_ma_cat == (), "VLM de nghi bo va preset giu hinh da nghe theo"


def test_ban_giu_hinh_co_canh_bi_cat_thi_bi_TU_CHOI():
    """Chot o `kiem_ban`: neu mot ban sua sau lam ro ri mot thao tac cat vao che
    do nay, no phai do o cho nay chu khong lo ra o ban giao cho khach."""
    b = bt.BanBienTap(GIU_HINH,
                      (bt.QuyetDinh("c1", THAO_TAC_GIU),
                       bt.QuyetDinh("c2", THAO_TAC_CAT)), 20.0,
                      ghi_chu={"ti_le_giu": 0.5})
    with pytest.raises(bt.BanBienTapError):
        bt.kiem_ban(b)


def test_hop_dong_v4_van_cam_moi_thao_tac_o_che_do_giu_hinh():
    from apps.auto_scan_video.hop_dong_v4 import THAO_TAC_CHO_PHEP

    assert THAO_TAC_CHO_PHEP[GIU_HINH] == ()


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Cat thong minh: nguong, va nguong CAO HON cho canh co thoai
# ══════════════════════════════════════════════════════════════════════════════

def test_cat_khi_do_tin_VUOT_nguong():
    b = bt.lap_ban(preset=CAT, chi_muc=_ci(6), hieu_canh=[_h(0, "bo", 0.9)])
    assert b.quyet_dinh[0].thao_tac == THAO_TAC_CAT


def test_KHONG_cat_khi_do_tin_duoi_nguong():
    b = bt.lap_ban(preset=CAT, chi_muc=_ci(6), hieu_canh=[_h(0, "bo", 0.5)])
    assert b.quyet_dinh[0].thao_tac == THAO_TAC_GIU
    assert "duoi nguong" in b.quyet_dinh[0].ly_do


def test_canh_CO_LOI_THOAI_can_do_tin_CAO_HON():
    """🔑 Hai thiet hai khong ngang nhau, nen hai nguong khong duoc ngang nhau."""
    giua = (bt.NGUONG_BO + bt.NGUONG_BO_CO_THOAI) / 2
    assert bt.NGUONG_BO < giua < bt.NGUONG_BO_CO_THOAI

    ci = _ci(6)
    bg = {"doan": [{"bat": 0.0, "ket": 9.0, "chu": "co loi thoai"}]}

    khong_thoai = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=[_h(0, "bo", giua)])
    co_thoai = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=[_h(0, "bo", giua)],
                          ban_ghi=bg)

    assert khong_thoai.quyet_dinh[0].thao_tac == THAO_TAC_CAT
    assert co_thoai.quyet_dinh[0].thao_tac == THAO_TAC_GIU
    assert "loi thoai" in co_thoai.quyet_dinh[0].ly_do


def test_KHONG_co_bang_chung_thi_GIU():
    """⚠️ Cat mot canh ma ta khong co bang chung gi ve no la cat mu."""
    b = bt.lap_ban(preset=CAT, chi_muc=_ci(4), hieu_canh=[])
    assert b.cac_ma_cat == () and len(b.cac_ma_giu) == 4


def test_VLM_khong_chac_thi_GIU():
    b = bt.lap_ban(preset=CAT, chi_muc=_ci(4),
                   hieu_canh=[_h(0, "khong_chac", 0.99)])
    assert b.quyet_dinh[0].thao_tac == THAO_TAC_GIU


# ══════════════════════════════════════════════════════════════════════════════
#  §4  San/tran thoi luong, va khong bao gio video rong
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_bao_gio_cat_SACH():
    """🔴 Khach tra tien cho mot tep khong co gi."""
    b = bt.lap_ban(preset=CAT, chi_muc=_ci(4),
                   hieu_canh=[_h(i, "bo", 1.0) for i in range(4)])
    assert b.cac_ma_giu, "cat sach moi canh"
    bt.kiem_ban(b)


def test_ban_CAT_SACH_bi_tu_choi_ngay_ca_khi_ti_le_bao_sai():
    """🔴 Chot nay chua bao gio la thu CUU ta trong cac mau thu tren — **san giu
    lai** luon ra tay truoc, nen kiem dot bien cho thay go han no di van xanh.

    ⇒ Mau thu nay co y noi doi ve `ti_le_giu` (bao 1.0 trong khi cat sach), de
      chi con chot "khong bao gio cat sach" moi bat duoc. Do dung la tinh huong
      mot loi tinh ti le sai se tao ra — va luc do chot nay la lop cuoi cung
      giua khach va mot tep video rong.
    """
    b = bt.BanBienTap(
        CAT,
        tuple(bt.QuyetDinh(f"c{i}", THAO_TAC_CAT) for i in range(3)),
        30.0, ghi_chu={"ti_le_giu": 1.0})
    with pytest.raises(bt.BanBienTapError) as e:
        bt.kiem_ban(b)
    assert "khong con video" in str(e.value)


def test_giu_lai_it_nhat_bang_SAN():
    b = bt.lap_ban(preset=CAT, chi_muc=_ci(10),
                   hieu_canh=[_h(i, "bo", 1.0) for i in range(10)])
    assert float(b.ghi_chu["ti_le_giu"]) >= bt.SAN_GIU_LAI - 1e-9


def test_hoan_cat_theo_do_tin_THAP_NHAT_truoc():
    """🔑 Giu theo thu tu se giu dau video va cat sach doan cuoi. Neu buoc phai
    giu lai, ta giu nhung canh ma bang chung YEU nhat."""
    ci = _ci(4)
    hieu = [_h(0, "bo", 0.99), _h(1, "bo", 0.98),
            _h(2, "bo", 0.70), _h(3, "bo", 0.97)]
    b = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=hieu)

    # Phai hoan dung canh co do tin thap nhat (canh_0002), khong phai canh dau.
    theo_ma = {q.ma_canh: q for q in b.quyet_dinh}
    assert theo_ma["canh_0002"].thao_tac == THAO_TAC_GIU
    assert "hoan cat" in theo_ma["canh_0002"].ly_do


def test_chi_muc_RONG_bi_tu_choi():
    with pytest.raises(bt.BanBienTapError):
        bt.lap_ban(preset=CAT, chi_muc=cn.ChiMucCanh((), 0.0))


def test_preset_bia_ra_bi_tu_choi():
    with pytest.raises(bt.BanBienTapError):
        bt.lap_ban(preset="mot_preset_khong_co", chi_muc=_ci(3))


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Tat dinh + van tay
# ══════════════════════════════════════════════════════════════════════════════

def test_cung_dau_vao_ra_CUNG_ban():
    ci, hieu = _ci(6), [_h(i, "bo", 0.9) for i in range(3)]
    a = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=hieu)
    b = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=hieu)
    assert a.sang_dict() == b.sang_dict()
    assert a.van_tay() == b.van_tay()


def test_doi_QUYET_DINH_thi_van_tay_DOI():
    ci = _ci(6)
    a = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=[_h(0, "bo", 0.9)])
    b = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=[_h(0, "bo", 0.1)])
    assert a.van_tay() != b.van_tay()


def test_doi_PHIEN_BAN_CHINH_SACH_thi_van_tay_giai_doan_DOI(monkeypatch):
    """⛔ Doi luat cat ma van tay khong doi thi lan chay dung lai mot ban bien
    tap sinh boi luat CU — mot thay doi san pham khong bao gio toi khach."""
    from apps.auto_scan_video import thi_hanh

    a = thi_hanh.phien_ban_engine(pipeline.EDIT_PLAN)
    monkeypatch.setattr(bt, "PHIEN_BAN_BAN", bt.PHIEN_BAN_BAN + 1)
    assert thi_hanh.phien_ban_engine(pipeline.EDIT_PLAN) != a


def test_doi_NGUONG_TACH_CANH_thi_van_tay_giai_doan_DOI(monkeypatch):
    from apps.auto_scan_video import thi_hanh

    a = thi_hanh.phien_ban_engine(pipeline.EDIT_PLAN)
    monkeypatch.setattr(cn, "PHIEN_BAN_CANH", cn.PHIEN_BAN_CANH + "x")
    assert thi_hanh.phien_ban_engine(pipeline.EDIT_PLAN) != a


def test_thu_tu_NGUON_duoc_giu_nguyen():
    ci = _ci(8)
    b = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=[_h(3, "bo", 0.9)])
    assert [q.ma_canh for q in b.quyet_dinh] == [c.ma for c in ci.canh]


# ══════════════════════════════════════════════════════════════════════════════
#  §6  Doan bi CAT khong duoc xuong ha nguon
# ══════════════════════════════════════════════════════════════════════════════

def test_doan_thuoc_canh_bi_CAT_KHONG_co_trong_danh_sach_ha_nguon():
    """⛔ Bang chung chinh cua cong thoat: mot doan thuoc canh da cat ma van lot
    xuong la mot cau duoc DICH va DOC THANH TIENG cho mot doan hinh khong con."""
    ci = _ci(4)          # 0-10, 10-20, 20-30, 30-40
    ban_ghi = {"doan": [
        {"ma": "s1", "bat": 1.0, "ket": 5.0, "chu": "trong canh 0"},
        {"ma": "s2", "bat": 12.0, "ket": 18.0, "chu": "trong canh 1"},
        {"ma": "s3", "bat": 22.0, "ket": 28.0, "chu": "trong canh 2"},
    ]}
    ban = bt.lap_ban(preset=CAT, chi_muc=ci,
                     hieu_canh=[_h(1, "bo", 0.95)], ban_ghi=ban_ghi)
    assert "canh_0001" in ban.cac_ma_cat

    con = bt.doan_giu_lai(ban_ghi, ban, ci)
    ma = {d["ma"] for d in con["doan"]}
    assert "s2" not in ma, "doan thuoc canh da cat van xuong ha nguon"
    assert {"s1", "s3"} <= ma


def test_loc_giu_NGUYEN_thu_tu_va_moc_thoi_gian():
    """⚠️ Canh thoi gian la viec cua pha 16; o day ta chi loc."""
    ci = _ci(3)
    ban_ghi = {"doan": [{"ma": f"s{i}", "bat": i * 10.0 + 1, "ket": i * 10.0 + 5,
                         "chu": f"cau {i}"} for i in range(3)]}
    ban = bt.lap_ban(preset=GIU_HINH, chi_muc=ci)
    con = bt.doan_giu_lai(ban_ghi, ban, ci)
    assert [d["ma"] for d in con["doan"]] == ["s0", "s1", "s2"]
    assert con["doan"][1]["bat"] == 11.0


def test_ban_chep_loi_da_loc_MANG_van_tay_cua_ban():
    """De mot buoc ha nguon doc duoc no da loc theo BAN NAO — hai ban khac nhau
    cho ra hai danh sach doan khac nhau."""
    ci = _ci(3)
    ban = bt.lap_ban(preset=GIU_HINH, chi_muc=ci)
    con = bt.doan_giu_lai({"doan": []}, ban, ci)
    assert con["da_loc_theo_ban"] == ban.van_tay()


def test_giu_hinh_thi_KHONG_doan_nao_bi_loc_di():
    ci = _ci(5)
    ban_ghi = {"doan": [{"ma": f"s{i}", "bat": i * 10.0, "ket": i * 10.0 + 9,
                         "chu": "x"} for i in range(5)]}
    ban = bt.lap_ban(preset=GIU_HINH, chi_muc=ci)
    assert len(bt.doan_giu_lai(ban_ghi, ban, ci)["doan"]) == 5
