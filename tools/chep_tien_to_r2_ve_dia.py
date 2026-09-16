r"""
chep_tien_to_r2_ve_dia.py — chép mọi object của MỘT tiền tố từ R2 về đĩa máy chủ,
TRƯỚC khi bật `LTT_STORAGE_LOCAL_PREFIXES` cho tiền tố đó (W-KHO).

    C:\LTTPlatform\venv\Scripts\python.exe tools\chep_tien_to_r2_ve_dia.py --tien-to voice/
    C:\LTTPlatform\venv\Scripts\python.exe tools\chep_tien_to_r2_ve_dia.py --tien-to voice/ --chep

## Vì sao phải chép TRƯỚC

`RoutedStorage` chỉ đổi NƠI ĐỌC/GHI, không di chuyển dữ liệu. Bật định tuyến mà
chưa chép thì mọi khoá `voice/…` đang sống trên R2 (bản nghe thử giọng mẫu
`voice/mau/…`, tệp kết quả còn hạn `voice/out/…`) lập tức "biến mất" với app:
`exists()` trả `False` trên đĩa, nút nghe thử không dựng, link tải 404.

## Hợp đồng

- Mặc định CHỈ LIỆT KÊ. `--chep` mới ghi.
- KHÔNG BAO GIỜ xoá gì trên R2. Dọn R2 là một quyết định riêng, sau khi đã kiểm.
- Idempotent: tệp đã có trên đĩa CÙNG kích thước thì bỏ qua — chạy lại sau khi
  bật định tuyến để nhặt nốt tệp ghi vào R2 trong khoảng chuyển giao.
- Ghi qua `LocalStorage.put` (ghi tệp tạm rồi đổi tên), cùng thư mục gốc mà
  `get_storage()` dùng (`<data_dir>\files`).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def ke_hoach(ds_r2, cuc_bo) -> list:
    """`ds_r2` = [(key, size)] → [(key, size, ly_do)] cho các tệp CẦN chép.

    Thuần, không I/O mạng — để test được mà không cần R2.
    """
    can = []
    for key, size in ds_r2:
        if key.endswith("/"):
            continue                       # "thư mục" rỗng do công cụ khác tạo
        if not cuc_bo.exists(key):
            can.append((key, size, "chua_co"))
        elif cuc_bo.size(key) != size:
            can.append((key, size, "lech_kich_thuoc"))
    return can


def thuc_hien(ke, r2, cuc_bo) -> int:
    """Chép theo kế hoạch; kiểm kích thước sau khi ghi. Trả số tệp đã chép."""
    from platform_core.storage import StorageError
    n = 0
    for key, size, _ in ke:
        with r2.open(key) as f:
            cuc_bo.put(key, f)
        if cuc_bo.size(key) != size:
            raise StorageError(f"chep lech kich thuoc: {key}")
        n += 1
    return n


def _liet_ke_r2(r2, tien_to: str):
    trang = r2._c().get_paginator("list_objects_v2")
    for p in trang.paginate(Bucket=r2.bucket, Prefix=tien_to):
        for o in p.get("Contents", []):
            yield o["Key"], int(o["Size"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tien-to", required=True, help="vd voice/ (bat buoc ket thuc bang /)")
    ap.add_argument("--chep", action="store_true", help="thuc su ghi (mac dinh chi liet ke)")
    ap.add_argument("--app-env", default=r"C:\LTTPlatform\secrets\app.env",
                    help="nap bien LTT_* chua co trong moi truong (khong in gia tri)")
    a = ap.parse_args(argv)

    # Dịch vụ nhận ENV qua nssm; một lệnh chạy tay thì không. Chỉ ĐẶT khoá chưa
    # có — biến đã đặt trong phiên (vd `LTT_DATA_DIR` thử nghiệm) thắng tệp.
    if a.app_env and os.path.isfile(a.app_env):
        with open(a.app_env, encoding="utf-8") as fh:
            for dong in fh:
                t = dong.strip()
                if t and not t.startswith("#") and "=" in t:
                    k, v = t.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    tien_to = a.tien_to.strip().replace("\\", "/").lstrip("/")
    if not tien_to.endswith("/") or ".." in tien_to:
        print("tien to phai ket thuc bang '/' va khong chua '..'")
        return 2

    from platform_core.storage import LocalStorage, _r2_from_env
    from platform_core.runtime_paths import resolve_runtime_paths
    r2 = _r2_from_env()
    cuc_bo = LocalStorage(os.path.join(resolve_runtime_paths().data_dir, "files"))

    ds = list(_liet_ke_r2(r2, tien_to))
    ke = ke_hoach(ds, cuc_bo)
    print(f"R2 {tien_to}: {len(ds)} object, {sum(s for _, s in ds) / 1e6:.1f} MB")
    print(f"can chep ve {cuc_bo.root}: {len(ke)} tep, {sum(s for _, s, _ in ke) / 1e6:.1f} MB")
    for key, size, ly_do in ke[:50]:
        print(f"  {ly_do:16} {size:10}  {key}")
    if not a.chep:
        print("(chi liet ke - them --chep de ghi)")
        return 0
    n = thuc_hien(ke, r2, cuc_bo)
    print(f"XONG: da chep {n} tep. R2 KHONG bi xoa gi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
