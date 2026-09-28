"""Giai doan MEDIA_PREPARE — noi engine that gap xuong song thi hanh.

Tep nay chi lam mot viec: bien tep nguon cua khach thanh hai artifact chinh tac
va tra chung cho `thi_hanh.chay_giai_doan` promote. No **khong** ghi checkpoint,
**khong** cham vi tien, **khong** quyet dinh gi ve vong doi — nhung thu do thuoc
xuong song, va giu chung o mot cho la ly do tam giai doan sau se de noi vao.

Hai artifact ra:

    source_probe.json   ket qua soi + ket luan chinh sach   (kind=json)
    audio_full.wav      16 kHz mot kenh, vat lieu cho ASR    (kind=audio)

⭐ Ban goc KHONG bi cham. `audio_full.wav` la mot dong lineage MOI tro ve no.
   Mat ban goc la mat kha nang tinh lai moi thu ha nguon (Prompt 08 muc 4).

## 🔴 `media_prepare` KHONG cat gi — lan P0-c da DO va KHONG doi (28/09/2026)

De xuat: ap cua so `cat_dau_cuoi` cua khach o day, de ASR khong phai nghe phan
khach da bo. Do xong thi KHONG lam, va ba con so la ly do:

1. **Cua so la PHAN SO, khong phai giay** (`cat_dau_cuoi.py:11-14`). Phep doi
   sang giay o `cat_dau_cuoi.giao` nhan `thoi_luong` tu NGUOI GOI, va hom nay
   DUNG hai nguoi goi — `giai_doan_hinh_anh.py:369` (cat that) va
   `giai_doan_qc.py:271-275` (dung lai de biet do dai mong doi) — ca hai nhan do
   dai GD1. Them mot lan ap o day thi khai `[0,05 ; 0,95]` thanh 0,81 thay vi
   0,90, va **CA HAI cho van dong y voi nhau tren mot ban giao SAI** ⇒ QC T2
   lech 0 giay, khong phep kiem nao do. Do o `test_4973`.
2. **Nam module doc `run.source_key`** — ban goc, toan bo do dai. Nang nhat:
   RENDER (`giai_doan_ket_xuat.py:130`, `-c:v copy` HINH cua ban goc) va
   AUDIO_PREPARE (`giai_doan_am_thanh.py:67`, nhac nen tu ban goc). Cat mot dau
   chi o ban tieng ASR ⇒ loi thoai tieng Viet dat len hinh va nen lech dung
   `dau_cat` giay. Tap hop chot o `test_4975`.
3. **`giai_doan_chep_loi.py:104-107` chon ban tieng theo DUOI `.wav`**, khong
   theo truc. Nen ca phuong an nhe nhat (them mot artifact da cat, giu
   `audio_full.wav` dung nghia *full*) cung la mot xo so ve TRUC neu lam mot
   minh o tep nay. Do o `test_4976`.

⭐ Cai duoc do duoc va NHO: vat lieu ASR giam dung `1 - (den - tu)` = **10 %**
   tren bo moc that (`test_4977`). Co hoc cua phep cat thi tam thuong — cai chan
   la DAY DIEN TRUC, va no nam o nam tep giai doan khac.

⇒ Muon lam that thi mot lan duy nhat phai lam CA BA: bo mot trong hai cho ap cua
  so, bu `dau_cat` o bien ASR, va cho `_khoa_tieng_asr` biet truc. Khong lam mot
  minh o day.
"""
from __future__ import annotations

import hashlib
import io
import json
import tempfile
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, nhap_media


class ThieuNguon(nhap_media.MediaError):
    """Khoa nguon cua run khong doc duoc."""


def _duong_doc_duoc(kho: Storage, khoa: str, thu_muc: Path) -> str:
    """Duong dan tren dia cua mot artifact, tai ve neu kho khong o local.

    `LocalStorage` cho ra duong that nen khong ton gi. Voi R2 thi phai tai ve —
    ffmpeg/ffprobe can mot tep, va mot URL da ky co the het han giua chung mot
    lan chay dai.
    """
    duong = kho.local_path(khoa) if hasattr(kho, "local_path") else None
    if duong:
        return duong
    # ⛔ KHONG `dich.write_bytes(f.read())`. Do la ca video nguon nam trong RAM
    #    cua worker — va o day khong co tran 90 MB nao nhu o route: mot tep 2 GiB
    #    di qua duong tai len ben vung se toi thang cho nay.
    #
    # ⭐ Va no hong theo kieu te nhat: khong loi, khong cham, chi la may bat dau
    #    swap khi hai lan chay trung nhau.
    # 🔴 N-58 (26/09/2026): `thu_muc` CÓ THỂ chưa tồn tại. `giai_doan_thoi_gian.py`
    #    truyền một thư mục CON (`t{lô}_{mã}`) và ⛔ không tạo nó, nên `open(..., "wb")`
    #    ném `Errno 2` ở đoạn ĐẦU TIÊN — 3/3 lượt production chết ở đây.
    #    ⭐ `giai_doan_qc_do_luong.py:161` thì `tm.mkdir()` trước khi gọi ⇒ hợp đồng
    #    "người gọi phải tạo thư mục" chưa bao giờ được gác. Gác ở BIÊN, một lần.
    thu_muc.mkdir(parents=True, exist_ok=True)
    # 🔴 N-59: tên tệp phải DẪN XUẤT TỪ KHOÁ. Với tên cố định `nguon.bin`, hai khoá
    #    khác nhau vào cùng một thư mục ghi đè nhau — và `giai_doan_qc.py:130-131`
    #    làm đúng điều đó, khiến QC so bản ra với CHÍNH NÓ. Lỗi IM LẶNG.
    #    ⛔ Không ai phụ thuộc chuỗi "nguon.bin" (đã grep cả kho).
    dich = thu_muc / (hashlib.sha1(khoa.encode("utf-8")).hexdigest()[:16] + ".bin")
    with kho.open(khoa) as f, open(dich, "wb") as ra:
        while True:
            khoi = f.read(assets.KHOI_DOC)
            if not khoi:
                break
            ra.write(khoi)
    return str(dich)


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Soi -> thi hanh chinh sach -> tach tieng. Tra ve cac phan de promote.

    Nem `MediaError` khi dau vao khong dat chinh sach. Do la mot **that bai cuoi
    cung**, khong phai mot lan thu lai: mot tep khong co luong tieng se khong tu
    moc them mot luong tieng o lan thu hai.
    """
    if not run.source_key:
        raise ThieuNguon(_t('Phiên chạy không có tệp nguồn.'))

    hoi_huy = None
    if ctx is not None and getattr(ctx, "is_cancelled", None):
        hoi_huy = ctx.is_cancelled

    with tempfile.TemporaryDirectory(prefix="asv-media-") as tam:
        thu_muc = Path(tam)
        nguon = _duong_doc_duoc(kho, run.source_key, thu_muc)

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(10, _t('Đang đọc thông tin tệp'))

        tt = nhap_media.soi(nguon, hoi_huy=hoi_huy)
        # ⛔ Chinh sach chay TRUOC khi ton mot giay ffmpeg nao. Tu choi som la
        #    khac biet giua mot cau tra loi tuc thi va mot lan hoan tien.
        nhap_media.kiem_chinh_sach(tt)

        # ── Phan 1: ket qua soi ───────────────────────────────────────────
        cong_cu = nhap_media.phien_ban_ffmpeg()
        ho_so = dict(tt)
        ho_so["ffmpeg"] = cong_cu
        ho_so["contract"] = run.contract_version
        goi = json.dumps(ho_so, sort_keys=True, ensure_ascii=False).encode("utf-8")

        khoa_ho_so = assets.khoa_staging(
            owner_id=run.owner_id, run_id=run.id, stage="media_prepare",
            van_tay=assets.bam(goi)[:32], duoi="json")
        kho.put(khoa_ho_so, io.BytesIO(goi), content_type="application/json")

        # ── Phan 2: ban tieng cho ASR ─────────────────────────────────────
        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(40, _t('Đang tách tiếng'))

        # 🔑 Van tay cua ban tieng dua tren CHECKSUM TEP NGUON, khong phai ten
        #    hay khoa cua no (Prompt 08 muc 8). Hai tep cung ten khac noi dung
        #    phai ra hai van tay; mot ten tep khong noi len dieu gi ve noi dung.
        checksum_nguon = assets.bam_tep(nguon)
        vt_tieng = nhap_media.van_tay_chuan_hoa(checksum_nguon=checksum_nguon,
                                                phien_ban_cong_cu=cong_cu)
        wav = str(thu_muc / "audio_full.wav")
        nhap_media.tach_tieng_cho_asr(nguon, wav, hoi_huy=hoi_huy)

        khoa_tieng = assets.khoa_staging(
            owner_id=run.owner_id, run_id=run.id, stage="media_prepare",
            van_tay=vt_tieng, duoi="wav")
        with open(wav, "rb") as f:
            kho.put(khoa_tieng, f, content_type="audio/wav")

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(90, _t('Đang lưu kết quả'))

        return {
            "phan": [
                {"staging_key": khoa_ho_so, "kind": "json", "duoi": "json",
                 "van_tay": assets.bam(goi)[:32]},
                {"staging_key": khoa_tieng, "kind": "audio", "duoi": "wav",
                 "van_tay": vt_tieng},
            ],
            "tom_tat": {
                # V6 pha 25: danh tinh NOI DUNG cua nguon — `audio_prepare` doc
                # thang tep nay, va cache dung chung khoa theo no.
                "checksum_nguon": checksum_nguon,
                "thoi_luong": tt["thoi_luong"],
                "codec_video": tt["codec_video"],
                "doc": tt["doc"],
                "vfr": tt["vfr"],
                "ffmpeg": cong_cu,
            },
        }
