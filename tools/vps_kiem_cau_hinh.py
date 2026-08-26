r"""Kiểm cấu hình VPS trên MÁY CHỦ trước khi mở bán.

## Vì sao cần một công cụ riêng cho việc này

`secrets/` **không bao giờ được chép khi deploy** (quy tắc ở `CLAUDE.md`). Toàn
bộ cấu hình VPS — địa chỉ Proxmox, token, id các ISO, đường vào router và cổng
vào — nằm ở `secrets/app.env` trong **cây nguồn**, và deploy không mang nó theo.

Đo ngày 2026-08-25: `C:\LTTPlatform\secretspp.env` có **0 biến VPS**, trong
khi cây nguồn có 12. Nghĩa là đặt `LTT_VPS=1` rồi deploy sẽ cho ra một trang
`/vps` **mở nhưng vĩnh viễn nói "Hiện chưa nhận máy mới"** — fail-closed làm
đúng việc, nhưng người vận hành sẽ đọc nó là "hệ thống hỏng" chứ không phải
"thiếu cấu hình", vì lý do thật nằm trong một dòng log.

Đây là loại lỗi chỉ lộ ra ở đúng lúc tệ nhất. Nên nó có một phép kiểm chạy được
trong mười giây, và phép kiểm đó nói **thiếu đúng biến nào**.

## Dùng

    python toolsps_kiem_cau_hinh.py
    python toolsps_kiem_cau_hinh.py --sinh-mau   # in khối cần thêm vào app.env

Không in giá trị bí mật — chỉ in tên biến và có/không.
"""
import argparse
import io
import pathlib
import sys

# Console Windows mac dinh cp1252; tep nay in tieng Viet co dau.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

# Tệp secrets của bản ĐANG CHẠY. Không phải tệp trong cây nguồn: sửa tệp nguồn
# không đổi gì trên máy chủ, và nhầm hai tệp này chính là cái bẫy ở trên.
APP_ENV = pathlib.Path("C:/LTTPlatform/secrets/app.env")
NGUON = pathlib.Path(__file__).resolve().parent.parent / "secrets" / "app.env"

# Biến BẮT BUỘC: thiếu một trong số này thì không tạo được máy nào.
BAT_BUOC = {
    "LTT_VPS": "cờ bật app — thiếu thì /vps trả 404",
    "LTT_VPS_PROXMOX_URL": "địa chỉ API Proxmox",
    "LTT_VPS_PROXMOX_TOKEN_ID": "token API (dạng user@realm!tên)",
    "LTT_VPS_PROXMOX_TOKEN_SECRET": "bí mật của token",
    "LTT_VPS_PROXMOX_NODE": "tên node trong cụm",
    "LTT_VPS_KHO_DIA": "kho lưu trữ đặt đĩa máy khách",
    "LTT_VPS_ROUTER_HOST": "VM router — đặt chỗ DHCP + đo băng thông",
    "LTT_VPS_ROUTER_USER": "tài khoản SSH vào router",
    "LTT_VPS_ROUTER_SSH_KEY": "khoá riêng SSH vào router",
    "LTT_VPS_GATEWAY_HOST": "cổng vào Vultr — NAT 1:1",
    "LTT_VPS_GATEWAY_USER": "tài khoản SSH vào cổng vào",
    "LTT_VPS_GATEWAY_SSH_KEY": "khoá riêng SSH vào cổng vào",
    "LTT_VULTR_API_KEY": "cấp/thu hồi Reserved IP",
}

# ISO: thiếu một cái thì bản Windows đó biến khỏi danh mục — app vẫn chạy, chỉ
# là khách không mua được bản đó. Nên nó là CẢNH BÁO, không phải lỗi.
ISO = {
    "LTT_VPS_ISO_WINSRV2016_CORE": "Windows Server 2016 (Core)",
    "LTT_VPS_ISO_WINSRV2016_GUI": "Windows Server 2016 (giao diện)",
    "LTT_VPS_ISO_WINSRV2022_CORE": "Windows Server 2022 (Core)",
    "LTT_VPS_ISO_WINSRV2022_GUI": "Windows Server 2022 (giao diện)",
    "LTT_VPS_ISO_WIN10": "Windows 10 LTSC 2021",
}

TUY_CHON = {
    "LTT_VPS_VUNG": "mã vùng hiển thị (mặc định có sẵn)",
    "LTT_VPS_PROXMOX_CA": "chứng chỉ CA nếu không dùng TLS tự ký",
}


def _doc(tep: pathlib.Path) -> dict:
    """Đọc app.env thành dict. `utf-8-sig` vì tệp có thể có BOM."""
    if not tep.exists():
        return {}
    ra = {}
    for dong in tep.read_text(encoding="utf-8-sig").splitlines():
        dong = dong.strip()
        if "=" in dong and not dong.startswith("#"):
            k, v = dong.split("=", 1)
            ra[k.strip()] = v.strip()
    return ra


def kiem_dieu_khoan() -> str:
    """Trang Điều khoản LTT VPS có tồn tại không. Trả chuỗi lỗi, hoặc rỗng.

    🔴 Vì sao đây là điều kiện MỞ BÁN chứ không phải một liên kết hỏng thường:
    khối clickwrap trên trang tạo máy nói *"Bấm 'Tạo máy' là bạn đồng ý với
    Điều khoản LTT VPS"*. Một liên kết chết ở đó làm cả câu ấy rỗng — khách
    "đồng ý" với một trang không tồn tại, và đó là lúc họ sắp trả tiền.

    ## Phép kiểm này ĐỔI BẢN CHẤT ngày 26/08, và đó là tin tốt

    Trước đó nó gọi HTTP ra `lttstudios.com` để xem trang WordPress có sống
    không — và suốt từ 25/08 câu trả lời là **404**: hai tệp HTML nằm trong kho
    nhưng chưa ai xuất bản. Một điều kiện mở bán phụ thuộc vào một thao tác thủ
    công trên một hệ thống khác, không có gì nhắc.

    Chủ sản phẩm chốt 26/08: điều khoản là **trang con của `/vps`**. Nên nó
    không thể "chưa xuất bản" nữa — nó lên tàu cùng app. Phép kiểm còn lại chỉ
    cần trả lời: **route có thật, và template có thật** không.

    ⭐ Không gọi mạng nữa cũng bỏ luôn cả một lớp nhiễu: hôm 25/08 chính máy này
       bị chặn 403 sau vài chục lần gọi, và khi đó `/terms/` — một trang chắc
       chắn sống — cũng trả 403. Một phép đo cần phân biệt ba trạng thái nay chỉ
       cần phân biệt hai.
    """
    # Chay tu `tools/` nen goc kho khong nam san trong `sys.path`.
    import sys
    goc = pathlib.Path(__file__).resolve().parent.parent
    if str(goc) not in sys.path:
        sys.path.insert(0, str(goc))

    mau = goc / "server" / "templates" / "vps_dieu_khoan.html"
    if not mau.exists():
        return f"thieu template {mau.name}"

    ma = (goc / "apps" / "vps" / "routes.py").read_text(encoding="utf-8")
    if '"/dieu-khoan"' not in ma:
        return "apps/vps/routes.py khong khai route /dieu-khoan"

    try:
        from apps.vps import dieu_khoan
        muc = dieu_khoan.NOI_DUNG()
    except Exception as exc:  # noqa: BLE001 — cong cu dong lenh, khong sap
        return f"khong dung duoc noi dung dieu khoan: {exc}"
    if len(muc) < 12:
        return f"dieu khoan chi co {len(muc)} muc — thieu so voi ban da duyet"

    ban = (goc / "server" / "templates" / "vps.html").read_text(encoding="utf-8")
    if "/dieu-khoan" not in ban:
        return "trang ban khong dan toi dieu khoan"
    return ""

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sinh-mau", action="store_true",
                    help="in khối cần thêm, lấy tên biến từ secrets nguồn")
    tham_so = ap.parse_args()

    if not APP_ENV.exists():
        print(f"KHONG THAY {APP_ENV}")
        print("  Day khong phai may chu (chua chay setup\2-cai-dat.ps1), hoac")
        print("  ban dang o may phat trien. Xem CLAUDE.md muc 'dang o may nao'.")
        return 2

    co = _doc(APP_ENV)
    thieu_bb = [k for k in BAT_BUOC if not co.get(k)]
    thieu_iso = [k for k in ISO if not co.get(k)]

    print(f"Doc: {APP_ENV}")
    print(f"  bien VPS dang co: {sum(1 for k in co if 'VPS' in k or 'VULTR' in k)}")
    print()

    print("BAT BUOC")
    for k, mo_ta in BAT_BUOC.items():
        print(f"  [{'x' if co.get(k) else ' '}] {k:<32} {mo_ta}")
    print()
    print("DIA CAI DAT (thieu = ban Windows do bien khoi danh muc)")
    for k, mo_ta in ISO.items():
        print(f"  [{'x' if co.get(k) else ' '}] {k:<32} {mo_ta}")
    print()
    print("TUY CHON")
    for k, mo_ta in TUY_CHON.items():
        print(f"  [{'x' if co.get(k) else ' '}] {k:<32} {mo_ta}")
    print()

    if tham_so.sinh_mau:
        nguon = _doc(NGUON)
        print("=" * 68)
        print("Khoi can them vao " + str(APP_ENV) + ":")
        print("(gia tri lay tu secrets nguon; KIEM lai truoc khi dan)")
        print("=" * 68)
        for k in list(BAT_BUOC) + list(ISO) + list(TUY_CHON):
            if not co.get(k) and nguon.get(k):
                print(f"{k}={nguon[k]}")
        print("=" * 68)
        print("Ghi bang UTF-8 KHONG BOM. Dung Out-File/Set-Content -Encoding utf8")
        print("(PowerShell 5.1 chen BOM -> json.load vo -> /health/ready tra 503).")
        print()

    loi_dk = kiem_dieu_khoan()
    print("DIEU KHOAN")
    if loi_dk:
        print(f"  [ ] trang Dieu khoan LTT VPS: {loi_dk}")
        print("      Clickwrap tro vao day. Lien ket 404 = khach 'dong y' voi")
        print("      mot trang khong ton tai, dung luc ho sap tra tien.")
    else:
        print("  [x] trang Dieu khoan LTT VPS song")
    print()

    # Chỉ CHẶN khi chắc chắn 404. "Không kết luận được" chỉ cảnh báo.
    # Truoc 26/08 cho nay chi chan khi chac chan 404, vi mot loi mang
    # khong phan biet duoc voi mot trang thieu. Nay phep kiem doc TEP
    # trong chinh kho — khong con trang thai "khong ket luan duoc".
    chac_chan_thieu = bool(loi_dk)
    if thieu_bb or chac_chan_thieu:
        if chac_chan_thieu and not thieu_bb:
            print("CHUA MO BAN DUOC: du bien moi truong, nhung trang Dieu khoan")
            print("chua xuat ban. Xuat ban hai tep nay len WordPress:")
            print("  docs/lttstudios-website/legal/vps-terms.html    -> /vps-terms/")
            print("  docs/lttstudios-website/vi/legal/vps-terms.html -> /dieu-khoan-vps/")
            return 1
    if thieu_bb:
        print(f"CHUA MO BAN DUOC: thieu {len(thieu_bb)} bien bat buoc.")
        print("  " + ", ".join(thieu_bb))
        print()
        print("Dat cac bien do vao " + str(APP_ENV) + " ROI moi khoi dong lai dich vu.")
        print("Chay lai lenh nay voi --sinh-mau de lay khoi can dan.")
        return 1

    if thieu_iso:
        print(f"CHAY DUOC, nhung {len(thieu_iso)} ban Windows se khong ban duoc:")
        for k in thieu_iso:
            print(f"  - {ISO[k]}  ({k})")
        return 0

    print("Du cau hinh. Con lai la viec cua chu san pham: khoi dong lai dich vu")
    print("roi kiem tren URL cong khai https://app.lttstudios.com/vps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
