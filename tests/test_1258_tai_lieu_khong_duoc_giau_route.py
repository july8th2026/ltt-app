"""test_1258 — mot route DANG CHAY ma tai lieu khong nhac la mot nang luc CHET.

## 🔴 Do duoc 14/09/2026

`docs/PUBLIC_API/DEVELOPER_GUIDE.md` nhac `/api/v1/messages` va
`/api/v1/responses` **dung 0 lan**, va co han mot muc tieu de:

    ### Chua co streaming
    `"stream": true` bi tu choi bang 400.

Trong khi **ca hai cua stream dang chay that** — do cung ngay: `/messages` tra
200 kem `event: message_start`, `/responses` tra 200 kem `event:
response.created`. Va theo `APP_API_COVERAGE_FINAL.md`, chung la duong ma
*"Codex CLI, Claude Code CLI, hai tien ich VS Code va Claude Desktop"* dang di.

⛔ Tai lieu ta XUAT BAN cho khach **phu nhan mot nang luc dang ban**. Mot
   developer doc trang do se ket luan API nay khong co streaming, va se khong
   bao gio tim thay hai cua ay.

## Vi sao chot o day chu khong phai "nho cap nhat tai lieu"

Loi van khong cuong che duoc gi. Route sinh ra tu ma; tai lieu viet tay. Hai
thu troi khoi nhau la chuyen cua thoi gian, khong phai cua su can than — va no
DA troi, im lang, du bao lau khong ai biet.

⇒ Phep kiem nay lay danh sach route tu **chinh ung dung dang chay**, roi doi
  moi route co tinh tien phai xuat hien trong tai lieu. Them mot cua moi ma
  quen viet tai lieu ⇒ **do**, khong can ai nho.
"""
from __future__ import annotations

import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
GUIDE = GOC / "docs" / "PUBLIC_API" / "DEVELOPER_GUIDE.md"

#: Route **khach goi de lam viec** — moi cai phai co mat trong tai lieu.
#:
#: ⛔ Day KHONG phai mot ban sao cua bang route: `test_route_nay_van_ton_tai`
#:    ben duoi doi chieu no voi ung dung that, nen mot cai ten chet o day se bi
#:    bat chu khong nam im.
ROUTE_PHAI_CO_TAI_LIEU = [
    "/api/v1/chat/completions",
    "/api/v1/messages",
    "/api/v1/responses",
    "/api/v1/jobs",
    "/api/v1/quotes",
    "/api/v1/models",
    "/api/v1/tools",
]


def _duong_that() -> set[str]:
    """Route CO THAT cua ung dung cong khai, doc tu chinh no."""
    from platform_core.public_api.config import load_public_api_config
    from server.api import build_public_api_app

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat"})
    app = build_public_api_app(cfg)
    return {getattr(r, "path", "") for r in app.routes}


@pytest.mark.parametrize("duong", ROUTE_PHAI_CO_TAI_LIEU)
def test_route_nay_van_ton_tai(duong):
    """Danh sach tren phai bam vao ung dung that, khong duoc thanh mot ban sao chet."""
    that = _duong_that()
    ngan = duong[len("/api/v1"):]
    assert any(p == ngan or p == duong for p in that), (
        f"`{duong}` khong con trong ung dung — sua danh sach o day, dung de no "
        f"khai mot route khong ton tai. Route that: {sorted(that)}")


@pytest.mark.parametrize("duong", ROUTE_PHAI_CO_TAI_LIEU)
def test_tai_lieu_phai_nhac_route_nay(duong):
    """🔴 Phep kiem chinh. Route chay ma tai lieu khong nhac = nang luc chet."""
    van = GUIDE.read_text(encoding="utf-8")
    assert duong in van, (
        f"`{duong}` DANG CHAY nhung `DEVELOPER_GUIDE.md` khong nhac toi no. "
        f"Mot developer doc trang nay se khong bao gio tim thay no. Do dung la "
        f"chuyen da xay ra voi /messages va /responses truoc 14/09/2026.")


def test_khong_con_cau_PHU_NHAN_streaming():
    """⛔ Doi chung: tai lieu tung noi thang la 'chua co streaming'.

    Menh de duong (route co mat) van co the song chung voi mot cau phu dinh o
    cho khac — va chinh cau phu dinh moi la thu developer doc va tin.

    ⛔ Va phep kiem nay chi cam cau ay o dang **TIEU DE**, khong cam o moi cho.
       Ban dau toi viet `assert "Chưa có streaming" not in van` va no DO ngay —
       vi chinh loi dinh chinh moi viet ("truoc day mang tieu de *...* va cau ay
       SAI") co chua nguyen van chuoi do. Mot bo do quet van ban khong phan biet
       duoc LOI GIAI THICH voi DIEU DUOC KHANG DINH; kho nay da ghi dung cai bay
       ay hai lan. Neo vao cu phap tieu de Markdown thi phan biet duoc.
    """
    van = GUIDE.read_text(encoding="utf-8")
    tieu_de = [d.strip() for d in van.splitlines() if d.lstrip().startswith("#")]
    xau = [d for d in tieu_de if "Chưa có streaming" in d]
    assert not xau, (
        f"tai lieu van mang TIEU DE {xau} trong khi /messages va /responses "
        "dang phuc vu")


def test_tai_lieu_noi_duoc_CACH_dung_stream_chu_khong_chi_nhac_ten():
    """Nhac ten ma khong noi cach dung thi developer van khong di duoc.

    Doi dung hai thu de phan biet hai giao thuc — chung KHAC nhau o day, va
    nham thi request bi tu choi:
      · Anthropic  -> `max_tokens`
      · Responses  -> `max_output_tokens`
    """
    van = GUIDE.read_text(encoding="utf-8")
    assert "max_output_tokens" in van, (
        "tai lieu khong noi `/responses` dung `max_output_tokens` — developer "
        "se gui `max_tokens` va bi tu choi")
    assert "text/event-stream" in van, (
        "tai lieu khong noi hai cua nay tra `text/event-stream`")
