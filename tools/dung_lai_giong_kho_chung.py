r"""
dung_lai_giong_kho_chung.py — dựng lại biểu diễn của giọng kho chung từ clip gốc
bền, GIỮ NGUYÊN `public_id` (W-KHO, sau deploy — `docs/LTT_VOICE/GUI_DOI_SOAT_VA_PLAN_V2.md`).

    C:\LTTPlatform\venv\Scripts\python.exe tools\dung_lai_giong_kho_chung.py
    C:\LTTPlatform\venv\Scripts\python.exe tools\dung_lai_giong_kho_chung.py --chay

## Vì sao cần

Bucket R2 xoá object quá ~7 ngày; nó đã xoá `source.wav` + `repr-*.npz` của 25
giọng kho chung (đo 15/09). Clip gốc còn nguyên, khớp SHA-256 từng byte, và đã
chép bền vào `<data_dir>\voice_goc\kho_chung\` (+ `manifest.json`).

## Vì sao KHÔNG đổi trạng thái hồ sơ

`jobs._ghi_danh::_ghi` coi một lượt chạy trên hồ sơ ĐÃ `active` là thành công
idempotent: khoá biểu diễn đặt theo sha của chính embedding — trùng khoá cũ thì
tệp vừa ghi KHÔI PHỤC đúng khoá dòng `VoiceRepr` cũ đang trỏ tới; khác khoá thì
dòng mới là biểu diễn mới nhất (`tim_repr_active` chọn dòng mới nhất). Không cần
lùi hồ sơ về `dang_ghi_danh` — thứ sẽ làm giọng biến mất khỏi bộ chọn giữa chừng.

## Hợp đồng

- Mặc định CHỈ LIỆT KÊ. `--chay` mới ghi kho + nộp job.
- TỪ CHỐI chạy khi `voice/` chưa định tuyến về đĩa (`LTT_STORAGE_LOCAL_PREFIXES`)
  — ghi lại lên R2 là mất lần nữa sau ~7 ngày. `--cho-phep-r2` để ép (không nên).
- Mỗi clip phải khớp `voice_ref.sha256` trước khi ghi; lệch là dừng cả lượt.
- Credit đi đúng sổ: `submit_with_credit` giữ `CREDIT_GHI_DANH`/giọng trên tài
  khoản CHỦ hồ sơ (tài khoản thử `.local` của kho chung).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def nap_env(duong: str) -> None:
    """Chỉ ĐẶT khoá chưa có — biến đã đặt trong phiên thắng tệp. Không in giá trị."""
    if not duong or not os.path.isfile(duong):
        return
    with open(duong, encoding="utf-8") as fh:
        for dong in fh:
            t = dong.strip()
            if t and not t.startswith("#") and "=" in t:
                k, v = t.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def ke_hoach(ho_so_ds, manifest: dict, doc_tep) -> list:
    """Thuần: [(public_id, owner_id, ref_id, source_key, sha)] + manifest ⇒ việc cần làm.

    Trả [(public_id, owner_id, ref_id, source_key, bytes)] hoặc ném `ValueError`
    nếu thiếu tệp / lệch sha — một clip sai là dừng cả lượt, không bỏ qua.
    """
    theo_ma = {g["public_id"]: g for g in manifest.get("giong", [])}
    ra = []
    for pid, owner, ref_id, source_key, sha in ho_so_ds:
        g = theo_ma.get(pid)
        if g is None:
            raise ValueError(f"{pid}: khong co trong manifest")
        du_lieu = doc_tep(g["tep"])
        that = hashlib.sha256(du_lieu).hexdigest()
        if that != sha or g.get("sha256") != sha:
            raise ValueError(f"{pid}: sha lech (tep {that[:12]}, csdl {str(sha)[:12]})")
        ra.append((pid, owner, ref_id, source_key, du_lieu))
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chay", action="store_true", help="ghi kho + nop job (mac dinh chi liet ke)")
    ap.add_argument("--cho-phep-r2", action="store_true",
                    help="ep chay khi voice/ con tren R2 (se mat lai sau ~7 ngay)")
    ap.add_argument("--app-env", default=r"C:\LTTPlatform\secrets\app.env")
    a = ap.parse_args(argv)
    nap_env(a.app_env)

    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile, VoiceRef
    from platform_core.db import get_session
    from platform_core.runtime_paths import resolve_runtime_paths
    from platform_core.storage import RoutedStorage, get_storage

    st = get_storage()
    cuc_bo = isinstance(st, RoutedStorage) and st.la_cuc_bo("voice/x")
    print(f"storage: {type(st).__name__} | voice/ tren dia: {cuc_bo}")
    if a.chay and not cuc_bo and not a.cho_phep_r2:
        print("DUNG: voice/ chua dinh tuyen ve dia (LTT_STORAGE_LOCAL_PREFIXES).")
        return 2

    goc = os.path.join(resolve_runtime_paths().data_dir, "voice_goc", "kho_chung")
    with open(os.path.join(goc, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)

    gen = get_session()
    db = next(gen)
    try:
        dong = db.execute(
            select(VoiceProfile.public_id, VoiceProfile.owner_id, VoiceRef.id,
                   VoiceRef.storage_key, VoiceRef.sha256)
            .join(VoiceRef, VoiceRef.profile_id == VoiceProfile.id)
            .where(VoiceProfile.dung_chung.is_(True),
                   VoiceProfile.trang_thai == "active")
            .order_by(VoiceProfile.ten_hien_thi)).all()

        def doc_tep(ten):
            with open(os.path.join(goc, ten), "rb") as fh:
                return fh.read()

        viec = ke_hoach([tuple(d) for d in dong], manifest, doc_tep)
        for pid, _o, _r, key, du_lieu in viec:
            co = st.exists(key)
            print(f"  {pid}  {len(du_lieu):9} byte  source {'CO' if co else 'THIEU'}  {key}")
        print(f"{len(viec)} giong khop sha256 voi manifest")
        if not a.chay:
            print("(chi liet ke - them --chay de ghi kho va nop job ghi danh)")
            return 0

        from apps.ltt_voice.manifest import MANIFEST
        from apps.ltt_voice.tham_so_cong_khai import SO_LAN_THU_JOB
        from platform_core.job_submit import dedupe_key_for, submit_with_credit
        from sqlalchemy import select as _select

        from platform_core.models import Job
        so_job = 0
        bo_qua = 0
        for pid, owner, ref_id, key, du_lieu in viec:
            khoa_trung = dedupe_key_for("ltt_voice.enroll",
                                        {"owner": str(owner), "voice_id": pid,
                                         "dung_lai": manifest.get("tao_luc", "")})
            # 🔴 16/09/2026: dedupe của `submit_with_credit` chỉ khớp job CHƯA kết
            #    thúc. Chạy lại sau khi vài giọng đã `done` thì nộp trùng và giữ
            #    credit lần nữa (đã xảy ra 1 job, huỷ + hoàn tay). Giọng đã dựng
            #    xong trong CÙNG lượt dựng lại (cùng khoá) thì bỏ qua.
            if db.execute(_select(Job.id).where(Job.dedupe_key == khoa_trung,
                                                Job.status == "done")).first():
                bo_qua += 1
                continue
            st.put(key, io.BytesIO(du_lieu), content_type="audio/wav")
            params = {"owner_id": str(owner), "voice_id": pid, "source_key": key,
                      "ref_id": int(ref_id), "nguon": "dung_lai_kho_chung",
                      "_job_type": "ltt_voice.enroll"}
            submit_with_credit(
                db, user_id=str(owner), app_slug=MANIFEST.slug,
                job_type="ltt_voice.enroll", params=params,
                dedupe_key=khoa_trung,
                max_attempts=SO_LAN_THU_JOB)
            db.commit()
            so_job += 1
        print(f"XONG: ghi {so_job} clip + nop {so_job} job ghi danh; "
              f"bo qua {bo_qua} giong da dung lai xong.")
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    sys.exit(main())
