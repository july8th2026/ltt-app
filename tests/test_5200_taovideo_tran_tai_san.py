"""5200 — trần tài sản tham chiếu của `taovideo` là trần cứng của engine.

Nguồn chân lý duy nhất: `apps/taovideo/refs.py` (`TRAN_ANH`/`TRAN_VIDEO`/
`TRAN_AUDIO`/`TRAN_TONG`), sao từ bản gốc
`D:/BOT GEMINI/app/modules/seedance_video/manifest.py` dòng 30
(`"max_ref_images": 9, "max_ref_videos": 3, "max_ref_audio": 3,
"max_ref_total": 12,  # Seedance 2.0 hard limits`).

⭐ Phép quan trọng nhất trong tệp này là **bánh cóc chống chồng chéo**
(`test_khong_con_so_tran_truoc_trui_*`): sáu chỗ từng khai cùng một trần bằng
số 4, và chỗ nào lệch thì khách bị chặn ở một cửa với con số khác con số cửa
kia cho. Bánh cóc đo **tính chất** — "cửa này có đi qua nguồn chân lý không" —
chứ không đo cách gõ, và mỗi phép dò đều có **đối chứng** bằng một đoạn mã giả
cố tình gõ lại số trần trụi (nếu bộ dò không bắt được đoạn giả đó thì nó cũng
không bắt được lỗi thật, và số 0 nó báo là vô nghĩa).
"""

from __future__ import annotations

import ast
import asyncio
import io
from pathlib import Path

import pytest
from starlette.datastructures import Headers, UploadFile

from apps.taovideo import refs

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT / "apps/taovideo/routes.py"
JOBS = ROOT / "apps/taovideo/jobs.py"
TRANG = ROOT / "apps/taovideo/templates/taovideo.html"

#: Năm cửa cưỡng chế trần trong mã Python. `TRAN_REF_PREFILL` là gán ở mức
#: module nên soi riêng ở phép kiểm của nó.
CUA_PYTHON = {
    "routes.py": ("_luu_refs", "_saved_refs_for_user", "queue"),
    "jobs.py": ("_reference_specs",),
}


# --------------------------------------------------------------------------
# Bốn hằng số phải khớp bản gốc
# --------------------------------------------------------------------------
def test_bon_hang_so_khop_ban_goc_seedance_2_0():
    assert (refs.TRAN_ANH, refs.TRAN_VIDEO, refs.TRAN_AUDIO, refs.TRAN_TONG) \
        == (9, 3, 3, 12)
    # Trần tổng KHÔNG phải tổng ba trần loại (9+3+3 = 15 ≠ 12): bản gốc khai
    # riêng, nên `kiem_tran` phải kiểm CẢ HAI vế, không suy vế nọ từ vế kia.
    assert refs.TRAN_ANH + refs.TRAN_VIDEO + refs.TRAN_AUDIO > refs.TRAN_TONG


def test_tran_ref_prefill_la_tran_anh_khong_phai_tran_tong():
    from apps.taovideo import routes
    # Đường giao bài chỉ giải mã ảnh (`kind == "image"`, `url` dạng `data:`).
    assert routes.TRAN_REF_PREFILL == refs.TRAN_ANH
    assert routes.TRAN_REF_PREFILL != refs.TRAN_TONG


# --------------------------------------------------------------------------
# ⭐ BÁNH CÓC CHỐNG CHỒNG CHÉO
# --------------------------------------------------------------------------
def _ham(cay: ast.AST, ten: str) -> ast.AST:
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and nut.name == ten:
            return nut
    raise AssertionError(f"khong tim thay ham {ten!r}")


def _co_nguon_chan_ly(nut: ast.AST) -> bool:
    """Thân hàm có đi qua `refs.kiem_tran(...)` hay đọc `refs.TRAN_*` không."""
    for con in ast.walk(nut):
        if isinstance(con, ast.Attribute) and isinstance(con.value, ast.Name) \
                and con.value.id == "refs" \
                and (con.attr == "kiem_tran" or con.attr.startswith("TRAN_")):
            return True
    return False


def _tran_trui(nut: ast.AST) -> list[str]:
    """Các phép so sánh dạng ``len(...) > <số>`` — một trần gõ trần trụi.

    Chỉ bắt chiều TRÊN (`>`, `>=`): đó là chiều của một cái trần. `len(parts)
    < 3` trong `_reference_specs` là phép kiểm HÌNH DẠNG storage key (tối
    thiểu ba đoạn), không phải trần, nên nó không bị bắt — và đó là lý do
    không cần danh sách miễn trừ nào ở đây.
    """
    xau = []
    for con in ast.walk(nut):
        if not isinstance(con, ast.Compare):
            continue
        if not any(isinstance(o, (ast.Gt, ast.GtE)) for o in con.ops):
            continue
        co_len = any(isinstance(g, ast.Call) and isinstance(g.func, ast.Name)
                     and g.func.id == "len" for g in ast.walk(con.left))
        so = [c for c in con.comparators
              if isinstance(c, ast.Constant) and isinstance(c.value, int)
              and not isinstance(c.value, bool)]
        if co_len and so:
            xau.append(f"dong {con.lineno}: len(...) > {so[0].value}")
    return xau


@pytest.mark.parametrize("tep", ["routes.py", "jobs.py"])
def test_khong_con_so_tran_truoc_trui_trong_python(tep):
    duong = ROUTES if tep == "routes.py" else JOBS
    cay = ast.parse(duong.read_text(encoding="utf-8"))
    for ten in CUA_PYTHON[tep]:
        nut = _ham(cay, ten)
        assert _co_nguon_chan_ly(nut), (
            f"{tep}:{ten} khong doc tran tu `refs` — neu no tu go lai so thi "
            f"hai cua se lech nhau ma khong ai bat")
        assert _tran_trui(nut) == [], f"{tep}:{ten} con tran go tran trui"


def test_bo_do_python_bat_duoc_so_tran_truoc_trui__doi_chung():
    """Đối chứng: chính hình dạng mã CŨ phải làm bộ dò ĐỎ.

    Không có phép này thì số 0 ở trên có thể chỉ vì bộ dò không dò được gì.
    """
    cu = ast.parse(
        "def _luu_refs(files):\n"
        "    actual = [f for f in files if f]\n"
        "    if len(actual) > 4:\n"
        "        raise ValueError('Tối đa 4 file tham chiếu.')\n")
    nut = _ham(cu, "_luu_refs")
    assert not _co_nguon_chan_ly(nut)          # khong di qua nguon chan ly
    assert _tran_trui(nut) == ["dong 3: len(...) > 4"]

    # ... va hinh dang HOP LE thi khong bi bat oan:
    lanh = ast.parse(
        "def _luu_refs(files):\n"
        "    actual = [f for f in files if f]\n"
        "    refs.kiem_tran(_loai_ref(f) for f in actual)\n"
        "    parts = ''.split('/')\n"
        "    assert len(parts) < 3\n")
    nut = _ham(lanh, "_luu_refs")
    assert _co_nguon_chan_ly(nut)
    assert _tran_trui(nut) == []


def _tran_trui_trang(noi_dung: str) -> list[str]:
    """Trần gõ trần trụi trong template: so sánh với một CHỮ SỐ trong JS."""
    import re
    xau = []
    for m in re.finditer(r"(total|tong|dem\[[^\]]*\]|files)\s*[><]=?\s*(\d+)",
                         noi_dung):
        xau.append(m.group(0))
    # Câu tiếng Việt nêu trần bằng chữ số cũng là một bản khai thứ hai.
    for m in re.finditer(r"[Tt]ối đa (\d+)", noi_dung):
        xau.append(m.group(0))
    return xau


def test_khong_con_so_tran_truoc_trui_trong_template():
    trang = TRANG.read_text(encoding="utf-8")
    assert _tran_trui_trang(trang) == []
    # ... va tran PHAI den tu server, khong phai tu JS:
    for thuoc in ("data-tran-anh", "data-tran-video", "data-tran-audio",
                  "data-tran-tong", "data-tran-byte"):
        assert thuoc in trang, thuoc
    for doc in ("d.tranAnh", "d.tranVideo", "d.tranAudio", "d.tranTong",
                "d.tranByte"):
        assert doc in trang, doc
    for ap in ("dem.image>TRAN.image", "dem.video>TRAN.video",
               "dem.audio>TRAN.audio", "total>TRAN.tong", "byte>TRAN.byte"):
        assert ap in trang, ap


def test_bo_do_template_bat_duoc_so_tran_truoc_trui__doi_chung():
    # Dung hai hinh dang CU cua dong 93 va dong 53:
    assert _tran_trui_trang("msg=total>4?'x':''") == ["total>4"]
    assert _tran_trui_trang("x.disabled=total>=4") == ["total>=4"]
    assert _tran_trui_trang('_("Tối đa 4 tài sản")') == ["Tối đa 4"]
    # ... va hinh dang moi khong bi bat oan:
    assert _tran_trui_trang("msg=total>TRAN.tong?'x':''") == []
    assert _tran_trui_trang('_("Tối đa {a} ảnh").format(a=tran_anh)') == []


def test_tran_byte_den_tu_hang_so_nen_tang_khong_go_lai():
    from apps.taovideo import routes
    from platform_core.storage import CLOUDFLARE_BODY_LIMIT
    # Cloudflare cắt body TRƯỚC khi mã của ta chạy ⇒ phép cộng byte ở server
    # không ngăn được 413; chỗ duy nhất có tác dụng là JS, và con số phải đi
    # từ hằng số nền tảng chứ không gõ lại.
    assert 0 < routes.TRAN_BYTE_MOT_LAN < CLOUDFLARE_BODY_LIMIT
    assert routes.TRAN_BYTE_MOT_LAN == int(CLOUDFLARE_BODY_LIMIT * 0.9)
    # Trần byte KHÔNG được dùng để hạ trần đếm: ca xấu nhất theo `_CAP` vượt
    # xa trần body, và đó là ca không điển hình — nó xử lý ở client.
    xau_nhat = (refs.TRAN_ANH * routes._CAP["image"]
                + refs.TRAN_VIDEO * routes._CAP["video"]
                + refs.TRAN_AUDIO * routes._CAP["audio"])
    assert xau_nhat > CLOUDFLARE_BODY_LIMIT


# --------------------------------------------------------------------------
# Trần theo TỪNG LOẠI, trần TỔNG, và đối chứng dưới trần
# --------------------------------------------------------------------------
def _n(loai: str, n: int) -> list[str]:
    return [loai] * n


def test_tran_theo_tung_loai_dung_bang_ban_goc():
    # Đúng trần thì QUA (biên dưới của phép từ chối).
    assert refs.kiem_tran(_n("image", 9))["image"] == 9
    assert refs.kiem_tran(_n("video", 3))["video"] == 3
    assert refs.kiem_tran(_n("audio", 3))["audio"] == 3
    # Vượt một đơn vị thì TỪ CHỐI, và vì ĐÚNG loại đó.
    with pytest.raises(ValueError, match="9 ảnh"):
        refs.kiem_tran(_n("image", 10))
    with pytest.raises(ValueError, match="3 video"):
        refs.kiem_tran(_n("video", 4))
    with pytest.raises(ValueError, match="3 audio"):
        refs.kiem_tran(_n("audio", 4))


def test_tran_tong_ap_rieng_voi_tran_loai():
    # 9 ảnh + 3 video = 12 = đúng trần tổng ⇒ QUA.
    dem = refs.kiem_tran(_n("image", 9) + _n("video", 3))
    assert sum(dem.values()) == refs.TRAN_TONG
    # Thêm một tài sản nữa (13) ⇒ từ chối vì TỔNG, không vì loại nào:
    # 9 ảnh vẫn đúng trần ảnh, 3 video đúng trần video, 1 audio đúng trần audio.
    with pytest.raises(ValueError, match="12 tài sản"):
        refs.kiem_tran(_n("image", 9) + _n("video", 3) + _n("audio", 1))


def test_duoi_tran_thi_khong_he_bi_tu_choi__doi_chung():
    """Không có phép này thì ba phép trên có thể xanh chỉ vì hàm luôn ném."""
    assert refs.kiem_tran([]) == {"image": 0, "video": 0, "audio": 0}
    assert refs.kiem_tran(_n("image", 4)) == {"image": 4, "video": 0, "audio": 0}
    assert refs.kiem_tran(_n("image", 8) + _n("video", 2) + _n("audio", 1)) \
        == {"image": 8, "video": 2, "audio": 1}
    # Biên chính xác: 12 qua, 13 không.
    refs.kiem_tran(_n("image", 9) + _n("video", 3))


def test_kind_la_thi_dem_ve_anh_khong_am_tham_bi_bo():
    # Ref cũ trong `job.params` có thể thiếu/lệch `kind`; đếm về ảnh (cùng quy
    # ước với `routes`/`jobs`) chứ KHÔNG bỏ khỏi phép đếm — bỏ im lặng thì một
    # tài sản trả tiền lọt qua trần.
    assert refs.kiem_tran([None, "", "khong-biet"]) \
        == {"image": 3, "video": 0, "audio": 0}


# --------------------------------------------------------------------------
# Đường thật: `/queue` (`_luu_refs`) và WORKER (`_reference_specs`)
# --------------------------------------------------------------------------
class _Storage:
    def __init__(self):
        self.files = {}

    def put(self, key, stream, content_type="application/octet-stream"):
        self.files[key] = (stream.read(), content_type)

    def exists(self, key):
        return key in self.files

    def size(self, key):
        return len(self.files[key][0])

    def open(self, key):
        return io.BytesIO(self.files[key][0])

    def delete(self, key):
        self.files.pop(key, None)


def _png(ten: str) -> UploadFile:
    return UploadFile(io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 32),
                      filename=ten, headers=Headers({"content-type": "image/png"}))


def _mp4(ten: str) -> UploadFile:
    return UploadFile(io.BytesIO(b"\x00\x00\x00\x18ftypisommedia"),
                      filename=ten, headers=Headers({"content-type": "video/mp4"}))


@pytest.fixture()
def _db_va_kho(tmp_path, monkeypatch):
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401  — nap Base.metadata truoc create_all
    import platform_core.storage as storage_module
    from tests.conftest import bao_dam_user
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tran-5200.db').as_posix()}")
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    bao_dam_user(db, "u1"); db.commit(); db.close()
    kho = _Storage()
    monkeypatch.setattr(storage_module, "get_storage", lambda: kho)
    try:
        yield kho
    finally:
        dbmod.reset_engine()


def test_luu_refs_nhan_dung_tran_anh_va_tu_choi_vuot(_db_va_kho):
    from apps.taovideo.routes import _luu_refs
    # 9 ảnh — trần MỚI: trước 27/09 ca này bị từ chối ở số 4.
    ra = asyncio.run(_luu_refs("u1", [_png(f"{i}.png") for i in range(9)], []))
    assert len(ra) == 9
    with pytest.raises(ValueError, match="9 ảnh"):
        asyncio.run(_luu_refs("u1", [_png(f"x{i}.png") for i in range(10)], []))


def test_luu_refs_tu_choi_theo_TUNG_loai_va_theo_tong(_db_va_kho):
    from apps.taovideo.routes import _luu_refs
    # 4 video: dưới trần TỔNG (12) nhưng vượt trần LOẠI (3) ⇒ phải đỏ vì video.
    with pytest.raises(ValueError, match="3 video"):
        asyncio.run(_luu_refs("u1", [_mp4(f"v{i}.mp4") for i in range(4)], []))
    # 9 ảnh + 3 video = 12 ⇒ qua; thêm một ảnh nữa thì vượt TRẦN ẢNH trước.
    ra = asyncio.run(_luu_refs(
        "u1", [_png(f"a{i}.png") for i in range(9)]
        + [_mp4(f"b{i}.mp4") for i in range(3)], []))
    assert len(ra) == 12


def test_app_released_van_chay_y_cu_voi_dau_vao_duoi_tran_cu(_db_va_kho):
    """9b — mọi thay đổi là NỚI RỘNG: đầu vào cũ phải cho kết quả cũ."""
    from apps.taovideo.routes import _luu_refs
    ra = asyncio.run(_luu_refs(
        "u1", [_png("anh.png"), _mp4("clip.mp4")], ["first_frame"], ["hero"]))
    assert [r["kind"] for r in ra] == ["image", "video"]
    assert ra[0]["role"] == "first_frame" and ra[0]["handle"] == "hero"
    assert ra[1]["role"] == "reference_video"
    # Định dạng lạ vẫn bị từ chối y như cũ (trần nới, cửa MIME không nới).
    la = UploadFile(io.BytesIO(b"x"), filename="x.exe",
                    headers=Headers({"content-type": "application/octet-stream"}))
    with pytest.raises(ValueError, match="không hỗ trợ"):
        asyncio.run(_luu_refs("u1", [la], []))


def test_tran_o_worker_khong_thap_hon_tran_o_cua(tmp_path):
    """⭐ `_reference_specs` chạy SAU khi credit đã giữ.

    Nếu worker còn kẹt ở 4 thì khách nộp 9 ảnh sẽ BỊ TRỪ TIỀN rồi job chết —
    xấu hơn hẳn việc từ chối ngay ở cửa. Nên trần ở đây phải bằng trần ở cửa.
    """
    from apps.taovideo.jobs import _reference_specs
    from platform_core.storage import LocalStorage, set_storage
    kho = LocalStorage(str(tmp_path / "files")); set_storage(kho)
    try:
        keys = []
        for i in range(13):
            key = f"taovideo/u1/refs/{i}.png"
            kho.put(key, io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")
            keys.append(key)
        anh = [{"storage_key": k, "kind": "image"} for k in keys]
        # 9 ảnh: QUA ở worker (trước 27/09 chỗ này kẹt ở 4).
        assert len(_reference_specs({"refs": anh[:9]}, "u1", kho)) == 9
        # 10 ảnh: từ chối vì TRẦN ẢNH, cùng thông điệp với cửa.
        with pytest.raises(ValueError, match="9 ảnh"):
            _reference_specs({"refs": anh[:10]}, "u1", kho)
        # Tổng 13 (9 ảnh + 3 video + 1 audio) ⇒ từ chối vì TỔNG.
        tron = ([{"storage_key": k, "kind": "image"} for k in keys[:9]]
                + [{"storage_key": k, "kind": "video"} for k in keys[9:12]]
                + [{"storage_key": keys[12], "kind": "audio"}])
        with pytest.raises(ValueError, match="12 tài sản"):
            _reference_specs({"refs": tron}, "u1", kho)
    finally:
        set_storage(None)
