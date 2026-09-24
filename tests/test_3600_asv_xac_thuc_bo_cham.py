"""Task 10 — hop dong cua CONG CU XAC THUC bo cham ngu nghia.

🔴 **Phep kiem o day canh chinh CAI THUOC DO, khong canh bo cham.** Cau hoi cua
   Task 10 la *"44/95 la ban dich te that, hay bo cham qua tay"*, va cau tra loi
   do se duoc doc tu con so ma cong cu nay in ra. Mot cong cu dem sai thi ca hai
   cau tra loi deu sai, va khong ai bat duoc — vi khong con thuoc do nao khac.

⛔ Khong goi may B trong tep nay. Moi phep kiem o day la TINH.
"""
from __future__ import annotations

import json
import random

import pytest

from tools import bench_b2_xac_thuc_bo_cham as bc


# ══════════════════════════════════════════════════════════════════════════════
#  1. Nguong — viet TRUOC khi do, va banh coc de khong ai noi sau khi thay so
# ══════════════════════════════════════════════════════════════════════════════

def test_nguong_da_viet_truoc_va_khong_duoc_noi():
    """⛔ Ba hang so nay la PHAN QUYET cua Task 10. Doi chung = doi ket luan."""
    assert bc.NGUONG_BAO_DONG_GIA == 0.15
    assert bc.N_TOI_THIEU == 100
    # Cong ap `--temp 1.0` va `seed` khong co hieu luc => mot luot don le khong
    # phai mot phan quyet.
    assert bc.LUOT_MOI_CAP >= 3


def test_gop_duoi_co_mau_toi_thieu_bi_TU_CHOI(tmp_path):
    """Co mau nho hon `N_TOI_THIEU` khong duoc phep cho ra mot phan quyet.

    ⚠️ Rao nam o `gop` chu khong o `do`, vi `do` duoc phep chay TUNG PHAN (mot
    nua dai cau moi tien trinh). Chinh vi vay rao phai o cho hop nhat — neu
    khong, hai phan 50 cau se lang le thanh mot phan quyet tren 50 cau.
    """
    phan = tmp_path / "phan.json"
    phan.write_text(json.dumps({"bao_dong_gia": {
        "n": 40, "luot": 3, "tu": 0,
        "cac_luot": [{"phan_quyet": {}, "loi_lo": []} for _ in range(3)]}}),
        encoding="utf-8")
    tiem = tmp_path / "tiem.json"
    tiem.write_text(json.dumps({"bat_loi_tiem": {}}), encoding="utf-8")
    with pytest.raises(SystemExit):
        bc.main(["gop", "--fa", str(phan), "--tiem", str(tiem),
                 "--ra", str(tmp_path / "ra.json")])


# ══════════════════════════════════════════════════════════════════════════════
#  2. Phep LAM HONG — doi chung am chi co nghia neu no that su lam hong
# ══════════════════════════════════════════════════════════════════════════════

def test_lat_nghia_that_su_lat_nghia():
    assert bc.lam_hong_lat_nghia("Sản lượng tăng trong năm nay.") == \
        "Sản lượng giảm trong năm nay."
    # Them phu dinh vao mot cau khang dinh.
    ra = bc.lam_hong_lat_nghia("Ông ấy có mặt tại hiện trường.")
    assert ra is not None and "không có" in ra


def test_lat_nghia_tra_None_khi_khong_ap_duoc_phep_nao():
    """⭐ `None`, ⛔ khong tra lai cau nguyen ven.

    Mot cau "da lam hong" ma thuc ra khong doi gi se di vao cot *bo cham khong
    bat duoc* va keo ti le bat xuong — tuc ta ket toi bo cham mot loi cua chinh
    bo do.
    """
    assert bc.lam_hong_lat_nghia("Mưa rơi.") is None


def test_sai_thuc_the_doi_SO_khi_cau_co_so():
    rng = random.Random(1)
    ra = bc.lam_hong_sai_thuc_the("Có 12 người tham dự.", rng)
    assert ra == "Có 19 người tham dự."


def test_sai_thuc_the_doi_TEN_RIENG_khi_cau_khong_co_so():
    rng = random.Random(1)
    goc = "Hội nghị diễn ra tại Stanford vào mùa thu."
    ra = bc.lam_hong_sai_thuc_the(goc, rng)
    assert ra is not None and ra != goc and "Stanford" not in ra
    assert any(t in ra for t in bc.TEN_THAY_THE)


def test_sai_thuc_the_tra_None_khi_khong_co_gi_de_doi():
    assert bc.lam_hong_sai_thuc_the("mưa rơi rất to.", random.Random(1)) is None


def test_dung_cap_tiem_tach_HAI_LOAI_va_du_so_moi_loai():
    """⛔ Hai loai tach rieng tu day cho toi bao cao.

    Gop lai thanh mot ti le tong se giau mat truong hop nguy hiem nhat: bat gan
    het `sai_thuc_the` va bo gan het `lat_nghia` van cho ra mot con so dep.
    """
    cap = [(i, f"源{i}", f"Sản lượng tăng {i} phần trăm trong năm.")
           for i in range(40)]
    ra = bc.dung_cap_tiem(cap, moi_loai=5, rng=random.Random(bc.HAT_GIONG))
    assert len(ra) == 10
    assert sum(1 for m in ra if m["loai"] == "lat_nghia") == 5
    assert sum(1 for m in ra if m["loai"] == "sai_thuc_the") == 5
    assert len({m["ma"] for m in ra}) == 10
    # Moi cap tiem PHAI khac ban goc cua chinh dong do.
    goc = {i: v for i, _, v in cap}
    assert all(m["chu"] != goc[m["dong_flores"]] for m in ra)


def test_dung_cap_tiem_KHONG_im_lang_khi_thieu_cap():
    """Thieu cap thi dung, ⛔ khong tra ve mot bo nho hon roi de nguoi doc tuong
    la da du — mot mau so nho hon lam ti le bat NHAY len vo co."""
    with pytest.raises(SystemExit):
        bc.dung_cap_tiem([(0, "源", "Mưa rơi.")], moi_loai=3,
                         rng=random.Random(1))


# ══════════════════════════════════════════════════════════════════════════════
#  3. Gop nhieu luot — TRUNG VI
# ══════════════════════════════════════════════════════════════════════════════

def _luot(**dat) -> dict:
    return {"phan_quyet": {m: {"dat": v, "do_tin": 1.0, "ly_do": ""}
                           for m, v in dat.items()}, "loi_lo": []}


def test_gop_trung_vi_lay_DA_SO_chu_khong_lay_mot_luot():
    luot = [_luot(a=False, b=True), _luot(a=True, b=True),
            _luot(a=False, b=False)]
    gop = bc.gop_trung_vi(luot, ["a", "b"])
    assert gop["a"] == {"dat": False, "so_luot": 3, "so_bao_sai": 2}
    assert gop["b"] == {"dat": True, "so_luot": 3, "so_bao_sai": 1}


def test_gop_trung_vi_BO_HAN_ma_nam_trong_LO_HONG():
    """⛔ Ma nam trong mot lo HONG: khong phai `dat`, cung khong phai
    `khong dat` — la mot cau hoi CHUA duoc hoi xong.

    🔴 Ban dau phep kiem nay doi dieu do cho MOI ma vang mat, va do la **sai**:
       model chi liet ke muc no thay co loi, nen mot ma vang mat trong mot lo
       CHAY DUOC nghia la **sach**. Xem `test_ma_vang_trong_lo_CHAY_DUOC_...`.
    """
    luot = {"phan_quyet": {"a": {"dat": True}},
            "loi_lo": [{"ma_lo": ["vang_mat"], "loi": "LuocDoSai"}]}
    gop = bc.gop_trung_vi([luot], ["a", "vang_mat"])
    assert "vang_mat" not in gop
    tl = bc._ti_le([luot], ["a", "vang_mat"], gop)
    assert tl["n_hoi"] == 2 and tl["n_co_phan_quyet"] == 1
    assert tl["ti_le_trung_vi"] == 0.0


def test_gop_phan_giu_nguyen_SO_LUOT_cua_tung_cau():
    """⛔ Ghep theo TUNG luot, khong bien moi phan thanh mot luot rieng.

    Lam sai thi "trung vi tren 3 luot" tro thanh "mot luot" cho moi cau — tuc
    dung cai ma chinh phep do nay khai la khong du de phan quyet.
    """
    def phan(tu, ma_dat):
        return {"n": len(ma_dat), "luot": 3, "tu": tu,
                "cac_luot": [_luot(**{m: v[k] for m, v in ma_dat.items()})
                             for k in range(3)]}

    a = phan(0, {"flores_0000": [False, False, True],
                 "flores_0001": [True, True, True]})
    b = phan(2, {"flores_0002": [False, True, False],
                 "flores_0003": [True, True, True]})
    g = bc.gop_phan([a, b])
    assert g["n"] == 4 and g["luot"] == 3
    assert all(v["so_luot"] == 3 for v in g["gop"].values())
    # Hai cau bi da so cham sai => 2/4.
    assert g["so_bi_cham_sai"] == 2 and g["ti_le_trung_vi"] == 0.5
    assert g["ti_le_tung_luot"] == [0.5, 0.25, 0.25]


def test_gop_phan_TU_CHOI_hai_phan_trung_ma():
    """Trung ma nghia la hai tien trinh da hoi cung mot cau — dem hai lan."""
    p = {"n": 1, "luot": 1, "tu": 0,
         "cac_luot": [_luot(flores_0000=True)]}
    with pytest.raises(SystemExit):
        bc.gop_phan([p, dict(p)])


def test_ti_le_bao_cao_DAI_cua_tung_luot():
    luot = [_luot(a=False, b=False), _luot(a=True, b=True),
            _luot(a=False, b=True)]
    tl = bc._ti_le(luot, ["a", "b"], bc.gop_trung_vi(luot, ["a", "b"]))
    assert tl["ti_le_tung_luot"] == [1.0, 0.0, 0.5]
    assert tl["dai"] == [0.0, 1.0]


# ══════════════════════════════════════════════════════════════════════════════
#  4. Ti le BAT loi tiem — ⛔ khong duoc dao chieu
# ══════════════════════════════════════════════════════════════════════════════

def test_ti_le_bat_loi_tiem_dem_theo_CHIEU_DUNG(monkeypatch):
    """🔴 `khong dat` tren mot cap DA LAM HONG nghia la **BAT DUOC**.

    Mot dau tru lac cho o day dao nguoi mu thanh nguoi tinh: bo cham bat 0/15
    se duoc in ra la 100 %, va ta se ket luan no dang tin dung luc no chet.
    """
    muc = [{"ma": "tiem_lat_nghia_0500", "dong_flores": 500,
            "loai": "lat_nghia", "goc": "源", "chu": "x"},
           {"ma": "tiem_sai_thuc_the_0501", "dong_flores": 501,
            "loai": "sai_thuc_the", "goc": "源", "chu": "y"}]
    monkeypatch.setattr(bc, "dung_cap_tiem", lambda *a, **k: muc)
    monkeypatch.setattr(bc, "doc_flores", lambda *a, **k: [])
    # `lat_nghia` bi BAT o ca 2 luot; `sai_thuc_the` khong bi bat lan nao.
    monkeypatch.setattr(bc, "cham_mot_luot", lambda db, m, ban="v3": _luot(
        tiem_lat_nghia_0500=False, tiem_sai_thuc_the_0501=True))

    ra = bc.ti_le_bat_loi_tiem(db=None, moi_loai=1, bo_qua=0, luot=2)
    ln = ra["theo_loai"]["lat_nghia"]
    st = ra["theo_loai"]["sai_thuc_the"]
    assert ln["ti_le_trung_vi"] == 1.0 and ln["ti_le_tung_luot"] == [1.0, 1.0]
    assert ln["dat_nguong_mach"] is True
    assert st["ti_le_trung_vi"] == 0.0 and st["ti_le_tung_luot"] == [0.0, 0.0]
    assert st["dat_nguong_mach"] is False


# ══════════════════════════════════════════════════════════════════════════════
#  5. Lo HONG khong duoc doc thanh "khong co loi nao"
# ══════════════════════════════════════════════════════════════════════════════

def test_lo_hong_KHONG_duoc_dem_la_dat(monkeypatch):
    """⚠️ "Khong hoi duoc" khac han "da hoi va khong thay gi".

    `qc_ai.doc_ngu_nghia` mac dinh ma thieu la `dat`; neu `cham_mot_luot` cung
    lam vay thi ti le bao dong gia se **dep len** moi lan cong loi — tuc cong
    cang hong, bo cham cang trong dang tin.
    """
    from apps.auto_scan_video import ai

    def no(*a, **k):
        raise ai.AiError("cong tu choi")

    monkeypatch.setattr(ai, "goi", no)
    ra = bc.cham_mot_luot(None, [{"ma": "m1", "goc": "源", "chu": "v"}])
    assert ra["phan_quyet"] == {}
    assert len(ra["loi_lo"]) == 1 and "AiError" in ra["loi_lo"][0]["loi"]
    assert bc.gop_trung_vi([ra], ["m1"]) == {}


# ══════════════════════════════════════════════════════════════════════════════
#  6. Phan quyet in ra phai lat dung o nguong
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ti_le,mong", [
    (0.15, "DANG TIN"), (0.1501, "sua BO CHAM"), (0.46, "sua BO CHAM")])
def test_bao_cao_lat_phan_quyet_dung_o_nguong(ti_le, mong):
    van = bc.bao_cao({"bao_dong_gia": {
        "n_hoi": 100, "n_co_phan_quyet": 100, "ti_le_trung_vi": ti_le,
        "dai": [ti_le, ti_le], "luot": 3}})
    assert mong in van


def test_bao_cao_KEU_LEN_khi_mu_o_mot_loai():
    van = bc.bao_cao({
        "bao_dong_gia": {"n_hoi": 100, "n_co_phan_quyet": 100,
                         "ti_le_trung_vi": 0.02, "dai": [0.0, 0.04], "luot": 3},
        "bat_loi_tiem": {"luot": 3, "theo_loai": {"lat_nghia": {
            "n_hoi": 15, "n_co_phan_quyet": 15, "ti_le_trung_vi": 0.2,
            "dai": [0.2, 0.2], "dat_nguong_mach": False}}}})
    assert "MU o `lat_nghia`" in van


# ══════════════════════════════════════════════════════════════════════════════
#  6b. Ban ghi commit len kho KHONG duoc mang chu cua FLORES (ShareAlike)
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_ghi_sach_bo_HET_khoa_mang_chu():
    """🔴 Rao CO HOC, khong phai mot y dinh tot.

    FLORES la CC-BY-SA-4.0 (ShareAlike) va `ly_do` cua model trich thang doan
    nguon lan ban dich vao trong no — mot tep bang chung "day du" se la mot ban
    phan phoi lai FLORES nam trong mot kho khong theo giay phep do.
    """
    day_du = {
        "bao_dong_gia": {
            "n": 2, "ti_le_trung_vi": 0.5,
            "gop": {"flores_0000": {"dat": False, "so_luot": 3,
                                    "so_bao_sai": 2}},
            "cac_luot": [{"phan_quyet": {"flores_0000": {
                "dat": False, "do_tin": 0.9,
                "ly_do": "Bản gốc nói X, bản dịch thành Y"}}, "loi_lo": []}]},
        "bat_loi_tiem": {"gop": {}, "cac_luot": [],
                         "dong_flores_da_dung": [100, 101]},
    }
    sach = bc.ban_ghi_sach(day_du)
    van = json.dumps(sach, ensure_ascii=False)
    assert "Bản gốc nói X" not in van
    assert "cac_luot" not in sach["bao_dong_gia"]
    # ...nhung thu tra loi duoc cau hoi cua Task 10 thi VAN CON.
    assert sach["bao_dong_gia"]["ti_le_trung_vi"] == 0.5
    assert sach["bao_dong_gia"]["gop"]["flores_0000"]["so_bao_sai"] == 2
    assert sach["bat_loi_tiem"]["dong_flores_da_dung"] == [100, 101]


# ══════════════════════════════════════════════════════════════════════════════
#  7. FLORES — hai tep lech dong thi DUNG
# ══════════════════════════════════════════════════════════════════════════════

def test_doc_flores_DUNG_khi_hai_tep_lech_so_dong(tmp_path):
    """Hai tep lech mot dong lam MOI cap sai, va moi phan quyet "dich sai" sau
    do la THAT — tuc phep do tu bien thanh mot phep do ve chinh no."""
    d = tmp_path / "dev"
    d.mkdir()
    (d / "zho_Hans.dev").write_text("一\n二\n三\n", encoding="utf-8")
    (d / "vie_Latn.dev").write_text("mot\nhai\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        bc.doc_flores(tmp_path)


def test_doc_flores_ghep_theo_CHI_SO_DONG(tmp_path):
    d = tmp_path / "dev"
    d.mkdir()
    (d / "zho_Hans.dev").write_text("一\n二\n", encoding="utf-8")
    (d / "vie_Latn.dev").write_text("mot\nhai\n", encoding="utf-8")
    assert bc.doc_flores(tmp_path) == [(0, "一", "mot"), (1, "二", "hai")]


# ══════════════════════════════════════════════════════════════════════════════
#  8. Cổng NỀN SẠCH — phải qua TRƯỚC khi so hai lời nhắc
# ══════════════════════════════════════════════════════════════════════════════

def test_nguong_nen_sach_viet_truoc():
    """⛔ Trần lấy đúng mức V1 đã đo (1/30 lô): không được làm nền tệ hơn lúc
    chưa đụng vào. Đổi hai hằng số này = đổi kết luận."""
    assert bc.NGUONG_LO_HONG == 0.033
    assert bc.NGUONG_DO_PHU == 28 / 30


def test_thong_ke_luoc_do_dem_LO_chu_khong_dem_MUC():
    """🔑 Mất theo LÔ nghĩa là mất cả một cụm, không phải mẫu ngẫu nhiên.

    30 mục = 3 lô mỗi lượt. Một lô hỏng ở lượt 2 ⇒ 1/9 lô, và độ phủ lượt đó
    tụt xuống 20/30 — hai con số nói hai điều khác nhau, cả hai đều cần.
    """
    def luot(mat):
        return {"phan_quyet": {},
                "loi_lo": ([{"ma_lo": [f"m{i}" for i in range(mat)],
                             "loi": "LuocDoSai"}] if mat else [])}

    tk = bc.thong_ke_luoc_do([luot(0), luot(10), luot(0)], 30)
    assert tk["tong_lo"] == 9 and tk["so_lo_hong"] == 1
    assert tk["ti_le_lo_hong"] == round(1 / 9, 4)
    assert tk["do_phu_tung_luot"] == [1.0, round(20 / 30, 4), 1.0]
    assert tk["nen_sach"] is False


def test_nen_sach_do_theo_MA_MAT_chu_khong_theo_MA_MODEL_NHAC_TOI():
    """🔴 Phép kiểm này từng khai *"0 lô hỏng mà mỗi lượt chỉ trả lời 15/30 vẫn
    là kênh mất dữ liệu"* — **sai**, và nó suýt làm ta đi sửa một thứ không hỏng.

    Model chỉ liệt kê mục nó thấy có lỗi, nên "chỉ nhắc 15/30" có thể là 15 mục
    **sạch**. Cái đếm được là mã nằm trong một lô **hỏng**.
    """
    def luot(mat=0):
        return {"phan_quyet": {},
                "loi_lo": ([{"ma_lo": [f"m{i}" for i in range(mat)],
                             "loi": "x"}] if mat else [])}

    assert bc.thong_ke_luoc_do([luot()] * 3, 30)["nen_sach"] is True
    assert bc.thong_ke_luoc_do([luot(15)] * 3, 30)["nen_sach"] is False
    assert bc.thong_ke_luoc_do([luot(), luot(), luot(10)],
                               30)["nen_sach"] is False


def test_nhiet_do_ngu_nghia_DA_GHIM_va_bench_dung_CUNG_gia_tri():
    """⛔ Đo ở một nhiệt độ khác đường sản phẩm là đo một hệ thống khác."""
    import inspect

    from apps.auto_scan_video import qc_ai

    assert qc_ai.NHIET_DO_NGU_NGHIA == 0.0
    assert "qc_ai.NHIET_DO_NGU_NGHIA" in inspect.getsource(bc.cham_mot_luot)


# ══════════════════════════════════════════════════════════════════════════════
#  9. HAI cách một mã vắng mặt — và chúng KHÔNG cùng nghĩa
# ══════════════════════════════════════════════════════════════════════════════

def test_ma_vang_trong_lo_CHAY_DUOC_la_DAT_chu_khong_phai_chua_tra_loi():
    """🔴 Đo 24/09: model **chỉ liệt kê những mục nó thấy có lỗi**.

    Lô 200–209 trả về **0/10** mã kèm `khong_dat=0`; lô 220–229 trả về 10/10.
    Coi 10 mục SẠCH đó là "chưa trả lời" làm mẫu số tụt 30 → 16, và tỉ lệ báo
    động giả **nhảy từ 23% lên 44%** mà không một phán quyết nào đổi.

    ⭐ `qc_ai.doc_ngu_nghia` vốn ghi rõ mã thiếu là **ĐẠT** — phép đo phải đếm
       theo cùng hợp đồng với sản phẩm, nếu không nó đo một hệ thống khác.
    """
    luot = {"phan_quyet": {"a": {"dat": False}}, "loi_lo": []}
    gop = bc.gop_trung_vi([luot], ["a", "b", "c"])
    assert set(gop) == {"a", "b", "c"}
    assert gop["b"]["dat"] is True and gop["c"]["dat"] is True
    assert bc._ti_le([luot], ["a", "b", "c"], gop)["ti_le_trung_vi"] == round(
        1 / 3, 4)


def test_ma_trong_lo_HONG_thi_KHONG_duoc_dem():
    """⛔ Lô hỏng = chưa hỏi xong. Đếm nó là ĐẠT sẽ làm mỗi lần cổng lỗi biến
    thành một điểm cộng cho bộ chấm."""
    luot = {"phan_quyet": {"a": {"dat": False}},
            "loi_lo": [{"ma_lo": ["b", "c"], "loi": "LuocDoSai"}]}
    gop = bc.gop_trung_vi([luot], ["a", "b", "c"])
    assert set(gop) == {"a"}
    tk = bc.thong_ke_luoc_do([luot], 3)
    assert tk["do_phu_tung_luot"] == [round(1 / 3, 4)]


def test_do_phu_dem_ma_DA_HOI_XONG_khong_dem_ma_model_nhac_toi():
    """Một lượt sạch hoàn toàn (model không nhắc mã nào) vẫn là độ phủ 100%."""
    luot = {"phan_quyet": {}, "loi_lo": []}
    assert bc.thong_ke_luoc_do([luot], 10)["do_phu_tung_luot"] == [1.0]
    assert bc.thong_ke_luoc_do([luot], 10)["nen_sach"] is True


# ══════════════════════════════════════════════════════════════════════════════
#  10. Bản lời nhắc ĐÓNG BĂNG — để so ba bản trên CÙNG một nền
# ══════════════════════════════════════════════════════════════════════════════

def test_ba_ban_loi_nhac_deu_goi_duoc_va_v3_la_ban_HIEN_HANH():
    """⛔ `v1`/`v2` là bản **chép nguyên văn từ git**, `v3` là bản sản phẩm.

    🔑 Giữ chúng ở `tools/` chứ không ở `apps/`: sản phẩm chỉ được có MỘT lời
       nhắc. Nhưng không giữ thì ta đang so **một bản đo sạch với hai bản đo
       bẩn** — V1 và V2 đều đo ở nhiệt độ mặc định, và ghim nhiệt độ đã chứng
       minh là nó đổi kết quả (lô hỏng 22,2% → 0%).
    """
    from apps.auto_scan_video import qc_ai

    lo = [{"ma": "seg_0001", "goc": "源", "chu": "dich"}]
    assert set(bc.BAN_LOI_NHAC) == {"v1", "v2", "v3"}
    for _ten, (dung, _doc) in bc.BAN_LOI_NHAC.items():
        msgs = dung(lo, "vi")
        assert msgs[0]["role"] == "system" and msgs[0]["content"]
    # v3 phai la DUNG ham cua san pham, khong phai mot ban chep thu ba.
    assert (bc.BAN_LOI_NHAC["v3"][0](lo, "vi")
            == qc_ai.loi_nhac_ngu_nghia(lo, "vi"))


def test_ban_v1_hoi_NHI_PHAN_con_v2_hoi_PHAN_MUC():
    """Chốt rằng hai bản đóng băng thật sự khác nhau ở đúng chỗ ta nói."""
    lo = [{"ma": "seg_0001", "goc": "源", "chu": "dich"}]
    v1 = bc.BAN_LOI_NHAC["v1"][0](lo, "vi")[0]["content"]
    v2 = bc.BAN_LOI_NHAC["v2"][0](lo, "vi")[0]["content"]
    assert "dat=false" in v1 and "do_tin" in v1 and "nghiem_trong" not in v1
    assert "nghiem_trong" in v2 and "do_tin" not in v2
    # V2 CHUA co san muc cho sai thuc the — do la cai V3 them vao.
    assert "TEN RIENG" not in v2


def test_ban_doc_v1_KHONG_loc_doan_trich_va_doc_dat_tu_model():
    """V1 tin thẳng `dat` của model — đó chính là bản ta đang so để thấy khác."""
    ra = bc.BAN_LOI_NHAC["v1"][1](
        {"doan": {"m": {"dat": False, "ly_do": "x"}}}, {"m"}, {})
    assert ra[0]["dat"] is False and ra[0]["muc"] == "" and ra[0]["loi"] == []


# ══════════════════════════════════════════════════════════════════════════════
#  11. ĐỐI CHIẾU THẲNG — ⛔ bỏ phép trừ
# ══════════════════════════════════════════════════════════════════════════════

def _so_soi(pq: dict):
    return {"muc": [{"dong_flores": i, "phan_quyet": v} for i, v in pq.items()]}


def _cham(dat: dict):
    return {"gop": {f"flores_{i:04d}": {"dat": v} for i, v in dat.items()}}


def test_doi_chieu_tinh_THANG_khong_tru():
    """🔴 `báo động giả − sàn lỗi` chỉ đúng nếu bộ chấm bắt được **MỌI** lỗi có
    sẵn, tức ngầm giả định độ nhạy 100% trên lỗi TỰ NHIÊN — thứ ta chỉ đo trên
    lỗi TA TIÊM, mà lỗi tiêm không cùng hình dạng với lỗi tự nhiên.

    ⇒ Đối chiếu thẳng: bốn ô, không giả định nào.
    """
    so = _so_soi({1: "ro", 2: "ro", 3: "khong_loi", 4: "khong_loi",
                  5: "khong_loi"})
    # Bộ chấm: bắt trúng 1, bỏ sót 2, báo nhầm 3, đúng âm 4 và 5.
    ch = _cham({1: False, 2: True, 3: False, 4: True, 5: True})
    k = bc.doi_chieu(so, ch)["theo_dinh_nghia"]["chinh"]
    assert (k["dung"], k["bao_dong_gia"], k["bo_sot"], k["dung_am"]) == (1, 1, 1, 2)
    assert k["ti_le_bao_dong_gia_that"] == 0.5     # 1 nhầm / 2 gắn cờ
    assert k["do_nhay_loi_tu_nhien"] == 0.5        # 1 trúng / 2 lỗi thật
    assert k["dong_bao_dong_gia"] == [3] and k["dong_bo_sot"] == [2]


def test_doi_chieu_BA_dinh_nghia_loi_viet_TRUOC():
    """⛔ Ba định nghĩa khai trước, ⛔ không chọn cái nào cho ra số đẹp."""
    assert bc.COI_LA_LOI["chinh"] == ("ro",)
    assert bc.COI_LA_LOI["rong"] == ("ro", "zh_lech")
    so = _so_soi({1: "zh_lech", 2: "bien", 3: "khong_loi"})
    ch = _cham({1: False, 2: False, 3: True})
    r = bc.doi_chieu(so, ch)["theo_dinh_nghia"]
    # `chinh`: khong ca nao la loi => ca hai lan gan co deu la bao dong gia.
    assert r["chinh"]["bao_dong_gia"] == 2
    assert r["rong"]["bao_dong_gia"] == 1      # zh_lech duoc tinh la loi
    assert r["rong_nhat"]["bao_dong_gia"] == 0


def test_doi_chieu_BO_dong_bo_cham_khong_cham_duoc():
    """Dòng bộ chấm không trả lời được ⇒ ⛔ không đếm vào ô nào cả."""
    so = _so_soi({1: "ro", 2: "khong_loi"})
    r = bc.doi_chieu(so, _cham({1: False}))
    assert r["n"] == 1 and r["dong_khong_cham_duoc"] == [2]
