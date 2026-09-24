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
#:
#: ⭐ Tai xuat tu `ai.py` — mot nguon duy nhat cho ca nam thao tac AI.
from .ai import THU_TU_PROVIDER  # noqa: E402  (tai xuat co chu dinh)

PROVIDER_CHINH = THU_TU_PROVIDER[0]

#: 🔴 **`MODEL_THEO_PROVIDER = {"ltt_llm": "ltt_llm"}` DA BI GO — no la mot loi
#:    dang song, tim ra o pha 08.**
#:
#:    `ltt_llm` la **bi danh cong khai cua app**, khong phai id model. Do duoc:
#:    `providers.models_for("ltt_llm")` tra ve dung `qwen38-api` va
#:    `qwen38-vision`, khong co `ltt_llm`. Truyen bi danh vao thi `chon_key` nem
#:    `ThieuKeyError`, va `dieu_phoi.goi` doc do la *"provider nay khong phuc vu
#:    duoc, di tiep"* — tuc **bo qua provider trong im lang** roi nem
#:    `KhongCoProviderNao`.
#:
#:    Docstring cua `dieu_phoi.goi` da canh bao chinh xac dieu nay va ke ten hai
#:    nan nhan truoc: `platform_core/agent/planner.py` (moi luot lap ke hoach roi
#:    xuong Gemini du khai "model nha di truoc") va `tools/kiem_ltt_llm.py`. Ca
#:    hai hong **suot nhieu thang**. Day la nan nhan thu BA, va no khong bi phat
#:    hien vi giai doan dich van la engine gia tu pha 05 — chua goi that lan nao.
#:
#: ⇒ Nay hoi `ai.ban_do_model(ai.DICH_THUAT)`, tuc hoi registry. Ngay may B doi
#:   GGUF ben duoi, registry doi va ta di theo.
#:
#: ⭐ Bai hoc dang hon ca ba loi: **mot vi du trong docstring la ma ma nguoi ta
#:    chep**. No sai thi no khong sai mot minh.
MODEL_CHINH = ""     # ⛔ giu ten de nguoi doc cu tim thay ghi chu nay

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

    🔑 **Quy tac 5 (Han-Viet) them 24/09 vi CO BANG CHUNG, khong vi phong doan.**

       Ban NEN do tay 30 cau (`B2_DICH.md` §4.1): `小美` -> *Tieu My* ✅ (nhat
       quan ca 10 lan), `李宗盛` -> *Ly Tong Thanh* ✅, nhung `光子` -> ⛔
       **"Photon"** — dich nghia den sang tieng Anh. Luc do loi nhac co **bon**
       quy tac va **khong quy tac nao** noi ve ten rieng.
       ⇒ 2/3 dung la **may**, ⛔ khong phai mot hanh vi duoc bao dam.

    ⛔ Doi loi nhac PHAI keo theo `van_ban.PHIEN_BAN_LOI_NHAC` — no nam trong
       van tay, va thieu no thi lan chay dung lai ket qua sinh boi loi nhac CU.

    ⭐ Yeu cau tra ve JSON **khoa theo ma doan**. Do la thu lam phep gop tat
       dinh: khong phai doi chieu theo thu tu, khong phai doan xem doan nao
       ung voi doan nao, va thieu mot ma la mot dieu **do duoc** chu khong phai
       mot thu phai suy ra.
    """
    bang = {d["ma"]: d["chu"] for d in lo}
    # ⚠️ **Lời nhắc ghép THẲNG trong `{"role": …, "content": …}`, ⛔ không gán ra
    #    một biến trước.** `tools/check_i18n._la_tin_nhan_model` nhận một lời
    #    nhắc **theo HÌNH DẠNG** — nó leo qua `BinOp`/`JoinedStr` lên tới `Dict`
    #    có khoá `"role"`, nhưng ⛔ **không leo qua một phép gán**. Quy tắc 5 là
    #    câu đầu tiên ở đây có dấu tiếng Việt (bốn quy tắc cũ thuần ASCII), nên
    #    nó là câu đầu tiên chạm vào bánh cóc — và với `he_thong = (...)` thì bộ
    #    đếm coi nó là **chuỗi giao diện chưa bọc `_()`**.
    # ⛔ Và bọc `_()` ở đây sai theo hướng nguy hiểm: lời nhắc sẽ **đổi theo ngôn
    #    ngữ giao diện của khách** — một thiết lập hiển thị lặng lẽ đổi HÀNH VI
    #    dịch. Chính docstring của bộ đếm nói đúng điều đó.
    # ⇒ Viết đúng hình dạng nó nhận. ⚠️ Khoảng trống của bộ đếm (không leo qua
    #    phép gán) đã báo điều phối, ⛔ làn này không tự sửa công cụ dùng chung.
    return [
        {"role": "system", "content": (
            "Ban la mot dich gia phu de chuyen nghiep. Dich sang TIENG VIET tu "
            "nhien, dung van noi, giu nguyen y va giu nguyen sac thai cua nguoi "
            "noi.\n"
            "QUY TAC:\n"
            "1. Tra ve DUY NHAT mot doi tuong JSON, khoa la ma doan, gia tri la "
            "cau tieng Viet.\n"
            "2. Phai co DU moi ma duoc dua vao. Khong bo qua ma nao.\n"
            "3. Khong them giai thich, khong them ma moi.\n"
            "4. Giu do dai gan voi cau goc — ban dich se duoc doc thanh tieng va "
            "phai vua khung thoi gian cua no.\n"
            "5. TEN RIENG — hoi HAI cau, THEO THU TU:\n"
            "5.1 Ten nay DA CO loi viet quen trong tieng Viet chua? Neu CO thi "
            "dung DUNG loi quen do, bat ke no la nguoi, noi chon hay to chuc. "
            "Vi du: 首尔 -> Seoul, 东京 -> Tokyo, 北京 -> Bắc Kinh, "
            "上海 -> Thượng Hải, 李宗盛 -> Lý Tông Thịnh, 李小龙 -> Lý Tiểu Long, "
            "腾讯 -> Tencent, 华为 -> Huawei.\n"
            "5.2 Neu KHONG co loi quen, hoac ban khong chac, thi moi xet LOAI:\n"
            "  - nguoi hoac dia danh: phien AM HAN-VIET, CO DAU tieng Viet day "
            "du. Vi du: 张伟 -> Trương Vĩ, 小美 -> Tiểu Mỹ, 王芳 -> Vương Phương. "
            "KHONG dich nghia den, KHONG doi sang tieng Anh, KHONG bo dau.\n"
            "  - to chuc, thuong hieu, ten san pham: GIU NGUYEN DANG goc, "
            "KHONG phien am Han-Viet va KHONG dich nghia den.\n"
            "Mot ten xuat hien nhieu lan phai duoc xu ly GIONG NHAU o moi lan."
            + (f"\nNgon ngu nguon: {ngon_ngu_goc}." if ngon_ngu_goc else "")
        )},
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
    from . import ai

    ma_gui = {d["ma"] for d in lo}
    try:
        kq = ai.goi(db, ai.DICH_THUAT, _loi_nhac(lo, ngon_ngu_goc),
                    ctx=ctx, temperature=0.2)
    except ai.AiMoHo as exc:
        # ⛔ Mat ket noi SAU KHI da bat dau gui. Provider co the da nhan va da
        #    tinh tien. Doi thanh loi rieng cua mien dich de tang tren khong bao
        #    gio thu lai (I5/G7).
        raise DichMoHo(str(exc)) from exc

    return _doc_ban_dich(kq["noi_dung"], ma_gui)


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
