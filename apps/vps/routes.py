"""HTTP của app VPS. CHỈ lo HTTP — mọi quy tắc ở `apps/vps/services/`.

Router KHÔNG tự viết prefix `/vps`; nền tảng gắn từ `MANIFEST.route_prefix`.

## Lớp chặn thứ hai, và thứ tự của nó

`MANIFEST.enabled` đọc cờ `LTT_VPS` lúc nạp, nhưng mọi handler ở đây còn kiểm lại
qua `Depends(_cong_co)`. Hai lớp vì chúng hỏng theo hai kiểu: manifest quyết định
app có **hiện trong catalog** không; route quyết định một URL gõ thẳng có **trả
lời** không.

**Thứ tự trong chữ ký quan trọng.** `Depends` chạy theo thứ tự khai báo, nên cổng
cờ phải đứng **trước** `require_login`. Đặt sau thì một route "đã đóng" vẫn chuyển
hướng về `/login` — tức là vẫn xác nhận nó tồn tại, và vẫn bắt khách đăng nhập vào
một thứ không mở.

404 chứ không 403: 403 xác nhận bề mặt này có thật.
"""
from __future__ import annotations

import logging

from fastapi import (APIRouter, Depends, Form, HTTPException, Request,
                     WebSocket, WebSocketDisconnect)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

import apps.vps as vps_app
from apps.vps import bang_thong, dieu_khoan, nhan, os_images, ten_may
from apps.vps.cost import CHU_KY_NGAY, PLANS, dia_tong_gb, lay_plan
from apps.vps.manifest import MANIFEST
from apps.vps.services import (billing, capacity, console, dieu_khien,
                               provisioning, sao_luu)
from apps.vps.services.proxmox import (ChuaCauHinh, ProxmoxError,
                                       client_tu_moi_truong)
from apps.vps.tables import VpsEvent, VpsInstance, VpsIp
from platform_core.i18n import N_
from platform_core.i18n import _ as _t
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

log = logging.getLogger(__name__)

router = APIRouter(tags=["vps"])


def _cong_co() -> None:
    """Cờ tắt → 404. Đặt TRƯỚC `require_login` trong mọi chữ ký."""
    if not vps_app.enabled():
        raise HTTPException(status_code=404)


def _chu(request: Request) -> str:
    u = user_hien_tai(request)
    uid = getattr(u, "id", None)
    if not uid:
        raise HTTPException(status_code=401)
    return str(uid)


def _suc_chua(db) -> tuple[capacity.SucChua | None, str]:
    """Sức chứa hiện tại, và lý do nếu không đọc được.

    Không đọc được Proxmox **không** phải lỗi trang: trang vẫn phải mở để khách
    xem máy của mình. Nhưng nút "Tạo máy" thì phải khoá — bán khi không biết còn
    bao nhiêu chỗ là đúng thứ `capacity.py` sinh ra để phòng.
    """
    try:
        client = client_tu_moi_truong()
        return provisioning.suc_chua_hien_tai(
            db, client.trang_thai_node(), client.kho_luu_tru(),
            client.danh_sach_vm()), ""
    except ChuaCauHinh as exc:
        return None, f"chua cau hinh Proxmox: {exc}"
    except ProxmoxError as exc:
        log.warning("vps: khong doc duoc suc chua: %s", exc)
        return None, "khong ket noi duoc may chu ao"


def _may_cua_toi(db, user_id: str) -> list:
    """Máy của một khách, kèm địa chỉ đã ghép sẵn để template khỏi tính toán."""
    may = list(db.execute(
        select(VpsInstance)
        .where(VpsInstance.user_id == user_id,
               VpsInstance.trang_thai != "da_xoa")
        .order_by(VpsInstance.created_at.desc())
    ).scalars())
    if not may:
        return []

    # Địa chỉ khách gõ vào LÀ IP công khai riêng của máy — từ 2026-08-24 không
    # còn `IP:cổng`. Chưa cấp xong thì để trống, đừng hiện địa chỉ của cổng vào:
    # khách sẽ thử gõ nó và rơi vào máy người khác.
    ip_rieng = {}
    for x in db.execute(
        select(VpsIp).where(VpsIp.instance_id.in_([m.id for m in may]))
    ).scalars():
        ip_rieng.setdefault(x.instance_id, x)

    ket_qua = []
    for m in may:
        x = ip_rieng.get(m.id)
        ket_qua.append({
            "may": m,
            "trang_thai_nhan": nhan.trang_thai(m.trang_thai),
            # Class badge tra SAN o day, khong tra trong template: cho template
            # tu tra nghia la phai dang ky them mot ham toan cuc vao
            # `server/templating.py` — mot tep MOI app di qua — de phuc vu mot khu.
            "badge": nhan.badge(m.trang_thai),
            "buoc_tiep": nhan.buoc_tiep(m.trang_thai),
            "bang_thong": {
                "da_dung": bang_thong.doc_duoc(m.bang_thong_byte),
                "han_muc_gb": (lay_plan(m.plan_id).bang_thong_gb
                               if lay_plan(m.plan_id) else 0),
                "phan_tram": bang_thong.phan_tram(m),
                "bi_giam_toc": bool(m.bi_giam_toc),
            },
            "plan": lay_plan(m.plan_id),
            "os": os_images.lay_os(m.os_id),
            "dia_chi": x.dia_chi if x is not None else "",
            "con_han": billing.con_han(m),
            "con_ngay": billing.con_bao_nhieu_ngay(m),
        })
    return ket_qua


#: Mục lục của trang cài Windows — **một nguồn** cho cả cột bên trái lẫn thứ tự
#: các mục bên phải.
#:
#: ⚠️ Đây là **mục lục**, không phải tiến độ. Không có bước nào lưu ở máy chủ, và
#:    Prompt 04 cấm dựng một cái: một dấu tích lưu được là một lời hứa rằng hệ
#:    thống biết khách đang ở đâu, mà nó thì không biết.
BUOC_CAI_DAT: tuple[tuple[int, str], ...] = (
    (1, N_("Mở console")),
    (2, N_("Bắt đầu cài")),
    (3, N_("Chọn ổ đĩa")),
    (4, N_("Chờ cài và khởi động lại")),
    (5, N_("Đặt mật khẩu Administrator")),
    (6, N_("Bật Remote Desktop")),
    (7, N_("Gỡ đĩa cài")),
    (8, N_("Nối bằng Remote Desktop")),
)

#: Khoá trong `chi_tiet` **không hiện cho khách**, vì hai lý do khác nhau:
#:
#: * `upid`, `vmid` — chỉ có nghĩa với người vận hành, và chúng nói ra hình dạng
#:   của cụm (số hiệu máy trong Proxmox, id tác vụ);
#: * `boi`, `anh`, `bang_thong_byte` — có nghĩa, nhưng đã có **chỗ tốt hơn**:
#:   người thực hiện thì hiện ở nhãn sự kiện, tên ảnh chụp thì ở ô Ảnh chụp, và
#:   `bang_thong_byte` được chụp để dựng **lịch sử về sau** (D-04), không phải để
#:   đọc trong nhật ký.
_KHOA_NOI_BO = frozenset({"upid", "vmid", "boi", "anh", "bang_thong_byte"})

#: Khoá → nhãn người đọc. Khoá không có trong bảng này thì hiện **nguyên khoá**,
#: cùng lý do với `nhan.trang_thai()`: một mã lạ ít nhất cho ta thứ để tra khi
#: khách chụp màn hình gửi tới, còn một ô trống thì không.
_NHAN_KHOA = {
    "credit": N_("credit"),
    "den": N_("trả tới"),
    "plan_id": N_("gói"),
    "os_id": N_("hệ điều hành"),
    "vung": N_("vùng"),
    "loi": N_("lỗi"),
    "cu": N_("tên cũ"),
    "moi": N_("tên mới"),
}


def _gia_tri_doc_duoc(khoa: str, gt) -> str:
    """Vài giá trị cần đổi dạng trước khi hiện.

    ⚠️ `den` là ISO 8601 (`2026-09-19T00:00:00`) — đúng cho máy đọc, và **sai**
       cho một dòng nhật ký mà người Việt đang đọc. Cắt về `dd/mm/yyyy`; không
       parse thành `datetime` vì chuỗi này do chính ta ghi ra và cắt là đủ, còn
       một lần parse là một chỗ để ném ngoại lệ trên trang của khách.
    """
    if khoa == "den" and isinstance(gt, str) and len(gt) >= 10:
        return f"{gt[8:10]}/{gt[5:7]}/{gt[0:4]}"
    return str(gt)


def _chi_tiet_doc_duoc(chi_tiet) -> str:
    """`chi_tiet` (JSON tự do) → một câu ngắn, hoặc chuỗi rỗng.

    Trước Đợt 4 trang máy đổ **nguyên dict** ra cột thứ ba của nhật ký. Đó là
    thứ viết cho người vận hành đọc — mà nhật ký này tồn tại để trả lời khách
    câu *"vì sao máy tôi bị tắt"* sau ba tháng.

    ⚠️ Chỉ đổi **cách gọi**, không đổi **ngữ nghĩa**: không gộp hai khoá, không
       suy diễn thêm, không bỏ một khoá vì nó trông xấu. Bỏ chỉ khi nó có chỗ
       tốt hơn — xem `_KHOA_NOI_BO`.
    """
    if not isinstance(chi_tiet, dict):
        return ""
    phan = [f"{_t(_NHAN_KHOA.get(k, k))}: {_gia_tri_doc_duoc(k, v)}"
            for k, v in sorted(chi_tiet.items())
            if k not in _KHOA_NOI_BO and v not in (None, "", [], {})]
    return " · ".join(phan)


def _thong_ke(ds: list) -> dict:
    """Bốn con số ở đầu trang: tổng · đang chạy · đã tắt · sắp hết hạn.

    Đếm **ở đây, không trong template**: một vòng lặp đếm trong Jinja là logic
    không test được, và bốn con số này là thứ khách quét mắt đầu tiên — sai một
    con số ở đó là sai ấn tượng đầu tiên về trạng thái hệ thống của họ.

    "Sắp hết hạn" dùng đúng ngưỡng mà trang đã cảnh báo đỏ (`con_ngay <= 3`), để
    ô chỉ số và nhãn đỏ trong danh sách **không bao giờ nói hai câu khác nhau**
    về cùng một máy.
    """
    con_ngay = [x["con_ngay"] for x in ds]
    return {
        "tong": len(ds),
        "dang_chay": sum(1 for x in ds if x["may"].trang_thai == "dang_chay"),
        "da_tat": sum(1 for x in ds if x["may"].trang_thai == "da_tat"),
        "sap_het_han": sum(1 for n in con_ngay if n is not None and n <= 3),
    }


def _menu(active: str, *, may=None, ds=()) -> list:
    """Menu trái cho vỏ `vps_base.html`. Rỗng ⇒ không dựng vỏ điều khiển.

    Trả rỗng cho khách ẩn danh là **có chủ ý**: menu là công cụ của người đã
    mua. Vultr chia làm hai site vì lẽ đó — `vultr.com` bán hàng không có thanh
    bên, `console.vultr.com` mới có.
    """
    from apps.vps import nav

    return nav.menu(active, may=may,
                    danh_sach_may=[{"id": x["may"].id, "ten": x["may"].ten}
                                   for x in ds])


def _ai_do(request: Request) -> str:
    """`user_id` cua nguoi dang xem, hoac chuoi rong neu chua dang nhap.

    Khac `_chu`: `_chu` NEM 401 khi khong co ai. Dung cho nhung trang phuc vu ca
    khach an danh — o day chi co mot trang nhu vay, va no la trang ban.
    """
    return str(getattr(user_hien_tai(request), "id", "") or "")


@router.get("", response_class=HTMLResponse)
def trang_chinh(request: Request,
                _g: None = Depends(_cong_co),
                db=Depends(get_db)):
    """Trang ban. **Khong doi dang nhap** — xem `_ai_do`.

    Khach an danh thay bang gia va ly do nen mua; khach da dang nhap thay may cua
    ho va bieu mau tao may. Mot URL, chia se duoc, khong ngo cut.

    Truoc 25/08 trang nay doi dang nhap, nen the app trong catalog (hien cho ca
    khach an danh vi `public=True`) tro toi mot trang dang nhap — mot ngo cut o
    dung buoc dau tien cua pheu ban hang.

    `_cong_co` van dung TRUOC: cong khai nghia la "khong doi dang nhap", khong
    phai "bo qua co `LTT_VPS`".
    """
    user_id = _ai_do(request)
    suc_chua, loi_ha_tang = _suc_chua(db)

    goi = []
    for p in PLANS:
        con_cho = (capacity.cho_phep_ban(suc_chua, p.id).cho_phep
                   if suc_chua is not None else False)
        goi.append({
            "plan": p,
            "credit": p.credit_thang,
            "con_cho": con_cho,
            "os": [o for o in os_images.os_ban_duoc()
                   if os_images.hop_le(p.id, o.id)[0]],
        })

    may_cua_toi = _may_cua_toi(db, user_id) if user_id else []
    return templates.TemplateResponse(request, "vps.html", {
        "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "goi": goi,
        # Dựng từ CSDL, không viết cứng: xem `provisioning.vung_dang_mo`.
        "vung": provisioning.vung_dang_mo(db),
        # Danh sách ĐẦY ĐỦ để trang tạo máy dựng sẵn mọi lựa chọn một lần; JS ẩn
        # bớt theo gói đang chọn. Không có JS thì khách vẫn thấy hết và máy chủ
        # vẫn từ chối tổ hợp sai (`os_images.hop_le`) — trang không bao giờ im
        # lặng bán một thứ không cài được.
        "os_ban_duoc": os_images.os_ban_duoc(),
        # Khach an danh khong co may nao; goi ham nay voi user_id rong se quet
        # ca bang va tra ve may cua NGUOI KHAC.
        "may_cua_toi": may_cua_toi,
        "thong_ke": _thong_ke(may_cua_toi),
        # Tên gợi ý cho ô "Tên máy" — điền sẵn để khách bỏ trống cũng có một cái
        # tên gõ được, thay vì một chuỗi hex 8 ký tự ở ô xác nhận phá huỷ (D-01).
        "ten_goi_y": ten_may.tu_sinh(db, user_id) if user_id else "",
        "da_dang_nhap": bool(user_id),
        # Rỗng cho khách ẩn danh ⇒ `vps_base.html` không dựng vỏ điều khiển.
        "menu_trai": _menu("tong_quan", ds=may_cua_toi) if user_id else [],
        "suc_chua": suc_chua,
        "loi_ha_tang": loi_ha_tang,
        "loi": request.query_params.get("loi", ""),
    })


@router.get("/dieu-khoan", response_class=HTMLResponse)
def trang_dieu_khoan(request: Request, _g: None = Depends(_cong_co)):
    """Dieu khoan LTT VPS. **Khong doi dang nhap** — va do la ca van de.

    Clickwrap ngay duoi nut "Tao may" tro toi day. Mot trang dieu khoan doi dang
    nhap la mot trang khach KHONG doc duoc truoc khi quyet dinh, tuc ho dong y
    voi mot thu ho chua tung thay.

    ⭐ Truoc 26/08 trang nay nam o site marketing WordPress va **chua bao gio
       duoc xuat ban** — `https://lttstudios.com/vps-terms/` tra 404 suot tu
       25/08, trong khi clickwrap da tro vao do. Khach "dong y" voi mot trang
       khong ton tai, dung luc ho sap tra tien. Mot trang do chinh app phuc vu
       khong the o trang thai do: no song hay chet cung phan con lai cua app.

    ⚠️ Khong dung `_menu(...)`: menu trai la cong cu cua nguoi DA mua, va trang
       nay phai doc duoc boi nguoi chua co tai khoan. Xem `vps_base.html`.
    """
    return templates.TemplateResponse(request, "vps_dieu_khoan.html", {
        "nav": MANIFEST.slug, "app": MANIFEST,
        "hieu_luc": dieu_khoan.HIEU_LUC,
        "mo_dau": dieu_khoan.mo_dau(),
        "muc": dieu_khoan.NOI_DUNG(),
        # Ro rang la rong: khach an danh khong thay vo dieu khien. Da dang nhap
        # cung khong — dieu khoan la mot van ban de doc, khong phai mot trang
        # cong cu, va mot menu ben canh no chi lam nguoi ta doc kem hon.
        "menu_trai": [],
    })


@router.post("/tao", response_class=HTMLResponse)
def tao_may(request: Request,
            csrf_token: str = Form(...),
            plan_id: str = Form(...),
            os_id: str = Form(...),
            # KHÔNG có mặc định viết cứng. Mặc định cũ là `"port"` — một vùng
            # đã bị bỏ — nên mọi lần gửi thiếu trường này đều hỏng, và hỏng bằng
            # một câu lỗi nội bộ hiện ra trước mặt khách.
            vung: str = Form(...),
            # D-01. Bỏ trống ⇒ tự sinh `vps-01`. **Không** bắt buộc: một trường
            # bắt buộc ở bước cuối của luồng mua là một chỗ để khách bỏ dở.
            ten: str = Form(""),
            dia_them_gb: int = Form(0),
            _g: None = Depends(_cong_co),
            _u: str = Depends(require_login),
            db=Depends(get_db)):
    """Tạo một máy: kiểm điều kiện, thu chu kỳ đầu, rồi NỘP JOB.

    Không có gì chạm Proxmox trong request này. Clone + sysprep + boot lần đầu mất
    vài phút tới hơn mười, mà Cloudflare cắt request ở **100 giây** — làm đồng bộ
    thì khách nhận lỗi 524 trong khi một máy vẫn đang được tạo ở phía sau, và
    không ai biết nó tồn tại.
    """
    user_id = _chu(request)
    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))

    plan = lay_plan(plan_id)
    if plan is None:
        return _ve_trang(_t("Gói không hợp lệ."))

    duoc, ly_do = os_images.hop_le(plan_id, os_id, dia_them_gb)
    if not duoc:
        return _ve_trang(ly_do)

    suc_chua, loi_ha_tang = _suc_chua(db)
    if suc_chua is None:
        return _ve_trang(_t("Hệ thống đang bận, chưa nhận máy mới. Thử lại sau."))
    kiem = capacity.cho_phep_ban(suc_chua, plan_id, dia_them_gb)
    if not kiem.cho_phep:
        return _ve_trang(_t("Đã hết chỗ cho cấu hình này. Vui lòng chọn gói nhỏ hơn."))

    try:
        gateway = provisioning.chon_gateway(db, vung)
    except provisioning.KhongCoGatewayError:
        return _ve_trang(_t("Vùng bạn chọn hiện không nhận máy mới."))

    # Tên: bỏ trống thì tự sinh. Kiểm TRƯỚC khi ghi gì vào CSDL — một tên trùng
    # phát hiện sau khi đã trừ tiền là một lỗi phải hoàn tiền để sửa.
    try:
        ten_may_moi = (ten_may.kiem_va_doc_nhat(db, user_id, ten)
                       if str(ten or "").strip() else ten_may.tu_sinh(db, user_id))
    except ten_may.TenKhongHopLeError as exc:
        return _ve_trang(str(exc))

    may = VpsInstance(user_id=user_id, plan_id=plan_id, os_id=os_id,
                      ten=ten_may_moi,
                      dia_them_gb=int(dia_them_gb or 0),
                      gateway_id=gateway.id, trang_thai="dang_tao")
    db.add(may)
    db.flush()

    # Thu chu kỳ đầu TRƯỚC khi nộp job: hết credit thì không được chiếm chỗ.
    try:
        billing.thu_mot_chu_ky(db, may)
    except billing.ThieuCreditError as exc:
        db.rollback()
        return _ve_trang(_t("Không đủ credit: %(ly_do)s") % {"ly_do": exc})

    provisioning.ghi_su_kien(db, may.id, "tao_moi", boi=user_id,
                             plan_id=plan_id, os_id=os_id, vung=vung)

    from platform_core import jobs as job_queue
    job_queue.submit(db, user_id=user_id, app_slug=MANIFEST.slug,
                     job_type="vps.provision",
                     params={"instance_id": may.id})
    db.commit()
    return RedirectResponse(MANIFEST.route_prefix, status_code=303)


# ── vòng đời một máy ─────────────────────────────────────────────────────────

def _may_cua_khach(db, request: Request, instance_id: str) -> VpsInstance:
    """Lấy máy VÀ kiểm nó thuộc về người đang đăng nhập.

    404 chứ không 403 khi máy của người khác: 403 xác nhận id đó có thật, và
    một danh sách id có thật là thứ đầu tiên người ta dò.
    """
    may = db.get(VpsInstance, str(instance_id or ""))
    if may is None or str(may.user_id) != _chu(request):
        raise HTTPException(status_code=404)
    return may


def _thao_tac(request: Request, csrf_token: str, instance_id: str, db, ham):
    """Khuôn chung của bật/tắt/khởi động lại: CSRF → chủ sở hữu → gọi → về trang.

    Ba thao tác này chạy THẲNG, không qua hàng đợi — xem docstring của
    `services/dieu_khien.py`.
    """
    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))
    may = _may_cua_khach(db, request, instance_id)
    try:
        client = client_tu_moi_truong()
    except ChuaCauHinh:
        return _ve_trang(_t("Hệ thống đang bận, thử lại sau."))
    try:
        ham(db, may, client, boi=_chu(request))
    except dieu_khien.KhongDuocPhepError as exc:
        return _ve_trang(str(exc))
    except ProxmoxError as exc:
        log.warning("VPS: thao tac tren may %s that bai: %s", may.id, exc)
        return _ve_trang(_t("Máy chủ không nhận lệnh lúc này. Thử lại sau ít phút."))
    return RedirectResponse(f"{MANIFEST.route_prefix}/{may.id}", status_code=303)


@router.post("/{instance_id}/bat")
def bat_may(instance_id: str, request: Request, csrf_token: str = Form(...),
            _g: None = Depends(_cong_co), _u: str = Depends(require_login),
            db=Depends(get_db)):
    return _thao_tac(request, csrf_token, instance_id, db, dieu_khien.bat)


@router.post("/{instance_id}/tat")
def tat_may(instance_id: str, request: Request, csrf_token: str = Form(...),
            _g: None = Depends(_cong_co), _u: str = Depends(require_login),
            db=Depends(get_db)):
    return _thao_tac(request, csrf_token, instance_id, db, dieu_khien.tat)


@router.post("/{instance_id}/khoi-dong-lai")
def khoi_dong_lai_may(instance_id: str, request: Request,
                      csrf_token: str = Form(...),
                      _g: None = Depends(_cong_co),
                      _u: str = Depends(require_login), db=Depends(get_db)):
    return _thao_tac(request, csrf_token, instance_id, db, dieu_khien.khoi_dong_lai)


@router.post("/{instance_id}/go-dia-cai")
def go_dia_cai(instance_id: str, request: Request, csrf_token: str = Form(...),
               _g: None = Depends(_cong_co), _u: str = Depends(require_login),
               db=Depends(get_db)):
    """Khách bấm khi đã cài xong Windows. Xem `dieu_khien.go_dia_cai`."""
    return _thao_tac(request, csrf_token, instance_id, db, dieu_khien.go_dia_cai)


@router.post("/{instance_id}/doi-ten")
def doi_ten_may(instance_id: str, request: Request, csrf_token: str = Form(...),
                ten: str = Form(""),
                _g: None = Depends(_cong_co), _u: str = Depends(require_login),
                db=Depends(get_db)):
    """Đổi **nhãn** của máy (D-01). Không chạm vào máy, không chạm hệ điều hành.

    ⚠️ **KHÔNG đòi gõ xác nhận**, khác hẳn ba nút trong khối Nguy hiểm. Đổi nhãn
       là việc **đảo được** — đặt rào chắn ở việc đảo được thì rào chắn ở việc
       KHÔNG đảo được bị nhờn, và đó là lúc nó thôi bảo vệ được ai.

    Ghi vào nhật ký vì nó đổi thứ mà ô xác nhận phá huỷ đòi gõ: khách đổi tên
    rồi ba tháng sau không xoá được máy sẽ cần biết tên cũ là gì.
    """
    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))
    may = _may_cua_khach(db, request, instance_id)
    cu = may.ten or ""
    try:
        may.ten = ten_may.kiem_va_doc_nhat(db, _chu(request), ten,
                                           tru_id=may.id)
    except ten_may.TenKhongHopLeError as exc:
        return _ve_trang(str(exc))
    if may.ten != cu:
        provisioning.ghi_su_kien(db, may.id, "doi_ten", boi=_chu(request),
                                 cu=cu, moi=may.ten)
    db.commit()
    return RedirectResponse(f"{MANIFEST.route_prefix}/{may.id}", status_code=303)


@router.get("/{instance_id}/cai-dat", response_class=HTMLResponse)
def huong_dan_cai_dat(instance_id: str, request: Request,
                      _g: None = Depends(_cong_co),
                      _u: str = Depends(require_login), db=Depends(get_db)):
    """Hướng dẫn khách tự cài Windows trên máy của họ.

    Trang riêng chứ không nhét vào trang máy: khách đọc nó **song song với
    console** ở tab khác, và trang máy thì đã dài.
    """
    may = _may_cua_khach(db, request, instance_id)
    ip = db.execute(
        select(VpsIp).where(VpsIp.instance_id == may.id)).scalars().first()
    img = os_images.lay_os(may.os_id)
    plan = lay_plan(may.plan_id)
    return templates.TemplateResponse(request, "vps_cai_dat.html", {
        "nav": MANIFEST.slug, "app": MANIFEST,
        "may": may,
        "menu_trai": _menu("cai_dat", may=may),
        "os": img,
        "plan": plan,
        "trang_thai_nhan": nhan.trang_thai(may.trang_thai),
        "badge": nhan.badge(may.trang_thai),
        "dia_chi": ip.dia_chi if ip is not None else "",
        "cong": img.cong_quen if img is not None else 3389,
        # Đĩa THẬT của máy này (gói + đĩa mua thêm) — sơ đồ hộp thoại Windows
        # dựng từ con số này, nên nó khớp đúng thứ khách sắp nhìn thấy (D-03).
        "dia_gb": dia_tong_gb(may.plan_id, may.dia_them_gb) if plan else 0,
        "buoc_muc_luc": BUOC_CAI_DAT,
        "csrf_token": issue_csrf_token(request),
    })


@router.post("/{instance_id}/cai-lai")
def cai_lai_may(instance_id: str, request: Request, csrf_token: str = Form(...),
                xac_nhan: str = Form(""), os_id: str = Form(""),
                _g: None = Depends(_cong_co), _u: str = Depends(require_login),
                db=Depends(get_db)):
    """Cài lại từ đầu. **Mất sạch dữ liệu**, nên đòi gõ đúng tên máy để xác nhận.

    Khuôn của GitHub, và lý do giống hệt: nút này không hoàn tác được, nên nó
    phải khó bấm nhầm hơn một cú click.
    """
    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))
    may = _may_cua_khach(db, request, instance_id)
    if str(xac_nhan).strip() != (may.ten or may.id[:8]):
        return _ve_trang(_t("Gõ đúng tên máy để xác nhận cài lại."))
    if may.trang_thai in ("dang_tao", "da_xoa"):
        return _ve_trang(_t("Máy đang bận hoặc đã bị xoá."))

    if os_id and not os_images.hop_le(may.plan_id, os_id, may.dia_them_gb)[0]:
        return _ve_trang(os_images.hop_le(may.plan_id, os_id, may.dia_them_gb)[1])

    may.trang_thai = "dang_tao"
    provisioning.ghi_su_kien(db, may.id, "xin_cai_lai", boi=_chu(request),
                             os_id=os_id or may.os_id)
    from platform_core import jobs as job_queue
    job_queue.submit(db, user_id=_chu(request), app_slug=MANIFEST.slug,
                     job_type="vps.rebuild",
                     params={"instance_id": may.id, "os_id": os_id or ""})
    db.commit()
    return RedirectResponse(f"{MANIFEST.route_prefix}/{may.id}", status_code=303)


@router.post("/{instance_id}/khoi-phuc")
def khoi_phuc_may(instance_id: str, request: Request, csrf_token: str = Form(...),
                  xac_nhan: str = Form(""),
                  _g: None = Depends(_cong_co), _u: str = Depends(require_login),
                  db=Depends(get_db)):
    """Quay máy về ảnh chụp gần nhất. **Mất mọi thay đổi sau thời điểm chụp.**

    Đòi gõ đúng tên máy, cùng khuôn với "Cài lại": cả hai đều không hoàn tác
    được, và cả hai đều nằm cạnh những nút vô hại.

    Chạy THẲNG chứ không qua hàng đợi — `rollback` của Proxmox trên LVM-thin là
    một thao tác siêu dữ liệu, xong trong vài giây. Đẩy nó vào hàng đợi chỉ thêm
    một tầng để hỏng mà không nhanh hơn.
    """
    from apps.vps.services import sao_luu

    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))
    may = _may_cua_khach(db, request, instance_id)
    if str(xac_nhan).strip() != (may.ten or may.id[:8]):
        return _ve_trang(_t("Gõ đúng tên máy để xác nhận khôi phục."))
    try:
        dieu_khien.kiem_dieu_khien_duoc(may)
    except dieu_khien.KhongDuocPhepError as exc:
        return _ve_trang(str(exc))

    try:
        client = client_tu_moi_truong()
        ten_anh = sao_luu.anh_moi_nhat(client, may.vmid)
        if not ten_anh:
            return _ve_trang(_t("Máy này chưa có ảnh chụp nào."))
        # Máy PHẢI tắt trước khi quay lại ảnh: Proxmox từ chối rollback một máy
        # đang chạy nếu ảnh không kèm RAM — và ảnh của ta cố ý không kèm RAM.
        try:
            client.tat_cung(may.vmid)
        except ProxmoxError:
            pass                                 # đã tắt sẵn — không phải lỗi
        client.khoi_phuc_anh(may.vmid, ten_anh)
    except ProxmoxError as exc:
        log.warning("VPS: khoi phuc may %s that bai: %s", may.id, exc)
        return _ve_trang(_t("Máy chủ không nhận lệnh lúc này. Thử lại sau ít phút."))

    may.trang_thai = "da_tat"
    provisioning.ghi_su_kien(db, may.id, "khoi_phuc", boi=_chu(request),
                             anh=ten_anh)
    db.commit()
    return RedirectResponse(f"{MANIFEST.route_prefix}/{may.id}", status_code=303)


@router.post("/{instance_id}/xoa")
def xoa_may(instance_id: str, request: Request, csrf_token: str = Form(...),
            xac_nhan: str = Form(""),
            _g: None = Depends(_cong_co), _u: str = Depends(require_login),
            db=Depends(get_db)):
    """Xoá vĩnh viễn. Không hoàn tác được — cũng đòi gõ đúng tên máy."""
    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))
    may = _may_cua_khach(db, request, instance_id)
    if str(xac_nhan).strip() != (may.ten or may.id[:8]):
        return _ve_trang(_t("Gõ đúng tên máy để xác nhận xoá."))
    if may.trang_thai == "da_xoa":
        return RedirectResponse(MANIFEST.route_prefix, status_code=303)

    provisioning.ghi_su_kien(db, may.id, "xin_xoa", boi=_chu(request))
    from platform_core import jobs as job_queue
    job_queue.submit(db, user_id=_chu(request), app_slug=MANIFEST.slug,
                     job_type="vps.destroy",
                     params={"instance_id": may.id, "boi": _chu(request)})
    db.commit()
    return RedirectResponse(MANIFEST.route_prefix, status_code=303)


@router.get("/{instance_id}", response_class=HTMLResponse)
def trang_chi_tiet(instance_id: str, request: Request,
                   _g: None = Depends(_cong_co),
                   _u: str = Depends(require_login), db=Depends(get_db)):
    may = _may_cua_khach(db, request, instance_id)
    ip = db.execute(
        select(VpsIp).where(VpsIp.instance_id == may.id)).scalars().first()
    # Nhật ký: dịch mã máy đọc thành câu người đọc **ở đây**, không trong
    # template. Template chỉ lặp; một bảng tra chép tay trong Jinja là bản sao
    # thứ hai của `nhan.SU_KIEN`, và bản sao sẽ lệch.
    #
    # ⚠️ `chi_tiet` là JSON tự do. Trước Đợt 4 nó đổ **nguyên dict** ra cho khách
    #    xem. Ở đây rút thành một câu ngắn, và **bỏ những khoá chỉ có nghĩa với
    #    người vận hành** (`upid` của Proxmox, `vmid`) — chúng không giúp khách
    #    và chúng nói ra hình dạng của cụm.
    su_kien = [
        {
            "luc": e.created_at,
            "nhan": nhan.su_kien(e.loai),
            "that_bai": nhan.su_kien_that_bai(e.loai),
            "xau": nhan.su_kien_xau(e.loai),
            "chi_tiet": _chi_tiet_doc_duoc(e.chi_tiet),
        }
        for e in db.execute(
            select(VpsEvent).where(VpsEvent.instance_id == may.id)
            .order_by(VpsEvent.created_at.desc()).limit(20)).scalars()
    ]

    # Sao kê thanh toán — điều khoản LTT VPS hứa "sao kê từng lần thu nằm trong
    # trang máy của bạn", nên nó phải có thật.
    #
    # Nguồn là `vps_event` chứ không phải `credit_entries`: sổ credit chỉ có
    # `user_id`, không có `instance_id`, nên **không quy được một lần thu về một
    # máy cụ thể**. Khách có ba máy thì ba dòng trừ tiền giống hệt nhau, và
    # không ai trả lời được "cái nào của máy nào".
    sao_ke = [
        {
            "luc": e.created_at,
            "credit": int((e.chi_tiet or {}).get("credit") or 0),
            "den": str((e.chi_tiet or {}).get("den") or "")[:10],
        }
        for e in db.execute(
            select(VpsEvent)
            .where(VpsEvent.instance_id == may.id, VpsEvent.loai == "thu_phi")
            .order_by(VpsEvent.created_at.desc()).limit(24)).scalars()
    ]
    return templates.TemplateResponse(request, "vps_chi_tiet.html", {
        "nav": MANIFEST.slug, "app": MANIFEST,
        "may": may,
        "menu_trai": _menu("may", may=may),
        "trang_thai_nhan": nhan.trang_thai(may.trang_thai),
        "badge": nhan.badge(may.trang_thai),
        "buoc_tiep": nhan.buoc_tiep(may.trang_thai),
        "sao_luu_luc": may.sao_luu_luc,
        "bang_thong": {
            "da_dung": bang_thong.doc_duoc(may.bang_thong_byte),
            "han_muc_gb": (lay_plan(may.plan_id).bang_thong_gb
                           if lay_plan(may.plan_id) else 0),
            "phan_tram": bang_thong.phan_tram(may),
            "bi_giam_toc": bool(may.bi_giam_toc),
        },
        "plan": lay_plan(may.plan_id),
        "os": os_images.lay_os(may.os_id),
        "dia_chi": ip.dia_chi if ip is not None else "",
        "con_han": billing.con_han(may),
        "con_ngay": billing.con_bao_nhieu_ngay(may),
        "su_kien": su_kien,
        "sao_ke": sao_ke,
        "tong_da_tra": sum(x["credit"] for x in sao_ke),
        "os_ban_duoc": os_images.os_ban_duoc(),
        # Cổng để dựng địa chỉ RDP. Chỉ để **hiển thị hướng dẫn**: NAT 1:1 mở
        # toàn bộ cổng của IP riêng cho máy đó.
        "cong": (os_images.lay_os(may.os_id).cong_quen
                 if os_images.lay_os(may.os_id) else 3389),
        # Ba hằng số này hiện ra trước mặt khách, nên chúng phải đọc từ mã chứ
        # không viết cứng trong template: đổi chu kỳ hay nhịp ảnh chụp mà quên
        # sửa trang là nói sai với người đang trả tiền.
        "chu_ky_ngay": CHU_KY_NGAY,
        "an_han_ngay": billing.AN_HAN_TRUOC_KHI_XOA_NGAY,
        "so_anh_giu": sao_luu.GIU,
        "csrf_token": issue_csrf_token(request),
        "loi": request.query_params.get("loi", ""),
    })


# ── console trong trình duyệt ────────────────────────────────────────────────

@router.get("/{instance_id}/console", response_class=HTMLResponse)
def trang_console(instance_id: str, request: Request,
                  _g: None = Depends(_cong_co),
                  _u: str = Depends(require_login), db=Depends(get_db)):
    """Trang chứa noVNC. Vé cấp ở đây, tiêu ở bước mở WebSocket.

    Vé đi qua **query string của WebSocket**, không qua cookie: WebSocket không
    có CSRF, và một cookie tự động gửi kèm nghĩa là bất kỳ trang nào cũng mở
    được console của khách bằng một dòng JavaScript.
    """
    may = _may_cua_khach(db, request, instance_id)
    try:
        dieu_khien.kiem_dieu_khien_duoc(may)
    except dieu_khien.KhongDuocPhepError as exc:
        return _ve_trang(str(exc))

    # Mở phiên VNC NGAY Ở ĐÂY, không ở bước WebSocket: vé của Proxmox vừa là
    # query `vncticket` của URL (server dùng) vừa là **mật khẩu VNC** trong bước
    # bắt tay RFB (trình duyệt dùng). Gọi hai lần là hai phiên khác nhau, và vé
    # của phiên B không mở được cổng của phiên A.
    try:
        ve_pve = client_tu_moi_truong().ve_console(int(may.vmid))
    except (ProxmoxError, ChuaCauHinh) as exc:
        log.warning("VPS console: khong mo duoc phien VNC cho %s: %s", may.id, exc)
        return _ve_trang(_t("Không mở được console lúc này. Thử lại sau ít phút."))

    ip = db.execute(
        select(VpsIp).where(VpsIp.instance_id == may.id)).scalars().first()
    return templates.TemplateResponse(request, "vps_console.html", {
        "nav": MANIFEST.slug, "app": MANIFEST,
        "may": may,
        "menu_trai": _menu("console", may=may),
        # Dải danh tính dùng chung với trang máy và trang cài Windows: ba trang
        # cùng hiện MỘT danh tính, và ba bản sao sẽ lệch.
        "trang_thai_nhan": nhan.trang_thai(may.trang_thai),
        "badge": nhan.badge(may.trang_thai),
        "plan": lay_plan(may.plan_id),
        "os": os_images.lay_os(may.os_id),
        "dia_chi": ip.dia_chi if ip is not None else "",
        "ve": console.cap_ve(db, may, _chu(request),
                             cong=ve_pve.get("port") or 0,
                             pve_ve=ve_pve.get("ticket") or ""),
        # Trình duyệt cần vé này làm mật khẩu VNC. Nó chỉ mở được ĐÚNG cổng của
        # phiên này, trên một máy chủ mà khách không biết địa chỉ — chính giao
        # diện Proxmox cũng làm y như vậy với người dùng của nó.
        "vnc_mat_khau": ve_pve.get("ticket") or "",
        "han_ve_giay": console.HAN_VE_GIAY,
    })


@router.websocket("/{instance_id}/console/ws")
async def cau_console(websocket: WebSocket, instance_id: str, ve: str = ""):
    """Bắc cầu byte giữa trình duyệt khách và console của Proxmox.

    Khách **không bao giờ** biết địa chỉ Proxmox và không bao giờ cầm vé của
    Proxmox — nếu chạm được cổng 8006 thì họ chạm được giao diện quản trị của cả
    cụm, nơi có mọi máy của mọi khách và nút xoá của từng cái.

    Không dùng `Depends` ở đây: WebSocket của FastAPI không chạy chuỗi phụ thuộc
    giống HTTP, và trộn hai đường xác thực là cách chắc chắn để một trong hai bị
    bỏ quên. Tất cả kiểm tra nằm tường minh trong thân hàm.
    """
    import asyncio
    import ssl as ssl_mod

    if not vps_app.enabled():
        await websocket.close(code=1008)
        return

    from platform_core.db import get_session

    # `user_hien_tai` nhận bất cứ thứ gì có `.session`, và Starlette gắn session
    # cho CẢ WebSocket — nên không cần đường xác thực thứ hai. Hai đường xác
    # thực là cách chắc chắn để một trong hai bị bỏ quên.
    u = user_hien_tai(websocket)
    user_id = str(getattr(u, "id", "") or "")
    if not user_id:
        await websocket.close(code=1008)
        return

    gen = get_session()
    db = next(gen)
    try:
        may, cong, pve_ve = console.tieu_ve(db, ve, instance_id, user_id)
        client = client_tu_moi_truong()
        # Dùng lại ĐÚNG phiên VNC đã mở ở trang console. Gọi `ve_console` lần
        # nữa ở đây là mở một cổng mới, và vé của cổng B không mở được cổng A.
        dia_chi = console.dia_chi_websocket_proxmox(
            client.config, int(may.vmid), {"port": cong, "ticket": pve_ve})
    except (console.VeKhongHopLeError, ProxmoxError, ChuaCauHinh) as exc:
        log.warning("VPS console: tu choi mo cau: %s", exc)
        await websocket.close(code=1008)
        return
    finally:
        gen.close()

    import websockets

    ctx = ssl_mod.create_default_context()
    if not client.config.verify:
        # Cụm dùng chứng chỉ tự ký. Đây là kết nối TỪ SERVER MÌNH tới Proxmox
        # trong LAN, không phải kết nối của khách — cùng mức tin cậy với mọi lời
        # gọi API khác trong `proxmox.py`.
        ctx.check_hostname = False
        ctx.verify_mode = ssl_mod.CERT_NONE

    await websocket.accept(subprotocol="binary")
    try:
        async with websockets.connect(
                dia_chi, ssl=ctx, subprotocols=["binary"],
                additional_headers=client._headers(), open_timeout=20) as pve:
            # KHÔNG gửi dòng `user:ticket` nào ở đây. Đó là giao thức của
            # `termproxy` (xterm.js); `vncproxy` thì vé là **mật khẩu VNC** và
            # nó đi qua bước bắt tay RFB do trình duyệt thực hiện. Chèn một dòng
            # chữ vào giữa luồng nhị phân VNC làm Proxmox đóng kết nối ngay và
            # KHÔNG NÓI GÌ — triệu chứng chỉ là "console trắng". Mất một buổi
            # 24/08 để tìm ra, và chỉ tìm ra khi mở trình duyệt thật.

            async def khach_toi_pve():
                while True:
                    goi = await websocket.receive()
                    if goi.get("type") == "websocket.disconnect":
                        return
                    await pve.send(goi.get("bytes") or goi.get("text") or b"")

            async def pve_toi_khach():
                async for goi in pve:
                    if isinstance(goi, bytes):
                        await websocket.send_bytes(goi)
                    else:
                        await websocket.send_text(goi)

            xong, con_lai = await asyncio.wait(
                {asyncio.create_task(khach_toi_pve()),
                 asyncio.create_task(pve_toi_khach())},
                return_when=asyncio.FIRST_COMPLETED)
            for t in con_lai:
                t.cancel()
    except WebSocketDisconnect:
        pass
    except Exception as exc:            # noqa: BLE001 - biên của một cầu nối
        log.warning("VPS console: cau dut giua chung: %s: %s",
                    type(exc).__name__, exc)
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass                        # khách đã đóng trước


def _ve_trang(loi: str) -> RedirectResponse:
    """Về trang chính kèm một câu giải thích. Không dựng lại cả trang ở nhánh lỗi
    — nhánh lỗi dựng trang là chỗ hai đường code lệch nhau theo thời gian."""
    from urllib.parse import quote
    return RedirectResponse(f"{MANIFEST.route_prefix}?loi={quote(str(loi))}",
                            status_code=303)
