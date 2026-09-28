"""Tên tệp của khách KHÔNG được đi thẳng vào khoá lưu trữ — cả ba App tải lên.

## Lỗ thật, bắt lúc 01:25 ngày 10/09 bởi bộ rà bảo mật sau commit

Ba route tải lên đều dựng khoá lưu trữ từ **tên tệp do khách gửi**:

```
video_assembly   f"video_assembly/{user}/{lo}/clip/{tep.filename}"
transcript       duoi = "." + ten.rsplit(".", 1)[-1]      <- tren chuoi THO
audio_pause      duoi = "." + ten.rsplit(".", 1)[-1]      <- nhu tren
```

Đường thứ hai và thứ ba tinh vi hơn đường thứ nhất: `a.mp3/../../x` đi qua
`rsplit(".", 1)[-1]` cho ra `mp3/../../x`, tức **một đường vượt thư mục nằm
trong phần "đuôi tệp"**.

## ⛔ "storage đã chặn rồi" KHÔNG phải một lý do để bỏ qua

`platform_core/storage.py::_safe_key` có chặn `..`. Nhưng nó chặn bằng cách
**ném** `StorageError`, tức:

- khách gửi một tên lạ ⇒ **HTTP 500**, không phải một câu trả lời tử tế;
- App dựa vào một lớp phòng thủ nằm ở tệp khác, do người khác bảo trì, và
  không có gì buộc nó ở lại đó.

⭐ Và một backend khác (R2) có thể không đi qua cùng đường ấy. Một App không
   được phép biết chi tiết đó — nó phải tự làm sạch đầu vào của chính nó.

## Vì sao KHÔNG thay bằng UUID cho `video_assembly`

Bộ rà đề nghị "thay hẳn bằng UUID do máy chủ sinh". Đúng cho hai App kia, **sai**
cho `video_assembly`: chế độ khớp `sequential` — chế độ **production đang dùng** —
đọc **tiền tố tên tệp** (`^\\d{3,4}-scene`). Đổi tên là phá đúng hành vi ấy, và
phá **im lặng**: `semantic` vẫn chạy, video vẫn ra, chỉ sai clip.

⇒ Bản vá phải **làm sạch mà vẫn giữ tên**: `PurePosixPath(...).name` bỏ mọi phần
  đường dẫn, rồi `safe_name()` thay ký tự cấm.
"""
from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath

import pytest

from apps.video_assembly.services.tuong_thich.paths import safe_name

GOC = Path(__file__).resolve().parent.parent


def _chi_ma(tep: Path) -> str:
    """Nguồn đã BỎ chú thích và docstring.

    🔴 Bản đầu của tệp này quét thẳng văn bản nguồn, và nó **báo động trên chính
       đoạn chú thích giải thích nó** — đoạn nói *"`rsplit` trên chuỗi thô là
       chỗ lỗ nằm"*. Memory của kho ghi đúng hạng lỗi này: *một bộ dò trừng phạt
       việc giải thích thì không ai giữ nó lâu*.

    ⇒ Đọc **cây cú pháp**, không đọc văn bản: `ast.unparse` bỏ hết chú thích, và
      docstring thì lọc riêng.
    """
    cay = ast.parse(tep.read_text(encoding="utf-8"))
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                            ast.ClassDef)) and ast.get_docstring(nut):
            nut.body = nut.body[1:]
    return ast.unparse(cay)


def _lam_sach(ten: str) -> str:
    """Đúng phép biến đổi mà `apps/video_assembly/routes.py` dùng."""
    return safe_name(PurePosixPath((ten or "").replace(chr(92), "/")).name)


# ── 1. Phép làm sạch chặn được mọi hình dạng đã biết ───────────────────────

@pytest.mark.parametrize("doc_hai", [
    "../../secrets/app.env",
    "../" * 8 + "etc/passwd",
    ".." + chr(92) + ".." + chr(92) + "x.mp4",
    "/etc/shadow",
    "C:" + chr(92) + "Windows" + chr(92) + "x.mp4",
    "~/.ssh/id_rsa",
    "a" + chr(0) + "b.mp4",
])
def test_ten_doc_hai_khong_con_dau_vet_duong_dan(doc_hai) -> None:
    ten = _lam_sach(doc_hai)
    assert ten, f"{doc_hai!r} lam sach ra RONG"
    for cam in ("/", chr(92), "..", ":", "~"):
        assert cam not in ten, f"{doc_hai!r} -> {ten!r} con chua {cam!r}"


def test_tien_to_canh_duoc_GIU_NGUYEN() -> None:
    """🔴 Đây là vế còn lại, và nó quan trọng ngang vế an toàn.

    Chế độ `sequential` đọc tiền tố `^\\d{3,4}-scene`. Một bản vá "an toàn hơn"
    bằng cách đổi tên thành UUID sẽ phá đúng chế độ mà production đang dùng.
    """
    for ten in ("001-scene-mo-dau.mp4", "0042-scene_ket.mov",
                "123-scene - ban nhap.mkv"):
        assert _lam_sach(ten) == ten


def test_ten_rong_van_ra_mot_ten_dung_duoc() -> None:
    """Một tên rỗng làm khoá kết thúc bằng `/`, và `_safe_key` sẽ ném."""
    for xau in ("", "   ", "...", "///", "/"):
        assert _lam_sach(xau)


# ── 2. Ba route không được ghép tên thô vào khoá ───────────────────────────

def test_video_assembly_lam_sach_truoc_khi_dung_ten() -> None:
    van = _chi_ma(GOC / "apps" / "video_assembly" / "routes.py")
    assert "safe_name(" in van
    assert "PurePosixPath(" in van
    # Tên thô không được đi thẳng vào danh sách sẽ thành khoá.
    assert "du_lieu.append((tep.filename" not in van


@pytest.mark.parametrize("app", ["transcript", "audio_pause"])
def test_hai_app_am_thanh_lay_duoi_tu_DANH_SACH_CHO_PHEP(app) -> None:
    """`rsplit(".", 1)[-1]` trên chuỗi thô là chỗ lỗ nằm: nó trả về **mọi thứ
    sau dấu chấm cuối**, kể cả dấu gạch chéo."""
    van = _chi_ma(GOC / "apps" / app / "routes.py")
    assert "ten.rsplit" not in van, f"{app}: van lay duoi tu chuoi tho"
    # ⚠️ Khớp trên nguồn ĐÃ `unparse`, nên đừng chốt dấu ngoặc: `ast.unparse`
    #    bọc thêm một lớp quanh generator (`next((d for d in ...))`). Chốt cái
    #    KHÔNG đổi qua unparse — phép lọc theo danh sách cho phép.
    assert "DUOI_NHAN if ten.endswith(d)" in van, (
        f"{app}: duoi khong lay tu danh sach cho phep")


@pytest.mark.parametrize("app", ["transcript", "audio_pause", "video_assembly",
                                 ])
def test_khoa_luu_tru_luon_bat_dau_bang_slug_va_user(app) -> None:
    """Khoá phải neo vào `<slug>/<user>/…`: đó là thứ làm phép kiểm sở hữu ở
    route đọc kết quả có nghĩa."""
    for dong in _chi_ma(GOC / "apps" / app / "routes.py").splitlines():
        if 'f"' in dong and "/{user}/" in dong:
            assert dong.strip().split('f"')[1].startswith(app), \
                f"{app}: khoa khong bat dau bang slug: {dong.strip()}"


# ── 3. Đối chứng: phép làm sạch phải THẬT SỰ đổi chuỗi ─────────────────────

def test_phep_lam_sach_khong_phai_mot_ham_dong_nhat() -> None:
    """Thiếu phép kiểm này, một bản `safe_name = lambda s: s` vẫn xanh ở mọi
    khẳng định "không chứa `/`" nếu đầu vào tình cờ sạch."""
    assert _lam_sach("../../x.mp4") != "../../x.mp4"
    assert _lam_sach("a:b.mp4") != "a:b.mp4"
