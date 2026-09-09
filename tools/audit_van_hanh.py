r"""
audit_van_hanh.py — kiểm tra sức khoẻ vận hành trước khi mở cho người dùng thật.

    python tools\audit_van_hanh.py            # kiểm, thoát 1 nếu có mục ĐỎ
    python tools\audit_van_hanh.py --nhanh    # bỏ phần gọi HTTP qua Internet

Khác `setup/4-nghiem-thu.ps1` (nghiệm thu sau khi CÀI): file này trả lời câu
"hệ thống có sẵn sàng cho người dùng thật không" — hàng đợi có tắc, đĩa có đầy,
sao lưu có mới, app nào chết, credit có khớp.

Mỗi mục trả một trong ba mức:
  OK    — đo được và đạt
  CANH  — đo được nhưng cần để mắt
  DO    — phải xử lý trước khi cho người dùng vào

Nguyên tắc: **không mục nào được đoán**. Không đo được thì báo CANH kèm lý do,
chứ không im lặng cho qua — im lặng là cách một hệ thống hỏng trông như đang tốt.
"""
from __future__ import annotations

import io
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

GOC = pathlib.Path(__file__).resolve().parent.parent
CAI = pathlib.Path(r"C:\LTTPlatform")
NHANH = "--nhanh" in sys.argv

ket_qua: list[tuple[str, str, str]] = []       # (muc, ten, chi_tiet)


def ghi(muc: str, ten: str, chi_tiet: str = "") -> None:
    ket_qua.append((muc, ten, chi_tiet))
    print(f"  [{muc:4s}] {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


def _ps(lenh: str) -> str:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", lenh],
                           capture_output=True, text=True, timeout=60)
        return (r.stdout or "").strip()
    except Exception as e:                       # noqa: BLE001
        return f"__LOI__{type(e).__name__}: {e}"


# ── 1. Dịch vụ ────────────────────────────────────────────────────────────────
def kiem_dich_vu() -> None:
    print("\n1. DỊCH VỤ")
    # `LTTStudioCodex` gỡ 09/09/2026 (pha 07) — giữ nó ở đây thì mọi lượt
    # audit sau khi deploy đều báo THIẾU một dịch vụ đã cố ý bỏ.
    for ten in ("LTTStudioWeb", "LTTStudioWorker"):
        ra = _ps(f"(Get-Service {ten} -ErrorAction SilentlyContinue).Status")
        if ra.startswith("__LOI__"):
            ghi("CANH", ten, f"không đọc được: {ra[7:]}")
        elif ra == "Running":
            ghi("OK", ten, "Running")
        elif not ra:
            ghi("DO", ten, "KHÔNG TỒN TẠI")
        else:
            ghi("DO", ten, f"trạng thái {ra}")


# ── 2. Đĩa ────────────────────────────────────────────────────────────────────
def kiem_dia() -> None:
    print("\n2. ĐĨA")
    ra = _ps("Get-PSDrive -PSProvider FileSystem | "
             "Where-Object { $_.Used -ne $null } | "
             "ForEach-Object { \"$($_.Name)|$($_.Used)|$($_.Free)\" }")
    if ra.startswith("__LOI__") or not ra:
        ghi("CANH", "dung lượng đĩa", "không đọc được")
        return
    for dong in ra.splitlines():
        try:
            ten, dung, con = dong.split("|")
            dung_i, con_i = int(dung), int(con)
        except ValueError:
            continue
        tong = dung_i + con_i
        if tong == 0:
            continue
        pct = con_i * 100 // tong
        gb = con_i / (1024 ** 3)
        # Job video ngốn hàng chục GB một lượt; dưới 20 GB là hết chỗ giữa chừng,
        # và job hỏng nửa vời tốn credit mà không ra kết quả.
        muc = "OK" if gb >= 50 else ("CANH" if gb >= 20 else "DO")
        ghi(muc, f"ổ {ten}:", f"còn {gb:.0f} GB ({pct}%)")


# ── 3. Cơ sở dữ liệu ─────────────────────────────────────────────────────────
def _nap_env_production() -> bool:
    f = CAI / "secrets" / "app.env"
    if not f.is_file():
        return False
    for dong in f.read_text(encoding="utf-8").splitlines():
        if "=" in dong and not dong.lstrip().startswith("#"):
            k, v = dong.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    return True


def kiem_csdl() -> None:
    print("\n3. CƠ SỞ DỮ LIỆU")
    if not _nap_env_production():
        ghi("CANH", "CSDL", "không thấy app.env — bỏ qua (máy phát triển?)")
        return
    try:
        import sqlalchemy as sa
        e = sa.create_engine(os.environ["LTT_DATABASE_URL"], pool_pre_ping=True)
        with e.connect() as c:
            head = c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
            ghi("OK", "kết nối + migration", f"head {head}")

            n_user = c.execute(sa.text("SELECT count(*) FROM users")).scalar()
            n_verified = c.execute(sa.text(
                "SELECT count(*) FROM users WHERE is_verified")).scalar()
            ghi("OK", "người dùng", f"{n_user} tài khoản, {n_verified} đã xác thực email")

            # Sổ credit phải KHỚP: tổng bút toán = tổng số dư. Lệch nghĩa là có
            # đường cộng/trừ credit đi tắt qua sổ — lỗi tiền, nặng nhất.
            tong = c.execute(sa.text("SELECT COALESCE(SUM(delta),0) FROM credit_entries")).scalar()
            am = c.execute(sa.text(
                "SELECT count(*) FROM (SELECT user_id, SUM(delta) s FROM credit_entries "
                "GROUP BY user_id) t WHERE t.s < 0")).scalar()
            ghi("OK" if am == 0 else "DO", "sổ credit",
                f"tổng {tong} credit, {am} tài khoản ÂM")

            n_paid = c.execute(sa.text(
                "SELECT count(*) FROM payment_orders WHERE status='paid'")).scalar()
            n_treo = c.execute(sa.text(
                "SELECT count(*) FROM payment_orders WHERE status='pending'")).scalar()
            ghi("OK", "đơn nạp", f"{n_paid} đã trả, {n_treo} đang chờ")
    except Exception as exc:                     # noqa: BLE001
        ghi("DO", "CSDL", f"{type(exc).__name__}: {exc}")


# ── 4. Hàng đợi job ──────────────────────────────────────────────────────────
def kiem_hang_doi() -> None:
    print("\n4. HÀNG ĐỢI JOB")
    if "LTT_DATABASE_URL" not in os.environ:
        ghi("CANH", "hàng đợi", "chưa có cấu hình CSDL")
        return
    try:
        import sqlalchemy as sa
        e = sa.create_engine(os.environ["LTT_DATABASE_URL"], pool_pre_ping=True)
        with e.connect() as c:
            rows = dict(c.execute(sa.text(
                "SELECT status, count(*) FROM jobs GROUP BY status")).all())
            ghi("OK", "job theo trạng thái",
                ", ".join(f"{k}={v}" for k, v in sorted(rows.items())) or "chưa có job")

            gio = datetime.now(timezone.utc) - timedelta(hours=1)
            ket = c.execute(sa.text(
                "SELECT count(*) FROM jobs WHERE status='running' AND started_at < :t"),
                {"t": gio}).scalar()
            ghi("OK" if ket == 0 else "CANH", "job chạy quá 1 giờ",
                f"{ket} job — có thể là job dài, hoặc worker đã chết giữa chừng")

            # Ten trang thai lay TU CHINH CSDL, khong go tay. Bo kiem nay tung
            # hoi `status='failed'` trong khi CSDL dung 'error' — truy van luon
            # tra 0 nen no bao XANH ma thuc ra khong do gi.
            ngay = datetime.now(timezone.utc) - timedelta(days=1)
            co = {r[0] for r in c.execute(sa.text("SELECT DISTINCT status FROM jobs"))}
            ten_loi = [s for s in co if s in ("error", "failed", "cancelled", "canceled")]
            ten_xong = [s for s in co if s in ("done", "succeeded", "success")]
            loi = c.execute(sa.text(
                "SELECT count(*) FROM jobs WHERE status = ANY(:s) AND created_at > :t"),
                {"s": ten_loi or ["__khong_co__"], "t": ngay}).scalar()
            xong = c.execute(sa.text(
                "SELECT count(*) FROM jobs WHERE status = ANY(:s) AND created_at > :t"),
                {"s": ten_xong or ["__khong_co__"], "t": ngay}).scalar()
            tong = loi + xong
            ti_le = (loi * 100 // tong) if tong else 0
            ghi("OK" if ti_le < 20 else ("CANH" if ti_le < 50 else "DO"),
                "tỉ lệ lỗi 24 giờ qua", f"{loi}/{tong} job lỗi ({ti_le}%)")
    except Exception as exc:                     # noqa: BLE001
        ghi("CANH", "hàng đợi", f"{type(exc).__name__}: {exc}")


# ── 5. Đường công khai ───────────────────────────────────────────────────────
def kiem_duong_cong_khai() -> None:
    print("\n5. ĐƯỜNG CÔNG KHAI (qua Cloudflare)")
    if NHANH:
        ghi("CANH", "HTTP", "bỏ qua vì --nhanh")
        return
    try:
        import httpx
    except ImportError:
        ghi("CANH", "HTTP", "thiếu httpx")
        return

    GOC_URL = "https://app.lttstudios.com"
    can = [("/health/ready", (200,)), ("/health/live", (200,)),
           ("/", (200, 302, 303)), ("/en/", (200,)),
           ("/nap", (200, 302, 303)),
           # Webhook: KHÔNG được 404/302. 405 cho GET nghĩa là đường vẫn sống.
           ("/webhooks/payment/payos", (405, 400, 200))]
    for duong, ok in can:
        try:
            r = httpx.get(GOC_URL + duong, follow_redirects=False, timeout=25.0)
            ghi("OK" if r.status_code in ok else "DO", duong,
                f"HTTP {r.status_code}" + ("" if r.status_code in ok else f" (mong {ok})"))
        except Exception as exc:                 # noqa: BLE001
            ghi("DO", duong, f"{type(exc).__name__}")


# ── 6. App trong registry ────────────────────────────────────────────────────
def kiem_app() -> None:
    print("\n6. APP")
    sys.path.insert(0, str(GOC))
    try:
        from platform_core import registry
    except Exception as exc:                     # noqa: BLE001
        ghi("DO", "registry", f"không nạp được: {type(exc).__name__}: {exc}")
        return
    try:
        ds = registry.discover()
    except Exception as exc:                     # noqa: BLE001
        ghi("DO", "registry", f"{type(exc).__name__}: {exc}")
        return
    bat = [a for a in ds if getattr(a.manifest, "enabled", True)]
    ghi("OK", "nạp manifest", f"{len(ds)} app, {len(bat)} đang bật")
    if not NHANH:
        try:
            import httpx
            for a in bat:
                p = getattr(a.manifest, "route_prefix", "")
                if not p:
                    continue
                try:
                    r = httpx.get("https://app.lttstudios.com" + p,
                                  follow_redirects=False, timeout=25.0)
                    # 303 = bắt đăng nhập, đúng cho app cần tài khoản.
                    ghi("OK" if r.status_code in (200, 302, 303) else "DO",
                        f"app {a.manifest.slug}", f"{p} → {r.status_code}")
                except Exception as exc:         # noqa: BLE001
                    ghi("DO", f"app {a.manifest.slug}", f"{p} → {type(exc).__name__}")
        except ImportError:
            pass


# ── 7. GPU ───────────────────────────────────────────────────────────────────
def kiem_gpu() -> None:
    print("\n7. GPU")
    sys.path.insert(0, str(GOC))
    try:
        from platform_core import gpu
        ds = gpu.list_gpus()
    except Exception as exc:                     # noqa: BLE001
        ghi("CANH", "GPU", f"không đọc được: {type(exc).__name__}")
        return
    if not ds:
        ghi("CANH", "GPU", "không thấy GPU — app dùng GPU sẽ xếp hàng vô hạn")
        return
    for g in ds:
        tong = getattr(g, "memory_total", 0) or 0
        con = getattr(g, "memory_free", 0) or 0
        ghi("OK", f"GPU {getattr(g, 'index', '?')}",
            f"{getattr(g, 'name', '?')} — còn {con}/{tong} MB")


# ── 8. Sao lưu ───────────────────────────────────────────────────────────────
def kiem_sao_luu() -> None:
    print("\n8. SAO LƯU")
    thu_muc = [CAI / "backups", pathlib.Path(r"D:\LTTBackups")]
    thay = False
    for d in thu_muc:
        if not d.is_dir():
            continue
        files = sorted(d.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        files += sorted(d.glob("*.sql*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            continue
        thay = True
        moi = files[0]
        tuoi = (datetime.now() - datetime.fromtimestamp(moi.stat().st_mtime)).days
        mb = moi.stat().st_size / (1024 ** 2)
        # Quá 7 ngày là mất quá nhiều dữ liệu nếu phải khôi phục.
        ghi("OK" if tuoi <= 2 else ("CANH" if tuoi <= 7 else "DO"),
            f"sao lưu {d.name}", f"{moi.name} — {tuoi} ngày trước, {mb:.0f} MB")
    if not thay:
        ghi("DO", "sao lưu", "KHÔNG tìm thấy bản sao lưu nào")


# ── 9. Log lỗi gần đây ───────────────────────────────────────────────────────
def kiem_log() -> None:
    print("\n9. LOG")
    d = CAI / "logs"
    if not d.is_dir():
        ghi("CANH", "log", "không thấy thư mục log")
        return
    import re as _re
    moc = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    # Loi TAM THOI luc deploy: Postgres dung roi chay lai, worker thu lai va di
    # tiep. Dem chung nhu loi that se lam moi lan deploy thanh mot bao dong gia.
    TAM_THOI = ("the database system is starting up",
                "the database system is shutting down",
                "server closed the connection unexpectedly")
    tong_that = 0
    for f in sorted(d.glob("*err*.log")):
        try:
            noi_dung = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        khoi = noi_dung.split("Traceback (most recent call last)")
        gan_day = tam = 0
        for k in khoi[1:]:
            dau = _re.search(r"(20\d\d-\d\d-\d\d \d\d:\d\d)", k)
            if dau and dau.group(1) < moc:
                continue                      # cu hon 24h, bo qua
            gan_day += 1
            if any(x in k for x in TAM_THOI):
                tam += 1
        that = gan_day - tam
        tong_that += that
        if gan_day == 0:
            continue
        ghi("OK" if that == 0 else ("CANH" if that < 10 else "DO"),
            f"log {f.name}",
            f"{gan_day} traceback trong 24h — {tam} tạm thời (deploy), {that} thật")
    if tong_that == 0:
        ghi("OK", "log 24h", "không có lỗi thật nào ngoài lúc deploy")


def main() -> int:
    print("=" * 62)
    print("  AUDIT VẬN HÀNH — app.lttstudios.com")
    print(f"  {datetime.now():%d/%m/%Y %H:%M}")
    print("=" * 62)
    for f in (kiem_dich_vu, kiem_dia, kiem_csdl, kiem_hang_doi,
              kiem_duong_cong_khai, kiem_app, kiem_gpu, kiem_sao_luu, kiem_log):
        try:
            f()
        except Exception as exc:                 # noqa: BLE001
            ghi("DO", f.__name__, f"chính mục kiểm tra bị lỗi: {type(exc).__name__}: {exc}")

    do = [k for k in ket_qua if k[0] == "DO"]
    canh = [k for k in ket_qua if k[0] == "CANH"]
    print("\n" + "=" * 62)
    print(f"  TỔNG: {len(ket_qua)} mục · {len(do)} ĐỎ · {len(canh)} CẢNH BÁO")
    if do:
        print("\n  PHẢI XỬ LÝ TRƯỚC KHI CHO NGƯỜI DÙNG VÀO:")
        for _m, t, c in do:
            print(f"    - {t}: {c}")
    if canh:
        print("\n  Để mắt:")
        for _m, t, c in canh:
            print(f"    - {t}: {c}")
    print("=" * 62)
    return 1 if do else 0


if __name__ == "__main__":
    raise SystemExit(main())
