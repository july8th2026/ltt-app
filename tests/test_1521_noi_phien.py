"""test_1521 — `tools/noi_phien.py`: một phiên khách → mọi lượt, ghép bốn sổ. (T4 P2)

Thiết kế: `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` §4 (P2), §5.

Công cụ CHỈ ĐỌC trả lời *"lượt X trên máy B thuộc phiên nào của khách nào, tốn
bao nhiêu, chờ bao lâu?"* bằng cách nối `public_api_requests` (phiên, mã lượt)
→ `llm_waiters` (chờ/chạy/token/TTFB) → `credit_entries` (tiền) → dòng sổ B
(`llm_gateway.so`, khoá `"ma"`).

Chốt:
  1. `--phien` luôn kèm khách: hai khách trùng chuỗi phiên KHÔNG lẫn nhau.
  2. Một mã lượt có thể có NHIỀU dòng sổ B (A xếp lại khi B 429) ⇒ lấy hết,
     đúng thứ tự thời gian.
  3. Dòng sổ B của mã KHÔNG thuộc phiên không được ghép vào (đối chứng âm).
  4. `--ma` đi ngược từ một dòng sổ B về khách/phiên.
  5. Tiền = −Σ delta của `credit_entries` theo `job_id`; không có bút toán ⇒ None.
  6. Không ghi gì vào CSDL.

Đối chứng (tiêm lỗi, chạy tay khi viết): bỏ lọc `user_id` trong `gom` ⇒ (1) ĐỎ;
bỏ lọc tập mã trong `doc_so_b` ⇒ (3) ĐỎ.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

PHIEN = "829c76f3-5d2a-4b1e-9c3f-38eea5feef82"
MA1 = "st:" + "a1" * 16
MA2 = "st:" + "b2" * 16
MA_KHAC = "st:" + "c3" * 16      # lượt của khách B — cùng chuỗi phiên


def _session():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


@pytest.fixture()
def so(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "np.db").as_posix())
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.models import CreditEntry, LlmWaiter
    from platform_core.public_api import request_log
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    now = datetime(2026, 9, 19, 3, 0, tzinfo=timezone.utc)
    a = tao_nguoi_dung(db, email="a@example.com", password="a-good-password-12")
    b = tao_nguoi_dung(db, email="b@example.com", password="a-good-password-12")
    db.flush()
    for i, (uid, ma, st) in enumerate([(a.id, MA1, 200), (a.id, MA2, 200),
                                       (b.id, MA_KHAC, 200)]):
        request_log.record(db, request_id=f"r{i}", user_id=uid, method="POST",
                           route="/api/v1/messages", status=st, ma_luot=ma,
                           phien_khach=PHIEN, ung_dung_khach="claude-cli/2.1.275",
                           now=now + timedelta(seconds=i))
    # Lượt 429 phòng đầy của A: có phiên, KHÔNG có mã lượt.
    request_log.record(db, request_id="r9", user_id=a.id, method="POST",
                       route="/api/v1/messages", status=429, code="capacity_unavailable",
                       phien_khach=PHIEN, now=now + timedelta(seconds=9))
    db.add(LlmWaiter(id="w1", resource="ltt_38_3090", user_id=a.id, request_id=MA1,
                     model="qwen38-api", trang_thai="xong", ket_qua="xong",
                     created_at=now, admitted_at=now + timedelta(seconds=2),
                     finished_at=now + timedelta(seconds=12),
                     token_vao=1200, token_ra=300, token_cache=800, ttfb_s=1.5))
    db.add(LlmWaiter(id="w2", resource="ltt_38_3090", user_id=a.id, request_id=MA2,
                     model="qwen38-api", trang_thai="xong", ket_qua="loi",
                     created_at=now, admitted_at=now, finished_at=now))
    for uid, ma, d in [(a.id, MA1, -10), (a.id, MA1, +4), (b.id, MA_KHAC, -7)]:
        db.add(CreditEntry(user_id=uid, delta=d, job_id=ma,
                           kind="hold" if d < 0 else "refund"))
    db.commit()
    log_b = tmp_path / "gateway_err.log"
    dong = [
        ("2026-09-19 10:00:01,100", {"ma": MA1, "ma_http": 429, "ket_thuc": "ban",
                                     "ttft_s": None, "huy": False}),
        ("2026-09-19 10:00:03,200", {"ma": MA1, "ma_http": 200, "ket_thuc": "stop",
                                     "ttft_s": 0.8, "huy": False}),
        ("2026-09-19 10:00:04,000", {"ma": MA_KHAC, "ma_http": 200,
                                     "ket_thuc": "stop", "ttft_s": 9.9, "huy": False}),
    ]
    log_b.write_text(
        "rac khong phai dong so\n"
        + "".join(f"{t} INFO llm_gateway.so {json.dumps(d, sort_keys=True)}\n"
                  for t, d in dong),
        encoding="utf-8")
    yield db, a.id, b.id, log_b
    _close(gen)
    dbmod.reset_engine()


def test_phien_chi_lay_luot_cua_dung_khach(so):
    from tools import noi_phien

    db, a_id, _b_id, _log = so
    luot = noi_phien.gom(db, user_id=a_id, phien=PHIEN)
    assert [x["ma_luot"] for x in luot] == [MA1, MA2, ""], luot
    assert MA_KHAC not in {x["ma_luot"] for x in luot}, "lan luot cua khach khac"


def test_phien_bat_buoc_kem_khach(so):
    from tools import noi_phien

    db, *_ = so
    with pytest.raises(ValueError):
        noi_phien.gom(db, phien=PHIEN)


def test_ghep_waiter_va_tien(so):
    from tools import noi_phien

    db, a_id, *_ = so
    l1, l2, l9 = noi_phien.gom(db, user_id=a_id, phien=PHIEN)
    assert l1["model"] == "qwen38-api" and l1["ket_qua"] == "xong"
    assert (l1["cho_s"], l1["chay_s"]) == (2.0, 10.0)
    assert (l1["token_vao"], l1["token_ra"], l1["token_cache"], l1["ttfb_s"]) == (
        1200, 300, 800, 1.5)
    assert l1["credit_thu"] == 6
    # Lượt không đo được: NULL giữ nguyên là None, không thành 0.
    assert l2["token_ra"] is None and l2["credit_thu"] is None
    # Lượt 429 không mã: không có dòng chờ, không tiền.
    assert l9["status"] == 429 and l9["model"] is None and l9["credit_thu"] is None


def test_so_b_lay_moi_dong_cua_ma_va_bo_ma_ngoai_tap(so):
    from tools import noi_phien

    db, a_id, _b, log_b = so
    luot = noi_phien.gom(db, user_id=a_id, phien=PHIEN)
    so_b = noi_phien.doc_so_b([log_b], {x["ma_luot"] for x in luot if x["ma_luot"]})
    assert set(so_b) == {MA1}, "dong so B cua ma ngoai phien bi ghep vao"
    assert [d["ma_http"] for d in so_b[MA1]] == [429, 200], (
        "phai lay MOI dong cua mot ma (A xep lai khi B 429), dung thu tu")
    noi_phien.ghep_so_b(luot, so_b)
    assert len(luot[0]["so_b"]) == 2 and luot[1]["so_b"] == []


def test_ma_di_nguoc_ve_khach_va_phien(so):
    from tools import noi_phien

    db, _a, b_id, _log = so
    (x,) = noi_phien.gom(db, ma=MA_KHAC)
    assert x["user_id"] == b_id and x["phien_khach"] == PHIEN


def test_cli_in_duoc_va_khong_ghi_csdl(so, capsys, monkeypatch):
    from platform_core.public_api.tables import ApiRequestLog
    from tools import noi_phien

    db, a_id, _b, log_b = so
    truoc = db.query(ApiRequestLog).count()
    ma = noi_phien.main(["--phien", PHIEN, "--user-id", a_id,
                         "--so-b", str(log_b)])
    out = capsys.readouterr().out
    assert ma == 0
    assert MA1 in out and "ttft=0.8" in out and MA_KHAC not in out
    db.expire_all()
    assert db.query(ApiRequestLog).count() == truoc


def test_cli_phien_khong_khach_thi_tu_choi(so, capsys):
    from tools import noi_phien

    assert noi_phien.main(["--phien", PHIEN]) == 2
