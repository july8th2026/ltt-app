"""Ban khai cua Auto Scan Video — san pham KHACH NHIN THAY.

Ba app, mot san pham. Hai app kia (`asv_media`, `asv_gpu`) la executor an, khai
`surface="runtime"` + `catalog_parent="auto_scan_video"` nen chung khong tao the
catalog hay muc nav rieng. Ly do khong phai tham my: quyen nhat job duoc loc
theo **APP** (`platform_core/jobs.py:158-164`), nen mot app khai du ca ba nang
luc se chi chay duoc tren mot lan co du ca ba. Xem `pipeline.py` va ADR-001 D5.

⛔ CHUA MO CHO KHACH. `enabled=False` + `lifecycle="development"` +
   `public=False`. Prompt 05 cam ra mat cong khai, va `MVP_CONTRACT.md` van con
   bay giai doan chua co engine that.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest

#: Gia tam cho pha 05: chuoi giai doan van la job GIA, khong goi provider nao,
#: khong dung GPU. Mot gia khac 0 de duong tien duoc chay that (giu -> quyet
#: toan -> hoan), nhung du nho de mot lan thu nghiem khong ton gi dang ke.
#:
#: ⚠️ Bang gia THAT thuoc pha 21. Dat mot cong thuc "nhin cho giong that" o day
#:    la mot loi hua ma pha sau phai go.
#:
#: 🔴 MOT DIEU PHAI BIET TRUOC KHI VIET BANG GIA THAT (RISK-12-03).
#:
#:    `apps/ltt_voice/manifest.py:41 _gia()` uoc theo so ky tu **DA CHUAN HOA**,
#:    khong theo van ban tho. Vi du chinh no ghi: `"1.500.000 dong"` la 14 ky tu
#:    nhung doc ra `"mot trieu nam tram nghin dong"` — **no hon hai lan**.
#:
#:    Nen neu Auto Scan uoc chi phi TTS tu do dai ban dich THO, uoc luong se
#:    thap co he thong. Va uoc thap khong phai mot lech nho: `credit_held` be
#:    hon thuc te lam `features.kiem_tran_chi` **danh hong mot lan chay dang
#:    giua chung** — mot that bai chinh sach sach se, nhung la mot trai nghiem
#:    te hoan toan tranh duoc.
#:
#: ⇒ Uoc TTS phai dem tren `giong_noi.chuan_hoa_van_ban(...)`, dung ham da co.
#:
#: ⭐ Va luu y phan thu hai cua chinh docstring do: `ltt_voice` uoc bang **ky tu
#:    da chuan hoa** nhung quyet toan bang **giay tieng that su sinh ra** (do
#:    bang ffprobe). Do dung la ADR-001 D4 — do duoc, khong tinh lai — nen huong
#:    quyet toan cua ta da khop san voi ho.
GIA_THU_MOI_RUN = 1


def _gia(params: dict) -> int:
    """Gia cua job DIEU PHOI. Luon 0 — no khong lam viec tinh tien duoc.

    Tien cua ca lan chay duoc giu **mot lan tren `run.id`** trong
    `features.tao_run`, khong phai tren tung job. Neu ham nay tra ve mot so
    khac 0 thi moi luot `advance` — va no tu nop lai vai giay mot lan — se la
    mot lan tinh tien nua.
    """
    return 0


def _bao_tri() -> None:
    """Uy quyen cho `features.bao_tri`.

    ⛔ Import BEN TRONG ham, khong o dau tep: `manifest.py` duoc nap boi
       `registry.discover()` o moi tien trinh — ke ca nhung tien trinh khong bao
       gio chay viec nay — va keo ca `features` (kem SQLAlchemy, kho luu tru)
       vao do la bat moi worker tra gia nap cho mot ham no khong goi.
    """
    from .features import bao_tri

    bao_tri()


MANIFEST = AppManifest(
    slug="auto_scan_video",
    display_name=N_('Auto Scan Video'),
    route_prefix="/auto-scan-video",
    summary=N_('Lồng tiếng Việt cho video: giữ nguyên hình ảnh và độ dài, thay '
               'lời thoại gốc bằng giọng đọc tiếng Việt khớp thời điểm, giữ lại '
               'nhạc nền và tiếng động.'),
    icon="🎬",
    accent="#B45309",
    group=N_('Video'),

    #: Hai loai job, ca hai deu chi can `api`:
    #:   `advance`         — dieu phoi, chi doc/ghi CSDL va nop job con
    #:   `content_process` — goi model dich qua `platform_core/llm/dieu_phoi.py`
    #:
    #: ⭐ CONTENT nam o day chu khong o `asv_media` vi mot lan goi model khong
    #:    can ffmpeg. Xep no vao lan ffmpeg la giu mot suat co ffmpeg de ngoi
    #:    cho mang — mot suat khan hiem dung cho viec khong can no.
    job_types=("auto_scan_video.advance", "auto_scan_video.edit_plan",
               "auto_scan_video.content_process",
               #: QC bang AI — cung ly do voi CONTENT: mot lan goi model khong
               #: can ffmpeg. MAC DINH TAT (`LTT_ASV_QC_AI`), xem
               #: `giai_doan_qc_ai`.
               "auto_scan_video.qc_ai"),
    requires=("api",),

    #: 🔑 Bo quet han luu tru. Xem `features.bao_tri` va `assets.quet_het_han`:
    #:    truoc pha 27 `expires_at` duoc GHI vao moi artifact va khong cau lenh
    #:    nao doc no de xoa.
    #:
    #: ⚠️ Mot gio la mac dinh cua hop dong va no dung o day: chu ky la 30 NGAY,
    #:    nen quet day hon khong don duoc them gi, chi ton them mot luot doc.
    bao_tri=_bao_tri,
    credit_cost=_gia,

    max_runtime_s={
        #: Job dieu phoi tu nop lai moi ~2 giay khi run con song, nen no phai
        #: nhanh. Tran nay bat mot luot advance treo thay vi de no giu suat mai mai.
        "auto_scan_video.advance": 120,
        #: Dich chia lo, moi lo mot luot goi model. Mot ban ghi dai co the la
        #: hang chuc luot, nen tran phai rong hon nhieu.
        "auto_scan_video.content_process": 3600,
        #: QC ngu nghia cung chia lo va cung goi model moi lo. It luot hon
        #: `content_process` (soat ngan hon dich) nhung cung bac do lon, nen
        #: dung mot nua chu khong dung mot con so nho tuy tien.
        "auto_scan_video.qc_ai": 1800,
    },

    #: ⚠️ KHONG khai `admission_resource` o day — `AppManifest` khong co truong
    #:    do (`platform_core/registry.py:131` cho thay no thuoc `ToolSpec`).
    #:    Tai nguyen admission duoc chup **luc nop job**, trong
    #:    `jobs._nop_giai_doan_san_sang`, vi no la thuoc tinh cua mot lan chay
    #:    chu khong phai cua ca app.

    table_prefix="asv",

    # ── Chua mo ────────────────────────────────────────────────────────────
    enabled=False,
    public=False,

    #: ⭐ `customer` tu pha 20 — app da co `routes.py` that.
    #:
    #: 🔴 Truoc do no la `runtime`, va ly do van dung nguyen: `apps/ltt_llm` khai
    #:    `surface="customer"` khi CHUA co `routes.py`, va `nav_entries()` **tu
    #:    sinh** mot dong nav mac dinh (khai `nav=()` KHONG co nghia la "khong co
    #:    nav"). Moi khach da dang nhap thay mot link chet vao 404 suot nhieu tuan.
    #:
    #: ⚠️ Va `enabled=False` khong cuu duoc: `visible_on_surface` khong doc
    #:    `enabled` mot lan nao (`platform_core/registry.py:863-874`).
    #:
    #: `tests/test_413` chot HAI CHIEU — co routes ma con `runtime` la do (san
    #: pham khong hien o dau, hong IM LANG), va `customer` ma khong co routes
    #: cung do (link chet).
    surface="customer",
    lifecycle="development",
    capabilities=("video",),
    notes="Pha 05: mach doc GIA, chua co engine that. Khong mo cho khach.",
)
