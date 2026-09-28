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

    ⛔ Doi loi nhac PHAI keo theo `van_ban.PHIEN_BAN_LOI_NHAC_DICH` — no nam trong
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


# ══════════════════════════════════════════════════════════════════════════════
#  B14/V3 — bon CUA PHAT HIEN muon tu D:\Viral (doi chieu 28/09, KHONG sua dich)
# ══════════════════════════════════════════════════════════════════════════════
#
# Chu du an chot 28/09/2026 (sau khi lan B14 dua bang doi chieu
# `docs/auto_scan_video_final/B14_SO_SANH_VIRAL/V3_DICH.md`): "Nhung gi Viral da
# do roi thi ta SU DUNG, khong can do lai." Cac nguong duoi day la NGUYEN BAN
# cua Viral (`D:\Viral\resources\app-src\ai_dich.py` / `dich_gemini_web.py`,
# CHI DOC, khong sua) — KHONG hieu chinh cho du lieu ASV. Ghi ro N cua phep do
# goc de nguoi sau biet no manh den dau, khong phai de doi lai do.
#
# Ca ba ham deu la CUA PHAT HIEN: goi noi chi tra ve co/dem, KHONG cat, KHONG tu
# viet lai cau cua khach. Noi goi (`giai_doan_noi_dung.chay`) danh dau vao
# `outputs`/`tom_tat` + `log.warning`, dung nhu han_lot da lam.


def cau_dich_phinh_bia(nguon: str, dich_ra: str) -> bool:
    """N4 — cau dich PHINH/BIA so voi nguon (AI "ke/bia" dai bat thuong).

    Muon NGUYEN cong thuc `ai_dich.py:1062-1077 _parse_lo` (chot 28/09, khong
    hieu chinh):

        n_nguon = so ky tu nguon (nguon la van ban TRUNG, dinh lien — moi ky tu
                  Han xap xi 1 tu, DEM KY TU chu KHONG dem theo dau cach)
        n_dich  = dich CO dau cach -> dem TU; dich KHONG dau cach -> dem KY TU
        PHINH khi  n_dich > n_nguon * 10  VA  so_ky_tu(dich) > tran

    ⭐ Hai dieu kien VA (khong phai HOAC): mot minh ti le bat oan cau nguon cuc
       ngan, mot minh nguong tuyet doi bat oan cau nguon dai.

    🔴 **Dich cua ta CHI co hai dich, ca hai deu La Tinh CO dau cach**
       (`ngon_ngu.DICH_HOP_LE = (vi, en)`) — nen o day CHI dung nhanh tuyet doi
       `>90 ky tu` cua Viral. Nhanh `>60` (dich CJK dinh lien, dung khi Viral
       dich sang ja/ko/zh) khong ap dung cho ta — giu lai trong ham de doi so
       dung, nhung nhanh do se khong bao gio duoc chon voi dich=vi/en.

    Doi chung AM (bat buoc — xem test): mot cau nguon DAI dich ra DAI TUONG XUNG
    (ti le duoi 10x) khong duoc gan co, du ban dich dai hon 90 ky tu.
    """
    src = str(nguon or "").strip()
    tgt = str(dich_ra or "").strip()
    if not tgt:
        return False
    n_nguon = max(1, len(src))
    co_khoang_trang = " " in tgt
    n_dich = len(tgt.split()) if co_khoang_trang else len(tgt)
    tran_ky_tu = 90 if co_khoang_trang else 60
    return n_dich > n_nguon * 10 and len(tgt) > tran_ky_tu


#: Ti le "don vi dich / don vi nguon" cua mot ban dich VIET TU NHIEN (khong ep
#: ngan). NGUYEN BAN Viral (`dich_gemini_web.py:155-184 tran_tu_dich`, dong 169:
#: "0.75 la muc no GIU DUOC nghia, khong bia ra"), do that tren **2 loai video
#: khac mat do** (SRT anime thoai ngan · SRT thuyet minh phim Trung — ti le nen
#: do duoc 0,70-0,79x tren ca hai). Chot 28/09 cua chu du an: dung NGUYEN, khong
#: hieu chinh.
TI_LE_DICH_TREN_NGUON = 0.75


def _dem_don_vi_nguon(nguon: str) -> int:
    """So don vi "am tiet nguon" de tinh tran THEO MAT DO (N5).

    Muon cach dem cua Viral (`dich_gemini_web.py:79 _RE_AM` — chi dem ky tu
    CJK/kana, KHONG dem ca cau vi tieng Han dinh lien khong co dau cach): nguon
    co chu CJK thi dem so ky tu CJK; nguon KHONG co CJK (nguon en/vi, trong hop
    dong `ngon_ngu.NGUON_HOP_LE`) thi dem tu theo dau cach.
    """
    from . import ngon_ngu

    s = str(nguon or "")
    n_cjk = sum(1 for k in s if ngon_ngu._la_cjk(k))
    if n_cjk:
        return n_cjk
    return max(1, len(s.split()))


def tran_do_dai_theo_nguon(giay: float, nguon: str, *, dich,
                           toc_doc_giong: float | None = None) -> int:
    """N5 — tran DO DAI THEO MAT DO NGUON, cong THEM tran vat ly da co.

    ⚠️ **Khac PHA voi `nan_cho_vua`**: cua cua no chay SAU TTS (do giay tieng
       THAT); cua nay chay TRUOC TTS, ngay khi ban dich vua sinh ra o
       `content_process` — chua co tieng nao ca, chi uoc tu MAT DO NGUON. Hai
       cua BO SUNG nhau, KHONG thay nhau: `nan_cho_vua` van la cua CUOI CUNG
       truoc khi giao, con cua nay bat som hon — giam so vong nan-cho-vua ton
       kem (`ngon_ngu.py` tu ghi lai cai gia thieu cua re nay: mot NHIP sai 34%
       lam **751/943 giay** cua giai doan GIONG la vong `rut_ngan_cho_vua`).

    Cong thuc NGUYEN BAN Viral (`tran_tu_dich`): `min(giay * wps_dich,
    so_am_tiet_nguon * 0.75)`.

    🔴 **`wps_dich` KHONG lay tu bang `_TU_MOI_GIAY` cua Viral** (ho do `vi` =
       5,00 tren giong edge-tts CUA HO) — tien de do SAI voi ta: may sinh tieng
       cua san pham nay la LTT Voice VieNeu-TTS v3, mot hang TTS khac han. Day
       KHONG phai "hieu chinh nguong 0,75" (phan do van GIU NGUYEN theo chot
       28/09) — chi rieng `wps` (toc do DOC) la mot dac tinh CUA GIONG, khong
       phai cua ban dich, nen no PHAI doi theo giong THAT cua ta. Dung
       `ngon_ngu.NHIP` — da do tren chinh giong that cua san pham (vi=3,35,
       23/09; en=3,63) — dung KIEU tien le da chot o
       `V3_DICH.md` hang 8 cho CUNG mot ly do (bang nhip cua Viral cung khong
       duoc lay vi khac TTS).

    `ngon_ngu.ngan_sach_do_dai` da la tran VAT LY (`giay * NHIP * 0,92`) — ham
    nay lay `min` voi tran THEO NGUON de duoc CA HAI, dung nhu cong thuc goc.

    ## `toc_doc_giong` — B17 §4.1, lan P0-a3 NOI DAY (tra no P0-a2)

    🔴 **Cho GOI THU HAI cua `ngon_ngu.ngan_sach_do_dai`.** Lan P0-a2 da noi
       `long_tieng.loi_nhac` (tran GHI vao loi nhac gui model); cho nay la
       tran DO DAI dung o cua PHAT HIEN N5 — `tran_vat_ly` truoc lan nay LUON
       la hang so ca-ngon-ngu `NHIP[dich]`, ⛔ khong biet giong nao dang doc.

    ⚠️ **⛔ Khong tu them mot nhanh `min` moi o day** — `ngon_ngu.ngan_sach_do_dai`
       da tu SIET MOT CHIEU (`nhip = min(NHIP[dich], toc_doc_giong)` khi so do
       hop le), nen chuyen tiep tham so nay xuong la DU: `tran_vat_ly` chi co
       the nho di hoac giu nguyen so voi khi `toc_doc_giong=None`, ⛔ khong bao
       gio lon hon — va vi `min(tran_vat_ly, tran_theo_nguon)` o cuoi ham la
       don dieu KHONG GIAM theo `tran_vat_ly`, tran CUOI CUNG cung ⛔ khong bao
       gio noi ra. `test_4964` tiem nghich xac nhan dieu nay.

    ⚠️ `None` (mac dinh) = ben goi khong biet giong ⇒ `ngan_sach_do_dai` roi ve
       hang so ca-ngon-ngu, dung HANH VI TRUOC lan nay — xem `test_4963`.
    """
    from . import ngon_ngu

    tran_vat_ly = ngon_ngu.ngan_sach_do_dai(giay, dich,
                                            toc_doc_giong=toc_doc_giong)
    n_nguon = _dem_don_vi_nguon(nguon)
    tran_theo_nguon = max(1, int(n_nguon * TI_LE_DICH_TREN_NGUON))
    return min(tran_vat_ly, tran_theo_nguon)


def vuot_tran_theo_nguon(*, giay: float, nguon: str, dich_ra: str, dich,
                         toc_doc_giong: float | None = None
                         ) -> tuple[bool, int, int]:
    """N5 — co PHAT HIEN cho MOT doan. Tra `(vuot, do_dai_dich, tran)`.

    ⛔ Cua PHAT HIEN thuan tuy: chi danh dau + dem, KHONG cat/sua ban dich —
       noi goi (`giai_doan_noi_dung.chay`) ghi con so nay vao outputs/tom_tat,
       khong dung no de chan hay viet lai gi ca.

    Doi chung AM (bat buoc — xem test): mot doan noi NHANH THAT (giay ngan so
    voi nguon nhieu ky tu, tuc `n_nguon` lon) co tran RONG hon tuong ung, nen
    mot ban dich TUONG XUNG voi nhip noi that van KHONG bi gan co.

    ⚠️ `toc_doc_giong` (lan P0-a3, xem `tran_do_dai_theo_nguon`) chi CHUYEN
       TIEP xuong — ⛔ **chua co ben goi that nao truyen gia tri khac `None`**:
       `giai_doan_noi_dung.chay:435` (cho GOI THAT DUY NHAT cua ham nay, xem
       `test_4965`) chua mang tham so nay, du no da co san `ho_so` trong pham
       vi (dung `ho_so["toc_doc_giong"]` nhu `long_tieng.loi_nhac` da lam o
       P0-a2). Day la NO CON LAI cua chuoi nay — ngoai pham vi so huu tep cua
       lan P0-a3 (chi `dich_thuat.py`), de lan ke noi.
    """
    tran = tran_do_dai_theo_nguon(giay, nguon, dich=dich,
                                  toc_doc_giong=toc_doc_giong)
    do_dai = len(str(dich_ra or "").split())
    return do_dai > tran, do_dai, tran


#: N6 — nguong PHAT HIEN GOP CAU (nhieu doan bi model nhet chung vao MOT khoa
#: JSON). NGUYEN BAN Viral (`dich_gemini_web.py:1366-1416
#: _bo_key_gop/_nguong_gop`), do that **27.139 cue / 90 video**: p50=29 ky tu,
#: p90=48, p99=63, p99,9=91, max=921. Chot 28/09 cua chu du an: dung NGUYEN,
#: khong hieu chinh cho du lieu ASV — 27.139 cue la mot bang chung manh hon
#: nhieu thu ta tu do duoc.
TRAN_GOP_CAU_TUYET_DOI = 200          # ky tu — khong cue LANH nao trong mau vuot
HE_SO_GOP_CAU_TUONG_DOI = 4           # x trung vi CUA CHINH LO


def danh_dau_gop_cau(do_dai_theo_ma: dict) -> set:
    """N6 — ma nao trong CUNG MOT LO co do dai bat thuong (dau hieu GOP CAU).

    `do_dai_theo_ma`: `{ma_doan: so_ky_tu_ban_dich}` cua DUY NHAT mot lo (khong
    phai ca video) — tran TUONG DOI so voi trung vi CUA CHINH LO, vi mot cau dai
    bat thuong trong mot lo thoai it khac han mot lo thoai nhieu.

    Ca hai dieu kien VA (giu dung cong thuc Viral): vuot tran TUYET DOI 200 ky
    tu VA vuot trung vi CUA LO nhan 4 lan.

    ⭐ Doi chung AM (bat buoc — xem test): mot lo ma MOI cau deu dai DEU NHAU
       (phim nhieu loi thoai, khong phai loi gop) khong bi gan co — moi gia tri
       gan trung vi cua chinh no nen khong vuot `trung_vi * 4`, mien la tung gia
       tri con duoi tran tuyet doi 200.
    """
    if not do_dai_theo_ma:
        return set()
    gia_tri = sorted(do_dai_theo_ma.values())
    n = len(gia_tri)
    trung_vi = (gia_tri[n // 2] if n % 2
                else (gia_tri[n // 2 - 1] + gia_tri[n // 2]) / 2)
    nguong_tuong_doi = trung_vi * HE_SO_GOP_CAU_TUONG_DOI
    return {ma for ma, do_dai in do_dai_theo_ma.items()
            if do_dai > TRAN_GOP_CAU_TUYET_DOI and do_dai > nguong_tuong_doi}
