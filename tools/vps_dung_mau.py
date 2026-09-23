"""Dựng HTML thật của các trang VPS, ra tệp, để soi bằng trình duyệt thật.

    python tools\\vps_dung_mau.py                 # dựng hết vào scratchpad
    python tools\\vps_dung_mau.py --ra D:\\tmp\\vps

## 🔴 Vì sao công cụ này phải tồn tại

Ba trong năm trang VPS (`/vps/{id}`, `/cai-dat`, `/console`) **không mở được nếu
không có một máy**. Sau đợt dọn 25/08, bốn bảng `vps_*` về **0 dòng**, 0 VM,
0 Reserved IP — nên trên máy này, ba trang đó không có cách nào để nhìn thấy.

Ba đường không đi được:

* **Sửa rồi xem trên production.** `/vps` đang bán hàng thật (`LTT_VPS=1` trên
  máy chủ). Deploy để xem một thay đổi trình bày là đổi thứ khách đang dùng để
  lấy một ảnh chụp.
* **Tạo một máy thật.** Trừ credit thật (bút toán append-only, không xoá được)
  và ăn một Reserved IP — mà hạn ngạch của Vultr đếm **cả IP vừa xoá**.
* **Đọc template rồi suy ra.** `CLAUDE.md` mục 5 đã chốt không được, và audit
  25/08 chứng minh vì sao: ba lỗi nặng nhất hôm đó đều có **HTML đúng** và **cây
  trợ năng đúng**. Chỉ `getComputedStyle` trên trang render mới thấy.

⇒ Đường thứ tư: render **bằng chính ứng dụng** (đúng `ltt.css`, đúng `asset_ver`,
đúng i18n, đúng macro) trên một CSDL SQLite dùng một lần, ghi ra tệp, rồi mở bằng
`file://`. Không tốn tiền, không chạm production, và vẫn là **bố cục thật**.

## ⛔ Nó KHÔNG chứng minh được gì

Nói rõ ở đây để không ai trích dẫn nó sai:

* WebSocket console (cần Proxmox thật),
* luồng POST đầu-tới-cuối (tạo · bật · tắt · xoá),
* hành vi thật của job trong worker,
* mọi thứ đi qua Cloudflare (cache, CSP biên, minify) — quy tắc 5b.

Nó chứng minh: **bố cục, tràn ngang, tương phản, reflow, và trạng thái nào hiện
ra cái gì.** Đúng phần mà đọc mã không trả lời được, và không hơn.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
import tempfile

GOC = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))

TINH = GOC / "server" / "static"

#: Bề ngang nên soi. Sáu mốc của Prompt 06; công cụ chỉ ghi ra, người soi tự đặt.
BE_NGANG = (1920, 1440, 1280, 1024, 768, 390)


def _mo_moi_truong(thu_muc: pathlib.Path):
    """CSDL SQLite dùng một lần + cờ bật + khoá phiên giả.

    ⚠️ **Không** chạm `LTT_DATABASE_URL` thật. Đặt biến môi trường TRƯỚC khi
    `platform_core.db` dựng engine, và gọi `reset_engine()` để chắc chắn không
    dùng lại engine của một lần import trước.
    """
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(thu_muc / 'mau.db').as_posix()}"
    os.environ["LTT_ENV"] = "development"
    os.environ["LTT_SESSION_SECRET"] = "vps-dung-mau"
    os.environ["LTT_VPS"] = "1"
    os.environ.pop("TURNSTILE_SECRET_KEY", None)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.vps.tables       # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    return dbmod


def _tao_khach(dbmod, credit_ban_dau: int = 50_000) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="mau@lttstudios.test",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, credit_ban_dau)
        db.commit()
        return str(u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _client():
    from fastapi.testclient import TestClient
    from server.app import create_app
    return TestClient(create_app(), base_url="https://testserver",
                      follow_redirects=False)


def _co_suc_chua(bat: bool) -> None:
    """Giả vờ node Proxmox trả lời (hoặc không).

    🔴 **Vì sao phải giả, và vì sao phải nói rõ là giả.** Máy phát triển không
    nói được tới Proxmox, nên `nguon_luc.do_nguon_luc()` trả `None` và trang đi vào
    nhánh **fail-closed**: bảng giá chỉ đọc, không dựng `<form>`, mọi gói hiện
    "hết chỗ". Đó là một trạng thái **thật và đáng soi** — nhưng nó KHÔNG phải
    trạng thái mà khách đang thấy trên production, nơi node trả lời bình thường.

    Dựng cả hai cảnh là cách duy nhất để so ảnh chụp với trang đang chạy.

    ⚠️ Con số dưới đây là **hư cấu để render**, không phải số đo. Đừng trích nó
       vào bất kỳ tài liệu nào nói về công suất thật — số thật ở
       `docs/VPS/PHAN_TICH_VPS_PROXMOX.md`.
    """
    from apps.vps import bang_thong
    from apps.vps.services import capacity, nguon_luc

    if not bat:
        # Khong do duoc gi ca: dung ca `suc_chua` lan hai gioi han. Day la
        # canh fail-closed that — trang phai noi "dang bao tri", KHONG noi
        # "het cho" (su co 23/09).
        nguon_luc.do_nguon_luc = lambda db, profile=None: nguon_luc.DoDuoc(
            None, None, None)
        return

    gia = capacity.SucChua(ram_mb_tong=196_608, dia_gb_tong=900,
                           ram_mb_da_hua=24_576, dia_gb_da_hua=240,
                           dia_gb_dang_dung=96, cpu_tong=32, vcpu_da_hua=8)
    nguon_luc.do_nguon_luc = lambda db, profile=None: nguon_luc.DoDuoc(
        suc_chua=gia, free_ipv4=7, gateway_slots=150,
        da_hua_bang_thong_gb=0,
        ngan_sach_bang_thong_gb=bang_thong.ngan_sach_hua_gb())


def _co_cong_vao(dbmod) -> None:
    """Một cổng vào đang nhận máy — nếu không thì `vung` rỗng và biểu mẫu thiếu
    trường ẩn `vung`, tức một biểu mẫu không gửi được."""
    from apps.vps.tables import VpsGateway

    gen = dbmod.get_session()
    db = next(gen)
    try:
        db.add(VpsGateway(ten="cong-vao-mau", vung="sgp",
                          ip_cong_khai="203.0.113.10",
                          dang_nhan_may_moi=True))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


#: Bộ máy giả phủ các trạng thái mà Prompt 02 đòi soi bằng mắt.
#:
#: ⚠️ Đây là **dữ liệu để render**, không phải dữ liệu thật và không phải một
#:    kịch bản thử nghiệp vụ. Nó tồn tại để trả lời đúng một câu hỏi: *"trạng
#:    thái này hiện ra trông thế nào"* — câu mà đọc template không trả lời được.
MAY_MAU = (
    # (ten, plan, os, trang_thai, con_ngay, bang_thong_%, giam_toc, ip, ly_do)
    ("vps-01", "vps-vua", "winsrv2022-gui", "dang_chay", 24, 14, False,
     "45.77.23.125", ""),
    ("vps-02", "vps-nho", "winsrv2022-core", "da_tat", 2, 92, False,
     "45.77.23.126", ""),
    ("may-render", "vps-lon", "win10", "dang_tao", 30, 0, False, "", ""),
    ("vps-04", "vps-nho", "winsrv2016-core", "bi_treo", -3, 100, True,
     "45.77.23.128", "Hết hạn thanh toán ngày 24/08/2026."),
    ("vps-05", "vps-vua", "winsrv2022-gui", "loi", 12, 41, False, "",
     "Không cấp được địa chỉ IP: hết địa chỉ rảnh ở cổng vào."),
)


def _tao_may_gia(dbmod, user_id: str) -> None:
    """Dựng bộ máy giả để soi màn B (và màn C ở Đợt 4).

    🔴 **Vì sao phải giả.** Sau đợt dọn 25/08, bốn bảng `vps_*` về **0 dòng** —
       không có máy nào trên máy này, và tạo một máy thật thì trừ credit thật và
       ăn một Reserved IP của Vultr (hạn ngạch đếm cả IP vừa xoá). Mà ba trạng
       thái đáng soi nhất — `dang_tao`, `bi_treo`, `loi` — thì **không dựng được
       theo yêu cầu** kể cả khi có máy thật: phải chờ chúng tự xảy ra.
    """
    from datetime import datetime, timedelta, timezone

    from apps.vps.cost import lay_plan
    from apps.vps.tables import VpsEvent, VpsInstance, VpsIp

    gen = dbmod.get_session()
    db = next(gen)
    try:
        gw = db.execute(select_gateway()).scalars().first()
        gid = gw.id if gw is not None else ""
        bay_gio = datetime.now(timezone.utc)
        for i, (ten, plan_id, os_id, tt, con_ngay, pt, giam, ip, ly_do) in \
                enumerate(MAY_MAU):
            plan = lay_plan(plan_id)
            han = int(plan.bang_thong_gb) * 1024 ** 3 if plan else 0
            m = VpsInstance(
                user_id=user_id, ten=ten, plan_id=plan_id, os_id=os_id,
                gateway_id=gid, trang_thai=tt, vmid=9000 + i, ly_do=ly_do,
                bang_thong_byte=int(han * pt / 100), bi_giam_toc=giam,
                paid_until=bay_gio + timedelta(days=con_ngay),
                sao_luu_luc=(bay_gio - timedelta(days=3)
                             if tt in ("dang_chay", "da_tat") else None),
            )
            db.add(m)
            db.flush()
            if ip:
                db.add(VpsIp(gateway_id=gid, dia_chi=ip, instance_id=m.id))
            # Nhật ký giả: đủ loại để soi CẢ nhãn người đọc, CẢ chấm đỏ của sự
            # kiện xấu, CẢ nhánh `_that_bai` mà `dieu_khien._lam` sinh động.
            for j, (loai, ct) in enumerate((
                    ("tao_moi", {"plan_id": plan_id, "os_id": os_id, "vung": "sgp"}),
                    ("tao_xong", {"vmid": 9000 + i}),
                    ("thu_phi", {"credit": 1790, "den": "2026-09-19T00:00:00",
                                 "bang_thong_byte": 92 * 1024 ** 3}),
                    ("bat", {"upid": "UPID:pve:0000A1B2:..."}),
                    ("tat_that_bai", {"loi": "may khong tra loi lenh tat mem"}),
                    ("sao_luu", {"anh": "ltt-auto-20260823-031200"}),
            )):
                db.add(VpsEvent(instance_id=m.id, loai=loai, boi="he_thong",
                                chi_tiet=ct,
                                created_at=bay_gio - timedelta(hours=6 - j)))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def select_gateway():
    from sqlalchemy import select

    from apps.vps.tables import VpsGateway
    return select(VpsGateway)


def _ghi_console(ra: pathlib.Path, dbmod, can: set[str]) -> pathlib.Path:
    """Dựng trang console bằng cách render template trực tiếp.

    🔴 **Không đi qua route.** `trang_console` mở một phiên VNC thật trên Proxmox
       trước khi render — không có Proxmox thì nó chuyển hướng kèm câu lỗi, và ta
       không bao giờ thấy trang. Ở đây ta gọi thẳng template với một vé giả.

    ⛔ Vì thế cảnh này chứng minh **bố cục và trạng thái ban đầu**, và KHÔNG
       chứng minh gì về: bắt tay RFB, gõ phím, chuột, Ctrl+Alt+Del, ngắt–nối
       lại. Những thứ đó cần Proxmox thật (quyết định D-02).
    """
    from apps.vps import nhan, os_images
    from apps.vps.cost import lay_plan
    from apps.vps.manifest import MANIFEST
    from apps.vps.services import console as console_svc
    from server.templating import templates

    may = _doi_tuong_may_dau(dbmod)
    assert may is not None, "khong co may gia nao de dung trang console"
    html = templates.get_template("vps_console.html").render(
        request=_YEU_CAU_GIA, nav=MANIFEST.slug, app=MANIFEST, may=may,
        menu_trai=[], trang_thai_nhan=nhan.trang_thai(may.trang_thai),
        badge=nhan.badge(may.trang_thai), plan=lay_plan(may.plan_id),
        os=os_images.lay_os(may.os_id), dia_chi="45.77.23.125",
        ve="ve-gia-chi-de-render", vnc_mat_khau="mat-khau-gia",
        han_ve_giay=console_svc.HAN_VE_GIAY,
        lang_hien_tai=lambda: "vi", asset_ver="mau", so_du_credit=lambda r: 0,
        url_for=lambda ten, path="": f"/static/{path}",
        app_tabs=lambda r: [], home_workspace=False, csrf_token="x")
    return _ghi(ra, "E_console", html, can)


class _YeuCauGia:
    """Đủ thuộc tính để `base.html` render — không hơn."""
    scope = {"path": "/vps/console-mau"}
    base_url = "https://mau.local/"
    query_params: dict = {}
    cookies: dict = {}
    headers: dict = {}
    session: dict = {}
    state = type("S", (), {})()


_YEU_CAU_GIA = _YeuCauGia()


def _doi_tuong_may_dau(dbmod):
    from sqlalchemy import select

    from apps.vps.tables import VpsInstance

    gen = dbmod.get_session()
    db = next(gen)
    try:
        m = db.execute(select(VpsInstance)).scalars().first()
        if m is not None:
            db.expunge(m)
        return m
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _danh_sach_may(dbmod) -> list[dict]:
    """`[{id, trang_thai}]` của các máy giả — để dựng trang C cho từng trạng thái."""
    from sqlalchemy import select

    from apps.vps.tables import VpsInstance

    gen = dbmod.get_session()
    db = next(gen)
    try:
        return [{"id": str(m.id), "trang_thai": str(m.trang_thai)}
                for m in db.execute(select(VpsInstance)).scalars()]
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _dang_nhap(client) -> None:
    login = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
    client.post("/login", data={"username": "mau@lttstudios.test",
                                "password": "matkhau-tot-12",
                                "csrf_token": token})


_RE_TINH = re.compile(r'(["\'])/static/([^"\'?]+)(\?[^"\']*)?\1')


def _doi_duong_tinh(html: str, can: set[str]) -> str:
    """`/static/x?v=abc` → `static/x`, và ghi lại tệp nào cần chép sang.

    🔑 Giữ nguyên **nội dung** tệp tĩnh, chỉ đổi đường dẫn: mục đích của công cụ
    này là soi đúng `ltt.css` đang chạy, không phải một bản sao.

    🔴 **Đường TƯƠNG ĐỐI, phục vụ qua HTTP — KHÔNG phải `file://`.** Bản đầu của
       công cụ này ghi `file:///D:/...` và Chrome (qua `playwright-cli`) **chặn
       thẳng giao thức `file:`**.

       ⚠️ Triệu chứng của lần đó rất dễ đọc nhầm: mọi số đo trả về **0** và
          `docH == chiều cao khung nhìn` — trông y hệt *"trang render ra rỗng"*,
          trong khi sự thật là *"trình duyệt từ chối mở tệp"*. Suýt nữa thì đi
          tìm lỗi trong template.

    ⚠️ Bỏ `?v=` vì tệp chép sang không mang chuỗi truy vấn. Điều đó **không** làm
       mất tính chất đang soi: ở đây ta soi **bố cục**, còn cache-bust thì
       `test_304` và quy tắc 6 của `CLAUDE.md` canh ở chỗ khác.
    """
    def thay(m):
        ten = m.group(2)
        can.add(ten)
        return f'{m.group(1)}static/{ten}?v={_bam(ten)}{m.group(1)}'

    return _RE_TINH.sub(thay, html)


def _bam(ten: str) -> str:
    """Tám ký tự băm nội dung tệp tĩnh — để đổi tệp là đổi URL.

    🔴 **Không phải trang trí. Thiếu nó thì công cụ này nói dối.** Đo 26/08: sửa
       `ltt.css`, dựng lại, đo lại — và Chrome trả về **màu cũ**, vì URL
       `static/ltt.css` không đổi nên nó phục vụ bản trong bộ nhớ đệm. Suýt nữa
       thì kết luận "luật CSS mới không thắng được độ đặc hiệu", trong khi luật
       mới còn chưa bao giờ tới trình duyệt.

    ⭐ Đây đúng là quy tắc 6 của `CLAUDE.md` — cái bẫy Cloudflare đã cắn dự án
       này một lần ở production — tái diễn ở quy mô một thư mục tạm. Cùng bệnh,
       cùng thuốc: **đổi nội dung = đổi URL**.
    """
    import hashlib

    p = TINH / ten
    if not p.is_file():
        return "0"
    return hashlib.md5(p.read_bytes()).hexdigest()[:8]


def _ghi(ra: pathlib.Path, ten: str, html: str, can: set[str]) -> pathlib.Path:
    p = ra / f"{ten}.html"
    p.write_text(_doi_duong_tinh(html, can), encoding="utf-8", newline="")
    return p


def _chep_tinh(ra: pathlib.Path, can: set[str]) -> None:
    """Chép đúng những tệp tĩnh mà các trang vừa dựng **thật sự tham chiếu**.

    Chép cả `server/static/` là chép cả bộ noVNC và mọi bundle React — hàng chục
    MB cho một lần soi bố cục.
    """
    import shutil

    for ten in sorted(can):
        nguon = TINH / ten
        if not nguon.is_file():
            print(f"  ! thieu tep tinh: {ten}")
            continue
        dich = ra / "static" / ten
        dich.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(nguon, dich)


def dung(ra: pathlib.Path) -> list[pathlib.Path]:
    """Dựng mọi cảnh. Trả danh sách tệp đã ghi."""
    ra.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vps-mau-") as tmp:
        dbmod = _mo_moi_truong(pathlib.Path(tmp))
        user_id = _tao_khach(dbmod)
        _co_cong_vao(dbmod)
        client = _client()
        tep: list[pathlib.Path] = []
        can: set[str] = set()
        try:
            # ── A · Storefront, khách ẩn danh, node còn chỗ ────────────────
            #    Đây là cảnh khớp với production — dùng nó để so ảnh chụp.
            _co_suc_chua(True)
            r = client.get("/vps")
            assert r.status_code == 200, f"/vps an danh tra {r.status_code}"
            tep.append(_ghi(ra, "A_storefront_an_danh", r.text, can))

            # ── A' · Cùng trang, nhưng node KHÔNG trả lời ──────────────────
            #    Fail-closed: bảng giá chỉ đọc, không `<form>`, mọi gói hết chỗ.
            #    Khách vào đúng lúc cụm bận sẽ thấy trang này, nên nó phải đẹp
            #    và phải nói được đi đâu — không chỉ "hết chỗ" rồi dừng.
            _co_suc_chua(False)
            r = client.get("/vps")
            tep.append(_ghi(ra, "A_storefront_het_suc_chua", r.text, can))

            # ── Điều khoản (không có vỏ điều khiển — chốt của test_298) ────
            r = client.get("/vps/dieu-khoan")
            assert r.status_code == 200
            tep.append(_ghi(ra, "A_dieu_khoan", r.text, can))

            # ── B · Đã đăng nhập, 0 máy — trạng thái RỖNG ─────────────────
            #    Người vừa tạo tài khoản xong thấy đúng màn này. Một bảng trống
            #    ở đây là một ngõ cụt: họ không biết bước tiếp là gì.
            _co_suc_chua(True)
            _dang_nhap(client)
            r = client.get("/vps")
            assert r.status_code == 200, f"/vps da dang nhap tra {r.status_code}"
            tep.append(_ghi(ra, "B_dang_nhap_khong_may", r.text, can))

            # ── B' · Đã đăng nhập, NĂM máy ở năm trạng thái khác nhau ─────
            _tao_may_gia(dbmod, user_id)
            r = client.get("/vps")
            assert r.status_code == 200
            tep.append(_ghi(ra, "B_dang_nhap_co_may", r.text, can))

            # ── C · Trang một máy, ở từng trạng thái ───────────────────────
            #    Đây là ba trang mà KHÔNG có máy thì không mở được — lý do
            #    công cụ này tồn tại.
            for m in _danh_sach_may(dbmod):
                r = client.get(f"/vps/{m['id']}")
                assert r.status_code == 200,                     f"/vps/{m['id']} tra {r.status_code}"
                tep.append(_ghi(ra, f"C_may_{m['trang_thai']}", r.text, can))

            # ── D · Hướng dẫn cài Windows ─────────────────────────────────
            #    Hai bản: một máy Windows Server (có bước chọn phiên bản) và
            #    một máy Windows 10 (không có) — nhánh điều kiện phải soi được.
            for m in _danh_sach_may(dbmod)[:3]:
                r = client.get(f"/vps/{m['id']}/cai-dat")
                assert r.status_code == 200,                     f"/cai-dat tra {r.status_code}"
                tep.append(_ghi(ra, f"D_cai_dat_{m['trang_thai']}", r.text, can))

            # ── E · Console ───────────────────────────────────────────────
            #    ⚠️ Route console gọi Proxmox THẬT để mở phiên VNC, nên ở đây nó
            #       luôn chuyển hướng về trang máy kèm một câu lỗi. Ta dựng
            #       trang bằng cách gọi thẳng template với dữ liệu giả — đủ để
            #       soi BỐ CỤC (thứ đọc mã không trả lời được), và KHÔNG đủ để
            #       nói gì về giao thức. Nói rõ ở đây để không ai trích dẫn sai.
            tep.append(_ghi_console(ra, dbmod, can))
        finally:
            client.close()
            dbmod.reset_engine()
        _chep_tinh(ra, can)
        return tep


def main() -> int:
    mac_dinh = pathlib.Path(
        os.environ.get("TEMP", tempfile.gettempdir())) / "vps_mau"
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ra", type=pathlib.Path, default=mac_dinh,
                    help="thu muc ghi HTML")
    ap.add_argument("--cong", type=int, default=8321,
                    help="cong goi y cho `python -m http.server`")
    tham_so = ap.parse_args()

    tep = dung(tham_so.ra)
    print(f"Da dung {len(tep)} canh vao {tham_so.ra}:")
    for p in tep:
        print(f"  {p.name}")
    # ⚠️ Phai phuc vu qua HTTP: Chrome (qua playwright-cli) CHAN giao thuc
    #    `file:`, va khi bi chan no khong bao loi ro — moi so do ve 0.
    print("\nSoi bang trinh duyet that (Chrome CHAN `file:`):")
    print(f"  cd {tham_so.ra}")
    print(f"  python -m http.server {tham_so.cong}")
    print(f"  playwright-cli open http://127.0.0.1:{tham_so.cong}/{tep[0].name}")
    print(f"  playwright-cli resize {BE_NGANG[1]} 900")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
