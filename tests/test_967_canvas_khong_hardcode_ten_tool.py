"""Đợt 5.2 — bánh cóc *"frontend không hardcode tên tool"* (`31 §5.2`).

## Vì sao phép kiểm này ở `tests/` chứ không ở `platform_core/`

`31 §5.2` viết: bánh cóc *"phải dựng ở phía **frontend**, không phải
`platform_core`"*. Đó là nói về chỗ **sửa** — danh sách tool phải đến từ
`/agent/api/palette`, và không được đẻ ra một bảng tên tool thứ hai bên trong
nền tảng.

Còn phép **kiểm** thì phải đứng ở chỗ nhìn được **cả hai bờ**: nguồn TypeScript
và registry Python. `vitest` không nạp được `platform_core`, nên nó chỉ kiểm
được một nửa — và một nửa ở đây là nửa không quan trọng.

## 🔴 CÁI GIÁ CỦA HARDCODE, ĐO ĐƯỢC 08/09/2026

```
ten tool hardcode trong frontend/agent-canvas/src :  21
trong do KHONG ton tai nhu mot `ToolSpec`         :  11
ToolSpec that ma frontend khong he nhac           :   5
```

Không cái nào gây lỗi — `_palette_tool` là *"bảng TRA CỨU CÓ MẶC ĐỊNH"*, nên
một tên chết chỉ **không bao giờ khớp**. Đó chính là hình dạng nguy hiểm: bảng
trôi khỏi thực tế, và **không gì báo**.

## Bánh cóc chốt TẬP HỢP, không chốt SỐ LƯỢNG

`DA_CHET` chỉ được **co lại**. Hai chiều đều cưỡng chế:

* thêm một tên hardcode **mới** không có trong registry ⇒ **đỏ**;
* xoá một tên khỏi frontend mà **quên** gỡ khỏi `DA_CHET` ⇒ **cũng đỏ**.

⭐ Chiều thứ hai là chiều hay bị bỏ. Một danh sách miễn trừ không tự co lại thì
   sau vài lần dọn nó mô tả một quá khứ không còn tồn tại — và lần sau người
   đọc không phân biệt được "đã sửa" với "chưa từng có".
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
NGUON = GOC / "frontend" / "agent-canvas" / "src"

#: Chuỗi hình dạng `<miền>.<hành động>` trong nháy đơn hoặc nháy kép.
_MAU = re.compile(r"""['"]([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)['"]""")

#: ⛔ CHỈ ĐƯỢC CO LẠI. Đây là những tên đang hardcode ở frontend mà **không có
#: `ToolSpec` nào mang tên ấy** — tức các hàng chết trong bảng tra cứu. Chúng
#: được miễn trừ để bánh cóc dựng được ngay hôm nay, không phải để ở lại.
#:
#: Cách gỡ đúng: lấy nhãn/biểu tượng/tầng từ `/agent/api/palette` thay vì tra
#: một bảng trong mã frontend. Khi ấy xoá tên khỏi bảng và xoá khỏi đây.
DA_CHET = frozenset({
    "asset.audio", "asset.image", "asset.images", "asset.video",
    "audio.generate", "media.merge_image", "media.merge_video",
    "text.generate", "text.script", "video.extract_frames",
    "video.social_import",
})


def _ten_hardcode() -> dict[str, set[str]]:
    """`tên tool -> {tệp}`. Đọc **nguồn**, không đọc bản build."""
    ra: dict[str, set[str]] = {}
    for f in sorted(NGUON.glob("*.ts*")):
        for ten in _MAU.findall(f.read_text(encoding="utf-8")):
            ra.setdefault(ten, set()).add(f.name)
    return ra


def _toolspec_that() -> set[str]:
    from platform_core import registry

    return {t.name for a in registry.discover() for t in a.manifest.tools}


@pytest.fixture(scope="module")
def hardcode() -> dict[str, set[str]]:
    # ⛔ KHONG `pytest.skip` khi thu muc vang. Do 08/09: ca BON worktree deu co
    #    `frontend/agent-canvas/src` — no duoc git theo doi, chi `node_modules`
    #    la khong. Nen mot `skip` o day la mot rao KHONG BAO GIO NO, va
    #    `check_bo_qua` goi dung ten no: "mot test bi bo qua la mot test KHONG
    #    canh gi ca".
    #
    # Va neu thu muc that su vang thi do la mot van de, khong phai mot ly do im
    # lang: `assert` duoi day noi thang ra thay vi bo qua.
    assert NGUON.is_dir(), f"khong thay {NGUON} — nguon frontend duoc git theo doi"
    return _ten_hardcode()


def test_khong_them_ten_tool_hardcode_MOI_ma_khong_co_that(hardcode):
    """⛔ Chiều thứ nhất: một tên mới phải **tồn tại** trong registry.

    Không có nó, bảng trình bày của frontend lớn lên bằng những hàng không bao
    giờ khớp — và mỗi hàng ấy trông y hệt một hàng đang hoạt động.
    """
    that = _toolspec_that()
    la = sorted(t for t in hardcode if t not in that and t not in DA_CHET)
    assert not la, (
        "ten tool hardcode MOI ma khong co `ToolSpec` nao mang ten do:\n  "
        + "\n  ".join(f"{t}  (o {', '.join(sorted(hardcode[t]))})" for t in la)
        + "\n\nLay nhan tu `/agent/api/palette` thay vi mot bang trong ma "
          "frontend. Neu that su phai hardcode, tao mot `ToolSpec` truoc.")


def test_danh_sach_mien_tru_KHONG_duoc_chua_thu_da_bien_mat(hardcode):
    """⭐ Chiều thứ hai — chiều hay bị bỏ.

    Một danh sách miễn trừ không tự co lại thì sau vài lần dọn nó mô tả một quá
    khứ không còn tồn tại, và người đọc sau không phân biệt được *"đã sửa"* với
    *"chưa từng có"*.
    """
    thua = sorted(DA_CHET - set(hardcode))
    assert not thua, (
        f"`DA_CHET` con {thua} nhung frontend khong con nhac toi chung.\n"
        "Da don roi thi go khoi danh sach — banh coc phai co lai cung.")


def test_moc_KHONG_duoc_TANG(hardcode):
    """Số hàng chết chỉ được giảm. Đây là mệnh đề về **xu hướng**, và nó bắt
    được cả trường hợp ai đó thêm tên mới rồi nhét luôn vào `DA_CHET`."""
    that = _toolspec_that()
    chet = {t for t in hardcode if t not in that}
    assert len(chet) <= len(DA_CHET), (
        f"so ten tool CHET tang: {len(chet)} > moc {len(DA_CHET)}\n"
        f"moi: {sorted(chet - DA_CHET)}")


def test_phep_kiem_nay_THUC_SU_doc_duoc_nguon(hardcode):
    """🔑 Đối chứng cho chính phép kiểm.

    Nếu đường dẫn sai hay `glob` hụt, `hardcode` rỗng và **cả ba bài trên đều
    xanh** — một bộ kiểm xanh vì nó không đo gì. Bài này bắt đúng trạng thái ấy.

    Cùng bài học với *"không đối chứng thì số 0 không phải phát hiện"*.
    """
    assert len(hardcode) >= 15, (
        f"chi doc duoc {len(hardcode)} ten tu {NGUON} — nghi phep kiem dang "
        "quet nham cho, khong phai frontend da sach")
    assert any(f.suffix in (".ts", ".tsx") for f in NGUON.glob("*.ts*"))
