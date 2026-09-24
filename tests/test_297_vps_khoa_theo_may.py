"""H39 — khoá theo máy: hai job không được cùng làm việc trên một máy.

## Đường thật dẫn tới lỗi này

Trước 25/08 hai job trên cùng một máy chạy song song được, và có ít nhất hai
đường tới đó:

* khách bấm **"Cài lại"** rồi đổi ý bấm **"Xoá"** — hai job vào hàng đợi;
* vòng bảo trì nộp job **xoá** (máy quá hạn ân hạn) **đúng lúc** khách bấm
  "Cài lại" để cứu máy.

Hậu quả không dừng ở một lỗi 500. Job xoá có thể **nhả địa chỉ trong mạng riêng**
trong khi job kia vẫn đang dựng VM — và địa chỉ vừa nhả được cấp cho **máy của
khách tiếp theo**. Hai máy cùng một địa chỉ là khách gõ đúng địa chỉ rồi rơi vào
máy người lạ, đúng thứ `mang.py` nói tuyệt đối không được có.
"""
from __future__ import annotations

import pytest

from apps.vps import jobs


class _Ctx:
    def __init__(self, jt):
        self.job_type = jt

    def progress(self, p, m):
        pass


# ── 1. Mọi nhánh đều chạy dưới khoá ─────────────────────────────────────────

def test_ba_job_deu_di_qua_khoa(monkeypatch):
    """Bỏ sót một nhánh thì nhánh đó là đường vòng qua khoá — và nó sẽ là nhánh
    gây ra sự cố, vì nó là nhánh không ai nghĩ tới."""
    da_khoa = []

    from contextlib import contextmanager

    @contextmanager
    def gia(instance_id, job_type):
        da_khoa.append((instance_id, job_type))
        yield

    monkeypatch.setattr(jobs, "_khoa_may", gia)
    for ten in ("_tao_may", "_dung_lai", "_xoa_may"):
        monkeypatch.setattr(jobs, ten, lambda p, c=None: {"ok": True})

    for jt in ("vps.provision", "vps.rebuild", "vps.destroy"):
        jobs.handle({"instance_id": "may-1"}, _Ctx(jt))
    assert da_khoa == [("may-1", "vps.provision"),
                       ("may-1", "vps.rebuild"),
                       ("may-1", "vps.destroy")]


def test_job_type_la_thi_TU_CHOI_truoc_khi_giu_khoa(monkeypatch):
    """Giữ khoá rồi mới phát hiện không biết làm gì là giữ khoá vô ích trong 45
    phút — và máy đó bị treo mọi thao tác suốt thời gian ấy."""
    da_khoa = []

    from contextlib import contextmanager

    @contextmanager
    def gia(instance_id, job_type):
        da_khoa.append(instance_id)
        yield

    monkeypatch.setattr(jobs, "_khoa_may", gia)
    with pytest.raises(jobs.VpsJobError):
        jobs.handle({"instance_id": "may-1"}, _Ctx("vps.khong-biet"))
    assert da_khoa == [], "khong duoc giu khoa cho mot job_type khong biet"


def test_thieu_instance_id_thi_TU_CHOI():
    """Khoá tên `vps-may:` (rỗng) sẽ khoá **mọi** máy cùng lúc."""
    with pytest.raises(jobs.VpsJobError) as e:
        jobs.handle({}, _Ctx("vps.provision"))
    assert "instance_id" in str(e.value)


# ── 2. Khoá thật sự loại trừ ────────────────────────────────────────────────

@pytest.fixture()
def db_that(monkeypatch):
    """CSDL thật (SQLite) để `leases` chạy đúng đường của nó, kể cả ràng buộc
    duy nhất — thứ tạo ra tính loại trừ."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401

    e = create_engine("sqlite://")
    dbmod.Base.metadata.create_all(e)
    Phien = sessionmaker(bind=e)

    def _mo():
        s = Phien()

        def gen():
            try:
                yield s
            finally:
                pass

        g = gen()
        return next(g), g

    monkeypatch.setattr(jobs, "_mo_db", _mo)
    return Phien()


def test_job_thu_hai_bi_TU_CHOI_khi_job_dau_dang_giu(db_that):
    """Đây là phép kiểm chính: hai lần vào khoá lồng nhau, lần hai phải hỏng."""
    with jobs._khoa_may("may-1", "vps.rebuild"):
        with pytest.raises(jobs.VpsJobError) as e:
            with jobs._khoa_may("may-1", "vps.destroy"):
                pytest.fail("khong duoc vao duoc")
    assert "job khac" in str(e.value)


def test_hai_MAY_KHAC_NHAU_khong_chan_nhau(db_that):
    """Khoá theo máy, không phải khoá theo app. Khoá cả app thì mười khách mua
    cùng lúc phải xếp hàng sau nhau."""
    with jobs._khoa_may("may-1", "vps.provision"):
        with jobs._khoa_may("may-2", "vps.provision"):
            pass


def test_nha_khoa_khi_job_NEM(db_that):
    """Job hỏng mà khoá không nhả thì máy đó bị treo mọi thao tác tới hết TTL —
    45 phút khách không làm gì được, vì một lỗi đã xảy ra xong từ lâu."""
    with pytest.raises(RuntimeError):
        with jobs._khoa_may("may-1", "vps.provision"):
            raise RuntimeError("job hong")
    # Vao lai duoc ngay = khoa da nha.
    with jobs._khoa_may("may-1", "vps.destroy"):
        pass


def test_TTL_dai_hon_job_dai_nhat():
    """Khoá hết hạn giữa lúc job còn chạy thì một job khác cướp được máy — đúng
    thứ khoá sinh ra để chặn."""
    from apps.vps.manifest import MANIFEST

    lau_nhat = max(MANIFEST.max_runtime_s.values())
    assert jobs.KHOA_MAY_TTL.total_seconds() > lau_nhat, (
        f"TTL {jobs.KHOA_MAY_TTL} khong du cho job dai {lau_nhat}s")


def test_khoa_dung_lease_cua_NEN_TANG_chu_khong_dung_bang_rieng():
    """Hai cơ chế khoá trong một hệ thống là hai cơ chế sẽ lệch nhau. Nền tảng
    đã có `platform_core/leases.py`, sinh ra cho đúng lớp vấn đề này (H36)."""
    import inspect

    nguon = inspect.getsource(jobs._khoa_may)
    assert "leases.acquire" in nguon and "leases.release" in nguon


# ── 3. Đối chiếu định kỳ: phép soi phải TỰ chạy ─────────────────────────────

def _maintenance_probe(db, monkeypatch):
    from apps.vps import bao_tri
    from apps.vps.services import billing, console
    calls = []
    # `dem_profile_mat_tin_hieu` them 23/09: mot cham CSDL MOI trong `mot_luot`.
    # Probe nay co y liet ke tuong minh moi ham cham CSDL — `db` o day la mot
    # `object()` tran, nen quen mot ten la mot AttributeError chu khong phai mot
    # ket qua sai im lang. Do la thiet ke dung; chi can them ten vao day.
    for name in ("_dong_bo_bang_thong_pinned", "_chup_anh_den_han",
                 "_hoan_may_tao_hong", "dem_profile_mat_tin_hieu"):
        monkeypatch.setattr(bao_tri, name, lambda *args, **kwargs: 0)
    monkeypatch.setattr(billing, "thu_phi_dinh_ky", lambda *args, **kwargs:
                        {"da_thu": 0, "da_treo": 0})
    monkeypatch.setattr(billing, "den_han_xoa", lambda *args, **kwargs: [])
    monkeypatch.setattr(console, "don_ve_het_han", lambda *args, **kwargs: 0)
    def cleanup(*args, **kwargs):
        calls.append("cleanup")
        return 0
    def reconcile(*args, **kwargs):
        calls.append("reconcile")
        return 7
    def soi_dien(*args, **kwargs):
        calls.append("soi_dien")
        return 0
    monkeypatch.setattr(bao_tri, "_don_thao_tac_qua_han", cleanup)
    monkeypatch.setattr(bao_tri, "_doi_chieu_profiles", reconcile)
    monkeypatch.setattr(bao_tri, "_doi_chieu_dinh_ky", soi_dien)
    return bao_tri.mot_luot(db), calls


def test_vong_bao_tri_CO_goi_doi_chieu(monkeypatch):
    """`vps_doctor` đối chiếu được từ 25/08, nhưng **không ai chạy nó định kỳ**.
    Một phép soi không ai chạy là một phép soi không tồn tại — và thứ nó tìm ra
    (Reserved IP mồ côi, $3/tháng) là loại hỏng không bao giờ tự kêu lên.

    ⚠️ HAI phép soi, không phải một — và trước 24/09/2026 phép đo ở đây chỉ nhìn
       thấy MỘT. `_doi_chieu_profiles` (module `reconciliation`) khai rõ là
       read-only và **không đọc điện**; chỗ duy nhất ghi `dien_quan_sat` và tìm
       IP mồ côi là `doi_chieu.quet`, gọi qua `_doi_chieu_dinh_ky` — thứ mà
       không mã sản phẩm nào gọi cho tới hôm nay, trong khi test này vẫn xanh.
       Đo hậu quả trên production: máy 204 mang `dien_quan_sat = chay` từ 16/09
       còn Proxmox trả `tat`.
    """
    result, calls = _maintenance_probe(object(), monkeypatch)
    assert result["mo_coi"] == 7
    assert calls.count("reconcile") == 1
    assert calls.count("soi_dien") == 1, "vong bao tri khong chay phep soi do dien"


def test_doi_chieu_chay_HANG_NGAY_chu_khong_hang_gio():
    """Nó gọi ra Proxmox + router + gateway + Vultr. Thứ nó tìm (mồ côi) không
    xuất hiện theo nhịp giờ, nên quét mỗi giờ chỉ là bốn vòng gọi mạng thừa."""
    from apps.vps import bao_tri

    assert bao_tri.DOI_CHIEU_MOI_GIAY >= 12 * 3600


def test_doi_chieu_dat_moc_TRUOC_khi_chay(monkeypatch):
    """Đặt mốc sau khi chạy thì một lần ném sẽ quay lại ngay và ném lại mỗi giờ."""
    from apps.vps import bao_tri, doi_chieu

    monkeypatch.setattr(bao_tri, "_moc_doi_chieu", 0.0)

    def no(db, client):
        raise RuntimeError("nguon ngoai hong")

    monkeypatch.setattr(doi_chieu, "quet", no)
    with pytest.raises(RuntimeError):
        bao_tri._doi_chieu_dinh_ky(object(), object())
    # Lan hai phai bi hoan lai, khong nem nua.
    assert bao_tri._doi_chieu_dinh_ky(object(), object()) == 0


def test_MOT_phep_quet_dung_chung_cho_ca_hai_noi_goi():
    """Chép logic quét sang `vps_doctor` nghĩa là có hai bản, và bản trong vòng
    bảo trì (thứ thật sự chạy hằng ngày) sẽ là bản bị quên."""
    from pathlib import Path

    doctor = Path("tools/vps_doctor.py").read_text(encoding="utf-8")
    assert "from apps.vps import doi_chieu" in doctor
    assert "doi_chieu.quet(db, client)" in doctor
    # Doctor chi HIEN THI: khong duoc tu dung lai phep so sanh.
    assert "danh_sach_dat_cho" not in doctor


def test_doi_chieu_KHONG_TU_SUA():
    """Tự sửa là đặt cược rằng phép đối chiếu không bao giờ sai — và một phép
    đối chiếu sai mà tự sửa thì xoá đúng thứ nó hiểu nhầm. Một VM đang được job
    khác dựng dở trông y hệt một VM mồ côi."""
    import inspect

    from apps.vps import doi_chieu

    nguon = inspect.getsource(doi_chieu)
    for cam in ("db.delete", "xoa_ip(", "go_cho(", "client.xoa(", "db.commit"):
        assert cam not in nguon, f"doi_chieu khong duoc goi {cam}"


def test_doi_chieu_BO_QUA_may_cua_chu_nha():
    """8 máy của chủ nhà chạy trên cùng node. Báo chúng là mồ côi mỗi ngày sẽ
    dạy người đọc bỏ qua chính báo cáo này."""
    import inspect

    from apps.vps import doi_chieu

    assert 'startswith("vps-")' in inspect.getsource(doi_chieu.quet)


def test_mot_nguon_im_lang_khong_lam_mat_ca_bao_cao():
    """Người chạy phép này thường đang tìm một sự cố. Mất nửa báo cáo vì một
    nguồn không trả lời là mất đúng nửa họ cần."""
    from apps.vps import doi_chieu

    kq = doi_chieu.KetQua()
    ra = doi_chieu._an_toan("thu", lambda: 1 / 0, "mac_dinh", kq)
    assert ra == "mac_dinh"
    assert kq.khong_doc_duoc and "ZeroDivisionError" in kq.khong_doc_duoc[0]


# ── 4. Chốt biên dịch trong script deploy ───────────────────────────────────

def test_deploy_CO_chot_bien_dich_va_no_dung_TRUOC_Stop_Service():
    """Deploy là robocopy + alembic. Không có chốt thì một tệp `.py` cụt được
    chép thẳng sang production.

    Chốt phải đứng **trước** `Stop-Service`: hỏng ở đó thì dịch vụ vẫn đang chạy
    và không ai mất gì. Đặt sau thì ta đã tự tay tạo ra downtime rồi mới phát
    hiện không deploy được."""
    from pathlib import Path

    ps = Path("setup/2-cai-dat.ps1").read_text(encoding="utf-8")
    dong = ps.splitlines()

    def _dong_lenh(bat_dau: str) -> int:
        """Số dòng của LỆNH đầu tiên, bỏ qua chú thích.

        So bằng `str.index` trên cả tệp thì phép kiểm bắt nhầm chính **chú thích**
        giải thích vì sao chốt phải đứng trước — một test đỏ vì tài liệu nói đúng
        là một test sẽ bị xoá, không phải được sửa."""
        for i, d in enumerate(dong):
            if d.strip().startswith(bat_dau):
                return i
        return -1

    def _dong_chua(loi: str) -> int:
        """Dòng LỆNH đầu tiên **chứa** `loi`, bỏ qua chú thích.

        🔴 VÌ SAO CẦN BẢN NÀY chứ không chỉ `_dong_lenh`: bản trước định vị chốt
           bằng đúng chuỗi mã `"& $pyKiem"`. Ngày 01/09 chốt được viết lại để
           không thể treo vô hạn (dùng `System.Diagnostics.Process` thay cho toán
           tử gọi + đường ống), và phép kiểm đỏ — **không phải vì bất biến bị phá
           mà vì cái thước đo nó đã cũ**.

        ⛔ Đó là một hồi quy của *phép kiểm*, và nó nguy hiểm theo kiểu riêng:
           một chốt đỏ trông y hệt một lỗi thật, nên phản ứng tự nhiên là hoàn
           nguyên bản vá — tức khôi phục lại đúng chỗ treo vừa sửa.

        ⭐ Nên nay định vị bằng **thứ bất biến nói tới** (`compileall`), không
           bằng cách nó được gọi. Đổi cách gọi là việc bình thường; bỏ chốt đi
           mới là chuyện phải đỏ.
        """
        for i, d in enumerate(dong):
            t = d.strip()
            if t.startswith("#"):
                continue
            if loi in t:
                return i
        return -1

    i_chot = _dong_chua("compileall")
    i_dung = _dong_lenh("Stop-Service")
    assert "compileall" in ps, "deploy khong co chot bien dich"
    assert i_chot >= 0 and i_dung >= 0
    assert i_chot < i_dung, (
        f"chot o dong {i_chot}, Stop-Service o dong {i_dung} — "
        f"chot phai chay TRUOC khi dung dich vu")
    assert "DUNG deploy" in ps


def test_script_deploy_THUAN_ASCII():
    """PowerShell 5.1 đọc `.ps1` không BOM theo bảng mã ANSI; một dấu tiếng Việt
    làm hỏng cả câu lệnh và báo lỗi ở dòng khác."""
    from pathlib import Path

    tho = Path("setup/2-cai-dat.ps1").read_bytes()
    xau = [i for i, b in enumerate(tho) if b > 127]
    assert not xau, f"co {len(xau)} byte ngoai ASCII, dau tien o {xau[:1]}"
