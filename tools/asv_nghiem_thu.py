"""Chay muoi ba kich ban nghiem thu cua Prompt 21 va GHI SO DO duoc.

    python tools/asv_nghiem_thu.py                # chay het, in bang
    python tools/asv_nghiem_thu.py --json ra.json # ghi them ket qua ra tep

## Vi sao day la mot TEP THAT chu khong phai mot doan chay mot lan

Pha 21 doi *"ghi lai lenh chinh xac, khuon media, thoi luong tung giai doan"*.
Mot bang so chep tay vao bao cao la mot bang so khong ai chay lai duoc — va no
bat dau sai tu lan doi ten phep kiem dau tien.

⭐ Lan chay dau tien cua tep nay (02/09) duoc thuc hien bang mot doan tam, va
   doan do bi don mat khi phien noi lai. So do van con trong bao cao, nhung
   **khong tai hien duoc** — dung cai bay ma `CLAUDE.md` canh bao. Nen no thanh
   mot tep trong `tools/`.

⛔ Day KHONG phai mot phep kiem: no khong khang dinh gi ca, no **do**. Phan
   khang dinh nam o `tests/test_424_ma_tran_nghiem_thu.py`, va do la cho mot
   cong thieu bang chung se lam gate do.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Muoi ba kich ban cua Prompt 21, theo dung thu tu de trong prompt.
#:
#: ⚠️ Moi muc tro toi mot node id THAT. `test_424` chot rang moi bang chung
#:    duoc vien dan deu ton tai, nhung no chot MA TRAN chu khong chot tep nay —
#:    nen o day co mot phep kiem ton tai rieng ngay truoc khi chay.
KICH_BAN: list[tuple[str, str, str]] = [
    ("S1", "duong hanh phuc, mot video dai dien",
     "tests/test_402_asv_mach_doc_gia.py::test_run_chay_het_CHIN_giai_doan_va_ve_done"),
    ("S2", "hai nguoi dung: run/asset/output rieng",
     "tests/test_419_asv_tiem_loi.py::test_hai_nguoi_dung_chay_dong_thoi_khong_lan_du_lieu"),
    ("S3", "nop trung — dedupe job dieu phoi",
     "tests/test_402_asv_mach_doc_gia.py::test_moi_dong_giai_doan_deu_mang_chu_so_huu"),
    ("S4", "provider truot thoang qua -> thu lai an toan",
     "tests/test_418_asv_phan_loai_loi.py::test_loi_TAM_THOI_duoc_giu_NGUYEN_de_nen_tang_thu_lai"),
    ("S5", "dispatch MO HO -> khong bao gio tu dong thu lai",
     "tests/test_418_asv_phan_loai_loi.py::test_mo_ho_thanh_AmbiguousProviderError_KHONG_BAO_GIO_tu_dong_thu_lai"),
    ("S6", "giong hong sau khi thuong nguon xong -> chay tiep",
     "tests/test_409_asv_giong_noi.py::TestPhucHoiTungDoan"),
    ("S7", "render hong -> chay lai TU BAN DUNG",
     "tests/test_415_asv_cong_thoat_render.py::test_render_lai_KHONG_danh_thuc_mot_giai_doan_thuong_nguon_nao"),
    ("S8", "ngat worker sau moi giai doan ben vung",
     "tests/test_403_asv_vong_doi_artifact.py"),
    ("S9", "huy giua mot giai doan dai",
     "tests/test_414_asv_ket_xuat.py::test_huy_giua_chung_thi_GIET_tien_trinh_va_khong_de_lai_ket_qua"),
    ("S10", "dau vao hong / khong ho tro",
     "tests/test_419_asv_tiem_loi.py::test_video_KHONG_CO_TIENG_hong_ngay_va_khong_thu_lai"),
    ("S11", "artifact trung gian mat -> vo hieu cache",
     "tests/test_419_asv_tiem_loi.py::test_artifact_bien_mat_thi_CACHE_khong_dung_lai_no"),
    ("S12", "tranh chap tai nguyen / dinh tuyen GPU",
     "tests/test_402_asv_mach_doc_gia.py::test_lan_ffmpeg_KHONG_nhat_duoc_job_GPU"),
    ("S13", "QC tu choi ban ra hong",
     "tests/test_420_asv_qc.py::test_QC_hong_thi_RUN_KHONG_ve_done"),
]


def _ton_tai(node: str) -> bool:
    tep = node.split("::", 1)[0]
    return (GOC / tep).is_file()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    thieu = [n for _, _, n in KICH_BAN if not _ton_tai(n)]
    if thieu:
        print("TEP BANG CHUNG KHONG TON TAI:", *thieu, sep="\n  ")
        return 2

    ra = []
    for ma, mo_ta, node in KICH_BAN:
        t0 = time.monotonic()
        r = subprocess.run(
            [sys.executable, "-m", "pytest", node, "-q", "-p", "no:cacheprovider"],
            capture_output=True, text=True, cwd=str(GOC))
        giay = round(time.monotonic() - t0, 1)
        dong = [d for d in r.stdout.splitlines()
                if " passed" in d or " failed" in d or " error" in d]
        ra.append({"ma": ma, "mo_ta": mo_ta, "node": node,
                   "ket_qua": "PASS" if r.returncode == 0 else "FAIL",
                   "giay": giay,
                   "tom_tat": dong[-1].strip() if dong else ""})
        print(f"{ma:4} {ra[-1]['ket_qua']:5} {giay:6.1f}s  {mo_ta}", flush=True)

    dat = sum(1 for x in ra if x["ket_qua"] == "PASS")
    print(f"\nKICH BAN: {dat}/{len(ra)} PASS"
          f" | TONG {round(sum(x['giay'] for x in ra), 1)} giay")
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(ra, ensure_ascii=False, indent=2), encoding="utf-8")
        print("da ghi:", args.json)

    # ⛔ Ma thoat khac 0 khi co bat ky kich ban nao do — de mot lan chay trong
    #    CI khong the "xanh" trong khi mot kich ban hong.
    print("RESULT:", "PASS" if dat == len(ra) else "FAIL")
    return 0 if dat == len(ra) else 1


if __name__ == "__main__":
    raise SystemExit(main())
