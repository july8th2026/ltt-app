"""
test_824 — trích văn bản: BA loại hỏng phải phân biệt được. (H44 P06 bước 3)

🔴 Tệp này tồn tại vì một lỗi ĐANG SỐNG trên production, tìm ra 06/09 ở
   `apps/chataistudio/features.py:46-51`:

       except Exception as exc:
           raise ValueError(_t('Không đọc được nội dung PDF.')) from exc

   `pypdf` **không tồn tại** trên máy chủ (vắng ở cả bốn `requirements*.txt` và
   ở `C:\\LTTPlatform\\venv`), nên `ImportError` rơi vào `except Exception` và
   đi ra thành *"Không đọc được nội dung PDF."* — **máy chủ thiếu thư viện, mà
   thông báo đổ lỗi cho tệp của khách**.

⭐ Cái giá không phải một lỗi bị che. Khách đi thử tệp khác, rồi tệp khác nữa,
   rồi kết luận sản phẩm hỏng — và **không ai báo lỗi**, vì thông báo đã trả lời
   họ rồi. Một thông báo trỏ sai hướng đắt hơn im lặng.

⇒ Ba loại phải phân biệt ở **tầng kiểu**, không phải ở tầng câu chữ. Đó là thứ
  tệp này chốt, và nó chốt bằng cách bắt từng loại riêng.
"""
from __future__ import annotations

import io
import json

import pytest

from apps.chatltt.services import trich_van_ban as T


# ── 1. Ba loại hỏng, ba kiểu ───────────────────────────────────────────────

def test_THIEU_THU_VIEN_khong_bi_bao_thanh_TEP_HONG(monkeypatch):
    """🔴 Mệnh đề trung tâm — chính là lỗi đang sống ở `chataistudio`.

    Giả lập máy chủ thiếu `pypdf`, rồi đòi hỏi ngoại lệ nói **đúng ai có lỗi**.
    """
    import builtins
    that = builtins.__import__

    def gia(ten, *a, **k):
        if ten == "pypdf":
            raise ImportError("No module named 'pypdf'")
        return that(ten, *a, **k)

    monkeypatch.setattr(builtins, "__import__", gia)

    with pytest.raises(T.ThieuThuVien) as e:
        T.trich(b"%PDF-1.4 gia", content_type="application/pdf")

    # ⛔ Doi chung ve NOI DUNG: thong bao khong duoc do loi cho tep cua khach.
    assert "khong phai loi cua tep" in str(e.value)
    assert not isinstance(e.value, T.KhongDocDuoc), (
        "thieu thu vien bi xep chung voi tep hong — dung lai loi cua "
        "`chataistudio`")


def test_dinh_dang_LA_la_KhongHoTro_chu_khong_phai_tep_hong():
    with pytest.raises(T.KhongHoTro):
        T.trich(b"MZ\x90\x00", content_type="application/x-msdownload")


def test_tep_chu_KHONG_phai_UTF8_la_KhongDocDuoc():
    """Tệp lưu bằng bảng mã Windows cũ — ca thường với người dùng Việt.

    ⛔ Bản đầu dùng `"chữ tiếng Việt".encode("cp1258")` và phép kiểm đỏ **ngay ở
       dòng dựng dữ liệu**: cp1258 không mã hoá nổi `ữ`. Fixture không dựng được
       thì phép kiểm không đo gì cả — nó chỉ báo rằng tôi gõ sai.
    """
    with pytest.raises(T.KhongDocDuoc):
        T.trich(b"ghi chu: caf\xe9 s\xe1ng", content_type="text/plain")


def test_JSON_hong_la_KhongDocDuoc():
    with pytest.raises(T.KhongDocDuoc):
        T.trich(b'{"a": ', content_type="application/json")


def test_ba_loai_la_BA_kieu_KHAC_nhau():
    """⭐ Đối chứng cấu trúc. Nếu ba lớp cùng kế thừa nhau theo cách bắt được
    lẫn nhau thì `except` của người gọi sẽ gộp lại đúng thứ tệp này tách ra."""
    assert not issubclass(T.ThieuThuVien, T.KhongDocDuoc)
    assert not issubclass(T.KhongDocDuoc, T.ThieuThuVien)
    assert not issubclass(T.KhongHoTro, T.KhongDocDuoc)
    assert not issubclass(T.KhongDocDuoc, T.KhongHoTro)


# ── 2. Đường thành công ────────────────────────────────────────────────────

def test_chu_thuan_ra_MOT_trang_so_KHONG():
    """`trang = 0` nghĩa là **không biết**, không phải "trang đầu"."""
    trang = T.trich(b"mot ghi chu ngan.", content_type="text/plain")
    assert trang == [(0, "mot ghi chu ngan.")]


def test_JSON_hop_le_van_giu_NGUYEN_VAN_chu_khong_bi_dinh_dang_lai():
    goc = json.dumps({"ten": "Lan", "ghi_chu": "co dau tieng Viet"},
                     ensure_ascii=False)
    trang = T.trich(goc.encode("utf-8"), content_type="application/json")
    assert trang[0][1] == goc


def test_content_type_co_charset_van_nhan_duoc():
    """⛔ Trình duyệt gửi `text/plain; charset=utf-8`. So chuỗi thô thì trượt."""
    assert T.trich(b"xin chao", content_type="text/plain; charset=utf-8")


# ── 3. PDF thật ───────────────────────────────────────────────────────────

def _pdf_that(dong: list[str]) -> bytes:
    """Dựng một PDF **hợp lệ thật**: đủ catalog, trang, phông, và bảng `xref`.

    ⛔ Bản đầu của hàm này dùng `PdfWriter.add_blank_page` rồi gắn một luồng nội
       dung — thiếu **tài nguyên phông**, nên `extract_text()` trả rỗng và phép
       kiểm đỏ với thông báo *"PDF không có lớp chữ"*. Nghĩa là fixture của tôi
       tự dựng đúng cái ca lỗi mà nó định phân biệt.

    ⭐ Bẫy 24: một đầu vào **giả** chỉ chứng minh bộ giả chạy đúng. Ở đây đầu
       vào phải đi qua đúng đường `pypdf` sẽ đi trên máy chủ — nên nó phải là
       một PDF mà một trình đọc bất kỳ cũng mở được, không phải một cấu trúc
       vừa đủ lừa `pypdf`.
    """
    so_trang = len(dong)
    id_trang = [3 + 2 * i for i in range(so_trang)]
    id_noi = [4 + 2 * i for i in range(so_trang)]
    id_font = 3 + 2 * so_trang

    obj: list[tuple[int, bytes]] = [(1, b"<</Type/Catalog/Pages 2 0 R>>")]
    kids = b" ".join(b"%d 0 R" % i for i in id_trang)
    obj.append((2, b"<</Type/Pages/Kids[" + kids + b"]/Count %d>>" % so_trang))
    for k, chu in enumerate(dong):
        noi = ("BT /F1 24 Tf 72 700 Td (%s) Tj ET" % chu).encode("latin-1")
        obj.append((id_trang[k],
                    b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
                    b"/Resources<</Font<</F1 %d 0 R>>>>/Contents %d 0 R>>"
                    % (id_font, id_noi[k])))
        obj.append((id_noi[k],
                    b"<</Length %d>>stream\n" % len(noi) + noi + b"\nendstream"))
    obj.append((id_font, b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"))
    obj.sort()

    ra = io.BytesIO()
    ra.write(b"%PDF-1.4\n")
    viTri: dict[int, int] = {}
    for so, than in obj:
        viTri[so] = ra.tell()
        ra.write(b"%d 0 obj" % so + than + b"\nendobj\n")
    moc = ra.tell()
    n = max(viTri) + 1
    ra.write(b"xref\n0 %d\n0000000000 65535 f \n" % n)
    for i in range(1, n):
        ra.write(b"%010d 00000 n \n" % viTri.get(i, 0))
    ra.write(b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (n, moc))
    return ra.getvalue()


def test_PDF_that_ra_dung_so_TRANG_va_trang_bat_dau_tu_1():
    """🟢 Đường thật, đi qua chính `pypdf` sẽ chạy trên máy chủ."""
    du = _pdf_that(["Trang mot noi ve credit", "Trang hai noi ve token"])
    trang = T.trich(du, content_type="application/pdf")

    assert [so for so, _ in trang] == [1, 2], "trang phai 1-based"
    assert "credit" in trang[0][1]
    assert "token" in trang[1][1]


def test_PDF_KHONG_co_lop_chu_la_KhongDocDuoc_chu_khong_phai_THANH_CONG_RONG():
    """🔴 PDF ảnh scan là ca **thường**, không phải góc hiếm.

    Trả về "thành công, 0 đoạn" là câu trả lời tệ hơn một lỗi: nó nghe như đã
    xong. Và nó quyết định chuyện tiền — xem quy tắc hoàn ở bước 3b.
    """
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    ra = io.BytesIO()
    w.write(ra)

    with pytest.raises(T.KhongDocDuoc) as e:
        T.trich(ra.getvalue(), content_type="application/pdf")
    assert "khong co lop chu" in str(e.value)


def test_byte_KHONG_phai_PDF_la_KhongDocDuoc():
    with pytest.raises(T.KhongDocDuoc):
        T.trich(b"day khong phai PDF", content_type="application/pdf")


# ── 4. Trần ───────────────────────────────────────────────────────────────

def test_tai_lieu_qua_dai_bi_TU_CHOI_chu_khong_bi_CAT_LANG_LE(monkeypatch):
    """⛔ Cắt lặng lẽ thì người dùng hỏi về trang 400 và nhận "không thấy" —
    một câu trả lời SAI trông y hệt một câu trả lời đúng."""
    monkeypatch.setattr(T, "TRAN_KY_TU", 100)
    with pytest.raises(T.KhongDocDuoc) as e:
        T.trich(b"x" * 500, content_type="text/plain")
    assert "qua dai" in str(e.value)


def test_tran_MAC_DINH_cao_hon_ca_THUONG_hai_bac_do_lon():
    """⭐ "Trần đặt DƯỚI nhu cầu bình thường biến thất bại thành MẶC ĐỊNH".

    Tài liệu người ta hỏi thường 10–50 trang ≈ 20k–100k ký tự. Trần phải bỏ xa
    mức ấy, nếu không thì chế độ hỏng trở thành chế độ thường.
    """
    assert T.TRAN_KY_TU >= 1_000_000


# ── 5. Cắt theo trang ─────────────────────────────────────────────────────

def test_doan_KHONG_vat_qua_hai_trang():
    """🔴 Một đoạn vắt qua hai trang thì `trang` của nó là số nào? Không có câu
    trả lời đúng ⇒ trích dẫn sẽ trỏ sai. Cắt trong từng trang."""
    a = "Cau ve trang mot. " * 60
    b = "Cau ve trang hai. " * 60
    doan = T.thanh_doan([(1, a), (2, b)], tran=400, chong=0)

    for _, so, noi in doan:
        assert not ("trang mot" in noi and "trang hai" in noi), (
            f"doan vat qua hai trang: {noi[:80]!r}")
    assert {so for _, so, _ in doan} == {1, 2}


def test_thu_tu_chay_SUOT_ca_tep_chu_khong_reset_moi_trang():
    """`thu_tu` là khoá `unique` cùng `tep_id`. Reset mỗi trang là va khoá."""
    doan = T.thanh_doan([(1, "Cau mot. " * 50), (2, "Cau hai. " * 50)],
                        tran=200, chong=0)
    assert [t for t, _, _ in doan] == list(range(len(doan)))
