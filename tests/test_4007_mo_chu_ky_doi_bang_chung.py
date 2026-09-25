"""Mở một chu kỳ đã trả tiền thì phải CHỨNG MINH được là tiền đã rời tài khoản.

## Vì sao có tệp này

🔴 Rà soát 25/09/2026 tìm ra **ba lỗ tiền, và cả ba là MỘT lỗ**: `billing.mo_chu_ky`
   — hàm *cấp thời gian đã trả tiền* — tin lời người gọi. Nó nhận `gia` rồi đẩy
   `paid_until` thêm một chu kỳ, xoá `xoa_sau`, và phát sự kiện `thu_phi` với đúng
   số `gia` đó. Nó ⛔ không hề hỏi sổ credit xem có đồng nào rời tài khoản chưa.

   Ba người gọi, hai người gọi sai:

   1. **Nút "Cài lại"** (`routes.py` `/cai-lai` → job `vps.rebuild` → `_dung_lai`
      → `_tao_may` → `_quyet_toan`). Route ⛔ không đặt giữ chỗ nào, nên trong
      `_quyet_toan` điều kiện `so_da_giu(job_id) > 0` trượt ⇒ bước trừ tiền bị bỏ
      qua, nhưng `mo_chu_ky(gia=1490)` **vẫn chạy**: `paid_until` +30 ngày,
      `xoa_sau = None`, và một sự kiện `thu_phi` ghi `credit=1490` **cho khoản
      chưa bao giờ bị trừ**. Khách số dư 0, máy sắp bị xoá, bấm "Cài lại" là máy
      sống thêm một tháng — bấm lại thì sống mãi. Không phép kiểm nào phủ.
   2. **Đường gia hạn** (`thu_mot_chu_ky`): `credit.tru` trả `True/False`, và giá
      trị đó **bị vứt**. `tru` thất bại (một `giu_cho` song song vừa ăn hết số dư)
      thì chu kỳ vẫn mở miễn phí. `tru` tự chặn số dư âm, nên thiệt hại ⛔ không
      phải số dư âm — nó là một chu kỳ miễn phí cộng một dòng sổ nói dối.
   3. Bất kỳ người gọi **tương lai** nào. Đây là chỗ đáng sợ nhất: vá hai người
      gọi trên là hai lần sửa, và người gọi thứ tư lại sai y như vậy.

⇒ Nên thuốc ⛔ không phải vá từng người gọi. Nó là một **bất biến ở biên**:
  `mo_chu_ky` tự tra sổ credit, và từ chối mở một chu kỳ CÓ PHÍ khi không tìm ra
  bút toán tương ứng. Người gọi ⛔ không thể nói dối, vì nó không còn được hỏi.

## Bằng chứng có đúng hai dạng

* `job:<job_id>`      — đã quyết toán một giữ chỗ (đường tạo máy)
* `but_toan:<id>`     — một dòng trừ tiền cụ thể trong sổ (đường gia hạn)
* `""` (rỗng)         — hợp lệ **chỉ khi** `gia == 0`, tức chu kỳ miễn phí

Cả hai dạng đều được **tra lại trong sổ**, không phải nhận lời.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

LUC = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


class _May:
    def __init__(self, paid_until=None, xoa_sau=None):
        self.id = "may-4007"
        self.user_id = "u-4007"
        self.plan_id = "vps-nho"
        self.dia_them_gb = 0
        self.bang_thong_byte = 0
        self.paid_until = paid_until
        self.xoa_sau = xoa_sau
        self.trang_thai = "dang_chay"


class _Ctx:
    def __init__(self, job_id=""):
        self.job_id = job_id


@pytest.fixture()
def su_kien(monkeypatch):
    """Bắt mọi sự kiện `billing` ghi, để đọc được cái nói dối."""
    from apps.vps.services import billing

    da_ghi: list[tuple] = []
    monkeypatch.setattr(billing, "ghi_su_kien",
                        lambda db, may_id, ten, **kw: da_ghi.append((ten, kw)))
    return da_ghi


# ── 1. Bất biến ở biên: không bằng chứng thì không mở chu kỳ có phí ──────────

def test_gia_duong_ma_KHONG_co_bang_chung_thi_NEM(su_kien):
    from apps.vps.services import billing

    may = _May()
    with pytest.raises(billing.ChuaThanhToanError):
        billing.mo_chu_ky(None, may, gia=1490, bang_chung="", now=LUC)
    assert may.paid_until is None, "khong duoc noi han khi nem"
    assert su_kien == [], "khong duoc phat thu_phi khi nem"


def test_bang_chung_bia_ra_cung_bi_TU_CHOI(su_kien, monkeypatch):
    """Người gọi ⛔ không thể tự khai là đã trả tiền — hàm đi tra sổ."""
    from platform_core import credit

    from apps.vps.services import billing

    monkeypatch.setattr(credit, "da_thu_cho_job", lambda db, job_id: 0)
    may = _May()
    with pytest.raises(billing.ChuaThanhToanError):
        billing.mo_chu_ky(None, may, gia=1490, bang_chung="job:khong-co-that",
                          now=LUC)
    assert may.paid_until is None


def test_tra_it_hon_gia_thi_cung_bi_TU_CHOI(su_kien, monkeypatch):
    from platform_core import credit

    from apps.vps.services import billing

    monkeypatch.setattr(credit, "da_thu_cho_job", lambda db, job_id: 1000)
    with pytest.raises(billing.ChuaThanhToanError):
        billing.mo_chu_ky(None, _May(), gia=1490, bang_chung="job:j1", now=LUC)


def test_co_bang_chung_dung_thi_mo_duoc_va_phat_thu_phi(su_kien, monkeypatch):
    from platform_core import credit

    from apps.vps.services import billing

    monkeypatch.setattr(credit, "da_thu_cho_job", lambda db, job_id: 1490)
    may = _May()
    assert billing.mo_chu_ky(None, may, gia=1490, bang_chung="job:j1",
                             now=LUC) == 1490
    assert may.paid_until is not None and may.xoa_sau is None
    assert [ten for ten, _ in su_kien] == ["thu_phi"]


def test_chu_ky_MIEN_PHI_khong_can_bang_chung_va_KHONG_phat_thu_phi(su_kien):
    """`gia == 0` là máy nội bộ / bảng giá chưa đặt. Không có gì để chứng minh,
    và ⛔ cũng không được phát `thu_phi` — sự kiện đó là **khoá** của vòng quét
    `bao_tri._hoan_tien_may_hong`, phát khống là mở đường hoàn một khoản chưa
    bao giờ thu."""
    from apps.vps.services import billing

    may = _May()
    assert billing.mo_chu_ky(None, may, gia=0, bang_chung="", now=LUC) == 0
    assert may.paid_until is not None
    assert su_kien == []


# ── 2. "Cài lại" ⛔ không được tặng một chu kỳ ───────────────────────────────

def _quyet_toan_voi(monkeypatch, *, job_id, da_giu):
    from platform_core import credit

    from apps.vps import jobs
    from apps.vps.services import billing

    monkeypatch.setattr(credit, "so_da_giu", lambda db, jid: da_giu)
    monkeypatch.setattr(credit, "da_thu_cho_job", lambda db, jid: da_giu)
    monkeypatch.setattr(
        credit, "quyet_toan",
        lambda db, uid, jid, gia: type("R", (), {"charged_credit": da_giu})())
    monkeypatch.setattr(billing, "credit_thang", lambda *a, **kw: 1490)
    han_cu = LUC + timedelta(days=3)
    may = _May(paid_until=han_cu, xoa_sau=LUC + timedelta(days=10))
    jobs._quyet_toan(None, may, _Ctx(job_id))
    return may, han_cu


def test_cai_lai_KHONG_noi_han_va_KHONG_xoa_moc_xoa(monkeypatch, su_kien):
    """Job có `job_id` nhưng KHÔNG có giữ chỗ = đường `vps.rebuild`. Cài lại là
    **dựng lại máy**, ⛔ không phải một chu kỳ mới: khách đã trả cho kỳ đang chạy,
    nên đẩy hạn là tặng, mà thu thêm một tháng cũng sai."""
    may, han_cu = _quyet_toan_voi(monkeypatch, job_id="job-rebuild", da_giu=0)
    assert may.paid_until == han_cu, "cai lai khong duoc doi han"
    assert may.xoa_sau is not None, "cai lai khong duoc xoa moc xoa"
    assert su_kien == [], "khong duoc phat thu_phi cho khoan khong thu"


def test_tao_may_that_co_giu_cho_thi_van_thu_va_mo_chu_ky(monkeypatch, su_kien):
    may, han_cu = _quyet_toan_voi(monkeypatch, job_id="job-tao", da_giu=1490)
    assert may.paid_until != han_cu and may.xoa_sau is None
    assert [ten for ten, _ in su_kien] == ["thu_phi"]


def test_khong_co_job_id_thi_mo_chu_ky_MIEN_PHI_chu_khong_phat_thu_phi(
        monkeypatch, su_kien):
    """Máy cũ tạo trước 23/09 / gọi ngoài hàng đợi: cố ý mở chu kỳ không thu.
    Nhưng phải mở với `gia=0` — bản cũ truyền cả giá vào nên sổ sách nói dối."""
    may, han_cu = _quyet_toan_voi(monkeypatch, job_id="", da_giu=0)
    assert may.paid_until != han_cu, "may cu van duoc mo chu ky"
    assert su_kien == [], "nhung KHONG duoc phat thu_phi"


# ── 3. Đường gia hạn phải tôn trọng kết quả của `credit.tru` ─────────────────

def test_tru_that_bai_thi_KHONG_mo_chu_ky(monkeypatch, su_kien):
    """`credit.tru` trả `False` khi số dư không đủ (một `giu_cho` song song vừa
    ăn hết). Bản cũ vứt giá trị đó ⇒ chu kỳ mở miễn phí. Nay phải `ThieuCreditError`
    để `chay_mot_vong` treo máy — đúng đường đã có sẵn."""
    from platform_core import credit

    from apps.vps.services import billing

    monkeypatch.setattr(billing, "credit_thang", lambda *a, **kw: 1490)
    monkeypatch.setattr(credit, "so_du", lambda db, uid: 5000)
    monkeypatch.setattr(credit, "tru_co_but_toan",
                        lambda db, uid, so, **kw: None)
    may = _May(paid_until=LUC)
    # ⚠️ `billing` có `ThieuCreditError` RIÊNG (không phải của `credit`), và đó là
    #    lớp mà `chay_mot_vong` bắt để treo máy — nên phải đúng lớp này.
    with pytest.raises(billing.ThieuCreditError):
        billing.thu_mot_chu_ky(None, may, now=LUC)
    assert may.paid_until == LUC, "khong duoc noi han khi chua tru duoc"
    assert su_kien == []


def test_tru_thanh_cong_thi_mo_chu_ky_voi_bang_chung_but_toan(monkeypatch,
                                                             su_kien):
    from platform_core import credit

    from apps.vps.services import billing

    monkeypatch.setattr(billing, "credit_thang", lambda *a, **kw: 1490)
    monkeypatch.setattr(credit, "so_du", lambda db, uid: 5000)
    monkeypatch.setattr(credit, "tru_co_but_toan",
                        lambda db, uid, so, **kw: type("E", (), {"id": "bt-1"})())
    monkeypatch.setattr(credit, "so_da_tru_cua_but_toan",
                        lambda db, bt_id, uid: 1490)
    may = _May(paid_until=LUC)
    assert billing.thu_mot_chu_ky(None, may, now=LUC) == 1490
    assert may.paid_until != LUC
    assert [ten for ten, _ in su_kien] == ["thu_phi"]
