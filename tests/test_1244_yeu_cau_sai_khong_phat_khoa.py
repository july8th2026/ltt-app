"""test_1244 — mot YEU CAU SAI khong duoc phat KHOA. L-09, 13/09/2026.

## Su that do duoc

Gui mot anh hong qua `/api/v1/chat/completions`. May B tra DUNG CHUAN:

    400 {"error": {"code": 400, "type": "invalid_request_error",
                   "message": "Failed to load image or audio file"}}

May A lam phang thanh **503**, va `dieu_phoi` goi `api_pool.danh_dau_loi(db,
key)` **khong kem `http_status`**.

## Hai cai sai, moi cai mot huong

1. Khach nhan `503 retry: after_delay` cho mot yeu cau **khong bao gio** thanh
   cong — thu lai bao nhieu lan cung the.
2. `danh_dau_loi` doc `http_status=None` thanh *"5xx hoac loi mang"* =>
   `error_count += 1`. Nam lan la `APIKEY_ERROR`, thu hoi do **KHONG TU HOI**
   (tu 19/09: co han `ERROR_COOLDOWN_S` roi thu lai, nhung `error_count` giu
   nguyen nen loi ke tat lai ngay; ERROR khong han van cho admin — `test_1524`).

⇒ **Mot khach gui nam anh hong la tat model nha** cho toi khi co nguoi sua tay.
  Va bat ky ai co khoa API deu lam duoc, ke ca vo tinh.

⭐ Chinh `danh_dau_loi` DA co nhanh dung — *"400 <= s < 500: Bad request CUA TA
   — KHONG phat"* — nhung nhanh ay chi chay khi co nguoi **truyen ma vao**.
   Loi khong nam o luat; no nam o mot tham so khong duoc truyen.

## Day la CUA THU BA cua cung mot tham hoa D-005

    luat 1 (dau `cong_vlm.py`)  bit cua 429
    ban va 09/09                bit cua 504
    cua 400                     dung mo toi 13/09
"""
import pytest

from platform_core.llm import cong_vlm as CV


class KeyGia:
    """Du hinh dang cho `danh_dau_loi`, va GHI LAI thu no bi doi."""

    def __init__(self):
        self.total_failed = 0
        self.error_count = 0
        self.auth_error_count = 0
        self.health_score = 100
        self.status = "active"
        self.cooldown_until = None
        self.last_error = ""


def _danh_dau(http_status):
    """Chay `danh_dau_loi` tren mot key gia, tra ve key sau khi bi phat."""
    from platform_core import api_pool

    key = KeyGia()

    class DbGia:
        def flush(self):
            pass

    api_pool.danh_dau_loi(DbGia(), key, http_status=http_status, message="thu")
    return key


def test_400_KHONG_lam_tang_error_count():
    """🔴 MENH DE TRUNG TAM. `error_count` la thu dan toi `APIKEY_ERROR`."""
    assert _danh_dau(400).error_count == 0


def test_khong_truyen_ma_thi_BI_PHAT_nhu_loi_5xx():
    """Doi chung — va day la hanh vi DA GAY RA L-09.

    Giu phep kiem nay de ai doc cung thay: khong phai `danh_dau_loi` sai, ma la
    bên goi khong noi cho no biet loi thuoc loai gi.
    """
    assert _danh_dau(None).error_count == 1


def test_500_VAN_bi_phat():
    """Doi chung phia con lai: mot loi THAT cua thuong nguon van phai phat.

    Thieu phep nay thi mot ban sua "khong phat gi ca" cung xanh — va khi ay ta
    mat han co che phat hien mot khoa hong.
    """
    assert _danh_dau(500).error_count == 1


def test_401_403_van_di_duong_auth():
    """401/403 la loi cau hinh cua TA, khong phai cua khach — van phai dem."""
    assert _danh_dau(401).auth_error_count == 1
    assert _danh_dau(403).auth_error_count == 1


# ── Lop loi: 400/422 phai thanh `YeuCauSaiError`, khong phai `CongVlmError` ──

def _chat_tra(ma, than):
    """Dung mot `CongVlm` voi ham HTTP tiem vao, tra ve `(ma, than)` co dinh."""
    def goi(method, path, json=None, timeout=None):
        return ma, than

    return CV.CongVlm(goi=goi, timeout_s=5.0)


@pytest.mark.parametrize("ma", [400, 422])
def test_400_va_422_thanh_YeuCauSaiError(ma):
    c = _chat_tra(ma, {"error": {"code": ma, "type": "invalid_request_error",
                                 "message": "Failed to load image or audio file"}})
    with pytest.raises(CV.YeuCauSaiError) as e:
        c.chat(model="qwen35-api", messages=[{"role": "user", "content": "x"}])
    assert e.value.ma == ma
    assert "Failed to load image" in str(e.value), (
        "thong diep cua thuong nguon phai di THANG ra cho khach — "
        "'The model could not serve this request' khong noi cho ho biet gi")


def test_502_van_la_CongVlmError_va_MANG_MA():
    """Loi that cua thuong nguon giu nguyen lop cu — nhung nay co mang ma.

    ⛔ Mang ma la phan quan trong: thieu no thi `danh_dau_loi` lai doc thanh
       `None` va ta quay ve dung cho da gay ra L-09.
    """
    c = _chat_tra(502, {})
    with pytest.raises(CV.CongVlmError) as e:
        c.chat(model="qwen35-api", messages=[{"role": "user", "content": "x"}])
    assert not isinstance(e.value, CV.YeuCauSaiError)
    assert e.value.ma == 502


def test_YeuCauSaiError_la_con_cua_CongVlmError():
    """Ben goi cu bat `CongVlmError` van bat duoc no — khong ai bi bo roi.

    ⭐ Nhung `dieu_phoi` bat `YeuCauSaiError` TRUOC, nen no khong cascade va
       khong phat key. Thu tu `except` la ca ban sua.
    """
    assert issubclass(CV.YeuCauSaiError, CV.CongVlmError)
