"""Auto Scan Video V4 — the capability inventory's assumptions, pinned to real code.

`docs/auto_scan_video_v4/CAPABILITY_INVENTORY_V4.md` classifies every V4 need as
SUFFICIENT / EXTEND_OWNER_CONTRACT / ABSENT. Each SUFFICIENT verdict rests on a
specific name existing in a specific owner app. A markdown table cannot notice when
one of those names is renamed, moved, or deleted.

⛔ The failure this file prevents is late and expensive: Phase 11 discovers at
   implementation time that `ltt_llm_vision` was renamed, or Phase 09 discovers that
   the sample-voice catalogue moved, and the inventory that authorised "reuse, do not
   build" turns out to have been describing a tree that no longer exists.

⭐ These are **presence** checks on OTHER apps' surfaces, not behaviour tests of those
   apps. They assert the inventory's premises, nothing more. Each one names the V4
   phase that would be holding the bag.

⚠️ What this file must NOT become: a second copy of `tools/lint_app_contract.py`. That
   tool already enforces the cross-app import boundary and runs inside the gate. Here we
   check that the things the inventory *counted on* are still there — a different claim.
"""
from __future__ import annotations

from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
KIEM_KE = GOC / "docs" / "auto_scan_video_v4" / "CAPABILITY_INVENTORY_V4.md"


def _ten_dinh_danh_chua(nguon: str, tu: str) -> bool:
    """Co ten DINH DANH nao chua `tu` khong. Comment/docstring khong tinh.

    Tach ra thanh ham rieng vi mot ly do duy nhat: de
    `test_bo_do_ABSENT_that_su_bat_duoc` chay duoc no tren mot mau co san loi.
    """
    import ast

    try:
        cay = ast.parse(nguon)
    except SyntaxError:
        return False
    for nut in ast.walk(cay):
        ten = ""
        if isinstance(nut, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            ten = nut.name
        elif isinstance(nut, ast.Name):
            ten = nut.id
        elif isinstance(nut, ast.Attribute):
            ten = nut.attr
        if ten and tu.lower() in ten.lower():
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  Be mat khai bao — co che ma ca ban kiem ke dua vao
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("app_slug", ["ltt_voice", "ltt_llm", "autosubvideo"])
def test_app_bi_asv_goi_deu_TU_KHAI_be_mat(app_slug):
    """Ba app Auto Scan goi sang deu phai tu khai `BE_MAT_CONG_KHAI`.

    🔑 Day la co che khien pha 02 ket luan "khong co reach-through nao". Neu mot
       trong ba app bo ban khai di, cac import cua ASV thanh reach-through THAT —
       va luc do ket luan cua ban kiem ke sai chu khong phai ma cua ASV sai.
    """
    mod = __import__(f"apps.{app_slug}", fromlist=["BE_MAT_CONG_KHAI"])
    be_mat = getattr(mod, "BE_MAT_CONG_KHAI", None)
    assert be_mat, f"apps/{app_slug} khong con tu khai be mat cong khai"
    assert all(isinstance(x, tuple) and len(x) == 2 for x in be_mat)


def test_moi_ten_ASV_dang_import_deu_nam_trong_be_mat_da_khai():
    """Doi chieu tung cap (module, ten) that su duoc dung voi ban khai cua chu.

    ⭐ `tools/lint_app_contract.py` kiem chieu "ai duoc goi ai". Phep kiem nay
       kiem chieu con lai: **cai ten cu the** ASV dung co con duoc chu no cong
       nhan khong. Mot app co the giu `BE_MAT_CONG_KHAI` ma van bo mot ten khoi
       do, va chieu do khong loi nao bao cho toi khi mot lan chay that no.
    """
    from apps import autosubvideo, ltt_llm, ltt_voice

    dang_dung = {
        "ltt_voice": {
            ("apps.ltt_voice", "sidecar_client"),          # giong_noi.py:83
            ("apps.ltt_voice.features", "chuan_hoa"),      # giong_noi.py:102
            ("apps.ltt_voice.features", "giai_giong"),     # giong_noi.py:102
            ("apps.ltt_voice", "text_pipeline"),           # giong_noi.py:133
            ("apps.ltt_voice", "features"),                # giong_noi.py:149
            ("apps.ltt_voice.tham_so_cong_khai", "TRAN_MOI_LUOT_SINH"),
            ("apps.ltt_voice.doc_man_api", "ma_giong_cua_toi"),   # gia.py:81
            ("apps.ltt_voice.lan_ngon_ngu", "LAN_HOP_LE"),  # ngon_ngu.py
        },
        "ltt_llm": {("apps.ltt_llm", "ngan_sach")},        # dich_thuat.py:64
        "autosubvideo": {
            ("apps.autosubvideo.transcription", "transcribe_file"),
        },
    }
    khai = {"ltt_voice": ltt_voice.BE_MAT_CONG_KHAI,
            "ltt_llm": ltt_llm.BE_MAT_CONG_KHAI,
            "autosubvideo": autosubvideo.BE_MAT_CONG_KHAI}

    for app_slug, dung in dang_dung.items():
        ngoai = dung - set(khai[app_slug])
        assert not ngoai, (
            f"ASV dung {sorted(ngoai)} cua {app_slug} ma be mat khong con khai — "
            f"day la reach-through THAT, doc lai CAPABILITY_INVENTORY_V4.md muc 12")


# ══════════════════════════════════════════════════════════════════════════════
#  Tien de cua tung ket luan SUFFICIENT
# ══════════════════════════════════════════════════════════════════════════════

def test_alias_doc_anh_van_ton_tai():
    """Pha 11 (SceneAnalysis) dua vao day. Mat alias = mat ca duong VLM.

    🔴 DOI CAU HOI 11/09/2026 (D02, dual-model 2.3). Ban cu hoi
       *"`ltt_llm_vision` con trong bang khong"* — mot cau hoi ve MOT CAI TEN,
       va cai ten do vua bi cat. Thu Pha 11 that su can la **co mot model doc
       duoc anh**, nen do dung dieu do: bang bi danh khong rong, va model mac
       dinh doc duoc anh theo ban khai cong khai.
    """
    from apps.ltt_llm.features import ALIAS_SANG_ID
    from apps.ltt_llm.manifest import MANIFEST

    assert ALIAS_SANG_ID, "bang bi danh rong = mat ca duong VLM"
    models = MANIFEST.tools[0].api_contract["models"]
    doc_anh = [ten for ten, spec in models.items()
               if (spec.get("constraints") or {}).get("reads_images")]
    assert doc_anh, "khong bi danh nao khai doc duoc anh"
    # ⛔ Id vendor khong duoc ro ra be mat khach; day chi kiem lop dem con day du.
    for ten, noi_bo in ALIAS_SANG_ID.items():
        assert ten != noi_bo


def test_duong_goi_LLM_khong_ep_content_thanh_chuoi():
    """VLM can `content` la mot LIST (van ban + anh). Neu tang duoi ep str, hong.

    ⭐ Chot bang CHU KY ham chu khong bang mot luot goi that: mot luot goi that
       can may B, va mot phep kiem doc trang thai may la mot phep kiem do cai may
       (AGENTS muc 4b). Chu ky noi du dieu can biet — `messages: list` di thang.
    """
    import inspect

    from platform_core.llm.cong_vlm import CongVlm

    tham_so = inspect.signature(CongVlm.chat).parameters
    assert "messages" in tham_so
    assert tham_so["messages"].annotation in (list, "list")


def test_duong_tai_len_ben_vung_van_con(  ):
    """G6 phu thuoc vao day. Ba ten nay la ca ke hoach thay `await video.read()`."""
    from platform_core import upload_sessions

    for ten in ("create", "upload_target", "confirm", "promote"):
        assert hasattr(upload_sessions, ten), f"upload_sessions mat {ten}"


def test_bo_ma_hoa_phan_cung_van_con():
    """Pha 17 goi ham nay cho preset `smart_localize`."""
    from platform_core import media

    assert callable(media.detect_gpu_encoder)
    assert callable(media.probe)


# ══════════════════════════════════════════════════════════════════════════════
#  Tien de cua tung ket luan EXTEND_OWNER_CONTRACT
# ══════════════════════════════════════════════════════════════════════════════

def test_catalog_giong_mau_co_du_thuoc_tinh_cho_AUTO_MATCH():
    """Pha 09 rang buoc giong theo dac diem nguoi noi — day la thu no khop VAO.

    🔴 Neu bo loc nay bien mat, `AUTO_MATCH` khong con gi de khop va se thoai hoa
       thanh "lay giong mac dinh" — dung su nham lan ma `ADR-V4-001` D-V4-04 cam.
       Phep kiem do o day, som, thay vi lo ra o pha 09 duoi dang mot stub xanh.
    """
    from apps.ltt_voice import giong_mau

    assert set(giong_mau.NHAN_GIOI) == {"nam", "nu"}
    assert set(giong_mau.NHAN_VUNG) == {"bac", "trung", "nam"}
    assert giong_mau.NHAN_PHONG_CACH
    assert callable(giong_mau.loc)
    assert giong_mau.DANH_SACH, "catalog giong mau rong"


# ══════════════════════════════════════════════════════════════════════════════
#  Tien de cua tung ket luan ABSENT
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_kiem_ke_ton_tai_va_ket_luan_duoc_ghi_ra():
    """Ban kiem ke la san pham cua pha 02; mat no la mat can cu cua moi pha sau."""
    assert KIEM_KE.exists()
    van_ban = KIEM_KE.read_text(encoding="utf-8")
    for tu in ("SUFFICIENT", "EXTEND_OWNER_CONTRACT", "ABSENT",
               "BE_MAT_CONG_KHAI", "APP_DUOC_DUNG_APP"):
        assert tu in van_ban


@pytest.mark.parametrize("ten_mien", [
    "SceneAnalysis", "ContentProfile", "EditPlan", "VoiceBinding", "DubbingFit"])
def test_mien_nghiep_vu_V4_chua_ton_tai_o_dau_ca(ten_mien):
    """ABSENT phai duoc CHUNG MINH, khong duoc gia dinh.

    `V4_CAPABILITY_FIRST`: *"A 'new code' recommendation without proof of absence
    fails the phase."* Day la bang chung do — quet ca `apps/` va `platform_core/`.

    ⭐ Phep kiem nay se **do** khi pha 11/12/09/15 dung chung. Do la dung: luc do
       ban kiem ke phai doi ABSENT thanh da-xay, va mot dong do la loi nhac.

    🔴 **BAN DAU PHEP KIEM NAY QUET VAN BAN THO, VA NO DO NGAY — VI CHINH TOI.**
       `hop_dong_v4.py` nhac `ContentProfile`/`EditPlan`/`DubbingFit` trong mot
       docstring giai thich vi sao ngon ngu dich bi khoa o `vi`. Ba cai ten do
       la **loi van**, khong phai ma chay duoc.

       Mot phep kiem "da xay chua" ma tra loi CO khi doc mot cau van la mot phep
       kiem sai chieu: no bien viec VIET TAI LIEU thanh mot vi pham. Nen no doc
       **AST**, va chi nhin ten dinh danh — class, ham, bien, thuoc tinh. Comment
       va docstring la `ast.Constant`, khong phai ten, nen chung khong tinh.
    """
    thay = []
    for goc in (GOC / "apps", GOC / "platform_core"):
        for tep in goc.rglob("*.py"):
            if "__pycache__" in tep.parts:
                continue
            if _ten_dinh_danh_chua(tep.read_text(encoding="utf-8", errors="ignore"),
                                   ten_mien):
                thay.append(str(tep.relative_to(GOC)))
    assert not thay, (
        f"{ten_mien} da xuat hien o {thay} — cap nhat CAPABILITY_INVENTORY_V4.md, "
        f"no van dang ghi ABSENT")


def test_bo_do_ABSENT_that_su_bat_duoc():
    """Chung minh bo do khong phai mot den xanh noi vao khong.

    ⛔ Khong co phep kiem nay thi `test_mien_nghiep_vu_V4_chua_ton_tai_o_dau_ca`
       xanh du `_ten_dinh_danh_chua` luon tra `False` — mot bo do bi hong va mot
       ket luan ABSENT dung trong y het nhau tu ben ngoai. `test_401` dung dung
       cap doi nay cho cac guard cua no.
    """
    # Ten trong MA -> phai bat duoc, o ca ba dang no co the xuat hien.
    assert _ten_dinh_danh_chua("class EditPlan:\n    pass\n", "EditPlan")
    assert _ten_dinh_danh_chua("def lam_edit_plan_v2(): pass", "edit_plan")
    assert _ten_dinh_danh_chua("x = ke_hoach.EditPlan", "EditPlan")

    # Ten trong LOI VAN -> KHONG duoc tinh. Day la ca ly do bo do doc AST.
    assert not _ten_dinh_danh_chua('"""Noi ve EditPlan va DubbingFit."""\nx = 1\n',
                                   "EditPlan")
    assert not _ten_dinh_danh_chua("# EditPlan se lam o pha 12\ny = 2\n", "EditPlan")
