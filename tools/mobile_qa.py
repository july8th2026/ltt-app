r"""mobile_qa.py — bộ khung đo mobile, lái bằng registry.

    python tools\mobile_qa.py kiem-ke [--ra ho_so.json]   # liet ke surface khach
    python tools\mobile_qa.py bang                        # du bang cho studio_dev
    python tools\mobile_qa.py chat-seed  <uid>            # mot hoi thoai co noi dung
    python tools\mobile_qa.py agent-seed <uid>            # mot canvas CO node
    python tools\mobile_qa.py ommi-seed  <uid>            # tai nguyen + thu vien ommi
    python tools\mobile_qa.py wav-dai    <uid>            # WAV 10..600 giay
    python tools\mobile_qa.py quet --cookie "session=..." # quet mobile moi route

## Mot luot do day du, tu dau

    python tools\studio_dev.py --cong 8123          # may chu + du lieu Voice
    python tools\mobile_qa.py bang                  # bang cua MOI app
    python tools\mobile_qa.py chat-seed  <uid>
    python tools\mobile_qa.py agent-seed <uid>
    python tools\studio_dev.py --cong 8123 --cookie # lay cookie phien
    playwright-cli -s=mobileqa open --browser=chrome
    python tools\mobile_qa.py quet --cookie "<cookie>" --ra ket_qua.json

⛔ **Dung do tren mot trang RONG.** `studio_dev.py` da ghi bay nay cho Voice:
   *"so mot trang rong voi mot anh mau co du lieu -> moi khac biet deu doc len
   nhu mot loi bo cuc"*. Voi chat va canvas con nang hon — mot trang rong khong
   the tran ngang, va mot canvas rong thi khong pan duoc cho BAT KY dau vao nao,
   nen phep do khong phan biet duoc gi. Ba lenh `*-seed` ton tai vi ly do do.

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


def _mo_moi_truong_dev() -> None:
    os.environ["LTT_DATABASE_URL"] = "sqlite:///" + str(CSDL_DEV).replace("\\", "/")
    os.environ.setdefault("LTT_ENV", "development")
    os.environ.setdefault("LTT_SESSION_SECRET", "studio-dev-khong-bi-mat")


def _phien_dev():
    """Trả `(session, dọn)` trên sqlite của `studio_dev`, bảng đã dựng đủ."""
    _mo_moi_truong_dev()
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import registry

    dbmod.reset_engine()
    registry.load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    db = next(gen)

    def don():
        try:
            next(gen)
        except StopIteration:
            pass

    return db, don


def agent_seed(uid: str) -> str:
    """Dựng một workflow Agent Canvas **có node**. Trả `workflow_id`.

    🔴 VÌ SAO LỆNH NÀY TỒN TẠI — một phép đo trên canvas RỖNG không kết luận
       được gì. Ngày 05/09 tôi đo "kéo bằng ngón tay không pan được canvas" và
       suýt ghi nó thành một lỗi. Nhưng trong cùng lượt đo, **chuột giữa cũng
       không pan** — mà cấu hình `panOnDrag={[1,2]}` thì chuột giữa *phải* pan.
       Một phép đo trả lời "không" cho mọi đầu vào thì nó đang đo bộ đo.

    ⭐ Dùng chính `workflows.plan_to_canvas` của máy chủ chứ không tự bịa hình
       dạng `document`: hình dạng ấy là hợp đồng của app, và một bản chép tay sẽ
       lệch ngay khi app đổi.
    """
    from platform_core.agent import workflows

    ke_hoach = {
        "version": 1, "goal": "Do giao dien mobile", "budget_max_credit": 1000,
        "steps": [
            {"id": "source", "tool": "video.generate", "after": [], "fanout": 1,
             "max_retry": 0, "on_fail": "regenerate", "verify": None,
             "params": {"prompt": "Rung ban mai", "model": "seedance-2.0-mini",
                        "resolution": "720p", "duration": 5,
                        "aspect_ratio": "16:9", "generate_audio": True}},
            {"id": "upscale", "tool": "video.upscale", "after": ["source"],
             "fanout": 1, "max_retry": 0, "on_fail": "retry_same", "verify": None,
             "params": {"video_key": "$source.video_key", "preset": "fast",
                        "target_height": 1080, "codec": "h264", "preview": False}},
        ],
    }
    db, don = _phien_dev()
    try:
        row = workflows.create(db, user_id=uid, name="Canvas mau cho do mobile",
                               canvas=workflows.plan_to_canvas(ke_hoach))
        db.commit()
        return row.id
    finally:
        don()



def ommi_seed(uid: str) -> dict:
    """Dựng tài nguyên + thư viện cho `prompt_ai_ommi`. Trả số dòng đã tạo.

    🔴 VÌ SAO LỆNH NÀY TỒN TẠI. `docs/MOBILE/08_BAO_CAO.md` mục 9 ghi
       `prompt_ai_ommi` là *"chưa seed dữ liệu; mọi phép đo tương tác vẫn ở
       mức chưa đo"*. Đó không phải một hạng mục bị quên — đo trên một thư
       viện **rỗng** thì mọi thao tác cho cùng một số 0, và số 0 ấy không phân
       biệt được *"giao diện hỏng"* với *"không có gì để thao tác"*.

    ⭐ Dùng **chính service của app** (`resources.create`, `library.create`)
       chứ không tự dựng hàng trong bảng: hình dạng hàng là hợp đồng của app,
       và một bản chép tay sẽ lệch ngay khi app đổi. Cùng lý do `agent_seed`
       gọi `workflows.plan_to_canvas` thay vì tự bịa `document`.
    """
    from apps.prompt_ai_ommi.services import library, resources

    db, don = _phien_dev()
    dem = {"resource": 0, "variant": 0, "library": 0, "collection": 0}
    try:
        # Ten DAI co y: mot the 12 ky tu khong bao gio tran, nen no khong do
        # duoc gi ve bo cuc hep. Do la bay "trang rong" o mot dang khac.
        mau = [
            ("character", "Nu dao dien toc ngan, ao khoac da, anh sang nguoc",
             "Mot nhan vat dung de do be mat mobile o khung hep nhat"),
            ("background", "Pho co Ha Noi luc mua phun, den vang, mat duong uot",
             "Boi canh ten dai de kiem cat chu tren khung hep"),
            ("prop", "May quay phim co, than kim loai xuoc, day deo da nau",
             "Dao cu de kiem the va nhan xuong dong"),
        ]
        tao = []
        for kind, ten, mo_ta in mau:
            row = resources.create(db, owner_id=uid, kind=kind, name=ten,
                                   description=mo_ta,
                                   prompt_text=f"{ten}. {mo_ta}.")
            tao.append(row)
            dem["resource"] += 1
        db.flush()

        # `add_variant` doi `storage_key` — bien the la MOT ANH, khong phai
        # mot doan chu. Do la hop dong cua app; doc chu ky roi moi goi.
        for i, row in enumerate(tao[:2]):
            resources.add_variant(db, resource_id=row.id, owner_id=uid,
                                  storage_key=f"ommi/{uid}/mau-{i}.png",
                                  label="Ban mau de do bo cuc",
                                  width=1024, height=1024, bytes_size=512_000)
            dem["variant"] += 1

        for kind, ten in (("meta", "Khuon dao dien mac dinh"),
                          ("snippet", "Doan mo dau chuan"),
                          ("style", "Bang mau lanh")):
            library.create(db, kind, owner_id=uid, name=ten,
                           body="Noi dung mau du dai de kiem xuong dong tren "
                                "mot khung nhin 320px va o muc phong to 200%.")
            dem["library"] += 1

        resources.create_collection(db, owner_id=uid, name="Bo suu tap mau")
        dem["collection"] += 1

        db.commit()
        return dem
    finally:
        don()


#: Khung nhìn mặc định của một lượt quét.
#:
#: ⭐ **320 phải có mặt.** Ngày 05/09 nó bắt được hai lỗi mà 390px bỏ lọt, và
#:    một trong hai là do chính bản vá vùng chạm 44px sinh ra. Một bộ đo chỉ
#:    chạy ở khổ "chuẩn" là một bộ đo không bao giờ thấy mép.
KHUNG_MAC_DINH = ("p320", "p390", "p430", "tab768", "land844", "desk1440")


def route_khach(goc: str, cookie: str) -> list[str]:
    """Route khách hàng, lấy từ **registry + trang chủ đang chạy**, không gõ tay.

    ⛔ Một danh sách route chép tay là một danh sách sẽ cũ đi trong im lặng —
       đúng cơ chế đã làm bảng trong `CLAUDE.md` nói sai năm lần. Nguồn ở đây là
       `registry.discover()` cho phần app, cộng chính HTML trang chủ cho phần
       chrome nền tảng (nav là thứ duy nhất biết đủ các trang không thuộc app).
    """
    import re
    import urllib.request

    ra = []
    for x in kiem_ke():
        if x["surface"] != "customer" or not x["enabled"]:
            continue
        ra.append(x["route_prefix"])

    req = urllib.request.Request(goc + "/", headers={"Cookie": cookie} if cookie else {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", "replace")
    except OSError:
        html = ""
    for m in re.finditer(r'href="(/[^"#?]*)"', html):
        d = m.group(1)
        if d.startswith("/static/") or d in ra:
            continue
        ra.append(d)

    # Bỏ route trả 404 (app `capability-only`, app `enabled=False`) — giữ chúng
    # lại chỉ làm mọi bảng kết quả có một cột nhiễu.
    #
    # ⚠️ Dùng **GET**, không dùng `HEAD`. FastAPI chỉ đăng ký `HEAD` cho route
    #    nào khai nó, nên `HEAD /ltt-voice` trả **405** — và một bộ lọc "bỏ mọi
    #    thứ >= 400" sẽ vứt sạch 20 route rồi báo "quét 0 route" một cách rất
    #    tự tin. Đã xảy ra đúng như vậy ở lượt chạy đầu tiên.
    song = []
    for d in ra:
        try:
            rq = urllib.request.Request(
                goc + d, headers={"Cookie": cookie} if cookie else {})
            with urllib.request.urlopen(rq, timeout=15) as r:
                if r.status < 400:
                    song.append(d)
        except Exception as e:  # noqa: BLE001 - 404/timeout deu la "bo qua"
            # ⚠️ Không ném: một route 404 ở đây là **chuyện thường** (app
            #    capability-only, app `enabled=False`). Nhưng cũng không im:
            #    một route biến mất khỏi lượt quét mà không ai biết là cách một
            #    bề mặt khách hàng lặng lẽ rơi ra khỏi mọi phép đo.
            print(f"  [bo qua] {d}: {type(e).__name__}")
            continue
    return sorted(set(song))


def quet(goc: str, cookie: str, khung, routes=None, phien: str = "mobileqa") -> dict:
    """Chạy một lượt quét, trả `{ "<khung> <route>": {…số đo…} }`.

    Gọi `playwright-cli run-code` với `tools/mobile_quet.js` — dòng `CAU_HINH`
    trong tệp ấy được **thay** bằng cấu hình thật rồi ghi ra một tệp tạm.
    """
    import json as _json
    import re
    import subprocess
    import tempfile

    mau = (GOC / "tools" / "mobile_quet.js").read_text(encoding="utf-8")
    cau_hinh = {"goc": goc.rstrip("/"), "cookie": cookie,
                "routes": list(routes or []), "khung": list(khung)}
    moi, so = re.subn(r"const CAU_HINH = \{.*?\};",
                      "const CAU_HINH = " + _json.dumps(cau_hinh) + ";",
                      mau, count=1, flags=re.S)
    if so != 1:
        raise SystemExit("khong tim thay dong `const CAU_HINH = {...};` trong mobile_quet.js")

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(moi)
        tam = f.name
    # ⚠️ Tren Windows, `playwright-cli` cai bang npm la mot bo ba tep
    #    (khong duoi, `.cmd`, `.ps1`) va `subprocess` KHONG tu chon `.cmd` —
    #    no bao `WinError 2: khong tim thay tep`. `shutil.which` thi biet, vi no
    #    doc `PATHEXT`.
    import shutil

    lenh = shutil.which("playwright-cli")
    if not lenh:
        raise SystemExit("khong tim thay `playwright-cli` trong PATH. "
                         "Cai: npm install -g @playwright/cli@latest")
    try:
        r = subprocess.run(
            [lenh, f"-s={phien}", "--raw", "run-code", f"--filename={tam}"],
            capture_output=True, text=True, encoding="utf-8", timeout=1800)
    finally:
        os.unlink(tam)
    out = (r.stdout or "").strip()
    if not out.startswith('"'):
        raise SystemExit("playwright-cli khong tra JSON:\n" + (out or r.stderr)[:600])
    return _json.loads(_json.loads(out))


def tom_tat(kq: dict) -> list[str]:
    """Bảng tóm tắt ASCII — stdout Windows là cp1252, một dấu tiếng Việt làm vỡ."""
    import collections

    gom = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for k, v in kq.items():
        x = gom[k.split(" ")[0]]
        x[0] += 1
        x[1] += 1 if v.get("tran_ngang", 0) > 1 else 0
        x[2] += v.get("input_nho", 0)
        x[3] += v.get("target_be", 0)
        x[4] += v.get("console_loi", 0)
        x[5] += v.get("video_thieu_psi", 0)
    dong = [f"{'khung':<10}{'route':>6}{'tran':>6}{'inp<16':>8}"
            f"{'tgt<44':>8}{'console':>9}{'psi!':>6}"]
    for ten, x in gom.items():
        dong.append(f"{ten:<10}{x[0]:>6}{x[1]:>6}{x[2]:>8}{x[3]:>8}{x[4]:>9}{x[5]:>6}")
    for k, v in sorted(kq.items()):
        # 🔴 Bi day ve `/login` thi MOI so do cua dong nay vo nghia.
        #
        #    Do 06/09: ba route `prompt-ai-ommi` bao "0 tran, 0 loi console"
        #    va ca ba deu la trang dang nhap. Cookie khong co tac dung, va bo
        #    quet khong he biet — no do bat cu thu gi nhan duoc.
        #
        # ⛔ Hong theo huong DE CHIU: trang dang nhap ngan, khong tran ngang,
        #    khong co o nhap nho, khong co video. MOI con so deu dep, nen
        #    khong ai di kiem lai. Do la ly do dong nay phai KEU TO.
        if v.get("CHUA_DANG_NHAP"):
            dong.append(f"  [!] CHUA DANG NHAP  {k}: bi day ve "
                        f"{v.get(chr(39) + chr(39)) if False else v.get('url_thuc')}"
                        f" - MOI so do cua dong nay VO NGHIA")
            continue
        if v.get("tran_ngang", 0) > 1:
            dong.append(f"  TRAN     {k}: {v['tran_ngang']}px")
        if v.get("console_loi"):
            dong.append(f"  CONSOLE  {k}: {v.get('console_mau')}")
        if v.get("status") != 200:
            dong.append(f"  STATUS   {k}: {v.get('status')}")
        if v.get("video_thieu_psi"):
            dong.append(f"  PSI      {k}: {v['video_thieu_psi']} the")
        if v.get("bang_tran"):
            dong.append(f"  BANG     {k}: {v['bang_tran']} bang tran ma khong cuon duoc")
        if v.get("cot_an"):
            dong.append(f"  COT AN   {k}: {v['cot_an']}")
    return dong


def _ep_utf8() -> None:
    """`--help` cua tep nay VO tren console cp1252 — do 06/09, ma thoat 1.

    Docstring va nhan tham so deu co tieng Viet, nen `argparse` in ra la vo:

        UnicodeEncodeError: 'charmap' codec can't encode character 'ộ'

    ⇒ Khong ai kham pha duoc lenh nao cua cong cu nay tu chinh no.

    ⛔ Dung `reconfigure` tren luong DANG CO, khong tao mot `TextIOWrapper` MOI
       boc quanh `sys.stdout.buffer`: ban goc bi thu gom rac se dong buffer that
       va lam vo pytest — kho nay da tra gia mot lan cho dung loi do.
    """
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def main(argv=None) -> int:
    _ep_utf8()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    con = ap.add_subparsers(dest="lenh", required=True)

    k = con.add_parser("kiem-ke", help="liet ke surface khach hang tu registry")
    k.add_argument("--ra", help="ghi JSON ra tep (mac dinh: in bang tom tat)")

    con.add_parser("bang", help="du bang cua moi app vao sqlite cua studio_dev")

    w = con.add_parser("wav-dai", help="sinh WAV nhieu do dai de do chi phi ve song")
    w.add_argument("uid", help="uid cua tai khoan seed (ten thu muc trong kho)")

    c = con.add_parser("chat-seed", help="dung mot hoi thoai chatltt co noi dung that")
    c.add_argument("uid", help="uid cua tai khoan seed")

    g = con.add_parser("agent-seed", help="dung mot workflow Agent Canvas CO node")
    g.add_argument("uid", help="uid cua tai khoan seed")

    o = con.add_parser("ommi-seed", help="dung tai nguyen + thu vien cho prompt_ai_ommi")
    o.add_argument("uid", help="uid cua tai khoan seed")

    q = con.add_parser("quet", help="quet mobile moi route khach hang")
    q.add_argument("--goc", default="http://127.0.0.1:8123",
                   help="goc may chu do (mac dinh cong 8123 cua studio_dev)")
    q.add_argument("--cookie", default="", help="cookie phien, vd `session=...`")
    q.add_argument("--khung", default=",".join(KHUNG_MAC_DINH),
                   help="danh sach khung nhin, ngan bang dau phay")
    q.add_argument("--route", default="", help="chi quet nhung route nay (phay)")
    q.add_argument("--ra", help="ghi JSON day du ra tep")
    q.add_argument("--phien", default="mobileqa",
                   help="ten phien playwright-cli (mo truoc bang `open --browser=...`)")

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

    if a.lenh == "quet":
        goc = a.goc.rstrip("/")
        rt = [x for x in a.route.split(",") if x] or route_khach(goc, a.cookie)
        print(f"quet {len(rt)} route x {len(a.khung.split(','))} khung nhin ...")
        kq = quet(goc, a.cookie, a.khung.split(","), rt, a.phien)
        if a.ra:
            pathlib.Path(a.ra).write_text(
                json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
            print("da ghi", a.ra)
        for d in tom_tat(kq):
            print(d)
        return 0

    if a.lenh == "agent-seed":
        print("workflow_id:", agent_seed(a.uid))
        return 0

    if a.lenh == "ommi-seed":
        for k, v in ommi_seed(a.uid).items():
            print(f"  {k:<12} {v}")
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
