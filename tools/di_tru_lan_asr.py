r"""
di_tru_lan_asr.py — D003: đo lại làn giọng cũ ("mac_dinh_cu") bằng ASR.

## Vì sao công cụ này tồn tại

Migration `20260911_1000_voice_ngon_ngu_nguon` gắn `ngon_ngu_nguon = "mac_dinh_cu"`
cho MỌI dòng `voice_profile` đang có, vì `ngon_ngu` của chúng là một MẶC ĐỊNH
cột — chưa ai khai, chưa ai đo (xem `apps/ltt_voice/giong_vong_doi.py`). Một
giọng nhân bản tên tiếng Anh nhưng `ngon_ngu = "vi"` (mặc định cột) là chuyện
thật — công cụ này ĐO lại bằng ASR trên chính clip nguồn, và chỉ sửa khi đo đủ
tin.

## Cách chạy

    python tools/di_tru_lan_asr.py                      # CHẠY KHÔ — chỉ in, không ghi
    python tools/di_tru_lan_asr.py --ghi                 # ghi thật vào CSDL
    python tools/di_tru_lan_asr.py --dao tmp/nk.json      # đảo lại từ một nhật ký đã ghi

**Mặc định CHẠY KHÔ.** Chỉ `--ghi` mới ghi vào CSDL. Mỗi lượt `--ghi` ghi một
nhật ký JSON (`--nhat-ky`, mặc định `tmp/di_tru_lan_asr_nk.json`) TRƯỚC khi ghi
CSDL — `--dao <nhat_ky.json>` đọc lại nhật ký đó và khôi phục `ngon_ngu` +
`ngon_ngu_nguon` về giá trị cũ.

Chỉ xét hồ sơ `ngon_ngu_nguon == mac_dinh_cu` và `trang_thai != revoked` (giọng
đã thu hồi không còn clip nguồn để đo).

## ASR — đúng khuôn `tools/soi_kho_giong_cu.py::_nghe_lai`

Subprocess vào venv NỀN TẢNG (`LTT_PLATFORM_PYTHON`, mặc định
`C:\LTTPlatform\venv\Scripts\python.exe`), `faster_whisper.WhisperModel(...,
device='cpu', compute_type='int8')` — CỘNG `cpu_threads=<--luong, mặc định 4>`.

⚠️ Máy 10 lõi vật lý DÙNG CHUNG cho nhiều phiên (xem CLAUDE.md gốc). Không đặt
`cpu_threads` thì `ctranslate2` mặc định chiếm MỌI lõi cho một clip — công cụ
vận hành không được làm vậy trên máy chia sẻ. Xử lý TUẦN TỰ, một clip một lần —
không song song hoá vòng lặp này.

⛔ Sẽ chỉ chạy THẬT trên production ở thời điểm phát hành (Tier 2 của RC1) —
KHÔNG chạy ở task này.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.ltt_voice import giong_vong_doi

#: Nhãn ASR (`faster_whisper` `info.language`) -> làn sản phẩm hỗ trợ. Chỉ hai
#: làn `lan_ngon_ngu.LAN_HOP_LE` biết tới — đo ra bất cứ nhãn nào khác (`fr`,
#: `zh`, ...) là NGOÀI làn, và công cụ này giữ nguyên, không tự bịa một làn thứ ba.
LAN_DO = {"vi": "vi", "en": "en"}

#: Mặc định `--luong` khi `_do_mot` gọi ASR mà không qua `chay()`/`main()` (vd
#: gọi tay trong một REPL). `chay()` ghi đè giá trị này TRƯỚC khi xử lý bất cứ
#: hồ sơ nào, theo `--luong` của lượt chạy đó.
_LUONG_MAC_DINH = 4


def quyet_lan(do: dict, *, lan_hien: str, nguong: float) -> tuple[str, str]:
    """`do` (kết quả `_nghe_lai`) -> `(lan_moi, nguon_moi)`.

    Trả `("", "")` khi KHÔNG đổi gì — ASR hỏng (`do["loi"]`), đo ra một làn
    ngoài `LAN_DO`, hoặc độ tin dưới `nguong`. `lan_hien` chỉ có ở đây để giữ
    đúng chữ ký giao diện (Task 4/D003 dùng nó ở `khai_lan_hop_le`); quyết định
    ASR không cần so sánh với làn hiện có — đo thấp hơn ngưỡng thì giữ nguyên
    bất kể làn hiện tại là gì.
    """
    if do.get("loi"):
        return "", ""
    lan = LAN_DO.get(str(do.get("ngon_ngu") or ""))
    if not lan or float(do.get("do_tin") or 0) < nguong:
        return "", ""
    return lan, giong_vong_doi.NGUON_DO_ASR


def _nghe_lai(duong: str, *, luong: int) -> dict:
    """`{ngon_ngu, do_tin, text}` hoặc `{loi}` — gọi ASR ở venv NỀN TẢNG.

    Y HỆT khuôn `tools/soi_kho_giong_cu.py::_nghe_lai` — cùng một model ASR
    gần 1 GB không nên tồn tại hai bản trên cùng một máy — CỘNG `cpu_threads`
    vào `WhisperModel(...)` vì máy này dùng CHUNG.
    """
    py = os.environ.get("LTT_PLATFORM_PYTHON",
                        r"C:\LTTPlatform\venv\Scripts\python.exe")
    if not os.path.isfile(py):
        return {"loi": f"khong thay {py}"}
    ma = (
        "import sys,json\n"
        "from faster_whisper import WhisperModel\n"
        "m=WhisperModel(sys.argv[2], device='cpu', compute_type='int8',\n"
        "               cpu_threads=int(sys.argv[3]))\n"
        # language=None => de Whisper TU DO ngon ngu. Do la ca muc dich.
        "seg,info=m.transcribe(sys.argv[1], beam_size=5,\n"
        "                      condition_on_previous_text=False)\n"
        "t=' '.join(s.text for s in seg)\n"
        "print(json.dumps({'lang':info.language,'p':info.language_probability,\n"
        "                  'text':t}))\n"
    )
    try:
        r = subprocess.run([py, "-c", ma, duong,
                            os.environ.get("LTT_ASR_MODEL", "small"),
                            str(int(luong))],
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=600)
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"loi": f"{type(e).__name__}: {e}"}
    if r.returncode != 0:
        return {"loi": (r.stderr or "")[-200:]}
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
        return {"ngon_ngu": d["lang"], "do_tin": round(float(d["p"]), 3),
                "text": (d["text"] or "").strip()}
    except (ValueError, IndexError, KeyError) as e:
        return {"loi": f"khong doc duoc ket qua ASR: {e}"}


def _tim_khoa_nguon(db, ho_so) -> str:
    """Khoá `platform_core.storage` của clip nguồn MỚI NHẤT của `ho_so`.

    Một hồ sơ có thể có nhiều `VoiceRef` (gửi lại clip khác cho cùng giọng —
    xem `apps/ltt_voice/jobs.py::_ghi_danh`, ràng buộc `(profile_id, sha256)`
    duy nhất). Lấy bản MỚI NHẤT vì đó là clip đang đại diện cho giọng hôm nay.
    """
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceRef

    r = db.execute(
        select(VoiceRef.storage_key)
        .where(VoiceRef.profile_id == int(ho_so.id))
        .order_by(VoiceRef.id.desc())
    ).scalars().first()
    return str(r or "")


def _do_mot(db, ho_so) -> dict:
    """Đo làn của CLIP NGUỒN của `ho_so` bằng ASR.

    Tìm khoá clip nguồn (`_tim_khoa_nguon`), tải về một tệp tạm qua
    `platform_core.storage.get_storage()` (cùng khuôn `jobs._ghi_danh`), rồi
    gọi `_nghe_lai`. Không có clip nguồn hay không đọc được kho ⇒ trả `{loi}`,
    KHÔNG ném — một hồ sơ đo hỏng không được làm dừng cả lượt di trú.
    """
    khoa = _tim_khoa_nguon(db, ho_so)
    if not khoa:
        return {"loi": "khong co clip nguon (VoiceRef) cho ho so nay"}

    from platform_core.storage import StorageError, get_storage

    st = get_storage()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        try:
            with st.open(khoa) as f:
                tmp.write(f.read())
            tmp.close()
        except StorageError as e:
            tmp.close()
            return {"loi": f"khong doc duoc kho ({khoa}): {e}"}
        return _nghe_lai(tmp.name, luong=_LUONG_MAC_DINH)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def chay(*, ghi: bool, nguong: float, nhat_ky, luong: int = 4) -> dict:
    """Chạy một lượt di trú. `ghi=False` (mặc định) là CHẠY KHÔ: không ghi CSDL,
    không ghi nhật ký. `ghi=True` ghi nhật ký JSON TRƯỚC khi commit CSDL.

    Trả `{"xet", "se_doi", "da_ghi", "khong_chac"}`.
    """
    global _LUONG_MAC_DINH
    _LUONG_MAC_DINH = int(luong)

    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        ho_so_list = db.execute(
            select(VoiceProfile).where(
                VoiceProfile.ngon_ngu_nguon == giong_vong_doi.NGUON_MAC_DINH_CU,
                VoiceProfile.trang_thai != giong_vong_doi.TT_REVOKED,
            )
        ).scalars().all()

        xet = se_doi = da_ghi = khong_chac = 0
        muc_nk = []
        for hs in ho_so_list:
            xet += 1
            do = _do_mot(db, hs)
            lan_moi, nguon_moi = quyet_lan(do, lan_hien=hs.ngon_ngu, nguong=nguong)
            if not lan_moi:
                khong_chac += 1
                print(f"  {hs.public_id}  giu nguyen ({hs.ngon_ngu})  "
                      f"do={do.get('ngon_ngu', '?')}/{do.get('do_tin', do.get('loi', '?'))}")
                continue

            se_doi += 1
            print(f"  {hs.public_id}  {hs.ngon_ngu} -> {lan_moi}  "
                  f"(do_tin={do.get('do_tin')}, nguon={nguon_moi})"
                  + ("  [GHI]" if ghi else "  [chay kho]"))
            if not ghi:
                continue

            muc_nk.append({
                "public_id": hs.public_id,
                "cu": {"ngon_ngu": hs.ngon_ngu, "ngon_ngu_nguon": hs.ngon_ngu_nguon},
                "moi": {"ngon_ngu": lan_moi, "ngon_ngu_nguon": nguon_moi},
                "do": do,
            })
            hs.ngon_ngu = lan_moi
            hs.ngon_ngu_nguon = nguon_moi
            da_ghi += 1

        if ghi and muc_nk:
            duong = pathlib.Path(nhat_ky)
            duong.parent.mkdir(parents=True, exist_ok=True)
            # write_bytes, KHONG write_text: pathlib doi \n thanh \r\n tren
            # Windows tru khi truyen newline="" — ghi bytes UTF-8 tranh han.
            duong.write_bytes(
                json.dumps(muc_nk, ensure_ascii=False, indent=2).encode("utf-8"))

        if ghi:
            db.commit()
        else:
            db.rollback()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    return {"xet": xet, "se_doi": se_doi, "da_ghi": da_ghi, "khong_chac": khong_chac}


def dao(nhat_ky) -> dict:
    """Đảo ngược một nhật ký đã ghi bởi `chay(ghi=True, ...)`: khôi phục
    `ngon_ngu`/`ngon_ngu_nguon` của mỗi hồ sơ trong nhật ký về giá trị `cu`.

    Trả `{"da_dao": <so ho so>}`.
    """
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.db import get_session

    muc = json.loads(pathlib.Path(nhat_ky).read_text(encoding="utf-8"))

    gen = get_session()
    db = next(gen)
    try:
        da_dao = 0
        for m in muc:
            hs = db.execute(
                select(VoiceProfile)
                .where(VoiceProfile.public_id == m["public_id"])
            ).scalar_one_or_none()
            if hs is None:
                continue
            cu = m.get("cu") or {}
            hs.ngon_ngu = str(cu.get("ngon_ngu", hs.ngon_ngu))
            hs.ngon_ngu_nguon = str(cu.get("ngon_ngu_nguon", hs.ngon_ngu_nguon))
            da_dao += 1
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    return {"da_dao": da_dao}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="D003: do lan giong cu (mac_dinh_cu) bang ASR. Mac dinh CHAY KHO.")
    ap.add_argument("--ghi", action="store_true",
                    help="Ghi that vao CSDL (mac dinh: chi in, khong ghi).")
    ap.add_argument("--dao", metavar="NHAT_KY_JSON",
                    help="Dao lai tu mot nhat ky da ghi boi --ghi.")
    ap.add_argument("--nguong", type=float, default=0.90,
                    help="Do tin ASR toi thieu de sua (mac dinh 0.90).")
    ap.add_argument("--luong", type=int, default=4,
                    help="cpu_threads cho WhisperModel (mac dinh 4 — may dung chung).")
    ap.add_argument("--nhat-ky", default="tmp/di_tru_lan_asr_nk.json",
                    help="Duong ghi nhat ky JSON (chi dung khi --ghi).")
    a = ap.parse_args(argv)

    if a.dao:
        ket = dao(a.dao)
        print(f"Da dao {ket['da_dao']} ho so tu {a.dao}")
        return 0

    print(f"D003 — do lan giong cu bang ASR ({'GHI THAT' if a.ghi else 'CHAY KHO'}, "
          f"nguong={a.nguong}, luong={a.luong})")
    ket = chay(ghi=a.ghi, nguong=a.nguong, nhat_ky=a.nhat_ky, luong=a.luong)
    print("=" * 60)
    print(f"  Xet: {ket['xet']}   Se doi: {ket['se_doi']}   "
          f"Da ghi: {ket['da_ghi']}   Khong chac: {ket['khong_chac']}")
    if not a.ghi and ket["se_doi"]:
        print(f"  (CHAY KHO — dung --ghi de ghi that. Nhat ky se o {a.nhat_ky})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
