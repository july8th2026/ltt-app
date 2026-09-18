"""test_1453 — R-16 cảnh báo TTFT/nạp nguội máy B theo ngày. Thuần: không mạng, không SSH, không thư thật.

Mỗi ngưỡng có ca ĐỐI CHỨNG (ngay dưới ngưỡng ⇒ không cảnh báo), và chống spam kiểm bằng hai lần gửi.
"""
from __future__ import annotations

import base64
import datetime as dt
import json

from tools import canh_bao_ttft_b as C
from tools import tong_hop_ttft_b as T

NGAY = dt.date(2026, 9, 18)
TTL = 1800


def _d(luc, model="qwen38-api", stream=True, ttft=2.0, ma=200):
    return (f"{luc},123 INFO llm_gateway.so " + json.dumps(
        {"model": model, "stream": stream, "ttft_s": ttft, "ma_http": ma, "huy": False}) + "\n")


def _am(n, ttft, model="qwen38-api", gio=10):
    """n lượt stream ấm cách nhau 10 s, sau một lượt mồi (lượt mồi = nguội, TTFT nhỏ)."""
    dong = [_d(f"2026-09-18 {gio:02d}:00:00", model=model, ttft=1.0)]
    t0 = dt.datetime(2026, 9, 18, gio, 0, 10)
    for i in range(n):
        dong.append(_d((t0 + dt.timedelta(seconds=10 * i)).strftime("%Y-%m-%d %H:%M:%S"),
                       model=model, ttft=ttft))
    return dong


def _nguoi(n, ttft, model="qwen38-api"):
    """n lượt stream nguội: mỗi lượt cách lượt trước 1 giờ (> TTL)."""
    return [_d(f"2026-09-18 {h:02d}:30:00", model=model, ttft=ttft) for h in range(1, 1 + n)]


def _kq(dong):
    return C.danh_gia_ngay(T.doc_so(dong), NGAY, TTL)


def test_p95_am_vuot_va_doi_chung():
    assert [v["loai"] for v in _kq(_am(40, 46.0))["vuot"]] == ["p95_am"]
    assert _kq(_am(40, 45.0))["vuot"] == []          # đúng bằng ngưỡng: không vượt


def test_p95_khong_kich_khi_it_luot():
    """< 20 lượt ấm: p95 nearest-rank = max ⇒ in số nhưng không cảnh báo."""
    kq = _kq(_am(C.TOI_THIEU_LUOT_P95 - 1, 90.0))
    assert kq["vuot"] == []
    assert kq["theo_model"]["qwen38-api"]["ttft_am_p95_s"] == 90.0


def test_luot_nguoi_khong_vao_p95_am():
    """Nạp nguội chậm không kéo p95 ẤM lên (đó là ngưỡng kia)."""
    kq = _kq(_am(40, 5.0) + [_d("2026-09-18 20:00:00", ttft=99.0)])   # sau > TTL ⇒ nguội
    s = kq["theo_model"]["qwen38-api"]
    assert s["ttft_am_p95_s"] == 5.0
    assert s["nguoi_stream_ttft_tren_20s"] == 1


def test_nguoi_vuot_va_doi_chung():
    assert [v["loai"] for v in _kq(_nguoi(6, 25.0))["vuot"]] == ["nguoi"]
    assert _kq(_nguoi(5, 25.0))["vuot"] == []         # đúng 5: không vượt (> 5)
    assert _kq(_nguoi(6, 20.0))["vuot"] == []         # TTFT đúng 20 s: không tính (> 20)


def test_nguoi_theo_tung_model():
    dong = _nguoi(3, 30.0, "qwen38-api") + _nguoi(3, 30.0, "qwen35-api")
    assert _kq(dong)["vuot"] == []                    # 3 + 3 không gộp thành 6


def test_cua_dong_bo_khong_kich():
    """Cửa đồng bộ: ttft_s = cả lượt ⇒ chỉ tham khảo, không kích ngưỡng nào."""
    dong = [_d(f"2026-09-18 {h:02d}:30:00", stream=False, ttft=300.0) for h in range(1, 12)]
    kq = _kq(dong)
    assert kq["vuot"] == []
    assert kq["theo_model"]["qwen38-api"]["nguoi_dong_bo_tham_khao"] == 11


def test_ngay_truoc_la_ngu_canh_khong_bi_dem():
    """Lượt ngày trước quyết định lượt đầu ngày có nguội không, nhưng không bị đếm vào ngày."""
    dong = [_d("2026-09-17 23:59:00", ttft=80.0), _d("2026-09-18 00:05:00", ttft=30.0)]
    s = _kq(dong)["theo_model"]["qwen38-api"]
    assert s["luot_stream"] == 1 and s["nguoi_stream"] == 0      # 6 phút < TTL ⇒ ấm
    dong = [_d("2026-09-17 20:00:00"), _d("2026-09-18 00:05:00", ttft=30.0)]
    assert _kq(dong)["theo_model"]["qwen38-api"]["nguoi_stream_ttft_tren_20s"] == 1


def test_luot_dau_cua_so_khong_co_truoc_la_nguoi():
    s = _kq([_d("2026-09-18 08:00:00", ttft=30.0)])["theo_model"]["qwen38-api"]
    assert s["nguoi_stream"] == 1


def test_ma_khac_200_khong_tinh():
    kq = _kq(_am(40, 50.0)[:1] + [_d(f"2026-09-18 10:00:{10 + i:02d}", ttft=50.0, ma=429)
                                   for i in range(40)])
    assert kq["vuot"] == []


# ── gửi + chống spam ─────────────────────────────────────────────────────────
class _Hop:
    def __init__(self):
        self.thu = []

    def send(self, email):
        self.thu.append(email)


def test_gui_mot_lan_moi_dieu_kien(tmp_path):
    kq = _kq(_am(40, 46.0) + _nguoi(6, 25.0, model="qwen35-api"))
    hop, p = _Hop(), tmp_path / "tt.json"
    da = C.gui(kq, tt_path=p, to="truc@example.invalid", mailer=hop, hom_nay=NGAY)
    assert len(da) == 2 and len(hop.thu) == 1                    # một thư cho mọi điều kiện
    assert "qwen38-api/p95_am" in hop.thu[0].subject and "qwen35-api/nguoi" in hop.thu[0].subject
    assert C.gui(kq, tt_path=p, to="truc@example.invalid", mailer=hop, hom_nay=NGAY) == []
    assert len(hop.thu) == 1                                     # lần hai: im
    # điều kiện MỚI cùng ngày vẫn gửi, và chỉ nó
    kq2 = _kq(_am(40, 46.0) + _nguoi(6, 25.0, model="qwen35-api") + _nguoi(6, 25.0, model="m3"))
    assert [v["model"] for v in C.gui(kq2, tt_path=p, to="x@example.invalid",
                                      mailer=hop, hom_nay=NGAY)] == ["m3"]


def test_gui_loi_khong_ghi_trang_thai(tmp_path):
    class _Hong:
        def send(self, email):
            raise OSError("hop thu hong")

    kq, p = _kq(_nguoi(6, 25.0)), tmp_path / "tt.json"
    try:
        C.gui(kq, tt_path=p, to="x@example.invalid", mailer=_Hong(), hom_nay=NGAY)
    except OSError:
        pass
    assert not p.exists()                                        # lần sau còn gửi lại được


def test_vang_email_tat_mem(tmp_path, monkeypatch):
    from platform_core.public_api.ops_alerts import EMAIL_ENV
    monkeypatch.delenv(EMAIL_ENV, raising=False)
    hop = _Hop()
    assert C.gui(_kq(_nguoi(6, 25.0)), tt_path=tmp_path / "t.json", mailer=hop) == []
    assert hop.thu == [] and not (tmp_path / "t.json").exists()


def test_trang_thai_tia_muc_cu(tmp_path):
    p = tmp_path / "t.json"
    C.ghi_trang_thai(p, {"da_gui": {"2026-06-01|m|nguoi": "x", "2026-09-17|m|nguoi": "y"}}, NGAY)
    assert list(json.loads(p.read_text(encoding="utf-8"))["da_gui"]) == ["2026-09-17|m|nguoi"]


def test_main_chay_thu_khong_gui_khong_ghi(tmp_path, capsys, monkeypatch):
    so = tmp_path / "gateway_err.log"
    so.write_text("".join(_nguoi(6, 25.0)), encoding="utf-8")
    tt = tmp_path / "tt.json"
    monkeypatch.setattr(C, "gui", lambda *a, **k: (_ for _ in ()).throw(AssertionError("khong duoc gui")))
    assert C.main(["--so", str(so), "--ngay", "2026-09-18", "--trang-thai", str(tt)]) == 1
    assert "CHAY THU" in capsys.readouterr().out
    assert not tt.exists()


def test_main_doi_chung_khong_vuot(tmp_path):
    so = tmp_path / "gateway_err.log"
    so.write_text("".join(_am(40, 10.0) + _nguoi(5, 25.0, model="qwen35-api")), encoding="utf-8")
    assert C.main(["--so", str(so), "--ngay", "2026-09-18", "--gui",
                   "--trang-thai", str(tmp_path / "tt.json")]) == 0
    assert not (tmp_path / "tt.json").exists()


# ── đường đọc máy B ──────────────────────────────────────────────────────────
def test_lenh_b_chi_doc_va_dung_ngay():
    ps = C.lenh_ps_doc_so(NGAY)
    assert "2026-09-17" in ps and "2026-09-18" in ps and "gateway_err*.log" in ps
    for dong_tu in ("Remove-", "Set-", "Stop-", "Restart-", "Out-File", "Clear-", "Move-", "New-Item"):
        assert dong_tu not in ps


def test_doc_tu_b_giai_ma_va_bao_loi_ssh():
    goi = {}

    class _R:
        def __init__(self, ma, out=b""):
            self.returncode, self.stdout = ma, out

    def chay(lenh, **k):
        goi["lenh"] = lenh
        return _R(0, _d("2026-09-18 10:00:00").encode("utf-8"))

    assert len(T.doc_so(C.doc_tu_b(NGAY, chay=chay))) == 1
    ma = goi["lenh"][-1].rsplit(" ", 1)[1]
    assert base64.b64decode(ma).decode("utf-16-le") == C.lenh_ps_doc_so(NGAY)
    assert "BatchMode=yes" in goi["lenh"]

    import pytest
    with pytest.raises(RuntimeError):
        C.doc_tu_b(NGAY, chay=lambda *a, **k: _R(255))
