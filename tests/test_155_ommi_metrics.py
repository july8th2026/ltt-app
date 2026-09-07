"""
test_155 - H19.8: đo job OMMI chạy bao lâu, hỏng bao nhiêu, tốn bao nhiêu.

Hai quyết định thiết kế mà test này bảo vệ:

1. **P95, không phải trung bình.** Trung bình bị kéo xuống bởi số đông job
   nhanh nên luôn nói "mọi thứ ổn"; người dùng bỏ đi vì lần chờ *tệ*. Một bộ đo
   báo trung bình sẽ khiến người vận hành yên tâm sai.

2. **Theo từng người dùng.** Gộp toàn hệ thống vừa trái Q31 (credit tính theo
   từng người) vừa để người này nhìn thấy khối lượng việc của người khác.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.prompt_ai_ommi.services import metrics as m

A = "user-a"
B = "user-b"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


def _job(db, owner=A, *, giay=10, status="done", viec="director", credit=5,
         tuoi_ngay=1, app="prompt_ai_ommi"):
    from platform_core.models import Job
    t0 = datetime.now(timezone.utc) - timedelta(days=tuoi_ngay)
    row = Job(user_id=owner, app_slug=app, job_type="prompt_ai_ommi.director",
              params={"operation": viec}, status=status,
              result={"credit_cost": credit},
              created_at=t0, started_at=t0,
              finished_at=t0 + timedelta(seconds=giay))
    db.add(row)
    db.commit()
    return row


# ── Phân vị ─────────────────────────────────────────────────────────────────

def test_p95_khong_bi_so_dong_job_nhanh_keo_xuong():
    """Đây là lý do chọn P95 thay vì trung bình."""
    # 90 job nhanh + 10 job chậm. KHÔNG dùng đúng 95/5: khi ấy P95 rơi ngay
    # ranh giới hai nhóm và phép nội suy trả về một giá trị ở giữa — đúng về
    # toán nhưng không minh hoạ được điều đang muốn nói.
    mau = [1.0] * 90 + [100.0] * 10
    trung_binh = sum(mau) / len(mau)
    p95 = m._phan_vi(mau, 0.95)
    assert trung_binh < 12, "dựng mẫu sai — trung bình phải nhỏ"
    assert p95 >= 90, (
        f"P95={p95} không phản ánh lần chờ tệ; báo trung bình ({trung_binh:.1f}) "
        f"sẽ khiến người vận hành yên tâm sai")


def test_phan_vi_chiu_duoc_mot_mau_va_khong_mau():
    """"Một job trong 30 ngày" là trạng thái bình thường của người dùng mới —
    `statistics.quantiles` ném trong trường hợp đó."""
    assert m._phan_vi([], 0.95) == 0.0
    assert m._phan_vi([7.0], 0.95) == 7.0


def test_phan_vi_noi_suy_chu_khong_lay_bua_mot_phan_tu():
    assert m._phan_vi([0.0, 10.0], 0.5) == 5.0
    assert m._phan_vi([0.0, 100.0], 0.95) == 95.0


# ── Cô lập theo người dùng ──────────────────────────────────────────────────

def test_chi_dem_job_cua_chinh_nguoi_goi(db):
    _job(db, A, giay=5)
    _job(db, B, giay=500)
    ra = m.job_metrics(db, A)
    assert ra["tong_job"] == 1, "đếm cả job của người khác"
    assert ra["p95_giay"] < 100


def test_khong_dem_job_cua_app_khac(db):
    """App khác dùng chung bảng jobs; đếm nhầm là báo sai cả thời gian lẫn tiền."""
    _job(db, A, giay=5)
    _job(db, A, giay=900, app="taoanh")
    ra = m.job_metrics(db, A)
    assert ra["tong_job"] == 1


def test_khong_dem_job_ngoai_cua_so_thoi_gian(db):
    _job(db, A, tuoi_ngay=1)
    _job(db, A, tuoi_ngay=90)
    assert m.job_metrics(db, A, days=30)["tong_job"] == 1
    assert m.job_metrics(db, A, days=365)["tong_job"] == 2


# ── Tách theo loại việc ─────────────────────────────────────────────────────

def test_tach_theo_loai_viec_de_biet_cham_o_dau(db):
    _job(db, A, viec="director", giay=2, credit=3)
    _job(db, A, viec="render", giay=120, credit=20)
    _job(db, A, viec="render", giay=140, credit=20)

    ra = m.job_metrics(db, A)
    theo = {x["viec"]: x for x in ra["theo_viec"]}
    assert theo["render"]["tong"] == 2 and theo["director"]["tong"] == 1
    assert theo["render"]["p95_giay"] > theo["director"]["p95_giay"]
    assert theo["render"]["credit"] == 40
    assert ra["tong_credit"] == 43


def test_ti_le_loi_tinh_san_va_khong_chia_cho_khong(db):
    _job(db, A, viec="render", status="error")
    _job(db, A, viec="render", status="done")
    theo = {x["viec"]: x for x in m.job_metrics(db, A)["theo_viec"]}
    assert theo["render"]["ti_le_loi"] == 0.5
    # Không có job nào thì vẫn phải trả về cấu trúc hợp lệ, không nổ.
    assert m.job_metrics(db, B)["theo_viec"] == []
    assert m.job_metrics(db, B)["p95_giay"] == 0.0


def test_job_chua_chay_xong_khong_lam_hong_phep_do(db):
    """Job đang chạy chưa có `finished_at` — trừ hai giá trị None sẽ ném."""
    from platform_core.models import Job
    db.add(Job(user_id=A, app_slug="prompt_ai_ommi",
               job_type="prompt_ai_ommi.director", params={"operation": "render"},
               status="running", created_at=datetime.now(timezone.utc),
               started_at=datetime.now(timezone.utc), finished_at=None))
    db.commit()
    ra = m.job_metrics(db, A)
    assert ra["tong_job"] == 1
    theo = {x["viec"]: x for x in ra["theo_viec"]}
    assert theo["render"]["so_do_duoc"] == 0, "đếm cả job chưa xong vào thời gian chạy"


def test_dem_du_xong_loi_huy(db):
    _job(db, A, viec="render", status="done")
    _job(db, A, viec="render", status="error")
    _job(db, A, viec="render", status="cancelled")
    theo = {x["viec"]: x for x in m.job_metrics(db, A)["theo_viec"]}
    assert (theo["render"]["xong"], theo["render"]["loi"],
            theo["render"]["huy"]) == (1, 1, 1)


# ── Diễn tập khôi phục (H19.8) ──────────────────────────────────────────────

def test_drill_khoi_phuc_kiem_dung_cac_rang_buoc_song_con():
    """Drill cũ chỉ dump/restore một bảng giả — chứng minh `pg_dump` chạy được,
    KHÔNG chứng minh lược đồ thật khôi phục được.

    Ràng buộc mất sau restore là lỗi âm thầm nhất: dữ liệu vẫn vào được, chỉ là
    không còn gì chặn trùng lặp — ví dụ hai worker cùng giành một GPU.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    src = (root / "tools" / "restore_drill_schema.py").read_text(encoding="utf-8")

    assert "alembic" in src and "upgrade" in src, (
        "drill không dựng lược đồ thật bằng alembic")
    for ten in ("uq_gpu_lease_host_uuid", "uq_ommi_scene_version"):
        assert ten in src, f"drill không kiểm ràng buộc sống còn {ten}"
    assert "table_constraints" in src, "drill không đối chiếu số ràng buộc"


def test_moi_rang_buoc_unique_song_con_deu_nam_trong_drill():
    """Thêm một ràng buộc UNIQUE mới mà quên đưa vào drill thì lần khôi phục
    sau sẽ không ai kiểm nó."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    src = (root / "tools" / "restore_drill_schema.py").read_text(encoding="utf-8")

    from platform_core.registry import load_app_tables
    from platform_core.db import Base
    import platform_core.models  # noqa: F401
    load_app_tables()

    thieu, so_uq = [], 0
    for bang in Base.metadata.tables.values():
        for rb in bang.constraints:
            ten = getattr(rb, "name", None)
            if ten and str(ten).startswith("uq_"):
                so_uq += 1
                if str(ten) not in src:
                    thieu.append(str(ten))

    # ⛔ ĐỐI CHỨNG (Bẫy 31) — thêm 07/09/2026.
    #
    #    Vòng lặp lái bằng `Base.metadata.tables`, mà bảng của app chỉ có mặt
    #    sau `load_app_tables()`. Nếu lời gọi ấy hỏng **im lặng** — một app
    #    không import được, một `tables.py` đổi tên — thì tập bảng rỗng hoặc
    #    thiếu, `thieu` rỗng, và phép kiểm XANH trong khi drill không kiểm gì.
    #
    # 🔴 Đây là kiểu xanh rỗng khó thấy nhất: nó không đến từ mã của phép kiểm
    #    mà từ một **bước nạp** phía trước nó.
    #
    #    Đo 07/09/2026: 75 bảng, 28 ràng buộc `uq_`.
    assert so_uq >= 28, (
        f"chi thay {so_uq} rang buoc `uq_` tren {len(Base.metadata.tables)} "
        f"bang — mong doi >= 28. Nghi `load_app_tables()` khong nap du: mot "
        f"drill kiem tren tap bang thieu la mot drill khong bao dam gi.")

    assert not thieu, (
        f"ràng buộc UNIQUE không được drill kiểm: {sorted(set(thieu))}")
