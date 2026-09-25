"""Vòng chụp ảnh hằng tuần ⛔ không được là mã chết — trang bán đã hứa nó.

## Ca thật, tìm ra khi rà soát 25/09/2026

`bao_tri.mot_luot` đặt `client = None` một cách **cố ý**, kèm chú thích giải thích
vì sao: *"Never route pinned resources through the global/default compute
endpoint"* — mỗi máy ghim một hồ sơ hạ tầng riêng, nên không có, và không được có,
một client dùng chung.

Rồi nó gọi `_chup_anh_den_han(db, client)`, và hàm đó mở đầu bằng:

    if db is None or client is None:
        return 0

⇒ Cả vòng lặp là **mã chết**. Trang bán khoe *"Ảnh chụp hằng tuần"*, trang máy
  khoe *"Ảnh chụp gần nhất"*, và ⛔ không ảnh nào từng được chụp.

⚠️ Và thân vòng lặp **đã** tự lo đúng chuyện đó từ trước: nó phân giải client
   **theo từng máy** (`backend_factory.compute_backend(profiles.pinned_profile(...))`)
   rồi mới `if selected is None: continue`. Nên cái cửa ở đầu hàm ⛔ không bảo vệ
   thêm điều gì — nó chỉ chặn trước khi tới chỗ đã được bảo vệ.

## Lớp lỗi: một cửa hỏi SAI CÂU, và một phép kiểm chốt cửa đó lại

`test_289` có một ca tên `test_chua_cau_hinh_proxmox_thi_KHONG_danh_dau_da_chup`
với `_chup_anh_den_han(None, None) == 0`. Ý định của nó **đúng và phải giữ**: đánh
dấu "đã chụp" mà chưa chụp là ghi vào sổ một bản không tồn tại, và khách chỉ phát
hiện lúc cần khôi phục — tức lúc tệ nhất.

Nhưng nó chốt ý định đó **bằng cách gọi với `client=None`**, tức bằng chính hình
dạng mà đường chạy thật luôn đi qua. ⇒ Một phép kiểm **xanh** đang giữ một vòng
lặp **chết**, và nó xanh mãi mãi vì nó chứng minh đúng cái nó gây ra.

⭐ Hai câu hỏi khác nhau bị gộp vào một điều kiện:
   * *"có CSDL không"* — không thì thật sự không làm gì được;
   * *"có client dùng chung không"* — nay là **không**, theo thiết kế.
"""
from __future__ import annotations

from datetime import datetime, timezone

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


class _May:
    def __init__(self, may_id, ho_so=None):
        self.id = may_id
        self.vmid = 204
        self.trang_thai = "dang_chay"
        self.sao_luu_luc = None
        self.infrastructure_profile_id = ho_so


class _Scalars:
    """Đủ giao diện mà các vòng quét của `mot_luot` dùng: lặp, `.first()`, `.all()`."""

    def __init__(self, cac_may):
        self._cac = list(cac_may)

    def __iter__(self):
        return iter(self._cac)

    def first(self):
        return None            # khong co ho so mac dinh -> cac vong khac bo qua

    def all(self):
        return list(self._cac)


class _Db:
    def __init__(self, cac_may):
        self._may = cac_may
        self.so_lan_commit = 0

    def execute(self, _stmt):
        may = self._may

        class _R:
            # `mot_luot` còn gọi vài vòng dọn khác (console, thao tác quá hạn);
            # chúng đọc `rowcount`/`scalar`. Con giả phải trả lời được, nếu không
            # phép kiểm đỏ vì **con giả thiếu**, không vì mã sai — và một phép
            # kiểm đỏ sai lý do thì không ai đọc nó nữa.
            rowcount = 0

            @staticmethod
            def scalars():
                return _Scalars(may)

            @staticmethod
            def scalar():
                return 0

            @staticmethod
            def first():
                return None

            @staticmethod
            def all():
                return []
        return _R()

    def commit(self):
        self.so_lan_commit += 1


def _canh(monkeypatch, cac_may, *, co_client_theo_ho_so=True):
    """Dựng cảnh: mọi máy đều tới hạn chụp, và việc chụp luôn thành công."""
    from apps.vps import bao_tri, profiles
    from apps.vps.services import backend_factory, sao_luu

    da_chup: list[str] = []
    monkeypatch.setattr(sao_luu, "den_han_chup", lambda may, now=None: True)
    monkeypatch.setattr(sao_luu, "chup_va_don",
                        lambda client, may, now=None: f"anh-{may.id}")
    monkeypatch.setattr(profiles, "pinned_profile", lambda db, may: object())
    monkeypatch.setattr(
        backend_factory, "compute_backend",
        lambda _p: type("B", (), {"client": object() if co_client_theo_ho_so
                                  else None})())
    monkeypatch.setattr(bao_tri.billing, "ghi_su_kien",
                        lambda db, may_id, ten, **kw: da_chup.append(may_id))
    return bao_tri, da_chup


# ── 1. Đường chạy THẬT: không có client dùng chung, máy ghim hồ sơ ───────────

def test_client_dung_chung_la_None_van_phai_CHUP(monkeypatch):
    """Đúng hình dạng mà `mot_luot` gọi: `client=None`, máy ghim hồ sơ riêng."""
    may = _May("may-1", ho_so="ho-so-1")
    bao_tri, da_chup = _canh(monkeypatch, [may])

    n = bao_tri._chup_anh_den_han(_Db([may]), None, now=NOW)

    assert n == 1, "vong chup anh phai chay khi client dung chung la None"
    assert da_chup == ["may-1"]
    assert may.sao_luu_luc == NOW


def test_mot_luot_truyen_dung_gia_tri_ma_ham_kia_phai_nhan_duoc(monkeypatch):
    """Chốt chỗ NỐI: giá trị `mot_luot` truyền phải là giá trị hàm kia làm việc được.

    🔴 Đây là chỗ bản cũ hỏng, và hai đầu đều "đúng" khi xét riêng: `mot_luot`
       truyền `None` có lý do (không được có client dùng chung), `_chup_anh_den_han`
       từ chối `None` cũng có vẻ có lý. Chỉ cái **nối** giữa chúng là sai, nên một
       phép kiểm gọi hàm trực tiếp ⛔ không bao giờ thấy.

    ⚠️ Phạm vi của phép kiểm này **hẹp và tôi khai ra**: nó chỉ chốt *giá trị được
       truyền*. Nó ⛔ không chạy hết `mot_luot` — vòng đó gọi cả chục phép quét
       khác, và một con giả đủ cho tất cả sẽ đỏ vì **con giả thiếu** chứ không vì
       mã sai. Sự thật cần chốt ở đây là một: `None`. Việc `None` có chạy được hay
       không thì ca ở trên đã đo bằng đường thật.
    """
    may = _May("may-2", ho_so="ho-so-1")
    bao_tri, _ = _canh(monkeypatch, [may])
    goi_that = {}

    def _theo_doi(db_, client_, *, now=None):
        goi_that["client"] = client_
        return 0

    monkeypatch.setattr(bao_tri, "_chup_anh_den_han", _theo_doi)
    monkeypatch.setattr(bao_tri, "_dong_bo_bang_thong_pinned", lambda _db: 0)
    monkeypatch.setattr(bao_tri.billing, "thu_phi_dinh_ky",
                        lambda _db, now=None, khi_treo=None: {"da_thu": 0,
                                                             "da_treo": 0})
    try:
        bao_tri.mot_luot(_Db([may]), now=NOW)
    except Exception:                    # noqa: BLE001 - xem docstring, pham vi hep
        pass

    assert "client" in goi_that, "`mot_luot` khong goi vong chup anh nua?"
    assert goi_that["client"] is None, (
        "`mot_luot` truyen mot client dung chung — chu thich cua no noi ro la "
        "khong duoc, va ca tren chung minh `None` la gia tri lam viec duoc")


# ── 2. Ý định CŨ phải còn nguyên: chưa chụp thì ⛔ không đánh dấu ────────────

def test_may_KHONG_ghim_ho_so_va_khong_co_client_thi_KHONG_danh_dau(monkeypatch):
    """Ý định của `test_289` được giữ, nhưng chốt bằng một hình dạng KHÁC.

    Đánh dấu "đã chụp" mà chưa chụp là ghi vào sổ một bản không tồn tại.
    """
    may = _May("may-3", ho_so=None)          # khong ghim ho so
    bao_tri, da_chup = _canh(monkeypatch, [may])

    assert bao_tri._chup_anh_den_han(_Db([may]), None, now=NOW) == 0
    assert da_chup == [] and may.sao_luu_luc is None


def test_ho_so_khong_cho_ra_client_thi_cung_KHONG_danh_dau(monkeypatch):
    may = _May("may-4", ho_so="ho-so-1")
    bao_tri, da_chup = _canh(monkeypatch, [may], co_client_theo_ho_so=False)

    assert bao_tri._chup_anh_den_han(_Db([may]), None, now=NOW) == 0
    assert may.sao_luu_luc is None


def test_khong_co_CSDL_thi_khong_lam_gi(monkeypatch):
    from apps.vps import bao_tri

    assert bao_tri._chup_anh_den_han(None, None, now=NOW) == 0
