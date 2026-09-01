"""Bo chuyen doi dich thuat: ban ghi -> tieng Viet, qua bo dieu phoi LLM nen tang.

## Vi sao goi `platform_core/llm/dieu_phoi.py` chu khong tu dung HTTP

`apps/ltt_llm/manifest.py` ghi thang: *"Goi qua `platform_core/llm/dieu_phoi.py`
— dung tu dung HTTP, do dung la loi ma `dieu_phoi` sinh ra de sua."* Bo dieu
phoi lo bon thu ma mot lop HTTP tu viet se phai lam lai va se lam sai:

  * chon khoa qua `api_pool` (tuc theo dung pham vi da chot o pha 07);
  * `on_dispatch` / `on_rejected` — ngu nghia dispatch BEN VUNG (I5);
  * `AmbiguousProviderError` khi mat ket noi **sau khi da bat dau gui**;
  * id model rieng cho tung provider (`model_theo_provider`).

## Vi sao KHONG uy quyen mot job `ltt_llm.chat`

ADR-001 D5 du dinh uy quyen. Sau khi trace hop dong that, uy quyen **khong lam
duoc viec o day**: giai doan nay phai chia lo, goi N lan, gop lai va phat hien
phan hoi thieu. Mot job `ltt_llm.chat` la MOT luot goi — khong co cho cho logic
do, va `asv_stage` cung chi giu mot `job_id` cho moi giai doan.

⭐ Nhung phan **quan trong** cua D5 van duoc giu, va do moi la thu D5 bao ve:
   ta khong tu dung duong HTTP thu hai, khong tu chon khoa, va an toan dispatch
   van la cua nen tang. Xem `docs/auto_scan_video/adr/ADR-001…md` va muc "Sua
   doi" trong bao cao pha 11.

## Khong co du phong provider im lang

⛔ Prompt 11 muc 8. `THU_TU_PROVIDER` chi co MOT ten. Doi model la doi chat
   luong ban dich — tuc doi san pham — va mot lan doi lang le nghia la khach
   nhan mot ban dich khac ma khong ai noi gi. Muon them provider thi phai them
   vao van tay truoc (`van_ban.van_tay_van_ban` da co `provider`+`model`), roi
   moi them vao day.
"""
from __future__ import annotations

import json
import logging

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

#: MOT provider. Xem ghi chu dau tep truoc khi them cai thu hai.
THU_TU_PROVIDER = ("ltt_llm",)
MODEL_THEO_PROVIDER = {"ltt_llm": "ltt_llm"}
PROVIDER_CHINH = THU_TU_PROVIDER[0]
MODEL_CHINH = MODEL_THEO_PROVIDER[PROVIDER_CHINH]

#: So doan toi da moi lo. Nho de mot phan hoi hong chi lam mat mot lo, va de
#: model giu duoc ngu canh; du to de khong bien mot ban ghi 200 doan thanh 200
#: luot goi.
#:
#: ⚠️ Day la mot con so CHUA DO tren du lieu that. No duoc chon de an toan chu
#:    khong de toi uu; pha 21 co the do lai.
DOAN_MOI_LO = 20

#: Tran token ra cho MOI lo. Xin theo ten cua, khong dung mot mac dinh chung.
#:
#: 🔴 CLAUDE.md ghi mot loi da xay ra that: cua stream muon ngan sach 1.024 cua
#:    cua dong bo, va **moi cau tra loi dai cut o dung 1.024 token, im lang**.
#:    Bai hoc la xin theo TEN CUA.
def _tran_token_ra() -> int:
    try:
        from apps.ltt_llm import ngan_sach
        return int(ngan_sach.mac_dinh_cho("job"))
    except Exception as exc:      # noqa: BLE001 - app kia co the chua nap
        # ⛔ PHAI GHI LOG, va day la mot vi du tu no chung minh vi sao.
        #
        #    Ban dau cho nay `return 4096` im lang. Nhung neu `mac_dinh_cho` co
        #    that su hong — chu khong phai chi la `ltt_llm` chua nap — thi ta
        #    lang le dich bang mot tran token TU BIA, va moi ban dich dai se cut
        #    o day. Do dung la loi 1.024-token ma chinh ghi chu ben tren vien
        #    dan, chi khac la lan nay ta tu gay ra no.
        log.warning("khong doc duoc tran token cua ltt_llm (%s: %s) — "
                    "dung so an toan %d", type(exc).__name__, exc, 4096)
        return 4096


class DichError(RuntimeError):
    """Dich that bai theo cach KHONG mo ho — thu lai duoc."""


class DichMoHo(RuntimeError):
    """Da co the goi toi provider roi mat ket noi.

    ⛔ **Khong bao gio thu lai** loi nay mot cach tu dong (I5/G7). Provider co
       the da nhan yeu cau va da tinh tien; thu lai la bien mot lan goi tra tien
       thanh hai.
    """


def _loi_nhac(lo: list[dict], ngon_ngu_goc: str) -> list[dict]:
    """Dung hoi thoai cho MOT lo. Tra ve dang `messages` cua OpenAI.

    ⭐ Yeu cau tra ve JSON **khoa theo ma doan**. Do la thu lam phep gop tat
       dinh: khong phai doi chieu theo thu tu, khong phai doan xem doan nao
       ung voi doan nao, va thieu mot ma la mot dieu **do duoc** chu khong phai
       mot thu phai suy ra.
    """
    bang = {d["ma"]: d["chu"] for d in lo}
    he_thong = (
        "Ban la mot dich gia phu de chuyen nghiep. Dich sang TIENG VIET tu nhien, "
        "dung van noi, giu nguyen y va giu nguyen sac thai cua nguoi noi.\n"
        "QUY TAC:\n"
        "1. Tra ve DUY NHAT mot doi tuong JSON, khoa la ma doan, gia tri la cau "
        "tieng Viet.\n"
        "2. Phai co DU moi ma duoc dua vao. Khong bo qua ma nao.\n"
        "3. Khong them giai thich, khong them ma moi.\n"
        "4. Giu do dai gan voi cau goc — ban dich se duoc doc thanh tieng va "
        "phai vua khung thoi gian cua no."
    )
    if ngon_ngu_goc:
        he_thong += f"\nNgon ngu nguon: {ngon_ngu_goc}."
    return [
        {"role": "system", "content": he_thong},
        {"role": "user", "content": json.dumps(bang, ensure_ascii=False)},
    ]


def chia_lo(doan: list[dict], *, moi_lo: int = DOAN_MOI_LO) -> list[list[dict]]:
    """Chia doan thanh lo, GIU NGUYEN thu tu.

    Giu thu tu vi lo la don vi ngu canh: mot doan doc cung nhung doan lien ke
    cua no thi dich sat hon la doc mot minh.
    """
    moi_lo = max(1, int(moi_lo))
    return [doan[i:i + moi_lo] for i in range(0, len(doan), moi_lo)]


def _doc_ban_dich(noi_dung: str, ma_da_gui: set[str]) -> dict:
    """Doc JSON model tra ve. Nem `DichError` neu khong doc duoc hoac thieu ma.

    Chap nhan ca khi model boc JSON trong ```: do la thoi quen rat pho bien cua
    model va no khong dang lam hong mot lan chay.
    """
    van = str(noi_dung or "").strip()
    if van.startswith("```"):
        van = van.split("```")[1] if "```" in van[3:] else van[3:]
        if van.lstrip().startswith("json"):
            van = van.lstrip()[4:]
    dau, cuoi = van.find("{"), van.rfind("}")
    if dau < 0 or cuoi < dau:
        raise DichError(_t('Model không trả về JSON đọc được.'))
    try:
        goc = json.loads(van[dau:cuoi + 1])
    except json.JSONDecodeError as exc:
        raise DichError(_t('Model trả về JSON hỏng.')) from exc
    if not isinstance(goc, dict):
        raise DichError(_t('Model trả về JSON sai hình dạng.'))

    ra = {str(k): str(v) for k, v in goc.items()
          if str(k) in ma_da_gui and str(v or "").strip()}
    thieu = ma_da_gui - set(ra)
    if thieu:
        # PHAN HOI KHONG DAY DU (Prompt 11 muc 4). Bao ra kem so luong de nguoi
        # doc log biet no thieu nhieu hay it — mot lo thieu mot ma va mot lo
        # thieu ca lo la hai tinh huong rat khac nhau.
        raise DichError(
            _t('Model thiếu bản dịch cho {n}/{tong} đoạn.').format(
                n=len(thieu), tong=len(ma_da_gui)))
    return ra


def dich_mot_lo(db, lo: list[dict], *, ngon_ngu_goc: str, ctx=None) -> dict:
    """Dich MOT lo. Tra ve `{ma: cau_dich}`.

    🔑 `on_dispatch`/`on_rejected` la ngu nghia dispatch ben vung cua nen tang
       (I5). Truyen thang tu `JobContext`: chung ghi `provider_state` xuong CSDL
       **ngay truoc** khi goi ra ngoai, nen mot lan sap sau do doc ra duoc la
       "co the da goi" chu khong phai "chua goi".
    """
    from platform_core.llm import dieu_phoi

    ma_gui = {d["ma"] for d in lo}
    try:
        kq = dieu_phoi.goi(
            db,
            messages=_loi_nhac(lo, ngon_ngu_goc),
            thu_tu_provider=THU_TU_PROVIDER,
            model_theo_provider=MODEL_THEO_PROVIDER,
            max_tokens=_tran_token_ra(),
            temperature=0.2,
            on_dispatch=(getattr(ctx, "provider_dispatched", None)
                         if ctx is not None else None),
            on_rejected=(getattr(ctx, "provider_rejected", None)
                         if ctx is not None else None),
        )
    except Exception as exc:      # noqa: BLE001 - phan loai roi nem lai
        if type(exc).__name__ == "AmbiguousProviderError":
            # ⛔ Mat ket noi SAU KHI da bat dau gui. Provider co the da nhan va
            #    da tinh tien. Doi thanh mot loi rieng de tang tren khong bao
            #    gio thu lai (I5/G7).
            raise DichMoHo(str(exc)) from exc
        raise

    return _doc_ban_dich(getattr(kq, "content", "") or "", ma_gui)


def dich_ban_ghi(db, ban_ghi_goc: dict, *, ctx=None) -> dict:
    """Dich ca ban ghi theo lo. Tra ve `{ma: cau_dich}` da gop.

    Gop TAT DINH: moi lo tra ve mot bang khoa theo ma, va cac bang duoc gop lai.
    Khong co phep doi chieu theo thu tu, nen mot lo tra ve lon xon cung khong
    lam lech ket qua.
    """
    doan = list(ban_ghi_goc.get("doan") or [])
    ngon_ngu = str(ban_ghi_goc.get("ngon_ngu") or "")
    cac_lo = chia_lo(doan)

    gop: dict = {}
    for i, lo in enumerate(cac_lo, start=1):
        if ctx is not None and getattr(ctx, "is_cancelled", None) and ctx.is_cancelled():
            raise DichError(_t('Phiên chạy đã bị huỷ giữa chừng.'))
        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(int(10 + 80 * i / max(1, len(cac_lo))),
                         _t('Đang dịch'))
        gop.update(dich_mot_lo(db, lo, ngon_ngu_goc=ngon_ngu, ctx=ctx))
    return gop
