"""`F1` + `F2` — vòng hỏi tiến độ thay cho một lời gọi chặn-chờ.

🔴 **Lỗi thật, và nó giết mọi job.** `/result/{job}` phía cầu nối **chặn-chờ**
   tới khi sinh xong (~20 phút), còn `MayThat.ket_qua()` gọi nó với
   `timeout=30.0` — tham số của `urllib.request.urlopen`, tức timeout **socket**
   áp cho từng lần đọc. Nên `handle()` ném `socket.timeout` sau 30 giây với
   **mọi** job thật.

⭐ **Vì sao bộ test cũ xanh.** `ClientGia.result()` trả về ngay lập tức. Một
   client giả nhanh không thể hiện được một máy chủ chậm, nên đường thật chưa
   từng bị thử. Cùng loại mù đã che lỗi `tools.video_cloud`: cái giả không có
   tính chất mà cái thật hỏng vì nó.

   ⇒ `ClientChamGia` dưới đây **từ chối** trả kết quả cho tới khi tiến độ nói
     xong. Đó là tính chất bị thiếu, và nó biến bản cũ thành đỏ.

🔴 `F2` đi kèm: `handle()` nhận `ctx` mà **không gọi `ctx.progress()` lần nào**,
   nên người dùng nhìn 0% suốt hơn hai mươi phút — trong khi cầu nối đã trả sẵn
   `phase` · `current_step` · `total_steps`.
"""
from __future__ import annotations


import pytest

from apps.lttvideo import jobs
from apps.lttvideo.cong.may_gia_lap import MayGiaLap
from apps.lttvideo.cong.giao_uoc import LoiMay


class ClientChamGia(MayGiaLap):
    """⭐ KE THUA `MayGiaLap` chu khong dung tu dau.

    Giao uoc `May` co MUOI MOT cua. Mot ban gia viet tu dau chi thuc hien nhung
    cua ma phep kiem nghi toi, nen moi lan giao uoc moc them mot cua la mot lan
    phai sua tay MOI ban gia — va cai bi quen thi no `AttributeError` o tan luc
    chay job that.

    Ke thua thi `mac_dinh` / `kha_dung` / `nap_media` den tu ban ghi THAT, va
    phep kiem chi de len dung thu no dang do.

    Máy chủ **chậm**: `ket_qua()` nổ nếu hỏi trước khi tiến độ báo xong. Đó
    chính là hành vi của `/result` thật cộng timeout socket 30 giây.
    """

    def __init__(self, *, so_buoc: int = 4, tep=("/data/out/a.mp4",)):
        super().__init__()
        self.so_buoc = so_buoc
        self.tep = list(tep)
        self.lan_hoi = 0
        self.da_submit: dict | None = None
        self.da_cleanup = False

    # 🔴 Doi ten theo giao uoc `cong.May` (HM-2) — menh de khong doi mot chu.
    def gui_viec(self, settings):
        self.da_submit = settings
        return "J-CHAM"

    def tien_do(self, job_id):
        self.lan_hoi += 1
        if self.lan_hoi == 1:
            return {"phase": "encoding_text", "current_step": None,
                    "total_steps": None, "giay_da_chay": 3.0}
        if self.lan_hoi <= self.so_buoc:
            return {"phase": "denoising", "current_step": self.lan_hoi,
                    "total_steps": self.so_buoc, "giay_da_chay": 9.0}
        return {"phase": "done", "xong": True, "giay_da_chay": 30.0}

    def ket_qua(self, job_id):
        if self.lan_hoi <= self.so_buoc:
            # Đúng thứ xảy ra thật: doc socket qua han truoc khi may chu tra loi.
            raise LoiMay("GET /result/J-CHAM: TimeoutError: timed out")
        return {"tep": list(self.tep), "loi": [], "huy": False}

    def don_dep(self, job_id):
        self.da_cleanup = True

    def huy(self, job_id):
        return None

    def tai_ve(self, job_id, chi_so=0):
        return b"MP4DATA"


class KhoGia:
    def __init__(self):
        self.da_luu: dict[str, bytes] = {}

    def put(self, key, stream, content_type=""):
        self.da_luu[key] = stream.read()
        return type("SF", (), {"key": key, "size": len(self.da_luu[key])})()

    def exists(self, key):
        return key in self.da_luu


class CtxGia:
    """Ghi lại mọi lần báo tiến độ, đúng khuôn `job_runner.progress()`."""

    def __init__(self):
        self.moc: list[tuple[int, str]] = []

    def progress(self, percent: int, message: str = "") -> None:
        self.moc.append((int(percent), str(message)))


@pytest.fixture(autouse=True)
def _khong_ngu(monkeypatch):
    """Bỏ `sleep` — phép kiểm đo **hành vi**, không đo đồng hồ."""
    monkeypatch.setattr(jobs.time, "sleep", lambda _s: None)


def _chay(client, ctx=None, kho=None):
    return jobs.handle(
        {"prompt": "một dòng sông", "duration_s": 5, "nguoi_dung_id": 42},
        ctx=ctx, _client=client, _kho=kho or KhoGia(), _dieu_phoi=None)


# ── F1: khong duoc goi `result()` khi viec chua xong ───────────────────────

def test_job_cham_van_chay_xong():
    """⭐ Phép kiểm trung tâm. Bản cũ gọi `result()` ngay sau `submit()` nên nó
    ăn đúng ngoại lệ timeout mà máy chủ thật ném ra."""
    c = ClientChamGia()
    ra = _chay(c)
    assert ra["trang_thai"] == "xong"
    assert len(ra["video_keys"]) == 1


def test_co_hoi_tien_do_NHIEU_LAN_chu_khong_mot_lan():
    c = ClientChamGia(so_buoc=5)
    _chay(c)
    assert c.lan_hoi > 5, f"chi hoi {c.lan_hoi} lan — khong phai mot vong lap"


def test_NHIP_HOI_S_that_su_duoc_dung():
    """Hằng số này từng được khai mà **không dùng ở đâu cả** — nó ghi lại một ý
    định chưa bao giờ nối dây. Phép kiểm giữ cho nó ở trạng thái đang làm việc."""
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(jobs.handle))
    ten = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    assert "NHIP_HOI_S" in ten


# ── F2: nguoi dung phai thay tien do ───────────────────────────────────────

def test_co_bao_tien_do_qua_ctx():
    ctx = CtxGia()
    _chay(ClientChamGia(so_buoc=4), ctx=ctx)
    assert ctx.moc, "khong bao tien do lan nao — nguoi dung nhin 0% suot 20 phut"


def test_tien_do_TANG_DAN_va_ket_thuc_o_100():
    ctx = CtxGia()
    _chay(ClientChamGia(so_buoc=6), ctx=ctx)
    phan_tram = [p for p, _ in ctx.moc]
    assert phan_tram == sorted(phan_tram), f"tien do di lui: {phan_tram}"
    assert phan_tram[-1] == 100
    assert 0 <= min(phan_tram) and max(phan_tram) <= 100


def test_pha_nao_cung_co_loi_nhan_doc_duoc():
    """Một phần trăm trần trụi không nói người dùng máy đang làm gì."""
    ctx = CtxGia()
    _chay(ClientChamGia(), ctx=ctx)
    assert all(msg.strip() for _, msg in ctx.moc)


def test_ctx_None_thi_khong_vo():
    """Worker có thể gọi không kèm `ctx`; đường đó không được ném."""
    ra = _chay(ClientChamGia(), ctx=None)
    assert ra["trang_thai"] == "xong"


def test_loi_khi_bao_tien_do_KHONG_giet_job():
    """⭐ Báo tiến độ là **trang trí**, sinh video là **việc**. Một lần ghi
    tiến độ hỏng (CSDL bận, worker mất phiên) không được làm mất cả video đã
    tính tiền."""
    class CtxHong:
        def progress(self, percent, message=""):
            raise RuntimeError("CSDL ban")

    ra = _chay(ClientChamGia(), ctx=CtxHong())
    assert ra["trang_thai"] == "xong"


# ── Bien: hoi tien do hong thi van phai cho tiep ──────────────────────────

def test_progress_hong_giua_chung_thi_van_cho_tiep():
    """Một nhịp hỏi tiến độ hỏng là chuyện mạng bình thường. Nếu nó làm job
    thất bại thì ta đổi một lỗi hiển thị thành một lỗi mất tiền."""
    c = ClientChamGia(so_buoc=4)
    that = c.tien_do

    def thi_thoang_hong(job_id):
        d = that(job_id)
        if c.lan_hoi == 2:
            raise LoiMay("GET /progress: ConnectionResetError")
        return d

    c.tien_do = thi_thoang_hong
    ra = _chay(c)
    assert ra["trang_thai"] == "xong"


def test_khong_cho_vo_han():
    """Phải có trần thời gian: một job treo trên C-CLOUD không được giữ một
    worker của LTT mãi mãi."""
    import ast
    import inspect

    ma = inspect.getsource(jobs)
    assert "CHO_TOI_DA_S" in ma
    cay = ast.parse(ma)
    hang = {n.targets[0].id: n.value.value for n in ast.walk(cay)
            if isinstance(n, ast.Assign) and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name)
            and isinstance(n.value, ast.Constant)}
    assert hang.get("CHO_TOI_DA_S", 0) >= 1800, "tran cho qua ngan cho video 15s"
