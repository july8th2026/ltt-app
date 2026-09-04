r"""
studio_dev.py — dựng LTT Voice Studio ở TRẠNG THÁI CÓ DỮ LIỆU, để soi bằng mắt.

    python tools\studio_dev.py            # seed + chay tren cong 8123
    python tools\studio_dev.py --cookie   # in cookie phien (de Playwright dung)

## Vì sao cần một bộ khung riêng thay vì mở thẳng production

⛔ **Không được soi giao diện trên trang trống.** `docs/BAY_TRONG_CONG_CHAT_LUONG.md`
   và bài học `test_340` cùng nói một điều: một trang render 200 chưa chứng minh
   gì cả. Nhưng còn một cái bẫy hẹp hơn, và nó thuộc về việc SO SÁNH giao diện:

       chup mot trang RONG roi so voi mot anh mau CO DU LIEU
       -> moi khac biet deu doc len nhu mot loi bo cuc

   Vùng kết quả trống thì thấp; danh sách giọng trống thì ngắn; bảng phiên bản
   trống thì biến mất. So như thế cho ra một danh sách "thiếu" dài dằng dặc mà
   phần lớn chỉ là *chưa có dữ liệu*.

⭐ Nên tệp này seed đúng những thứ ảnh mẫu đang hiện: vài giọng, một giọng đã
   nhân bản, một kết quả đã xong có tệp phát được, và ít lượt gần đây.

🔴 KHÔNG chạm CSDL thật và KHÔNG chạm kho thật. Mọi thứ nằm dưới `tmp/studio_dev/`,
   một sqlite dùng một lần. Chạy lại là dựng lại từ đầu.

## Đăng nhập không đi qua ô mật khẩu

Bộ khung tự tạo một tài khoản dùng một lần rồi `POST /login` **bằng HTTP**, và
in ra cookie phiên. Playwright chỉ việc `cookie-set`.

⭐ Đây không phải mẹo vặt: nó giữ cho việc soi giao diện **không cần tới bất kỳ
   mật khẩu thật nào** của ai. Tài khoản thật của chủ máy không bao giờ phải đi
   qua một trình duyệt do máy điều khiển.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

THU_MUC = os.path.join(ROOT, "tmp", "studio_dev")
CSDL = os.path.join(THU_MUC, "studio.db")
KHO = os.path.join(THU_MUC, "kho")
EMAIL = "studio-dev@test.local"
MAT_KHAU = "khong-phai-mat-khau-that-12"
CONG_MAC_DINH = 8123

#: Kịch bản mẫu — cố ý có đủ thứ mà màn *Xem trước cách đọc* phải xử lý: số
#: tiền, ngày, phần trăm, và một câu tiếng Anh xen giữa.
KICH_BAN = (
    "Xin chào mọi người, chào mừng các bạn đến với LTT Voice Studio.\n"
    "Đây là công cụ AI Text to Speech mạnh mẽ, giúp bạn tạo giọng nói tự nhiên "
    "và biểu cảm chỉ trong vài giây.\n\n"
    "Hôm nay là ngày 20 tháng 5 năm 2025.\n"
    "Chúng ta sẽ cùng nhau khám phá những tính năng tuyệt vời của nền tảng này.\n"
    "Doanh thu tháng này đạt 1.250.000.000 đồng, tăng 15% so với tháng trước.\n\n"
    "Let's make content creation faster, easier, and more powerful with AI.\n"
    "LTT - Make it better. Make it LTT."
)


def _dat_moi_truong() -> None:
    os.environ["LTT_DATABASE_URL"] = "sqlite:///" + CSDL.replace("\\", "/")
    os.environ["LTT_ENV"] = "development"
    os.environ.setdefault("LTT_SESSION_SECRET", "studio-dev-khong-bi-mat")
    os.environ.pop("TURNSTILE_SECRET_KEY", None)
    # ⚠️ `sidecar_client.san_sang()` chi kiem token CO hay KHONG. Dat mot token
    #    gia o day de giao dien render dung trang thai "cong da thiet lap" —
    #    neu khong, mot banner do chiem het phia tren va moi phep do bo cuc deu
    #    lech. Lenh goi that se 401, va do la dieu DUNG: bo khung nay de soi
    #    GIAO DIEN, khong de kiem duong sinh tieng.
    os.environ.setdefault("LTT_VOICE_SIDECAR_TOKEN", "studio-dev-token-gia")


def _wav_im(duong: str, giay: float = 15.47, sr: int = 48_000) -> None:
    """Một tệp WAV im lặng, đủ để trình phát có thời lượng thật để hiện."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with wave.open(duong, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(b"\x00\x00" * int(sr * giay))


def seed(lam_lai: bool = True) -> None:
    if lam_lai and os.path.isdir(THU_MUC):
        shutil.rmtree(THU_MUC, ignore_errors=True)
    os.makedirs(THU_MUC, exist_ok=True)
    _dat_moi_truong()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models          # noqa: F401
    import apps.ltt_voice.tables         # noqa: F401
    import apps.ltt_voice.tables_du_an   # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, set_storage
    set_storage(LocalStorage(KHO))

    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session()
    db = next(gen)
    try:
        # Chạy lại với `--giu` thì tài khoản đã có; đó là một trạng thái hợp lệ,
        # không phải lỗi. Bản đầu để `UserError` bay lên và giết cả máy chủ.
        from platform_core.users import UserError
        try:
            u = tao_nguoi_dung(db, email=EMAIL, password=MAT_KHAU,
                               is_verified=True)
            db.commit()
            uid = str(u.id)
        except UserError:
            db.rollback()
            from platform_core.models import User
            from sqlalchemy import select
            uid = str(db.execute(
                select(User).where(User.email == EMAIL)).scalar_one().id)
            print("  [OK] dung lai tai khoan da co")
            return
        _seed_giong(db, uid)
        _seed_lich_su(db, uid)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    print(f"  [OK] seed xong: {THU_MUC}")
    print(f"       tai khoan: {EMAIL}")


def _seed_giong(db, uid: str) -> None:
    """Một giọng đã nhân bản, đang dùng được."""
    from apps.ltt_voice.tables import VoiceProfile, VoiceRepr

    p = VoiceProfile(public_id="vce_01K8f3a7GmQ2Jx7A", owner_id=uid,
                     ten_hien_thi="My Voice - Natural VI", ngon_ngu="vi",
                     trang_thai="active")
    db.add(p)
    db.flush()
    db.add(VoiceRepr(profile_id=p.id, ref_id=0, engine="vieneu",
                     storage_key="voice/repr/dev.bin",
                     fingerprint="dev", trang_thai="dang_dung"))


def _seed_lich_su(db, uid: str) -> None:
    """Ba lượt đọc đã xong, mới nhất có tệp phát được.

    ⚠️ Ghi THẲNG vào bảng `Job` của nền tảng chứ không chạy worker: bộ khung này
       để soi GIAO DIỆN, và bắt nó nạp model chỉ để có một hàng lịch sử là đổi
       mười giây lấy hai phút cộng một GPU.
    """
    from platform_core.models import Job

    from apps.ltt_voice.manifest import MANIFEST

    cau = [
        ("Xin chào mọi người, chào mừng các bạn đến với LTT Voice Studio.", 4.21),
        ("Đây là công cụ AI Text to Speech mạnh mẽ, giúp bạn tạo giọng nói "
         "tự nhiên và biểu cảm chỉ trong vài giây.", 6.37),
        ("Let's make content creation faster, easier, and more powerful with AI.",
         4.89),
    ]
    for i, (text, giay) in enumerate(cau):
        jid = f"devjob{i + 1:04d}"
        khoa = f"voice/out/{uid}/{jid}/tieng.wav"
        _wav_im(os.path.join(KHO, *khoa.split("/")), giay=giay)
        # 🔴 `"done"`, KHÔNG phải `"succeeded"`. Bản đầu của bộ khung dùng
        #    `"succeeded"` — nghe hợp lý, và **sai**: nền tảng dùng
        #    `models.JOB_DONE = "done"`. Hệ quả không phải một lỗi mà là một
        #    trạng thái GIẢ: ba lượt đọc hiện lên với chip **Error** đỏ ở màn
        #    Studio, và nếu tôi so ảnh lúc ấy thì tôi đang so một trang báo lỗi
        #    với một ảnh mẫu bình thường.
        #
        # ⭐ Đúng cái bẫy §27 cảnh báo, chỉ khác chiều: không phải trang RỖNG mà
        #    là trang SAI TRẠNG THÁI. Cả hai đều làm mọi khác biệt đọc lên như
        #    một lỗi bố cục.
        db.add(Job(
            id=jid, user_id=uid, app_slug=MANIFEST.slug,
            job_type="ltt_voice.synthesize", status="done",
            params={"text": text, "owner_id": uid},
            # ⚠️ `credit_cost` KHÔNG phải cột của `Job` — nó là một khoá trong
            #    `result` mà `job_runner` đọc để quyết toán. Đặt nhầm nó thành
            #    tham số khởi tạo cho ORM thì SQLAlchemy ném `TypeError`, và đó
            #    là một lời nhắc đúng: sổ tiền không nằm trong bảng job.
            # Khoa phai khop `features.KetQua.as_result` — template doc
            # `result.duration_s`, khong doc `giay`.
            result={"audio_key": khoa, "duration_s": round(giay, 3),
                    "text": text, "so_doan": 1,
                    "credit_cost": max(1, int(giay * 0.2)),
                    "toc_do": 1.0},
            progress=100))


def lay_cookie(cong: int) -> str:
    """Đăng nhập bằng HTTP rồi trả cookie phiên. Không đi qua ô mật khẩu nào."""
    import re
    import urllib.request

    goc = f"http://127.0.0.1:{cong}"
    bo = urllib.request.HTTPCookieProcessor()
    mo = urllib.request.build_opener(bo)

    with mo.open(f"{goc}/login", timeout=15) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not m:
        raise SystemExit("khong lay duoc csrf_token — may chu da chay chua?")

    import urllib.parse
    du_lieu = urllib.parse.urlencode({
        "username": EMAIL, "password": MAT_KHAU,
        "csrf_token": m.group(1)}).encode()
    try:
        mo.open(urllib.request.Request(f"{goc}/login", data=du_lieu), timeout=15)
    except urllib.error.HTTPError as e:
        if e.code not in (302, 303):
            raise
    for c in bo.cookiejar:
        if "session" in c.name.lower():
            return f"{c.name}={c.value}"
    raise SystemExit(f"khong thay cookie phien; co: "
                     f"{[c.name for c in bo.cookiejar]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cong", type=int, default=CONG_MAC_DINH)
    ap.add_argument("--cookie", action="store_true",
                    help="in cookie phien roi thoat (may chu phai dang chay)")
    ap.add_argument("--giu", action="store_true",
                    help="khong xoa du lieu cu truoc khi seed")
    a = ap.parse_args(argv)

    if a.cookie:
        print(lay_cookie(a.cong))
        return 0

    seed(lam_lai=not a.giu)
    _dat_moi_truong()

    import uvicorn
    print(f"  Studio dev: http://127.0.0.1:{a.cong}/ltt-voice")
    uvicorn.run("server.app:create_app", factory=True, host="127.0.0.1",
                port=a.cong, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
