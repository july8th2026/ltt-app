r"""mobile_qa.py — bộ khung đo mobile, lái bằng registry.

    python tools\mobile_qa.py kiem-ke [--ra ho_so.json]   # liet ke surface khach
    python tools\mobile_qa.py bang                        # du bang cho studio_dev

## Vì sao không gõ cứng danh sách app

`docs/MOBILE/01_MATRIX.md` phải nói đúng hiện trạng, mà hiện trạng đổi mỗi lần ai
đó thêm app hay lật `enabled`. Một danh sách chép tay **không có cách nào tự biết
nó đã cũ** — đúng cơ chế đã làm bảng trong `CLAUDE.md` nói sai năm lần. Nên chỗ
câu trả lời đến từ là `registry.discover()`, không phải một hằng số ở đây.

## Vì sao có lệnh `bang`

`tools/studio_dev.py` chỉ nạp bảng của `ltt_voice` — đúng với mục đích của nó.
Nhưng đo mobile thì đi qua **mọi** surface, và một sqlite thiếu `ommi_resource`
làm `/prompt-ai-ommi` trả 500. Ngày 05/09 lượt đo đầu tiên suýt ghi cái 500 ấy
vào báo cáo như một lỗi sản phẩm.

⛔ Đừng chữa bằng cách thêm `import apps.prompt_ai_ommi.tables` — đó là gõ cứng
   slug, và app thứ năm có `tables.py` sẽ lại rơi ra ngoài trong im lặng.
   `registry.load_app_tables()` đã làm đúng việc này cho cả Alembic lẫn server.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: sqlite dùng một lần của `studio_dev.py`. Không phải CSDL thật.
CSDL_DEV = GOC / "tmp" / "studio_dev" / "studio.db"


def kiem_ke() -> list[dict]:
    """Bản khai của mọi app, đọc lúc runtime từ registry."""
    from platform_core import registry

    ra = []
    for la in registry.discover():
        m = la.manifest
        ra.append({
            "slug": m.slug,
            "display": m.display_name,
            "route_prefix": m.route_prefix,
            "surface": m.surface,
            "lifecycle": m.lifecycle,
            "public": m.public,
            "enabled": m.enabled,
            "capabilities": list(m.capabilities),
            "job_types": list(m.job_types),
            "co_credit": m.credit_cost is not None,
        })
    ra.sort(key=lambda d: (d["surface"], d["slug"]))
    return ra


def du_bang() -> tuple[list[str], int]:
    """Dựng bảng của MỌI app vào sqlite của `studio_dev`. Trả (slug đã nạp, số bảng)."""
    os.environ["LTT_DATABASE_URL"] = "sqlite:///" + str(CSDL_DEV).replace("\\", "/")
    os.environ.setdefault("LTT_ENV", "development")
    os.environ.setdefault("LTT_SESSION_SECRET", "studio-dev-khong-bi-mat")

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import registry

    dbmod.reset_engine()
    da_nap = registry.load_app_tables()
    # `ltt_voice` có một module bảng thứ hai ngoài `tables.py`; registry chỉ
    # nạp `tables.py` theo hợp đồng, nên bảng dự án phải gọi tên ở đây.
    import apps.ltt_voice.tables_du_an  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    return da_nap, len(dbmod.Base.metadata.tables)


def wav_do_dai(uid: str, giay_list=(10, 60, 180, 300, 600)) -> list[tuple[int, int]]:
    """Sinh WAV nhieu do dai vao kho cua `studio_dev`, tra [(giay, byte)].

    Dung de do chi phi ve song (`docs/MOBILE/05_SONG_AM.md`). Dat 48 kHz mono
    16-bit vi do la dau ra that cua sidecar Voice.

    ⛔ KHONG ghi tep im lang. Mot tep toan `\\x00` nen rat tot va co the di duong
       tat trong bo giai ma — phep do se dep hon su that. Dung sin + nhieu de
       bien do that.
    """
    import math
    import random
    import struct
    import wave

    kho = GOC / "tmp" / "studio_dev" / "kho"
    sr = 48_000
    ra = []
    for giay in giay_list:
        p = kho / "voice" / "out" / uid / f"do-{giay}s" / "tieng.wav"
        p.parent.mkdir(parents=True, exist_ok=True)
        rnd = random.Random(1234)
        with wave.open(str(p), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sr)
            con, t = int(sr * giay), 0
            while con > 0:                       # ghi tung giay, khong dung
                khoi = min(sr, con)              # 100 MB RAM cho tep 600 giay
                mau = bytearray()
                for i in range(khoi):
                    v = math.sin(2 * math.pi * 220 * (t + i) / sr) * 0.4
                    v += (rnd.random() - 0.5) * 0.2
                    mau += struct.pack("<h", int(max(-1, min(1, v)) * 32767))
                f.writeframes(bytes(mau))
                con -= khoi
                t += khoi
        ra.append((giay, p.stat().st_size))
    return ra


#: Nội dung một hội thoại mẫu. Cố ý gồm đúng những thứ mà `03_VOICE_CHAT_MEDIA`
#: bắt phải kiểm trên màn hẹp: **câu dài không có chỗ ngắt**, **khối mã**, và
#: **bảng** — ba thứ duy nhất trong một trang chat có thể đẩy `<body>` tràn ngang.
_CHAT_MAU = [
    ("user", "Chao ban"),
    ("assistant", "Chao anh! Toi co the giup gi?"),
    ("user", "Cho toi mot doan lenh curl goi API cua LTT"),
    ("assistant",
     "Duoi day la vi du:\n\n"
     "```bash\n"
     "curl -X POST https://app.lttstudios.com/api/v1/tools/ltt_voice.tao_tieng/run "
     "-H 'Authorization: Bearer sk-ltt-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' "
     "-H 'Content-Type: application/json' "
     "-d '{\"van_ban\":\"xin chao\",\"giong\":\"nu-mien-bac\"}'\n"
     "```\n\n"
     "| Tham so | Kieu | Bat buoc |\n"
     "|---|---|---|\n"
     "| van_ban | string | co |\n"
     "| giong | string | co |\n"
     "| toc_do | number | khong |\n"),
    ("user",
     "URL nay bi sao vay https://app.lttstudios.com/api/v1/tools/"
     "ltt_voice.tao_tieng/run?tham_so_rat_dai_khong_co_cho_ngat_nao_ca=gia_tri_cung_rat_dai"),
    ("assistant",
     "Do la mot duong dan dai. " + ("Mot cau tra loi dai de trang phai cuon. " * 40)),
]


def chat_seed(uid: str) -> str:
    """Dựng một hội thoại có nội dung thật. Trả `conv_id`.

    ⛔ Đừng đo giao diện chat trên một trang RỖNG. `studio_dev.py` đã ghi đúng
       bẫy này cho Voice: *"so mot trang rong voi mot anh mau co du lieu -> moi
       khac biet deu doc len nhu mot loi bo cuc"*. Với chat nó còn nặng hơn —
       một trang chat rỗng **không có** tin nhắn, nên nó không thể tràn ngang,
       và một phép đo "0 px tràn" trên đó là một phép đo về sự trống rỗng.
    """
    os.environ["LTT_DATABASE_URL"] = "sqlite:///" + str(CSDL_DEV).replace("\\", "/")
    os.environ.setdefault("LTT_ENV", "development")
    os.environ.setdefault("LTT_SESSION_SECRET", "studio-dev-khong-bi-mat")

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import registry

    dbmod.reset_engine()
    registry.load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from apps.chatltt.services import hoi_thoai as H

    gen = dbmod.get_session()
    db = next(gen)
    try:
        hoi = H.tao_hoi_thoai(db, user_id=uid, model_alias="")
        H.doi_ten(db, user_id=uid, conv_id=hoi.id, title="Hoi thoai mau cho do mobile")
        cha = None
        for vai, van in _CHAT_MAU:
            m = H.them_thong_diep(db, user_id=uid, conv_id=hoi.id, role=vai,
                                  blocks=[{"type": "text", "text": van}],
                                  parent_id=cha)
            cha = m.id
        db.commit()
        return hoi.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    con = ap.add_subparsers(dest="lenh", required=True)

    k = con.add_parser("kiem-ke", help="liet ke surface khach hang tu registry")
    k.add_argument("--ra", help="ghi JSON ra tep (mac dinh: in bang tom tat)")

    con.add_parser("bang", help="du bang cua moi app vao sqlite cua studio_dev")

    w = con.add_parser("wav-dai", help="sinh WAV nhieu do dai de do chi phi ve song")
    w.add_argument("uid", help="uid cua tai khoan seed (ten thu muc trong kho)")

    c = con.add_parser("chat-seed", help="dung mot hoi thoai chatltt co noi dung that")
    c.add_argument("uid", help="uid cua tai khoan seed")

    a = ap.parse_args(argv)

    if a.lenh == "kiem-ke":
        d = kiem_ke()
        if a.ra:
            pathlib.Path(a.ra).write_text(
                json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"da ghi {len(d)} app -> {a.ra}")
            return 0
        # In ASCII: stdout Windows la cp1252, mot dau tieng Viet lam vo ca lenh.
        print(f"{'slug':<16}{'surface':<10}{'life':<12}{'pub':<6}{'en':<6}route")
        for x in d:
            print(f"{x['slug']:<16}{x['surface']:<10}{x['lifecycle']:<12}"
                  f"{str(x['public']):<6}{str(x['enabled']):<6}{x['route_prefix']}")
        return 0

    if a.lenh == "bang":
        if not CSDL_DEV.exists():
            print(f"chua co {CSDL_DEV} — chay `python tools\\studio_dev.py` truoc")
            return 1
        da_nap, so = du_bang()
        print(f"app co tables.py: {da_nap}")
        print(f"tong bang: {so}")
        return 0

    if a.lenh == "chat-seed":
        print("conv_id:", chat_seed(a.uid))
        return 0

    if a.lenh == "wav-dai":
        for giay, byte in wav_do_dai(a.uid):
            print(f"{giay:>4}s -> {byte // 1024:>7} KB   "
                  f"voice/out/{a.uid}/do-{giay}s/tieng.wav")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
