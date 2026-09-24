"""asv-final L_NO_KY_THUAT R-06 — `subprocess.run(..., text=True)` KHÔNG khai
`encoding` sập trên Windows khi output (thường là thông báo lỗi của ffprobe/
ffmpeg lặp lại đường dẫn) mang ký tự ngoài Latin-1 — đúng tình huống video
nghiệm thu thật mang TÊN TỆP TIẾNG TRUNG.

Tái hiện THẬT bằng ffprobe thật (không giả lập): gọi trên một đường dẫn
KHÔNG TỒN TẠI có tên tiếng Trung — ffprobe echo lại đúng tên đó vào stderr,
và trên Windows (locale mặc định `cp1252`) một `subprocess.run(text=True)`
thiếu `encoding` làm luồng đọc stderr NỘI BỘ của CPython sập
(`UnicodeDecodeError` trong `_readerthread`, nuốt mất `stderr` thay vì báo
lỗi rõ ràng cho người gọi) — khác hẳn với `encoding="utf-8"` đọc đúng.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest

TEN_TRUNG = "不存在的视频.mp4"


def _co_ffprobe() -> bool:
    return shutil.which("ffprobe") is not None


@pytest.mark.skipif(not _co_ffprobe(), reason="khong co ffprobe tren may nay")
def test_soi_KHONG_sap_tren_duong_dan_tieng_trung_khong_ton_tai(tmp_path):
    """`tests.fixtures.asv_e2e.soi()` (R-06 đã sửa) không được ném
    `UnicodeDecodeError` — chỉ được phép báo lỗi ffprobe THẬT (returncode != 0,
    `CalledProcessError` vì `check=True`)."""
    from tests.fixtures import asv_e2e

    duong = tmp_path / TEN_TRUNG
    with pytest.raises(subprocess.CalledProcessError):
        asv_e2e.soi(str(duong))
    # ⛔ Nếu dòng trên ném UnicodeDecodeError thay vì CalledProcessError thì
    #    R-06 đã tái phát — pytest.raises ở trên đã bắt đúng loại, không cần
    #    thêm gì; một UnicodeDecodeError sẽ khiến `pytest.raises` THẤT BẠI vì
    #    sai loại ngoại lệ.


@pytest.mark.skipif(not _co_ffprobe(), reason="khong co ffprobe tren may nay")
def test_doi_chung_KHONG_encoding_thi_that_su_sap(tmp_path):
    """Đối chứng: PHẢI tái hiện được crash gốc khi bỏ `encoding="utf-8"` —
    nếu không, phép kiểm trên không chứng minh được gì (có thể ffprobe/máy
    này không đụng bẫy cp1252 nữa vì lý do khác)."""
    duong = tmp_path / TEN_TRUNG
    import io
    # Bắt lỗi từ chính luồng đọc nội bộ của subprocess: trên Windows,
    # `_readerthread` giải mã bằng `locale.getpreferredencoding()` khi thiếu
    # `encoding`. Đo trực tiếp bằng cùng phép gọi asv_e2e.soi() TỪNG DÙNG
    # trước khi sửa (mô phỏng lại ở đây, không đụng bản đã sửa).
    ff = shutil.which("ffprobe") or "ffprobe"
    r = subprocess.run(
        [ff, "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", str(duong)], capture_output=True, text=True,
        check=False)
    # Trên máy KHÔNG phải cp1252 (vd. CI Linux UTF-8), bẫy này không nổ —
    # khi đó chỉ ghi nhận và bỏ qua, đừng biến một môi trường khác thành đỏ.
    import locale
    if locale.getpreferredencoding(False).lower() not in ("cp1252",):
        pytest.skip(f"locale mac dinh la {locale.getpreferredencoding(False)!r}, "
                    "khong tai hien duoc bay tren may nay")
    assert r.stderr is None, (
        "moi truong nay khong con tai hien duoc bay cp1252 (stderr doc duoc "
        f"binh thuong: {r.stderr!r}) — kiem lai gia thuyet doi chung")
