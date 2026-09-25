"""B3 - do dac MOT LAN, GIAI DOAN 1, tren MOT phim khach THAT.

⚠️ Day KHONG phai bai kiem hoi quy thuong truc. Khong nam trong dai so test cap
   cho chuong trinh nao — dung mot lan roi bo, khong `--accept`, khong gate.
   Muc dich DUY NHAT: tra loi cau hoi B3 dat ra — "mot phut video nguon ton bao
   nhieu phut tuong?" — bang mot luot chay THAT qua chinh `_mot_luot` cua
   `test_448`, co them do dac GIAY CPU (khong chi giay tuong) cho tung giai
   doan, vi phan lon giai doan la CHO may B / sidecar chu khong phai TINH
   (xem `docs/NHAT_KY.md` 2026-09-25, muc 4/7/8).

Chay:
    python -m pytest -q -p no:randomly tests/test_b3_do_dac_mot_lan.py -s

Doc moi truong:
    LTT_B3_TEN_TEP   ten tep uu tien trong `asv_e2e_that/` (rong = tep dau
                     tien theo thu tu bang chu cai — hien la clip 190,0 s)
    LTT_B3_RA        duong ghi bao cao JSON (rong = `_ket_qua/b3_bao_cao.json`)
    LTT_B3_MP4_RA    duong ghi tep MP4 GIAI DOAN 1 (rong =
                     `_ket_qua/b3_giai_doan1.mp4`)

⛔ Khong dung `_chay_hang_doi` rieng: no da lam dung viec "dong vai worker
   that + do gio tung job" (xem docstring cua no). Bai nay chi MONKEYPATCH
   `_mot_job` — noi worker that goi handler — de gan them mot phep do GIAY CPU
   canh phep do GIAY TUONG da co san, khong viet lai vong lap hang doi.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import psutil
import pytest

from tests.fixtures import asv_e2e as fx
from tests.test_423_asv_giao_dien import moi_truong  # noqa: F401
from tests import test_448_asv_v4_e2e_nghiem_thu as t448

import apps.ltt_voice.tables  # noqa: E402,F401  isort:skip


class LayMauCpu:
    """Cong don giay CPU (user+system) cua tien trinh nay + CAC TIEN TRINH CON,
    lay mau dinh ky o mot luong nen.

    🔴 **Can bien vi sao co luong nen, khong chi snapshot truoc/sau MOI job.**
       Tren Windows, `psutil` KHONG cong CPU cua mot tien trinh con DA THOAT vao
       cha (da ghi trong `docs/NHAT_KY.md` muc 7, va trong chinh
       `tools/asv_chay_worker_that.py::cpu_cay`). Mot demucs con song vai chuc
       giay roi thoat NGAY TRONG mot job se bi mot snapshot truoc/sau bo qua
       hoan toan neu no thoat truoc lan doc "sau". Lay mau moi 0,5 s va GIU LAI
       gia tri cuoi cung da thay cho tung pid (kha ca sau khi pid da bien mat)
       la cach re nhat vet duoc phan CPU do ma khong phai tu viet lai
       `Get-Counter`/ETW. ⛔ Van la CAN DUOI, khong phai gia tri dung tuyet doi
       — cung mot han che nhu `cpu_cay()`, ghi ro trong bao cao thay vi gia vo
       khong co.
    """

    def __init__(self, goc_pid: int, chu_ky_s: float = 0.5):
        self._goc = psutil.Process(goc_pid)
        self._chu_ky = chu_ky_s
        self._da_biet: dict[int, float] = {}
        self._khoa = threading.Lock()
        self._dung = threading.Event()
        self._luong = threading.Thread(target=self._vong_lap, daemon=True)
        self._loi_lay_mau = 0

    def _mot_lan(self) -> None:
        try:
            con = self._goc.children(recursive=True)
        except psutil.Error:
            con = []
        with self._khoa:
            for p in con:
                try:
                    t = p.cpu_times()
                except psutil.Error:
                    self._loi_lay_mau += 1
                    continue
                self._da_biet[p.pid] = t.user + t.system

    def bat_dau(self) -> None:
        self._mot_lan()
        self._luong.start()

    def _vong_lap(self) -> None:
        while not self._dung.wait(self._chu_ky):
            self._mot_lan()

    def dung(self) -> None:
        self._dung.set()
        self._luong.join(timeout=3)
        self._mot_lan()

    def tong_cpu_s(self) -> float:
        """Giay CPU cong don TU LUC `bat_dau()`: tien trinh nay + moi con da
        tung thay (con hay da thoat)."""
        try:
            t = self._goc.cpu_times()
            goc = t.user + t.system
        except psutil.Error:
            goc = 0.0
        with self._khoa:
            con = sum(self._da_biet.values())
        return goc + con


def _giay_cpu_moi_giai_doan(nhat_ky_job: list[dict]) -> dict:
    """Cong don `cpu_s`/`giay` (tuong) theo `job_type`, giu thu tu xuat hien."""
    theo_gd: dict[str, dict] = {}
    for j in nhat_ky_job:
        gd = theo_gd.setdefault(j["job_type"], {"cpu_s": 0.0, "giay_tuong": 0.0,
                                                  "so_job": 0})
        gd["cpu_s"] += float(j.get("cpu_s") or 0.0)
        gd["giay_tuong"] += float(j.get("giay") or 0.0)
        gd["so_job"] += 1
    for gd in theo_gd.values():
        gd["cpu_s"] = round(gd["cpu_s"], 2)
        gd["giay_tuong"] = round(gd["giay_tuong"], 2)
        gd["loi_trung_binh"] = (round(gd["cpu_s"] / gd["giay_tuong"], 3)
                                if gd["giay_tuong"] > 0 else None)
    return theo_gd


def test_b3_giai_doan1_mot_video(moi_truong, tmp_path, monkeypatch):
    from apps.auto_scan_video import hop_dong_v4

    phim = fx.phim_khach_that()
    if not phim:
        pytest.skip(f"khong co phim that trong {fx.THU_MUC_PHIM_THAT}")

    ten_uu_tien = os.environ.get("LTT_B3_TEN_TEP", "").strip()
    tep = next((t for t in phim if t.name == ten_uu_tien), None) if ten_uu_tien else None
    if tep is None:
        tep = phim[0]

    _app, a, csrf_a, b, _csrf_b = moi_truong
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_DEVICE", "cpu")
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_COMPUTE", "int8")

    if fx.dung_model_that():
        from platform_core.db import get_session
        so_khoa = 0
        for _db in get_session():
            so_khoa = fx.nap_khoa_pool(_db)
            _db.commit()
            break
        assert so_khoa, (
            "LTT_ASV_MODEL_THAT=1 nhung pool that khong co khoa `ltt_llm` nao "
            "dung duoc")

    dem_model = fx.dat_cua_model(monkeypatch, su_that=None)
    dem_giong = fx.dat_cua_giong(monkeypatch, tmp_path / "tieng")

    goc_s = round(float(fx.soi(str(tep))["format"]["duration"]), 3)

    mau = LayMauCpu(os.getpid())
    mau.bat_dau()

    # 🔑 Khoa THEO PHA, khong khoa ca luot: `PHA_NANG_CPU` (demucs, ASR,
    #    ffmpeg compose/render/qc) giu `cpu_nhieu` NGAN quanh dung job do;
    #    `PHA_MAY_TAO_TIENG` (voice_synthesis) giu `may_tao_tieng` SUOT pha
    #    giong; con lai (edit_plan, content_process, qc_ai...) la goi mang,
    #    KHONG khoa gi. Day la cong cu DA CO SAN va DA duoc `test_3000` doi
    #    chieu (6/12 bai do khi tiem lai hanh vi cu "khoa boc ca luot") — dat
    #    `LTT_B3_KHONG_KHOA=1` chi de chan doan/so sanh, KHONG dung mac dinh.
    khoa = None
    if os.environ.get("LTT_B3_KHONG_KHOA", "").strip() != "1":
        khoa = fx.KhoaTheoPha("b3-do-dac")

    nhat_ky_cpu: list[dict] = []
    goc_mot_job = t448._mot_job
    t_bat_dau_luot = time.time()

    def _mot_job_do_cpu(db, jobs, provider_failure_kind, handler, job, ctx,
                        da_hoan_s):
        cpu0 = mau.tong_cpu_s()
        w0 = time.time()
        ket = goc_mot_job(db, jobs, provider_failure_kind, handler, job, ctx,
                          da_hoan_s)
        cpu1 = mau.tong_cpu_s()
        w1 = time.time()
        nhat_ky_cpu.append({"job_type": job.job_type,
                            "cpu_s": round(cpu1 - cpu0, 2)})
        # ⭐ In NGAY + flush: chu du an khong doan duoc "con song hay da treo"
        #    tu mot tep log dung yen. Dong nay la BANG CHUNG SONG, khong phai
        #    tien trinh dem tien trinh.
        print(f"[b3] +{w1 - t_bat_dau_luot:6.1f}s tuong  "
              f"{job.job_type:<32} {w1 - w0:7.2f}s tuong rieng  "
              f"{cpu1 - cpu0:7.2f}s cpu rieng", flush=True)
        return ket

    monkeypatch.setattr(t448, "_mot_job", _mot_job_do_cpu)

    nhan = f"{tep.name}::b3_giu_hinh"
    t_tuong0 = time.time()
    kq = t448._mot_luot(
        a, csrf_a, b, tep, tmp_path / "ra",
        nhan=nhan, preset=hop_dong_v4.PRESET_GIU_HINH,
        che_do_giong=hop_dong_v4.CHE_DO_GIONG_TU_CHON, giong_id="Minh Đức",
        khoa=khoa)
    t_tuong1 = time.time()

    mau.dung()
    da_khoa = list(khoa.da_khoa) if khoa is not None else []

    # Gan giay CPU vao DUNG dong nhat_ky_job — hai danh sach cung thu tu vi
    # `_mot_job_do_cpu` append MOI LAN `_chay_hang_doi` goi no, giong het
    # `_chay_hang_doi` tu append `nhat_ky` cua no.
    assert len(kq["nhat_ky_job"]) == len(nhat_ky_cpu), (
        len(kq["nhat_ky_job"]), len(nhat_ky_cpu))
    for nk, kl in zip(kq["nhat_ky_job"], nhat_ky_cpu, strict=True):
        assert nk["job_type"] == kl["job_type"]
        nk["cpu_s"] = kl["cpu_s"]

    theo_giai_doan = _giay_cpu_moi_giai_doan(kq["nhat_ky_job"])
    tong_cpu_s = round(sum(g["cpu_s"] for g in theo_giai_doan.values()), 2)
    tong_tuong_s = round(t_tuong1 - t_tuong0, 2)

    # ── Chep tep MP4 ra ngoai `tmp_path` (pytest chi giu 3 thu gan nhat) ────
    duong_ra_mp4 = ""
    ra_nguon = (tmp_path / "ra" / f"ra_{t448._ten_an_toan(nhan)}.mp4")
    if ra_nguon.exists():
        dich = Path(os.environ.get("LTT_B3_MP4_RA")
                    or (Path.cwd() / "_ket_qua" / "b3_giai_doan1.mp4"))
        dich.parent.mkdir(parents=True, exist_ok=True)
        dich.write_bytes(ra_nguon.read_bytes())
        duong_ra_mp4 = str(dich)

    bao_cao = {
        "schema": "asv.v4.b3_do_dac_mot_lan.1",
        "ghi_luc": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "may": t448._dang_ky_may(),
        "nguon_that": {"ten": tep.name, "thoi_luong_s": goc_s,
                       "byte": tep.stat().st_size},
        "giong_that": bool(dem_giong.get("giong_that")),
        "model_that": bool(dem_model.get("model_that")),
        "preset": hop_dong_v4.PRESET_GIU_HINH,
        "trang_thai_run": kq["trang_thai_run"],
        "tong_tuong_s": tong_tuong_s,
        "tong_cpu_s": tong_cpu_s,
        "lan_nguon_s": (round(tong_tuong_s / goc_s, 3) if goc_s else None),
        "loi_lay_mau_cpu": mau._loi_lay_mau,
        "khoa_theo_pha_BAT": khoa is not None,
        "da_khoa_tung_job": [{"job_type": jt, "tai_nguyen": list(tn)}
                             for jt, tn in da_khoa],
        "theo_giai_doan": theo_giai_doan,
        "nhat_ky_job_chi_tiet": kq["nhat_ky_job"],
        "ra": kq.get("ra") or {},
        "loi_do_ban_ra": kq.get("loi_do_ban_ra") or "",
        "qc": kq.get("qc") or {},
        "so_ke": kq.get("so_ke") or {},
        "doi_soat": kq.get("doi_soat") or {},
        "giai_doan": kq.get("giai_doan") or [],
        "asr": kq.get("asr") or {},
        "ban_long_tieng": kq.get("ban_long_tieng") or {},
        "ban_bien_tap": kq.get("ban_bien_tap") or {},
        "vi_sao_hong": kq.get("vi_sao_hong") or [],
        "mp4_ra": duong_ra_mp4,
    }

    duong_bc = Path(os.environ.get("LTT_B3_RA")
                    or (Path.cwd() / "_ket_qua" / "b3_bao_cao.json"))
    duong_bc.parent.mkdir(parents=True, exist_ok=True)
    duong_bc.write_text(
        json.dumps(fx.sach_de_cong_bo(bao_cao), ensure_ascii=False, indent=2),
        encoding="utf-8")

    # 🔴 **Tep JSON da ghi UTF-8 O TREN roi — dong `print` nay chi la tien loi,
    #    va KHONG duoc phep lam mat bang chung da co neu no chet.** Do that
    #    25/09: console cua `nghiem_thu_asv.ps1`/PowerShell dung `cp1252`
    #    (khong phai UTF-8), va bao cao mang van ban tieng Trung tu ASR
    #    (`asr.van`) + tieng Viet co dau ⇒ `print()` nem `UnicodeEncodeError`
    #    NGAY SAU KHI da ghi xong tep — pytest bao "FAILED" cho mot luot THAT
    #    RA da `done`, 13/13 giai doan `succeeded`, QC dat. Bat loi o day thay
    #    vi de no lam do ca bai.
    try:
        print("\n" + json.dumps(bao_cao, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print(f"\n[b3] (bo qua in JSON day du - console khong doc duoc UTF-8; "
              f"bao cao day du da ghi tai {duong_bc})")

    # ⛔ KHONG assert QC/trang_thai o day chan cung: B3 la do dac, khong phai
    # cong chat luong — mot lan chay khong `done` VAN phai ghi bao cao (da
    # co o tren) de bao cao noi duoc no chet o dau, chu khong duoc `KeyError`
    # xoa mat bang chung. Nhung neu ra duoc mp4 thi doi dung 190s, khong cat.
    if kq["trang_thai_run"] == "done" and kq.get("ra"):
        ra_s = kq["ra"]["thoi_luong"]
        assert abs(ra_s - goc_s) <= 1.0, (
            f"GIAI DOAN 1 (giu hinh) phai giu NGUYEN do dai: "
            f"{goc_s:.2f}s -> {ra_s:.2f}s")
