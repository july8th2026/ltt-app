"""
test_840 — một PHIẾU DUYỆT không được rỗng. (H44 P09 bước 6)

## Cái này tìm ra bằng MẮT, không bằng test

`test_835` chốt rằng mọi đối số của tool **nội bộ** đều có nhãn, và **cố ý**
không đòi gì ở tool ngoài (`image.ltt`, `speech.ltt`) — lý lẽ ghi trong chính
tệp đó: *"hợp đồng của chúng nằm ở app khác và có thể đổi mà không ai ở đây
biết"*.

Lý lẽ ấy đúng về **quyền sở hữu** và sai về **kết quả**. Đo 07/09 trên trình
duyệt thật, khối `image.ltt` vẽ ra đúng thế này:

    <div class="ltc-tool" data-trang-thai="dang_chay">
      <button aria-label="Vẽ ảnh — Đang chạy" disabled>…</button>
    </div>

Không một dòng nào. Hai tool ngoài ấy lại đúng là **hai tool duy nhất tiêu tiền
của khách** — chúng thuộc lớp `PAID`, nên đường đi bình thường của chúng là mở
một phiếu duyệt. Nghĩa là: người dùng được hỏi *"duyệt không?"* mà không nhìn
thấy mình đang duyệt cái gì.

🔴 Và `tables.py` đã tự hứa điều ngược lại. Chú thích của `ChatlttApproval`:
   *"Đối số người dùng **nhìn thấy** khi bấm"*.

## Vì sao chốt ĐỐI SỐ BẮT BUỘC chứ không chốt mọi đối số

Đòi nhãn cho **mọi** khoá của app khác là đòi cái mà `test_835` đã đúng khi từ
chối: `mode`, `model`, `image_key` là núm kỹ thuật, và bắt ChatLTT chạy theo
từng lần app kia thêm một núm là một bánh cóc sẽ bị gỡ.

⇒ Mệnh đề đúng hẹp hơn và **bất biến** với việc app kia thêm núm: *một tool mà
  model được mời gọi phải có ít nhất một đối số **bắt buộc** hiện được ra màn
  hình.* Đổi tên `prompt` → `description` bên app ảnh ⇒ đỏ ở đây, ở cổng, trước
  khi màn hình của khách trắng.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
TSX = GOC / "frontend" / "chatltt" / "src" / "KhoiTool.tsx"


def _khoa_cua_bang(ten_bang: str) -> set:
    van = TSX.read_bytes().decode("utf-8")
    m = re.search(rf"const {ten_bang}[^=]*=\s*\{{(.*?)\n\}}", van, re.S)
    if not m:
        return set()
    return set(re.findall(r"^\s*'?([A-Za-z_][\w.]*)'?\s*:", m.group(1), re.M))


def _tool_spec(ten: str):
    """`ToolSpec` mang tên này, hoặc `None`. Đọc manifest THẬT, không bảng chép."""
    from platform_core.registry import discover

    for item in discover():
        if item.error:
            continue
        for t in getattr(item.manifest, "tools", ()) or ():
            if t.name == ten:
                return t
    return None


def _ngoai() -> list:
    """Tên trong `CHO_MODEL_GOI` KHÔNG thuộc `noi_bo.*` — phần `test_835` bỏ."""
    from apps.chatltt.services import chieu_tool

    return [t for t in chieu_tool.CHO_MODEL_GOI if not t.startswith("noi_bo.")]


def test_bo_trich_TU_KIEM():
    """⛔ Regex hỏng ⇒ tập rỗng ⇒ mọi phép kiểm dưới xanh sạch trên hư không."""
    assert "bieu_thuc" in _khoa_cua_bang("NHAN_DOI_SO")
    assert _ngoai(), "CHO_MODEL_GOI khong con ten ngoai nao — phep kiem thanh rong"


def test_moi_tool_NGOAI_duoc_moi_deu_ton_tai_that():
    """Đối chứng: nếu `discover()` không thấy tool nào thì phép kiểm dưới rỗng."""
    for ten in _ngoai():
        assert _tool_spec(ten) is not None, f"khong manifest nao khai {ten}"


@pytest.mark.parametrize("ten", ["image.ltt", "speech.ltt"])
def test_doi_so_BAT_BUOC_cua_tool_tra_tien_co_nhan(ten):
    """🔴 Phép kiểm thật của tệp này."""
    spec = _tool_spec(ten)
    assert spec is not None, f"{ten} khong con ton tai"
    bat_buoc = {k for k, v in (spec.params_schema or {}).items()
                if isinstance(v, dict) and v.get("required")}
    assert bat_buoc, f"{ten} khong khai doi so bat buoc nao"
    co_nhan = bat_buoc & _khoa_cua_bang("NHAN_DOI_SO")
    assert co_nhan, (
        f"{ten}: khong doi so BAT BUOC nao co nhan ({sorted(bat_buoc)}) — "
        f"phieu duyet cua no se ve ra RONG")


# ⛔ Đường phòng thủ thứ hai — *"thân rỗng thì vẫn phải nói ra một câu"* — được
#    chốt ở `frontend/chatltt/tests/KhoiTool.test.tsx`, bằng cách **render**.
#    Không chốt ở đây: quét chuỗi trong `.tsx` là đọc thứ đại diện, và tôi đã
#    trả giá đúng lỗi ấy một lần ở `BangDuAn` — phép kiểm quét `'onMouseEnter'`
#    rồi đỏ trên chính dòng chú thích giải thích nó.
