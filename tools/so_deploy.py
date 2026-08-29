"""So bản ĐANG CHẠY với cây nguồn, từng byte.

    python tools/so_deploy.py            # tóm tắt + liệt kê chỗ lệch
    python tools/so_deploy.py --het      # liệt kê hết, không cắt

Trả 0 khi khớp hoàn toàn, 1 khi lệch, 2 khi không thấy bản cài.

## ⭐ Vì sao đáng có một công cụ riêng cho việc này

Cập nhật ở kho này **xoá và thay TOÀN BỘ** `C:\\LTTPlatform\\app`. Không có
cách nào deploy *một phần*, nên câu hỏi "bản đang phục vụ khách có đúng là bản
tôi vừa sửa không" chỉ có hai đáp án — khớp hết, hoặc ai đó đã deploy đè lên.

Trước công cụ này, cách duy nhất để trả lời là **mở trang ra nhìn**, và cái đó
chỉ nhìn được những trang không cần đăng nhập. Ngày 27/08 câu hỏi rơi đúng vào
16 trang **cần đăng nhập** của `/developers`: Cloudflare chặn trình duyệt tự
động ở `/login` bằng thử thách bot, nên không phiên nào soi được chúng.

So byte trả lời được phần lớn câu hỏi đó mà **không cần đăng nhập gì cả**. Đo
27/08: `khop: 104 | lech: 0 | thieu: 0 | thua: 0`.

## ⛔ VÀ ĐÂY LÀ THỨ NÓ KHÔNG NÓI

Byte giống nhau **không** chứng minh hành vi giống nhau. Nó không biết gì về:

  · nhánh rẽ theo trạng thái tài khoản, quyền, dữ liệu thật đổ vào;
  · biến môi trường — `secrets/app.env` không nằm trong `app\\` và **không**
    được so ở đây (cố ý: công cụ này không đọc bí mật);
  · migration CSDL đã chạy tới đâu;
  · thứ Cloudflare phục vụ ở biên — CF có TTL riêng, nên origin đúng mà khách
    vẫn nhận bản cũ là chuyện **đã xảy ra thật** (xem CLAUDE.md quy tắc 6).

⇒ Nó đóng câu hỏi "origin có phải bản mới không", không đóng câu hỏi "trang có
   chạy đúng không". Đừng đọc `lech: 0` rộng hơn thế.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys

NGUON = pathlib.Path(__file__).resolve().parent.parent
DEPLOY = pathlib.Path(r"C:\LTTPlatform\app")

#: (thư mục, mẫu tên tệp). Chỉ những thứ **thay đổi thì người dùng thấy ngay**.
#: Không quét `.pyc`, không quét `venv\`, không quét `data\` (dữ liệu vận hành
#: thì LỆCH là đúng — cập nhật không chạm tới nó).
PHAM_VI = (
    ("server/templates", "*.html"),
    ("server/static", "*.css"),
    ("server/static", "*.js"),
    # CU: ("server/api", "*.py") + ("server/routes", "*.py").
    #
    # 🔴 Hai dong do de lai mot DIEM MU ngay trong cong cu an toan truoc deploy:
    #    `server/*.py` o CAP TREN CUNG khong duoc quet. Do la
    #    `admin.py` (5.000+ dong), `admin_api.py`, `app.py`, `templating.py`,
    #    `nexus_download.py` — tuc ca khu admin va vo ung dung.
    #
    # ⛔ Do 2026-08-29: `server/admin.py` LECH giua nguon va ban dang chay, va
    #    `so_deploy` bao "khop 452 | lech 9" ma khong he nhac toi no. Mot cong
    #    cu bao "toi da so xong" trong khi bo qua mot nua `server/` thi te hon
    #    khong co cong cu: nguoi ta tin no.
    #
    # `rglob` tu `server` da bao ham `server/api` va `server/routes`, nen mot
    # dong thay duoc ca hai — va khong bo sot phan con lai.
    ("server", "*.py"),
    ("apps", "*.py"),
    ("platform_core", "*.py"),
)


def _bam(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser(description="So ban dang chay voi cay nguon.")
    ap.add_argument("--het", action="store_true", help="liet ke het, khong cat")
    ap.add_argument("--deploy", default=str(DEPLOY), help="thu muc ban cai")
    args = ap.parse_args()

    deploy = pathlib.Path(args.deploy)
    if not deploy.exists():
        print(f"KHONG THAY ban cai: {deploy}")
        print("Day co the la may phat trien — xem CLAUDE.md muc 'dang o may nao'.")
        return 2

    lech: list[tuple[str, str, str]] = []
    thieu: list[str] = []
    thua: list[str] = []
    khop = 0

    for thu_muc, mau in PHAM_VI:
        goc = NGUON / thu_muc
        if not goc.exists():
            continue
        for f in sorted(goc.rglob(mau)):
            if "__pycache__" in f.parts:
                continue
            rel = f.relative_to(NGUON)
            d = deploy / rel
            if not d.is_file():
                thieu.append(rel.as_posix())
                continue
            if _bam(f) != _bam(d):
                lech.append((rel.as_posix(), _bam(f), _bam(d)))
            else:
                khop += 1

        goc_d = deploy / thu_muc
        if goc_d.exists():
            for f in sorted(goc_d.rglob(mau)):
                if "__pycache__" in f.parts:
                    continue
                if not (NGUON / f.relative_to(deploy)).is_file():
                    thua.append(f.relative_to(deploy).as_posix())

    print(f"khop: {khop} | lech: {len(lech)} | "
          f"thieu ben deploy: {len(thieu)} | thua ben deploy: {len(thua)}")

    cat = None if args.het else 25
    for r, a, b in lech[:cat]:
        print(f"  LECH  {r}  nguon={a} deploy={b}")
    for r in thieu[:cat]:
        print(f"  THIEU {r}  (co trong nguon, khong co ben deploy)")
    for r in thua[:cat]:
        print(f"  THUA  {r}  (con lai tu mot ban cu?)")
    if not args.het:
        du = max(0, len(lech) - 25) + max(0, len(thieu) - 25) + max(0, len(thua) - 25)
        if du:
            print(f"  ... va {du} muc nua — chay lai voi `--het` de xem het")

    if lech or thieu or thua:
        print()
        print("Ban dang chay KHONG khop cay nguon. Deploy lai bang")
        print("  powershell -ExecutionPolicy Bypass -File .\\setup\\2-cai-dat.ps1")
        print("hoac hoi phien khac xem ho co dang sua do khong.")
        return 1

    print()
    print("!! `lech: 0` chi noi ORIGIN dung ban moi. No KHONG noi Cloudflare da")
    print("   phuc vu ban moi (CF co TTL rieng), va KHONG noi trang chay dung.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
