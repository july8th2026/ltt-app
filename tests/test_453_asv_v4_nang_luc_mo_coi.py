"""Pha 27 — phep kiem ma kiem toan pha 26 YEU CAU dung, va no da tim them hai ca.

## Vi sao phep kiem nay ton tai

Kiem toan pha 26 ket luan rang chin phat hien khong phai chin loi doc lap ma la
**mot thoi quen lap lai nam lan**: VLM, cache giai doan, bo ma hoa phan cung, bo
quet artifact va `dich_thuat.py` deu duoc viet xong, co test don vi xanh, va
khong bao gio duoc noi vao mot duong chay that. Va no ket bang mot cau danh cho
pha 27:

    "Truoc khi sua tung cai mot, hay them mot phep kiem le ra da bat duoc ca
     nam: moi nang luc duoc khai phai co it nhat mot nguoi goi voi toi duoc tu
     `pipeline.CHUOI` hoac tu mot route."

⭐ **Mot nang luc co test don vi xanh va khong co nguoi goi trong ma san pham
   trong GIONG HET mot tinh nang da hoan thanh, tu moi goc nhin tru dung cai
   goc duy nhat co y nghia.** Test la thu che khuat no: chinh bo test la nguoi
   goi duy nhat, nen bang mau xanh la bang chung cho su ton tai chu khong phai
   cho su huu dung.

⇒ Nen phep kiem nay dem nguoi goi trong **ma san pham** va co y **khong** dem
  `tests/` lan `tools/`.

## ⛔ Gioi han cua no, noi thang ra

No bat duoc **nang luc khong co nguoi goi**. No KHONG bat duoc:

  * `B23-01` — `cache_dung_duoc` CO nguoi goi; loi nam o mot phep so sanh sai
    ben trong no (van tay 64 ky tu tim trong mot khoa chi chua 32).
  * `B24-01` — `chon_bo_ma_hoa` CO nguoi goi; loi la mot NHANH khong bao gio
    chay toi vi `ctx.gpu_uuid` luon rong.

Tuc 3/5, khong phai 5/5. Ghi ra day thay vi de nguoi doc sau nay tin rang co
phep kiem nay thi lop loi do da duoc dong.

## Cach no chot: TAP HOP, khong phai SO LUONG

Chot mot con so ("khong qua 30 ham mo coi") cho phep doi mot ham mo coi lay mot
ham khac ma bang van xanh. Chot tap hop thi mot ten MOI xuat hien la do, va mot
ten bien mat cung la do — buoc nguoi sua phai noi ro ho vua noi cai gi vao mach.
"""
from __future__ import annotations

import ast
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]

#: Goi cua Auto Scan Video. Bon app: mot app khach + ba executor noi bo.
GOI_ASV = ("apps/auto_scan_video", "apps/asv_media", "apps/asv_gpu",
           "apps/asv_voice")

#: Noi dem NGUOI GOI. ⛔ `tests/` va `tools/` KHONG nam o day, va do la ca diem
#: cua phep kiem: mot nang luc chi duoc goi tu bo test la mot nang luc chua
#: duoc noi vao san pham.
GOI_SAN_PHAM = ("apps", "platform_core", "server", "nexus_agent",
                "render_gateway")

#: Ham la CUA VAO cua nen tang, khong phai ham mo coi. Chung duoc goi qua
#: decorator route hoac qua ban khai app, nen khong loi goi truc tiep nao ton
#: tai trong ma nguon.
CUA_VAO = frozenset({
    "handle",          # `AppManifest.job_types` -> `jobs.handle`
    "bao_tri",         # `AppManifest.bao_tri`
    "bang_gia",        # `AppManifest.bang_gia`
    "suc_khoe",        # `AppManifest.suc_khoe`
})

#: 🔒 **BANH COC.** Nhung nang luc hien KHONG co nguoi goi trong ma san pham.
#:
#: Moi ten o day la mot mon no da biet. Danh sach nay chi duoc phep NGAN di.
#: Mot ten moi xuat hien nghia la ai do vua viet xong mot nang luc va quen noi
#: no vao mach — dung luc do, khong phai mot kiem toan sau.
MO_COI_DA_BIET = frozenset({
    # ── A27-01 (pha 27 phat hien) — QC ngu nghia/thi giac va SUA CHUA chua
    #    tung duoc goi. `loi.py` chi import LOP NGOAI LE cua chung, nen ca hai
    #    tep trong nhu dang duoc dung. Kiem toan pha 26 goi G14 la PARTIAL voi
    #    ly do "ban sua duoc tinh nhung khong duoc dieu khien"; do la mot nua.
    #    Nua kia la chinh `qc_ai` cung khong co nguoi goi nao.
    #    ⛔ Noi chung vao mach la mo rong tinh nang — ngoai pham vi pha 27
    #       ("no feature expansion"). Ban giao cho pha 28.
    #
    #    ✅ **`gon_theo_don_vi` da RA khoi danh sach nay.** Vong sua duoc noi vao
    #       mach o `jobs._sua_chua_neu_can`, va cung voi no la
    #       `vo_hieu_theo_day_chuyen` (xem duoi). Hai ten con lai cua `sua_chua`
    #       (`lap_ke_hoach`, `tu_nan`) chua bao gio o trong danh sach vi chung
    #       duoc goi tu trong chinh module.
    #
    #    🔴 Va viec noi vao mach **khong** phai mo rong tinh nang, du pha 27 da
    #       goi no nhu vay. Cong thoat cua pha 19 doi dung chu: *"repairs rerun
    #       the smallest safe scope until pass or bounded terminal failure"*.
    #       Bao cao pha 19 tu ghi phan thi hanh la NO. Nen day la tra no, khong
    #       phai them tinh nang — mot phan biet quyet dinh viec no duoc lam hay
    #       bi hoan them mot pha nua, va no da bi hoan bon pha.
    #
    #    ✅ **`doc_ngu_nghia` va `loi_nhac_ngu_nghia` da RA khoi danh sach
    #       (06/09).** Giai doan `qc_ai` (`giai_doan_qc_ai.py`) goi ca hai, va
    #       phan quyet cua chung di tiep vao vong sua qua `stage.outputs`.
    #
    #    🔴 Quyet dinh ve GIA — thu lam hai ten nay bi hoan bon pha — duoc
    #       tra loi bang mot cong tat o cap NGUOI VAN HANH (`LTT_ASV_QC_AI`),
    #       khong phai bang mot truong trong `settings`: mot truong `settings`
    #       la thu khach gui len, tuc khach tu bat duoc mot chi phi chua duoc
    #       dinh gia. Mac dinh TAT, nen khong lan chay nao dang tra them gi.
    #
    #    ⚠️ Bon ten con lai VAN mo coi, va ly do khac han: chung phuc vu QC
    #       **hinh** (`doc_hinh`, `loi_nhac_hinh`, `moc_cho_noi`) va QC **giong**
    #       (`so_khop_doc`). Hai loai do can them may moc that — rut khung quanh
    #       moi cho noi, va ASR tren chinh ban da ket xuat — chu khong chi can
    #       mot cong tat. Dieu kien de go: mot giai doan doc duoc chung.
    "doc_hinh", "loi_nhac_hinh", "moc_cho_noi", "so_khop_doc",

    # ── HO SO NOI DUNG — nang luc nay duoc KHAI CHO KHACH la chua san sang.
    #    `gia.py` bay `CHE_DO_GIONG_TU_KHOP` kem cau "tinh nang nay dang duoc
    #    hoan thien — hien tai hay tu chon giong". Tuc mon no nay da duoc noi
    #    that voi nguoi tra tien, khac han bon truong hop kia.
    "doc_ho_so", "loi_nhac_ho_so", "tom_tat_chi_muc", "can_cho_ho_so",

    # ── A26-01 — duong dich thu hai, da chet tu pha 14. Van tay khong con doc
    #    no nua (pha 27), nhung ban than duong thi con. Xoa no keo theo xoa ca
    #    `tests/test_408` va di doi hai lop ngoai le ma `loi.py` dang dung —
    #    lon hon thu blocker doi hoi.
    "dich_ban_ghi",

    # ── Tien ich co nguoi goi trong TUONG LAI gan, hoac chi dung tu test/tool.
    # ✅ `vo_hieu_theo_day_chuyen` da ra khoi day cung luc voi `gon_theo_don_vi`:
    #    no la buoc cuoi cua vong sua — danh dau artifact ha nguon la khong con
    #    dung. No tung nam trong nhom "co nguoi goi trong TUONG LAI gan", va
    #    tuong lai gan do dai bon pha.
    # ✅ `tien_do` da RA khoi danh sach (08/09, V5 R4) bang cach bi XOA,
    #    khong bang cach duoc noi vao mach. No tra `phan_tram` + danh sach
    #    giai doan; `quan_sat.dong_thoi_gian` tra dung nhung thu do va NHIEU
    #    hon (buoc dang chay, giay da chay, so ke), va chinh no la thu man
    #    tien do dang dung. Giu ca hai la giu hai nguon cho MOT con so.
    #
    # ⚠️ Mot phien khac tung go ten nay khoi day voi ly do *"no chi co nguoi
    #    goi vi mot VA CHAM TEN"*. Ly do do sai: do AST 08/09 cho ket qua ten
    #    `tien_do` co **khong mot call site nao** trong `apps/` — no la mo coi
    #    that, va go no khoi danh sach ma khong xoa ham se lam bai kiem DO.
    #    Nhan xet TONG QUAT cua ho thi dung: `_ten_duoc_goi_trong_san_pham()`
    #    khop theo ten TRAN nen mot ten trung o app khac co the che mot mon
    #    no that. Do la mot khiem khuyet co that cua bo do — chi khong phai
    #    khiem khuyet da xay ra o truong hop nay.
    # `asset_cua` roi danh sach 11/09: `cache_chung` (V6 pha 25) goi no.
    "don_theo_run",
    "cua_chan_cho_lo", "giai_quyet_mo_ho", "loi_khong_du_ngan_sach",
    "tong_credit", "tom_tat_cho_khach",
    "cua_so_ngu_canh", "dung_gpu", "van_tay_che_do", "van_tay_van_ban",
    "tu_json", "doc_wav", "ghi_wav",
})


def _tep_py(thu_muc: Path):
    for p in sorted(thu_muc.rglob("*.py")):
        if "__pycache__" not in p.parts:
            yield p


def _cay(p: Path):
    try:
        return ast.parse(p.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None


def _ten_duoc_goi_trong_san_pham() -> set[str]:
    """Ten duoc DUNG o trong chinh cac goi ASV. Hai chi tiet, ca hai da tung sai.

    🔴 **Dem THAM CHIEU, khong chi dem loi goi.** Ban dau cho nay chi doc
       `ast.Call`, nen mot ham truyen di nhu mot GIA TRI trong vo hinh voi no.
       `tables.sinh_id` la vi du song: no duoc dung qua `default=sinh_id`, tuc
       SQLAlchemy goi no chu ma ASV thi khong — va bo do se ket no la mo coi.

    🔴 **Chi quet CAC GOI ASV, khong quet ca `apps/`.** Phep khop la theo ten
       TRAN, nen mot ten trung o app khac "cuu" mot mon no cua ASV ma khong ai
       thay. Do 08/09: neu quet ca `apps/`, `sinh_id` duoc `apps/chatltt` cuu —
       dung ket luan, sai ly do, va mot ly do sai thi khong ben.

    ⭐ He qua thu hai, co y: pham vi cu la `GOI_SAN_PHAM`, tuc no con dem ca
       `platform_core/`, `server/`, `nexus_agent/`, `render_gateway/`. Ban moi
       **bo** chung. Nghia la mot ham ASV chi duoc goi tu ma NEN TANG se bi ket
       la mo coi — va do la ket luan dung: hop dong app noi nen tang chi doc
       `manifest.py`, khong goi thang vao app. Mot loi goi nhu the la mot vi
       pham hop dong, khong phai mot nguoi goi hop le. (Cua vao qua ban khai
       da nam trong `CUA_VAO`.)

    ⭐ Doi cA hai cung luc la co y. Chi sua ve pham vi thi `sinh_id` thanh mot
       mo coi GIA; chi sua ve tham chieu thi va cham ten van con. Do 08/09: sau
       khi doi ca hai, tap mo coi **khong doi** (23 ten, y het) — bo do manh len
       ma khong dich mot phan quyet nao.
    """
    ra: set[str] = set()
    for goi in GOI_ASV:
        d = GOC / goi
        if not d.is_dir():
            continue
        for p in _tep_py(d):
            cay = _cay(p)
            if cay is None:
                continue
            for n in ast.walk(cay):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    ra.add(n.id)
                elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
                    ra.add(n.attr)
    return ra


def _ham_cong_khai_cua_asv() -> dict[str, list[str]]:
    """Ham cong khai o MUC MODULE cua cac goi ASV -> noi dinh nghia.

    ⚠️ Chi muc module: mot phuong thuc trong mot lop duoc goi qua thuc the, va
       phep dem theo ten se sai ca hai chieu voi chung.
    """
    ra: dict[str, list[str]] = {}
    for goi in GOI_ASV:
        d = GOC / goi
        if not d.is_dir():
            continue
        for p in _tep_py(d):
            cay = _cay(p)
            if cay is None:
                continue
            for n in cay.body:
                if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not n.name.startswith("_")):
                    # Ham co decorator la cua vao (route), khong phai mo coi.
                    if n.decorator_list:
                        continue
                    ra.setdefault(n.name, []).append(
                        f"{p.relative_to(GOC).as_posix()}:{n.lineno}")
    return ra


def _mo_coi() -> dict[str, list[str]]:
    goi = _ten_duoc_goi_trong_san_pham()
    return {k: v for k, v in _ham_cong_khai_cua_asv().items()
            if k not in goi and k not in CUA_VAO}


def test_KHONG_co_nang_luc_mo_coi_MOI():
    """🔴 Mot ten moi o day = mot nang luc vua duoc viet xong va quen noi vao mach.

    Sua bang cach **noi no vao mach**, khong phai bang cach them ten vao
    `MO_COI_DA_BIET`. Neu buoc phai them, dong them phai ghi VI SAO va dieu kien
    de go ra — mot dong khong ly do la mon no bien thanh do dac.
    """
    moi = {k: v for k, v in _mo_coi().items() if k not in MO_COI_DA_BIET}
    assert not moi, (
        "nang luc khong co nguoi goi nao trong ma san pham:\n"
        + "\n".join(f"  {k} — {', '.join(v)}" for k, v in sorted(moi.items())))


def test_BANH_COC_khong_bi_noi_ra_trong_im_lang():
    """Danh sach mon no chi duoc phep NGAN di.

    ⭐ Chot TAP HOP chu khong chot SO LUONG: mot con so cho phep doi mot mon no
       lay mot mon no khac ma bang van xanh, va do la cach mot banh coc quay
       nguoc ma khong ai thay.
    """
    con_lai = set(_mo_coi()) & MO_COI_DA_BIET
    da_noi_vao_mach = MO_COI_DA_BIET - con_lai
    assert not da_noi_vao_mach, (
        "nhung ten sau DA co nguoi goi — hay xoa chung khoi `MO_COI_DA_BIET` "
        f"de banh coc khong quay nguoc: {sorted(da_noi_vao_mach)}")


def test_NAM_TRUONG_HOP_cua_pha_26_khong_con_mo_coi():
    """Ba trong nam truong hop kiem toan ke ten phai bien khoi danh sach.

    ⛔ Hai truong hop con lai (`B23-01`, `B24-01`) phep kiem nay **khong** bat
       duoc — ca hai deu CO nguoi goi, loi nam ben trong. Doc docstring dau tep.
    """
    mo_coi = set(_mo_coi())
    # VLM: `loi_nhac_canh` va `doc_hieu_canh` nay duoc `giai_doan_ban_bien_tap`
    # goi that.
    assert "loi_nhac_canh" not in mo_coi
    assert "doc_hieu_canh" not in mo_coi
    # Bo quet artifact het han.
    assert "quet_het_han" not in mo_coi


def test_moi_ten_trong_banh_coc_deu_la_ham_CO_THAT():
    """Mot ten go sai trong danh sach mien tru la mot mien tru cho ai ca — no im
    lang cho qua khong gi, va che mat mon no that mang ten dung."""
    tat_ca = set(_ham_cong_khai_cua_asv())
    ma = MO_COI_DA_BIET - tat_ca
    assert not ma, f"ten trong `MO_COI_DA_BIET` khong ung voi ham nao: {sorted(ma)}"
