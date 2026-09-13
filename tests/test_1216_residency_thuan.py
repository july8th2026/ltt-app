"""Residency 3090 (D01 B) — bảng `gpu_residency` (5.1) + máy trạng thái THUẦN (5.2).

Hai phần trong một tệp, đúng như plan Pha 5 xếp: phần **mô hình** chốt ba nghĩa vụ
của một bảng mới ở nền tảng (xếp loại lưu trữ · dọn hay lý do không cần · UNIQUE
vào drill khôi phục) cộng migration lên/xuống sạch; phần **thuần** chốt máy trạng
thái — không CSDL, không HTTP, không đồng hồ, nên nó kiểm được **không cần GPU**.
"""
from __future__ import annotations

import pathlib

import pytest

REV = "c7a3f1e5b904"
GOC = pathlib.Path(__file__).resolve().parents[1]
COT = {"nhom", "trang_thai", "tu_luc", "cua_so_bat_dau", "lan_nap_loi", "phien_ban"}


# ══════════════════════════════════════════════════════════════════════════════
# Phần A — bảng `gpu_residency` (Task 5.1)
# ══════════════════════════════════════════════════════════════════════════════

def test_migration_noi_dung_chuoi_va_mot_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config(str(GOC / "alembic.ini")))
    assert len(scripts.get_heads()) == 1, scripts.get_heads()
    rev = scripts.get_revision(REV)
    assert rev.down_revision == "b4d7f2c19e30"


@pytest.mark.timeout(240)
def test_len_roi_xuong_mot_buoc_sach_va_khop_mo_hinh(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    from platform_core.models import GpuResidency

    url = "sqlite:///" + (tmp_path / "mig.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.chdir(GOC)
    cfg = Config("alembic.ini")
    command.upgrade(cfg, REV)
    insp = inspect(create_engine(url))

    # Mô hình và migration phải nói CÙNG một tập cột — lệch là `create_all`
    # (test) và `alembic upgrade` (production) dựng hai lược đồ khác nhau.
    cot = {c["name"] for c in insp.get_columns("gpu_residency")}
    assert cot == COT
    assert {c.name for c in GpuResidency.__table__.columns} == cot
    uq = {u["name"] for u in insp.get_unique_constraints("gpu_residency")}
    assert "uq_gpu_residency_nhom" in uq

    command.downgrade(cfg, "-1")
    insp = inspect(create_engine(url))
    assert "gpu_residency" not in insp.get_table_names()


def test_governance_xep_loai_gpu_residency():
    """Không phải dữ liệu của khách (như `gpu_leases`): nó nói model nào đang cư
    trú trên một nhóm GPU — không có `user_id`, không có nội dung nào của khách.

    ⚠️ Lệch với chữ của plan (*"Store OPERATIONAL, dọn: không cần"*) và lệch có
    lý do **cơ học**: `test_211::test_operational_stores_all_declare_who_removes_them`
    đòi mọi Store OPERATIONAL phải khai một hàm dọn THẬT. Bảng này có đúng một
    dòng mỗi nhóm, ghi đè tại chỗ ⇒ không có gì để dọn, nên lời khai
    OPERATIONAL sẽ là một lời khai sai.
    """
    from platform_core.public_api import governance

    assert governance.unclassified(["gpu_residency"]) == []
    assert "gpu_residency" in governance.NOT_CUSTOMER_DATA
    assert governance.store_for("gpu_residency") is None


def test_drill_khoi_phuc_biet_uq_moi():
    """Lấy tên UNIQUE **từ chính mô hình**, không gõ lại chuỗi: đổi tên ràng buộc
    mà quên drill thì phép kiểm này đỏ, chứ không xanh vì đang so hai hằng số
    nhau. Và `assert ten` chặn kiểu xanh rỗng khi tập hợp co về rỗng.
    """
    from platform_core.models import GpuResidency

    van = (GOC / "tools" / "restore_drill_schema.py").read_text(encoding="utf-8")
    ten = {c.name for c in GpuResidency.__table__.constraints
           if (getattr(c, "name", "") or "").startswith("uq_")}
    assert ten, "bang gpu_residency khong con rang buoc UNIQUE nao"
    assert all(f'"{t}"' in van for t in ten), ten


# ══════════════════════════════════════════════════════════════════════════════
# Phần B — máy trạng thái thuần (Task 5.2)
#
# Ba mạch: (B1) từ vựng + bảng chuyển hợp lệ · (B2) hàm chuyển · (B3) câu hỏi
# admission. Không CSDL, không HTTP, không đồng hồ: thời gian vào bằng tham số.
# ══════════════════════════════════════════════════════════════════════════════

from platform_core.llm import residency as R  # noqa: E402


# ── B1. Từ vựng và bảng chuyển hợp lệ ────────────────────────────────────────

def test_tu_vung_du_va_khong_trung():
    assert len(set(R.TRANG_THAI)) == len(R.TRANG_THAI) == 7
    assert set(R.TRANG_THAI) == {R.LLM, R.XA_LLM, R.NHA_LLM, R.ANH, R.TRA_ANH,
                                R.NAP_LLM, R.LOI_NAP}
    assert len({R.NHA_LLM_LENH, R.NAP_LLM_LENH, R.FREE_COMFY_LENH}) == 3


def test_bang_chuyen_khai_du_moi_trang_thai_va_khong_tu_lap():
    assert set(R.CHUYEN_HOP_LE) == set(R.TRANG_THAI)
    for tu, den in R.CHUYEN_HOP_LE.items():
        assert den <= set(R.TRANG_THAI), (tu, den)
        assert tu not in den, f"{tu} tu lap: 'o lai' khong phai mot chuyen"


@pytest.mark.parametrize("tu,den", [
    # Đổi cư trú mà KHÔNG drain trước — chính là điều cả chương trình cấm (L-9).
    (R.LLM, R.NHA_LLM),
    (R.LLM, R.ANH),
    # Vẽ trước khi máy B xác nhận LTT-3.8 đã rời card ⇒ hai model một card.
    (R.XA_LLM, R.ANH),
    # Nạp LLM lại mà bỏ qua bước chờ lượt vẽ chạy hết ⇒ giết việc đang chạy.
    (R.ANH, R.NAP_LLM),
    # Khai "LLM đang cư trú" mà chưa nạp ⇒ admission mở cho một model không có.
    (R.TRA_ANH, R.LLM),
])
def test_chuyen_pha_bo_drain_khong_co_trong_bang(tu, den):
    assert den not in R.CHUYEN_HOP_LE[tu]


def test_moi_cap_ngoai_bang_deu_bi_may_tu_choi():
    """Bảng không phải tài liệu: `_sang` là cửa duy nhất đổi trạng thái, và nó
    NÉM với mọi cặp ngoài bảng. 7×7 cặp, trừ đường chéo và các cặp hợp lệ."""
    so_cam = 0
    for tu in R.TRANG_THAI:
        for den in R.TRANG_THAI:
            if tu == den or den in R.CHUYEN_HOP_LE[tu]:
                continue
            so_cam += 1
            with pytest.raises(ValueError):
                R._sang(R.TrangThai(ten=tu), den, 1.0)
    assert so_cam == 7 * 7 - 7 - sum(len(v) for v in R.CHUYEN_HOP_LE.values())
    assert so_cam >= 30, so_cam


def test_sang_dat_moc_thoi_gian_va_giu_phan_con_lai():
    tt = R.TrangThai(ten=R.NAP_LLM, tu_luc=5.0, cua_so_bat_dau=1.0, lan_nap_loi=2)
    moi = R._sang(tt, R.LOI_NAP, 99.0, lan_nap_loi=3)
    assert (moi.ten, moi.tu_luc, moi.lan_nap_loi) == (R.LOI_NAP, 99.0, 3)
    assert moi.cua_so_bat_dau == 1.0
    assert tt.ten == R.NAP_LLM, "TrangThai phai bat bien (frozen)"


# ── B2. Hàm chuyển `buoc_thuan` ──────────────────────────────────────────────

TS = R.ThamSoResidency()
BAY_GIO = 100.0


def qs(**k):
    """Quan sát "bình thường": LLM đang cư trú, rảnh, VRAM đầy của LLM."""
    base = dict(lease_llm=0, lease_anh=0, job_anh_cho=0, anh_bat_dau_trong_cua_so=0,
                nguoi_cho_llm=0, han_chot_llm_s=None, gateway_inflight_llm=0,
                llm_da_nap=True, vram_3090_mib=20000, nap_ket_qua="",
                lan_vao_anh_hong=0)
    base.update(k)
    return R.QuanSat(**base)


def tt0(ten):
    """Trạng thái vào bảng dưới: vào lúc 0, cửa sổ mở lúc 0, đã lỗi nạp một lần."""
    return R.TrangThai(ten=ten, tu_luc=0.0, cua_so_bat_dau=0.0, lan_nap_loi=1)


#: Một "sự kiện" ở máy này = một QUAN SÁT, vì máy không nhận sự kiện rời — nó đọc
#: sự thật rồi quyết. Mười ba quan sát dưới đây phủ mọi nhánh điều kiện của hàm.
SU_KIEN = {
    "rong": {},
    "anh_vao_hang": dict(job_anh_cho=1),
    "llm_con_lease": dict(job_anh_cho=1, lease_llm=1),
    "llm_con_inflight": dict(job_anh_cho=1, gateway_inflight_llm=1),
    # Không hỏi được máy B: mọi thứ về máy B là None.
    "may_b_im": dict(job_anh_cho=1, gateway_inflight_llm=None, llm_da_nap=None,
                     vram_3090_mib=None),
    "da_nha_xong": dict(job_anh_cho=1, llm_da_nap=False),
    "dang_ve": dict(lease_anh=1, llm_da_nap=False),
    "cua_so_het_tran": dict(job_anh_cho=2, lease_anh=1, anh_bat_dau_trong_cua_so=4,
                            nguoi_cho_llm=1, llm_da_nap=False),
    "han_chot_gap": dict(job_anh_cho=2, lease_anh=1, anh_bat_dau_trong_cua_so=1,
                         nguoi_cho_llm=1, han_chot_llm_s=150, llm_da_nap=False),
    "vram_con_ban": dict(llm_da_nap=False, vram_3090_mib=9000),
    "vram_sach": dict(llm_da_nap=False, vram_3090_mib=1500),
    "nap_xong": dict(nap_ket_qua="ok"),
    "nap_hong": dict(nap_ket_qua="loi"),
    # ── L-07, 13/09: phia anh KHONG DUNG DUOC ─────────────────────────────
    # Job anh van cho, may B im (khong hoi duoc) NHUNG ben goi da that bai
    # `tran_vao_anh_hong` lan lien tiep khi bat lai ComfyUI.
    "anh_hong_con_cho": dict(job_anh_cho=1, llm_da_nap=None,
                             lan_vao_anh_hong=TS.tran_vao_anh_hong),
    # Cung the, nhung mot luot ve dang chay ⇒ TUYET DOI khong duoc phat `nap_llm`.
    "anh_hong_dang_ve": dict(job_anh_cho=1, lease_anh=1, llm_da_nap=None,
                             lan_vao_anh_hong=TS.tran_vao_anh_hong),
}

_NHA = (R.NHA_LLM_LENH,)
_NAP = (R.NAP_LLM_LENH,)
_FREE = (R.FREE_COMFY_LENH,)

#: trạng thái → { sự kiện → (trạng thái sau, lệnh phát ra) } tại `BAY_GIO = 100`.
#: 7 × 15 = 105 ô, viết hết tay: ô nào "ở lại" cũng là một lời khai, không phải
#: một chỗ trống — đó là điểm khác giữa một bảng và một nhúm ví dụ.
BANG = {
    R.LLM: {
        "rong": (R.LLM, ()),
        # Có job ảnh xếp hàng là điều kiện DUY NHẤT rời `LLM`.
        "anh_vao_hang": (R.XA_LLM, ()),
        "llm_con_lease": (R.XA_LLM, ()),
        "llm_con_inflight": (R.XA_LLM, ()),
        "may_b_im": (R.XA_LLM, ()),
        "da_nha_xong": (R.XA_LLM, ()),
        "dang_ve": (R.LLM, ()),
        "cua_so_het_tran": (R.XA_LLM, ()),
        "han_chot_gap": (R.XA_LLM, ()),
        "vram_con_ban": (R.LLM, ()),
        "vram_sach": (R.LLM, ()),
        "nap_xong": (R.LLM, ()),
        "nap_hong": (R.LLM, ()),
        # L-07: phia anh khong dung duoc
        "anh_hong_con_cho": (R.LLM, ()),
        "anh_hong_dang_ve": (R.LLM, ()),
    },
    R.XA_LLM: {
        "rong": (R.LLM, ()),                       # job ảnh rút ⇒ huỷ việc đổi
        "anh_vao_hang": (R.NHA_LLM, _NHA),
        "llm_con_lease": (R.XA_LLM, ()),           # ⭐ drain: KHÔNG phát `nha`
        "llm_con_inflight": (R.XA_LLM, ()),        # ⭐ kể cả khi sổ lease rỗng
        "may_b_im": (R.XA_LLM, ()),                # ⭐ không đo được ⇒ chưa drain
        "da_nha_xong": (R.NHA_LLM, _NHA),
        "dang_ve": (R.NHA_LLM, _NHA),
        "cua_so_het_tran": (R.NHA_LLM, _NHA),
        "han_chot_gap": (R.NHA_LLM, _NHA),
        "vram_con_ban": (R.LLM, ()),
        "vram_sach": (R.LLM, ()),
        "nap_xong": (R.LLM, ()),
        "nap_hong": (R.LLM, ()),
        # L-07: phia anh khong dung duoc
        "anh_hong_con_cho": (R.NHA_LLM, _NHA),
        "anh_hong_dang_ve": (R.NHA_LLM, _NHA),
    },
    R.NHA_LLM: {
        # ⛔ BA Ô DƯỚI ĐỔI NGHĨA 13/09 (L-07), và đổi là ĐÚNG.
        #
        #    Cả ba đều có `job_anh_cho = 0` — tức **không còn việc ảnh nào**.
        #    Bản cũ "lặp lệnh tới khi thấy đã nhả": nhả card cho một việc không
        #    còn tồn tại, và ở lại đó mãi. Đó chính là ngõ cụt đã làm `ltt-3.8`
        #    chết 32 phút. Nay: việc ảnh rút hết ⇒ lui về `NAP_LLM`, lấy lại card.
        "rong": (R.NAP_LLM, _NAP),
        "anh_vao_hang": (R.NHA_LLM, _NHA),
        "llm_con_lease": (R.NHA_LLM, ()),
        "llm_con_inflight": (R.NHA_LLM, ()),
        "may_b_im": (R.NHA_LLM, ()),
        "da_nha_xong": (R.ANH, ()),                # máy B xác nhận ⇒ mở cửa sổ ảnh
        "dang_ve": (R.ANH, ()),
        "cua_so_het_tran": (R.ANH, ()),
        "han_chot_gap": (R.ANH, ()),
        # ⭐ Hai ô này cũng có `job_anh_cho = 0`, nên đường lui 1 thắng TRƯỚC
        #    nhánh `llm_da_nap is False → ANH`. Thứ tự ấy là cố ý: vào `ANH` khi
        #    không còn việc ảnh nào là bắt ComfyUI khởi động chỉ để đóng cửa sổ
        #    ngay lượt sau — và "bắt ComfyUI khởi động" đúng là bước đã gãy 404
        #    trong L-07. Không có việc thì đừng mở cửa.
        "vram_con_ban": (R.NAP_LLM, _NAP),
        "vram_sach": (R.NAP_LLM, _NAP),
        "nap_xong": (R.NAP_LLM, _NAP),
        "nap_hong": (R.NAP_LLM, _NAP),
        # L-07: phia anh khong dung duoc
        "anh_hong_con_cho": (R.NAP_LLM, _NAP),
        "anh_hong_dang_ve": (R.NHA_LLM, _NHA),
    },
    R.ANH: {
        "rong": (R.TRA_ANH, ()),                   # hết việc ảnh ⇒ đóng cửa sổ
        "anh_vao_hang": (R.ANH, ()),               # không ai chờ LLM ⇒ vẽ tiếp
        "llm_con_lease": (R.ANH, ()),
        "llm_con_inflight": (R.ANH, ()),
        "may_b_im": (R.ANH, ()),
        "da_nha_xong": (R.ANH, ()),
        "dang_ve": (R.ANH, ()),
        "cua_so_het_tran": (R.TRA_ANH, ()),        # 4 ảnh + có người chờ LLM
        "han_chot_gap": (R.TRA_ANH, ()),           # vẽ nữa là người chờ chết
        "vram_con_ban": (R.TRA_ANH, ()),
        "vram_sach": (R.TRA_ANH, ()),
        "nap_xong": (R.TRA_ANH, ()),
        "nap_hong": (R.TRA_ANH, ()),
        # L-07: phia anh khong dung duoc
        "anh_hong_con_cho": (R.ANH, ()),
        "anh_hong_dang_ve": (R.ANH, ()),
    },
    R.TRA_ANH: {
        "rong": (R.TRA_ANH, _FREE),                # VRAM còn của ảnh ⇒ dọn
        "anh_vao_hang": (R.TRA_ANH, _FREE),
        "llm_con_lease": (R.TRA_ANH, _FREE),
        "llm_con_inflight": (R.TRA_ANH, _FREE),
        "may_b_im": (R.TRA_ANH, _FREE),
        "da_nha_xong": (R.TRA_ANH, _FREE),
        "dang_ve": (R.TRA_ANH, ()),                # ⭐ lượt vẽ chạy tới hết
        "cua_so_het_tran": (R.TRA_ANH, ()),        # ⭐ không dọn VRAM dưới chân nó
        "han_chot_gap": (R.TRA_ANH, ()),
        "vram_con_ban": (R.TRA_ANH, _FREE),
        "vram_sach": (R.NAP_LLM, _NAP),            # sạch ⇒ nạp lại LTT-3.8
        "nap_xong": (R.TRA_ANH, _FREE),
        "nap_hong": (R.TRA_ANH, _FREE),
        # L-07: phia anh khong dung duoc
        "anh_hong_con_cho": (R.TRA_ANH, _FREE),
        "anh_hong_dang_ve": (R.TRA_ANH, ()),
    },
    R.NAP_LLM: {
        "rong": (R.NAP_LLM, ()),                   # đang nạp: chờ, không lệnh
        "anh_vao_hang": (R.NAP_LLM, ()),
        "llm_con_lease": (R.NAP_LLM, ()),
        "llm_con_inflight": (R.NAP_LLM, ()),
        "may_b_im": (R.NAP_LLM, ()),
        "da_nha_xong": (R.NAP_LLM, ()),
        "dang_ve": (R.NAP_LLM, ()),
        "cua_so_het_tran": (R.NAP_LLM, ()),
        "han_chot_gap": (R.NAP_LLM, ()),
        "vram_con_ban": (R.NAP_LLM, ()),
        "vram_sach": (R.NAP_LLM, ()),
        "nap_xong": (R.LLM, ()),
        "nap_hong": (R.LOI_NAP, ()),
        # L-07: phia anh khong dung duoc
        "anh_hong_con_cho": (R.NAP_LLM, ()),
        "anh_hong_dang_ve": (R.NAP_LLM, ()),
    },
    R.LOI_NAP: {
        "rong": (R.NAP_LLM, _NAP),                 # đã qua 30 s lùi ⇒ thử lại
        "anh_vao_hang": (R.NAP_LLM, _NAP),
        "llm_con_lease": (R.NAP_LLM, _NAP),
        "llm_con_inflight": (R.NAP_LLM, _NAP),
        "may_b_im": (R.NAP_LLM, _NAP),
        "da_nha_xong": (R.NAP_LLM, _NAP),
        "dang_ve": (R.LOI_NAP, ()),                # ⭐ không nạp lên card đang vẽ
        "cua_so_het_tran": (R.LOI_NAP, ()),
        "han_chot_gap": (R.LOI_NAP, ()),
        "vram_con_ban": (R.NAP_LLM, _NAP),
        "vram_sach": (R.NAP_LLM, _NAP),
        "nap_xong": (R.NAP_LLM, _NAP),
        "nap_hong": (R.NAP_LLM, _NAP),
        # L-07: phia anh khong dung duoc
        "anh_hong_con_cho": (R.NAP_LLM, _NAP),
        "anh_hong_dang_ve": (R.LOI_NAP, ()),
    },
}


@pytest.mark.parametrize("ten", list(BANG))
def test_bang_trang_thai_x_su_kien(ten):
    assert set(BANG[ten]) == set(SU_KIEN), f"{ten}: bang thieu su kien"
    for su_kien, mong in BANG[ten].items():
        moi, lenh = R.buoc_thuan(tt0(ten), qs(**SU_KIEN[su_kien]), TS, BAY_GIO)
        assert (moi.ten, lenh) == mong, f"{ten} + {su_kien}"


def test_bang_phu_het_91_o_va_moi_chuyen_hop_le_deu_song():
    assert len(SU_KIEN) == 15 and len(BANG) == 7
    assert sum(len(v) for v in BANG.values()) == 105
    # Mỗi chuyển trong `CHUYEN_HOP_LE` phải có ít nhất một ô của bảng đi qua nó —
    # một chuyển hợp lệ mà không quan sát nào sinh ra là mã chết.
    thay = {(tu, mong[0]) for tu, hang in BANG.items() for mong in hang.values()
            if mong[0] != tu}
    hop_le = {(tu, den) for tu, dens in R.CHUYEN_HOP_LE.items() for den in dens}
    assert thay == hop_le, f"lech: {hop_le ^ thay}"


# ── Các ca của plan (Step 1), giữ nguyên ý ───────────────────────────────────

def _kiem_khong_nha_khi_con_luot_chay():
    """Thân của phép kiểm bất biến số 1, tách ra để ĐỐI CHỨNG gọi lại được."""
    tt = R.TrangThai(ten=R.XA_LLM)
    for lease, inflight in ((1, 0), (0, 1), (0, None), (2, 3)):
        moi, lenh = R.buoc_thuan(
            tt, qs(job_anh_cho=1, lease_llm=lease, gateway_inflight_llm=inflight),
            TS, 10)
        assert R.NHA_LLM_LENH not in lenh and moi.ten == R.XA_LLM, (lease, inflight)


def test_khong_bao_gio_nha_llm_khi_con_luot_chay():
    _kiem_khong_nha_khi_con_luot_chay()


def test_doi_chung_phep_kiem_nha_llm_bat_duoc_viec_go_phanh(monkeypatch):
    """Plan §5.2: *"đổi điều kiện XA_LLM thành chỉ kiểm `lease_llm == 0` ⇒ ĐỎ"*.

    Gỡ đúng nửa phanh ấy (bỏ vế in-flight của gateway) và phép kiểm trên PHẢI đỏ.
    Không có ô này thì không ai biết phép kiểm kia có bắt được gì.
    """
    monkeypatch.setattr(R, "da_drain_xong", lambda quan_sat: quan_sat.lease_llm == 0)
    with pytest.raises(AssertionError):
        _kiem_khong_nha_khi_con_luot_chay()


def test_chu_trinh_day_du():
    tt = R.TrangThai()
    tt, lenh = R.buoc_thuan(tt, qs(job_anh_cho=1), TS, 0)
    assert tt.ten == R.XA_LLM
    tt, lenh = R.buoc_thuan(tt, qs(job_anh_cho=1), TS, 1)
    assert (tt.ten, lenh) == (R.NHA_LLM, (R.NHA_LLM_LENH,))
    tt, lenh = R.buoc_thuan(tt, qs(job_anh_cho=1, llm_da_nap=False), TS, 2)
    assert tt.ten == R.ANH and tt.cua_so_bat_dau == 2
    tt, lenh = R.buoc_thuan(tt, qs(llm_da_nap=False), TS, 200)
    assert tt.ten == R.TRA_ANH
    tt, lenh = R.buoc_thuan(tt, qs(llm_da_nap=False, vram_3090_mib=9000), TS, 201)
    assert lenh == (R.FREE_COMFY_LENH,) and tt.ten == R.TRA_ANH
    tt, lenh = R.buoc_thuan(tt, qs(llm_da_nap=False, vram_3090_mib=1500), TS, 202)
    assert (tt.ten, lenh) == (R.NAP_LLM, (R.NAP_LLM_LENH,))
    tt, lenh = R.buoc_thuan(tt, qs(nap_ket_qua="ok"), TS, 250)
    assert (tt.ten, tt.lan_nap_loi) == (R.LLM, 0)


def test_cua_so_dong_som_theo_han_chot_nguoi_cho_llm():
    """1 ảnh đã vào, còn ảnh chờ, người chờ LLM còn 150 s.

    150 − 16,3 (nạp lại, G4) − 110 (một ảnh, ANH_NOI_BO) − 30 (biên) = −6,3 ⇒ vẽ
    thêm một ảnh nữa là người chờ chết vì hết trần, nên cửa sổ đóng SỚM hơn trần
    của D01.
    """
    tt = R.TrangThai(ten=R.ANH, cua_so_bat_dau=0)
    moi, _ = R.buoc_thuan(tt, qs(job_anh_cho=3, lease_anh=1,
                                 anh_bat_dau_trong_cua_so=1, nguoi_cho_llm=1,
                                 han_chot_llm_s=150), TS, 60)
    assert moi.ten == R.TRA_ANH


def test_han_chot_du_rong_thi_ve_tiep_va_nguong_dung_la_16_3():
    """Ngưỡng đóng sớm = `t_nap_llm_s + t_anh_uoc_s + bien_s`. Ca này ghim nó ở
    đúng con số ĐO ĐƯỢC: 156,3 s. Nếu ai đưa 45,0 cũ về (⇒ 185,0) thì một hạn
    chót 160 s sẽ bị coi là gấp và cửa sổ đóng sớm vô cớ — ô này đỏ.
    """
    tt = R.TrangThai(ten=R.ANH, cua_so_bat_dau=0)
    chung = dict(job_anh_cho=3, lease_anh=1, anh_bat_dau_trong_cua_so=1,
                 nguoi_cho_llm=1)
    nguong = TS.t_nap_llm_s + TS.t_anh_uoc_s + TS.bien_s
    assert nguong == pytest.approx(156.3)
    rong, _ = R.buoc_thuan(tt, qs(han_chot_llm_s=nguong + 1, **chung), TS, 60)
    gap, _ = R.buoc_thuan(tt, qs(han_chot_llm_s=nguong - 1, **chung), TS, 60)
    assert (rong.ten, gap.ten) == (R.ANH, R.TRA_ANH)


def test_khong_ai_cho_llm_thi_ve_tiep_qua_tran():
    tt = R.TrangThai(ten=R.ANH, cua_so_bat_dau=0)
    moi, _ = R.buoc_thuan(tt, qs(job_anh_cho=9, anh_bat_dau_trong_cua_so=7),
                          TS, 2000)
    assert moi.ten == R.ANH, "work-conserving: khong ai cho thi dung dung xe"


def test_tra_anh_cho_luot_ve_dang_chay():
    tt = R.TrangThai(ten=R.TRA_ANH)
    moi, lenh = R.buoc_thuan(tt, qs(lease_anh=1, vram_3090_mib=100), TS, 5)
    assert moi.ten == R.TRA_ANH and lenh == ()


def test_nap_loi_lui_dan():
    tt = R.TrangThai(ten=R.NAP_LLM)
    tt, _ = R.buoc_thuan(tt, qs(nap_ket_qua="loi"), TS, 0)
    assert (tt.ten, tt.lan_nap_loi) == (R.LOI_NAP, 1)
    tt2, lenh = R.buoc_thuan(tt, qs(), TS, 29)
    assert tt2.ten == R.LOI_NAP and lenh == ()
    tt3, lenh = R.buoc_thuan(tt, qs(), TS, 30)
    assert (tt3.ten, lenh) == (R.NAP_LLM, (R.NAP_LLM_LENH,))


def test_lui_dan_gap_doi_va_cham_tran_16_lan():
    assert [R.lui_nap_s(R.TrangThai(lan_nap_loi=n), TS) for n in (1, 2, 3, 5)] == [
        30.0, 60.0, 120.0, 480.0]
    assert R.lui_nap_s(R.TrangThai(lan_nap_loi=9), TS) == 480.0
    assert R.lui_nap_s(R.TrangThai(lan_nap_loi=40), TS) == 480.0


def test_nap_ket_qua_cu_lam_phong_lui_dan_nen_may_b_phai_dat_lai():
    """Hợp đồng của người gọi, ghim lại vì nó VÔ HÌNH nếu chỉ đọc hàm.

    `nap_ket_qua` phải là kết quả của lượt nạp do lệnh `nap_llm` GẦN NHẤT khởi
    động; máy B đặt lại `""` khi nhận lệnh mới (Task 5.4 chạy nạp ở nền). Nếu nó
    giữ `"loi"` cũ thì máy quay vòng `LOI_NAP → NAP_LLM → LOI_NAP` và
    `lan_nap_loi` phồng lên — không sai an toàn, nhưng thời gian lùi chạm trần
    480 s vì một con số cũ, chứ không vì một lần nạp hỏng thật.
    """
    tt = R.TrangThai(ten=R.LOI_NAP, tu_luc=0.0, lan_nap_loi=1)
    tt, _ = R.buoc_thuan(tt, qs(nap_ket_qua="loi"), TS, 30)
    assert tt.ten == R.NAP_LLM
    tt, _ = R.buoc_thuan(tt, qs(nap_ket_qua="loi"), TS, 30)
    assert (tt.ten, tt.lan_nap_loi) == (R.LOI_NAP, 2)


def test_trang_thai_la_thi_nem():
    with pytest.raises(ValueError):
        R.buoc_thuan(R.TrangThai(ten="mot_trang_thai_khong_co"), qs(), TS, 1)


# ── Quét vét cạn: ba bất biến LỆNH trên toàn không gian quan sát ─────────────

def _quet_bat_bien():
    """Ba bất biến, kiểm trên 7 × 5.184 × 2 điểm chứ không trên vài ví dụ.

    Lệnh mới là thứ giết việc đang chạy, nên bất biến đặt ở TẦNG LỆNH:
      1. `nha_llm` ⇒ 0 lease LLM và gateway báo đúng 0 in-flight;
      2. `nap_llm` / `free_comfy` ⇒ không lượt vẽ nào đang chạy;
      3. vào `ANH` ⇒ máy B đã xác nhận LTT-3.8 KHÔNG còn nạp.
    Cộng luật bảng: không bước nào sinh ra một chuyển ngoài `CHUYEN_HOP_LE`.
    """
    import itertools

    thay = set()
    coi = itertools.product(
        (0, 1), (0, 1), (0, 2), (0, 4), (0, 1), (None, 150.0),
        (0, 1, None), (True, False, None), (None, 1500, 20000), ("", "ok", "loi"))
    for (ll, la, jc, abd, ncl, hc, gi, dn, vr, nk) in coi:
        quan_sat = R.QuanSat(lease_llm=ll, lease_anh=la, job_anh_cho=jc,
                             anh_bat_dau_trong_cua_so=abd, nguoi_cho_llm=ncl,
                             han_chot_llm_s=hc, gateway_inflight_llm=gi,
                             llm_da_nap=dn, vram_3090_mib=vr, nap_ket_qua=nk)
        for ten in R.TRANG_THAI:
            for bay_gio in (5.0, 1000.0):
                moi, lenh = R.buoc_thuan(tt0(ten), quan_sat, TS, bay_gio)
                assert moi.ten == ten or moi.ten in R.CHUYEN_HOP_LE[ten], (ten, moi)
                thay.add((ten, moi.ten))
                if R.NHA_LLM_LENH in lenh:
                    assert ll == 0 and gi == 0, (ten, quan_sat)
                if R.NAP_LLM_LENH in lenh or R.FREE_COMFY_LENH in lenh:
                    assert la == 0, (ten, lenh, quan_sat)
                if moi.ten == R.ANH and ten != R.ANH:
                    assert dn is False, (ten, quan_sat)
    return thay


def test_quet_vet_can_ba_bat_bien_lenh():
    thay = _quet_bat_bien()
    hop_le = {(tu, den) for tu, dens in R.CHUYEN_HOP_LE.items() for den in dens}
    # Đối chứng cho chính phép quét: nếu không gian quét co lại (một chiều bị gõ
    # cứng) thì tập chuyển thấy được sẽ thiếu, và ô này đỏ thay vì xanh rỗng.
    assert hop_le <= {c for c in thay if c[0] != c[1]}


def test_doi_chung_go_phanh_drain_lam_quet_do(monkeypatch):
    monkeypatch.setattr(R, "da_drain_xong", lambda quan_sat: quan_sat.lease_llm == 0)
    with pytest.raises(AssertionError):
        _quet_bat_bien()


def test_doi_chung_go_phanh_luot_ve_dang_chay_lam_quet_do(monkeypatch):
    """Phanh chiều NGƯỢC lại: nạp 16 GB trọng số lên card đang vẽ, hay dọn VRAM
    của ComfyUI đang vẽ, cũng là giết việc đang chạy — bằng OOM."""
    monkeypatch.setattr(R, "dang_ve_anh", lambda quan_sat: False)
    with pytest.raises(AssertionError):
        _quet_bat_bien()


# ── B3. Câu hỏi mà admission đặt ra (luật 0 của `luat_nhan`, Task 5.3) ───────

def test_mo_cho():
    assert R.mo_cho(R.LLM, "mac_dinh") and not R.mo_cho(R.XA_LLM, "mac_dinh")
    assert R.mo_cho(R.ANH, "theo_lo") and not R.mo_cho(R.TRA_ANH, "theo_lo")


def test_bang_mo_cho_day_du_7x2_va_dung_hai_o_mo():
    mo = {(ten, vai) for ten in R.TRANG_THAI for vai in R.VAI_TRO
          if R.mo_cho(ten, vai)}
    assert mo == {(R.LLM, R.MAC_DINH), (R.ANH, R.THEO_LO)}, mo
    # Năm trạng thái còn lại đóng cả hai cửa — đó là ý nghĩa của "đang đổi cư trú".
    dong = [ten for ten in R.TRANG_THAI
            if not any(R.mo_cho(ten, v) for v in R.VAI_TRO)]
    assert dong == [R.XA_LLM, R.NHA_LLM, R.TRA_ANH, R.NAP_LLM, R.LOI_NAP]


def test_khong_trang_thai_nao_mo_ca_hai_vai_tro():
    """Bất biến cốt tuỷ: hai model không bao giờ cùng được nhận lượt mới trên một
    card 24 GB. Nếu một trạng thái mở cả hai thì admission cấp suất cho cả LTT-3.8
    và model ảnh cùng lúc, và ca đó kết thúc bằng OOM ở giữa việc của khách."""
    for ten in R.TRANG_THAI:
        assert sum(R.mo_cho(ten, v) for v in R.VAI_TRO) <= 1, ten


def test_khong_mot_buoc_nao_lat_duoc_cu_tru():
    """Mọi chuyển hợp lệ phải đi qua ít nhất một trạng thái ĐÓNG cả hai cửa: không
    cặp `a → b` nào vừa mở `mac_dinh` ở `a` vừa mở `theo_lo` ở `b` (và ngược lại).

    Đây là chứng minh cơ học cho "drain trước, đổi sau" ở tầng ADMISSION — không
    có nó, một bước có thể chuyển quyền nhận lượt từ bên này sang bên kia trong
    khi lượt của bên này còn đang chạy.
    """
    for tu, dens in R.CHUYEN_HOP_LE.items():
        for den in dens:
            assert not (R.mo_cho(tu, R.MAC_DINH) and R.mo_cho(den, R.THEO_LO)), (tu, den)
            assert not (R.mo_cho(tu, R.THEO_LO) and R.mo_cho(den, R.MAC_DINH)), (tu, den)


def test_vai_tro_la_thi_nem_con_trang_thai_la_thi_dong():
    """Hai kiểu "lạ", hai cách xử KHÁC nhau, và lý do nằm ở hậu quả:

    · trạng thái lạ ⇒ **đóng** (fail-closed). Trọng tài sẽ ném ở `buoc_thuan` nên
      cái lạ ấy vẫn có người báo động; admission chỉ cần đừng mở cửa.
    · vai trò lạ ⇒ **ném**. Một `vai_tro` gõ sai trong manifest (`"theolo"`) mà
      trả về False sẽ làm app đó không bao giờ được nhận — một app chết ÂM THẦM,
      loại hỏng đắt nhất để truy.
    """
    assert not R.mo_cho("mot_trang_thai_khong_co", R.MAC_DINH)
    assert not R.mo_cho("mot_trang_thai_khong_co", R.THEO_LO)
    for vai in ("", "theolo", "mac dinh", "anh"):
        with pytest.raises(ValueError):
            R.mo_cho(R.LLM, vai)
