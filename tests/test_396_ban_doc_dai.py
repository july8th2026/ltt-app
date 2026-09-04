r"""
Bản đọc dài: ĐỌC TIẾP được, và một đoạn hỏng không kéo cả tài liệu theo.

Đây là hai yêu cầu P0 của đường tài liệu dài, và cả hai đều là mệnh đề về
**việc gì KHÔNG xảy ra** — nên chúng không tự lộ ra trong bất kỳ lượt chạy
thành công nào. Một bộ ghép chạy đúng và một bộ ghép sinh lại cả cuốn sách sau
mỗi lần hỏng cho ra **cùng một tệp WAV**; thứ phân biệt chúng chỉ là số lượt
gọi GPU, và không ai đếm nó trừ khi có phép kiểm đếm hộ.

⛔ Nên tệp này đếm. Nó không kiểm âm thanh (đã có `test_342`) — nó kiểm
   **sidecar được hỏi những đoạn nào**.
"""
from __future__ import annotations

import os
import shutil
import wave

import pytest


# ── giả lập kho và cổng giọng ────────────────────────────────────────────────

class KhoGia:
    """Đủ mặt `Storage` mà `ban_doc_dai` dùng: `local_path` và `put`."""

    def __init__(self, goc: str):
        self.goc = goc
        self.da_put: list = []

    def _p(self, khoa: str) -> str:
        return os.path.join(self.goc, *khoa.split("/"))

    def local_path(self, khoa: str):
        p = self._p(khoa)
        return p if os.path.exists(p) else None

    def put(self, khoa: str, stream, content_type: str = ""):
        p = self._p(khoa)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            shutil.copyfileobj(stream, f)
        self.da_put.append(khoa)
        return None


def _wav_nho(duong: str, giay: float = 0.5) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    with wave.open(duong, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b"\x00\x01" * int(16000 * giay))


class CongGia:
    """Cổng giọng giả. GHI LẠI từng lượt được hỏi những văn bản nào."""

    class SidecarBan(Exception):
        pass

    def __init__(self, hong_o: set | None = None):
        self.lo_da_goi: list = []       # mỗi phần tử: danh sách text của một lượt
        self.hong_o = hong_o or set()   # text nào làm lượt gọi ném lỗi
        self.ghep_voi = None

    def lo_ra_tep(self, texts, duong_ra, *, ref_b64=None, preset=None):
        self.lo_da_goi.append(list(texts))
        xau = [t for t in texts if t in self.hong_o]
        if xau:
            raise RuntimeError(f"engine hong o: {xau[0]!r}")
        for d in duong_ra:
            _wav_nho(d)
        return {"items": [{"duong": d} for d in duong_ra], "gen_s": 1.0}

    def ghep_tep(self, duong_vao, duong_ra, *, so_cau=None):
        self.ghep_voi = (list(duong_vao), list(so_cau or []))
        _wav_nho(duong_ra, giay=0.5 * len(duong_vao))
        return {"so_doan": len(duong_vao), "giay": 0.5 * len(duong_vao),
                "moc_s": [0.0] * (len(duong_vao) + 1), "nghi_s": 0.3}


class CtxGia:
    def __init__(self, job_id="job-abc"):
        self.job_id = job_id
        self.moc: list = []

    def progress(self, phan_tram, loi_nhan=""):
        self.moc.append((phan_tram, loi_nhan))


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    """Nối `ban_doc_dai` vào kho giả và cổng giả."""
    from apps.ltt_voice import ban_doc_dai

    kho = KhoGia(str(tmp_path / "kho"))
    cong = CongGia()
    monkeypatch.setattr(ban_doc_dai, "sidecar_client", cong)

    import platform_core.storage as st
    monkeypatch.setattr(st, "get_storage", lambda: kho)

    thu_muc = tmp_path / "tam"
    thu_muc.mkdir()
    return ban_doc_dai, kho, cong, str(thu_muc)


def _doan(n: int) -> list:
    return [f"Day la doan so {i}. No co hai cau." for i in range(n)]


# ── 1. đọc tiếp ──────────────────────────────────────────────────────────────

def test_doan_da_co_trong_kho_thi_KHONG_sinh_lai(moi_truong):
    """🔴 YÊU CẦU P0: máy chủ khởi động lại giữa chừng ⇒ đọc tiếp, không làm lại.

    Đặt sẵn 3/5 đoạn vào kho — đúng thứ còn lại sau một lượt chạy bị cắt ngang —
    rồi chạy. Cổng giọng chỉ được phép nhìn thấy hai đoạn cuối.

    ⚠️ Chốt bằng **văn bản đã hỏi**, không bằng số lượt gọi: một bản sửa sai
       chia lô khác đi vẫn phải qua được phép kiểm này, còn một bản sinh lại cả
       năm đoạn thì không, dù nó gọi đúng một lượt.
    """
    bdd, kho, cong, thu_muc = moi_truong
    doan = _doan(5)

    for i in (0, 1, 2):
        p = kho._p(bdd.khoa_doan("u1", "job-abc", i))
        _wav_nho(p)

    bdd.dung(doan, thu_muc=thu_muc, owner_id="u1", job_id="job-abc")

    da_hoi = [t for lo in cong.lo_da_goi for t in lo]
    assert da_hoi == doan[3:], da_hoi


def test_khong_co_gi_trong_kho_thi_sinh_du(moi_truong):
    bdd, kho, cong, thu_muc = moi_truong
    doan = _doan(5)
    bdd.dung(doan, thu_muc=thu_muc, owner_id="u1", job_id="job-abc")
    assert [t for lo in cong.lo_da_goi for t in lo] == doan


def test_lo_thu_hai_khong_lam_lai_lo_thu_nhat(moi_truong):
    """Chia lô là chuyện xếp việc, không được biến thành chuyện làm lại."""
    bdd, kho, cong, thu_muc = moi_truong
    doan = _doan(20)
    bdd.dung(doan, thu_muc=thu_muc, owner_id="u1", job_id="j", so_moi_lo=8)
    da_hoi = [t for lo in cong.lo_da_goi for t in lo]
    assert da_hoi == doan
    assert len(da_hoi) == len(set(da_hoi)), "co doan bi sinh hai lan"


# ── 2. một đoạn hỏng không kéo theo cả lô ────────────────────────────────────

def test_mot_doan_hong_thi_bay_doan_kia_van_duoc_giu(moi_truong):
    """🔴 YÊU CẦU P0: đoạn 47 hỏng thì đừng render lại 1–46.

    Một lô là tám đoạn. Nếu một đoạn làm engine ném lỗi thì bảy đoạn kia **đã
    sinh xong trên GPU** cũng mất theo — trừ khi ta thử lại từng đoạn một.

    Phép kiểm chốt điều thật sự quan trọng: sau khi lượt này ném lỗi, kho phải
    đã giữ được bảy đoạn tốt, để lần thử sau của nền tảng chỉ còn thiếu một.
    """
    bdd, kho, cong, thu_muc = moi_truong
    doan = _doan(8)
    cong.hong_o = {doan[5]}

    with pytest.raises(Exception):
        bdd.dung(doan, thu_muc=thu_muc, owner_id="u1", job_id="j",
                 so_moi_lo=8)

    da_giu = sorted(int(k.rsplit("/", 1)[-1].split(".")[0])
                    for k in kho.da_put)
    assert da_giu == [0, 1, 2, 3, 4, 6, 7], da_giu


def test_lan_thu_sau_chi_con_thieu_dung_doan_hong(moi_truong):
    """Nối tiếp phép kiểm trên: nền tảng thử lại ⇒ chỉ đoạn 5 được hỏi.

    ⭐ Đây là chỗ hai cơ chế gặp nhau. `SO_LAN_THU_JOB` của nền tảng thử lại cả
       job với **cùng `job_id`**; khoá đoạn gắn với `job_id`; nên lần thử sau
       nhìn thấy đúng bảy đoạn lần trước để lại. Không cơ chế nào trong hai cái
       biết về cái kia, và đó là lý do cách này rẻ.
    """
    bdd, kho, cong, thu_muc = moi_truong
    doan = _doan(8)
    cong.hong_o = {doan[5]}
    with pytest.raises(Exception):
        bdd.dung(doan, thu_muc=thu_muc, owner_id="u1", job_id="j", so_moi_lo=8)

    cong.hong_o = set()
    cong.lo_da_goi.clear()
    bdd.dung(doan, thu_muc=thu_muc, owner_id="u1", job_id="j", so_moi_lo=8)

    assert [t for lo in cong.lo_da_goi for t in lo] == [doan[5]]


def test_bay_len_nguyen_ven_khi_cong_dang_ban(moi_truong):
    """⛔ BẬN KHÔNG PHẢI HỎNG. `SidecarBan` phải bay thẳng lên cho `job_runner`
    xếp lại — bọc nó thành một lỗi khác là biến "máy đang bận" thành "job hỏng",
    và một job hỏng thì TRỪ CREDIT cho việc chưa từng chạy."""
    bdd, kho, cong, thu_muc = moi_truong

    def ban(*a, **k):
        raise cong.SidecarBan("dang ban")

    cong.lo_ra_tep = ban
    with pytest.raises(cong.SidecarBan):
        bdd.dung(_doan(8), thu_muc=thu_muc, owner_id="u1", job_id="j")


# ── 3. hợp đồng của khoá và của tiến độ ──────────────────────────────────────

def test_khoa_doan_co_job_id_nhu_MOT_DOAN_duong_dan(moi_truong):
    """🔴 `/{job_id}/` — có dấu gạch chéo hai đầu.

    `platform_core/job_content.py` nhận diện tệp của một job bằng cách tìm
    `/{job_id}/` như một ĐOẠN đường dẫn. `jobs.py` đã ghi lại cái giá của việc
    làm sai: tệp không bao giờ bị dọn, trong khi vòng bảo trì vẫn chạy và vẫn
    báo thành công — một rò rỉ hoàn toàn im lặng.
    """
    bdd, _, _, _ = moi_truong
    k = bdd.khoa_doan("u1", "job-abc", 7)
    assert "/job-abc/" in k
    assert k.endswith("/0007.wav"), k


def test_tien_do_that_va_khong_bao_gio_lui(moi_truong):
    """Tiến độ phải lấy từ SỐ ĐOẠN ĐÃ XONG, không phải từ một đồng hồ."""
    bdd, kho, cong, thu_muc = moi_truong
    ctx = CtxGia()
    bdd.dung(_doan(20), thu_muc=thu_muc, owner_id="u1", job_id="job-abc",
             ctx=ctx, so_moi_lo=8)

    pt = [p for p, _ in ctx.moc]
    assert pt, "khong bao tien do lan nao"
    assert pt == sorted(pt), pt
    assert max(pt) <= 100 and min(pt) >= 0


def test_tien_do_hong_khong_lam_hong_ban_doc(moi_truong):
    """Việc phụ không được giết việc chính — cùng luật với `nghe_thu.dung`."""
    bdd, kho, cong, thu_muc = moi_truong

    class CtxVo:
        job_id = "j"

        def progress(self, *a, **k):
            raise RuntimeError("bang dieu khien sap")

    duong, _ = bdd.dung(_doan(3), thu_muc=thu_muc, owner_id="u1", job_id="j",
                        ctx=CtxVo())
    assert os.path.isfile(duong)


def test_so_cau_duoc_tinh_cho_MOI_doan_ke_ca_doan_lay_lai_tu_kho(moi_truong):
    """⚠️ Đoạn lấy lại từ kho không mang theo văn bản của nó — chỉ có tệp.

    Nhưng bộ ghép CẦN số câu của mọi đoạn để phân biệt ranh giới câu với khe từ
    (`noi_dai.nhip_nghi`). Thiếu nó ở vài đoạn thì nhịp nghỉ tính trên một mẫu
    thiên lệch, và mối nối nghe khác đi tuỳ đoạn nào tình cờ còn trong kho —
    một khác biệt phụ thuộc LỊCH SỬ CHẠY, thứ khó truy nhất.
    """
    bdd, kho, cong, thu_muc = moi_truong
    doan = _doan(5)
    for i in (0, 1):
        _wav_nho(kho._p(bdd.khoa_doan("u1", "j", i)))

    bdd.dung(doan, thu_muc=thu_muc, owner_id="u1", job_id="j")

    duong_vao, so_cau = cong.ghep_voi
    assert len(duong_vao) == 5
    assert len(so_cau) == 5
    assert all(s >= 1 for s in so_cau)
