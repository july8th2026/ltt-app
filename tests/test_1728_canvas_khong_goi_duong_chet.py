"""Canvas **không được gọi** một endpoint mà bảng định tuyến thật không có.

## Lỗi đã xảy ra thật (23/09/2026)

`CanvasShell.tsx` chuyển sang mở workflow bằng cửa **v3** (`loadOrCreateWorkflowV3`,
bảng `workflow` + `workflow_draft`). Nhưng các nút *Assistant*, *Snapshot*,
*Share*, *Nhân workflow*, *Xuất mẫu* vẫn gọi cửa **v2**
(`/agent/api/workflows/{id}/...`, bảng `agent_workflows`). Hai cửa, **hai không
gian id**. Nên mọi nút ấy nhận `404` ngay lần bấm đầu — và không một phép kiểm
nào đỏ, vì mỗi bên nhìn riêng đều đúng.

⇒ Đây là lỗi ở **chỗ nối**, và chỗ nối là thứ không tệp nào sở hữu.

## Phép đo: TÊN HÀM NÀO VỚI TỚI ĐƯỢC TỪ GIAO DIỆN

`workflowApi.ts` cố ý còn giữ vài hàm v2 chết (Plan v1 gỡ sau). Một phép kiểm
chỉ `grep` đường dẫn trong cả tệp sẽ đỏ vì những hàm **không ai gọi** — và
người sau sẽ nới nó ra. Nên phép kiểm này đi theo **khả năng với tới**:

    goc   = tên được các tệp khác trong `src/**` import
    dong  = + tên mà một hàm đã với tới gọi trong thân nó
    do    = mọi đường dẫn `/agent/...` nằm trong thân các tên ấy

Hàm chết nằm ngoài bao đóng ⇒ không bị tính. Hàm chết được **nối lại** vào
giao diện ⇒ bị tính ngay lần import đầu tiên.

## ⭐ HAI bài, vì một bài không đủ

Bài 1 *"đường có trong bảng không"* **một mình sẽ không bắt được lỗi 23/09**:
`/agent/api/workflows/{id}/snapshots` **có** trong bảng. Nó `404` vì cái **id**
gửi vào thuộc không gian khác, chứ không vì đường vắng mặt. Một phép kiểm chỉ
có bài 1 sẽ báo xanh trên đúng ngày hỏng.

⇒ Bài 2 đo thứ thật sự hỏng: trình soạn nạp id từ cửa **v3**, nên **không một
  lời gọi với tới được nào** được phép trỏ vào không gian id **v2**
  (`/agent/api/workflows/...`). Hai bài cùng ở đây vì chúng dùng chung một bộ
  đo khả năng với tới.

## ⚠️ Phạm vi hẹp hơn lời tuyên bố

Phép này so **đường dẫn**, không so **phương thức**. Một `GET` vào một đường chỉ
nhận `POST` vẫn lọt.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
SRC = GOC / "frontend" / "agent-canvas" / "src"
API_TS = SRC / "workflowApi.ts"

#: Tiền tố route của app agent (`apps/agent/manifest.py::route_prefix`).
TIEN_TO = "/agent"

#: Đường dẫn trong nguồn TS: nằm trong nháy đơn / nháy kép / backtick.
_DUONG = re.compile(r"""['"`](/agent/[^'"`\s]*)""")

#: Chú thích. `workflowApi.ts` **nói về** các đường v2 trong chú thích (`/agent/**`,
#: "còn GUI được cho `/agent/api/workflows`") — nhắc tên một đường không phải là
#: gọi nó. Không cắt chú thích thì phép kiểm đỏ vì những câu văn, và người sau
#: sẽ nới nó ra cho tới khi nó không còn bắt được gì.
#:
#: `(?<!:)` giữ `https://...` nguyên vẹn: không có nó, một dòng có URL sẽ bị cắt
#: mất phần đuôi và một lời gọi thật có thể biến mất khỏi phép đo.
_CHU_THICH = re.compile(r"/\*.*?\*/|(?<!:)//[^\n]*", re.S)

#: Tiền tố của không gian id **v2** (`agent_workflows`). Trình soạn đã sang v3.
V2 = "/agent/api/workflows"
V3 = "/agent/api/v3/"
#: Khai báo ở cột 0 — ranh giới giữa hai "thân hàm".
_KHAI_BAO = re.compile(
    r"^(?:export\s+)?(?:async\s+)?(?:function|const|let|class)\s+(\w+)")
#: Tên đứng ngay trước `(`. Đòi ký tự kế tiếp không phải chữ/số để
#: `saveWorkflow` không khớp `saveWorkflowV3` (bẫy đã gặp ở test_970).
_GOI = re.compile(r"\b(\w+)\s*\(")
#: `import { a, b } from './workflowApi'` — cả `type X` lẫn `X`.
# 🔴 `(?:\.{1,2}/)+` chu KHONG phai `\.{1,2}/`.
#
#    Ban cu khop duoc `./workflowApi` va `../workflowApi` — dung khi MOI tep
#    con nam phang trong `src/`. Sau khi UI-3 tach `CanvasShell` xuong
#    `src/features/editor/hooks/`, duong import thanh `../../../workflowApi`
#    (ba cap), va bo do MU voi chung.
#
#    Do 28/09 tren cay that:
#        './workflowApi'        5 cho
#        '../workflowApi'       2 cho
#        '../../workflowApi'    7 cho   <- ban cu BO QUA
#        '../../../workflowApi' 17 cho  <- ban cu BO QUA
#    => 24/31 cho goi tro nen vo hinh; bo do chi con doc ra 2 duong (ca hai tu
#    `paletteApi.ts`, tep duy nhat con nam phang).
#
# ⭐ Va banh coc nay TU BAT DUOC minh da mu: `test_bai_2_KHONG_xanh_vi_canvas_rong`
#    va `test_phep_do_DOC_DUOC_du_nhieu_loi_goi` do ngay, thay vi de bo do im
#    lang bao "khong co duong chet nao". Mot cong tu kiem la mot cong dang tin.
_IMPORT = re.compile(
    r"import\s*\{([^}]*)\}\s*from\s*['\"](?:\.{1,2}/)+(?:src/)?workflowApi['\"]",
    re.S)


def chuan_hoa(duong: str) -> str:
    """`/a/${x}/b?q=1` -> `/a/{}/b`. Hai bên so với nhau ở cùng hình dạng."""
    duong = duong.split("?", 1)[0].split("#", 1)[0]
    duong = re.sub(r"\$\{[^}]*\}", "{}", duong)   # nội suy TS
    duong = re.sub(r"\{[^}]*\}", "{}", duong)     # tham số FastAPI
    return duong.rstrip("/") or "/"


def bo_chu_thich(nguon: str) -> str:
    """Xoá chú thích nhưng GIỮ NGUYÊN số dòng, để `tệp:dòng` còn tra được."""
    return _CHU_THICH.sub(lambda m: "\n" * m.group(0).count("\n"), nguon)


def _than_ham(nguon: str) -> dict[str, str]:
    """{tên khai báo ở cột 0: thân của nó cho tới khai báo kế tiếp}."""
    dong = nguon.splitlines()
    mocs: list[tuple[int, str]] = []
    for i, line in enumerate(dong):
        m = _KHAI_BAO.match(line)
        if m:
            mocs.append((i, m.group(1)))
    ra: dict[str, str] = {}
    for k, (i, ten) in enumerate(mocs):
        het = mocs[k + 1][0] if k + 1 < len(mocs) else len(dong)
        ra[ten] = "\n".join(dong[i:het])
    return ra


@pytest.fixture(scope="module")
def bang_dinh_tuyen() -> set[str]:
    """Bảng định tuyến THẬT của app đã dựng — thứ người dùng thật gặp."""
    from apps.agent.routes import router
    return {chuan_hoa(TIEN_TO + getattr(r, "path", "")) for r in router.routes}


@pytest.fixture(scope="module")
def duong_voi_toi_duoc() -> dict[str, list[str]]:
    """{đường dẫn: [nơi gọi]} cho mọi đường giao diện thật sự với tới được."""
    than = _than_ham(bo_chu_thich(API_TS.read_text(encoding="utf-8")))

    goc: set[str] = set()
    for tep in sorted(SRC.rglob("*.ts*")):
        if tep == API_TS:
            continue
        nguon = bo_chu_thich(tep.read_text(encoding="utf-8"))
        for khoi in _IMPORT.finditer(nguon):
            for phan in khoi.group(1).split(","):
                ten = phan.replace("type", " ").strip().split(" ")[-1].strip()
                if ten:
                    goc.add(ten)

    # Bao đóng: hàm đã với tới gọi ai thì người ấy cũng với tới được.
    toi = {t for t in goc if t in than}
    while True:
        them = {g for t in toi for g in _GOI.findall(than[t])
                if g in than and g not in toi}
        if not them:
            break
        toi |= them

    ra: dict[str, list[str]] = {}
    for ten in sorted(toi):
        for d in _DUONG.findall(than[ten]):
            ra.setdefault(chuan_hoa(d), []).append(f"workflowApi.ts::{ten}")
    # Tệp khác nếu tự gọi thẳng thì đường của nó luôn được tính.
    for tep in sorted(SRC.rglob("*.ts*")):
        if tep == API_TS:
            continue
        sach = bo_chu_thich(tep.read_text(encoding="utf-8"))
        for i, line in enumerate(sach.splitlines(), 1):
            for d in _DUONG.findall(line):
                ra.setdefault(chuan_hoa(d), []).append(f"{tep.name}:{i}")
    return ra


def test_moi_duong_giao_dien_goi_deu_co_trong_bang_dinh_tuyen(
        duong_voi_toi_duoc, bang_dinh_tuyen):
    """⛔ Giao diện không được mời người dùng làm một việc sẽ `404`."""
    gay = {d: noi for d, noi in sorted(duong_voi_toi_duoc.items())
           if d not in bang_dinh_tuyen}
    assert not gay, (
        "Giao dien goi endpoint KHONG CO trong bang dinh tuyen:\n"
        + "\n".join(f"  {d}   <- {', '.join(noi)}" for d, noi in gay.items())
        + "\nGo loi moi o giao dien, hoac mo lai duong o apps/agent/routes/.")


def la_khong_gian_v2(duong: str) -> bool:
    """`/agent/api/workflows/...` là v2; `/agent/api/v3/workflows/...` thì không.

    Tách bằng tiền tố **đầy đủ** chứ không bằng chữ `workflows`: hai đường chứa
    cùng một từ, và một bộ dò đọc `"workflows" in duong` sẽ báo cả hai.
    """
    return duong == V2 or duong.startswith(V2 + "/")


def test_khong_loi_goi_nao_con_tro_vao_khong_gian_id_v2(duong_voi_toi_duoc):
    """⛔ Bài 2 — thứ đã hỏng thật 23/09.

    Trình soạn nạp workflow qua `loadOrCreateWorkflowV3` (bảng `workflow`).
    Một lời gọi `/agent/api/workflows/{id}/...` sẽ tra id ấy trong
    `agent_workflows` và **không thấy** ⇒ `404` ở lần bấm đầu tiên.
    """
    gay = {d: noi for d, noi in sorted(duong_voi_toi_duoc.items())
           if la_khong_gian_v2(d)}
    assert not gay, (
        "Trinh soan nap id tu cua v3 nhung van goi cua v2 (se 404):\n"
        + "\n".join(f"  {d}   <- {', '.join(noi)}" for d, noi in gay.items())
        + "\nGo loi moi o giao dien, hoac chuyen cum ay sang `/agent/api/v3/`.")


def test_bo_phan_loai_TACH_duoc_v2_khoi_v3():
    """🔑 Đối chứng cho chính bài 2. Hai đường cùng chứa chữ `workflows`; một
    bộ dò đọc theo từ khoá sẽ báo cả đường v3 đang sống, và sẽ bị tắt đi."""
    assert la_khong_gian_v2("/agent/api/workflows/{}/snapshots")
    assert la_khong_gian_v2("/agent/api/workflows/import")
    assert not la_khong_gian_v2("/agent/api/v3/workflows/{}/publish")
    assert not la_khong_gian_v2("/agent/api/palette")


def test_bai_2_KHONG_xanh_vi_canvas_rong(duong_voi_toi_duoc):
    """🔑 Vế đối chứng: một `CanvasShell.tsx` rỗng cũng không gọi gì cả, và
    bài 2 sẽ xanh. Đòi cửa v3 phải THẬT SỰ có mặt mới tính là đã chuyển."""
    for song in ("/agent/api/v3/workflows/{}",
                 "/agent/api/v3/workflows/{}/publish",
                 "/agent/api/v3/workflows/{}/runs"):
        assert song in duong_voi_toi_duoc, (
            f"khong thay {song} — trinh soan chua that su di qua cua v3")


def test_phep_do_DOC_DUOC_du_nhieu_loi_goi(duong_voi_toi_duoc):
    """🔑 Vế đối chứng 1: một bộ dò hỏng đọc ra 0 đường và bài trên xanh.

    Số 0 không đối chứng thì không phải phát hiện — nó là dấu hiệu đọc nhầm.
    """
    assert len(duong_voi_toi_duoc) >= 8, (
        f"chi doc duoc {len(duong_voi_toi_duoc)} duong tu {SRC} - bo do hong?")


def test_mot_endpoint_CON_SONG_thi_khong_bi_bao(duong_voi_toi_duoc,
                                                bang_dinh_tuyen):
    """🔑 Vế đối chứng 2: đường v3 đang sống phải được đọc ra VÀ không bị báo.

    Không có vế này, một bộ dò báo *mọi thứ* cũng làm bài đầu "đúng" theo
    hướng ngược lại, và ai cũng sẽ tắt nó đi.
    """
    # ⚠️ `/agent/api/palette` (v2) DA RA khoi danh sach nay ngày 24/09: plan 02
    #    task 15 cắt Canvas sang `/agent/api/v3/palette`, nên đường v2 ấy không
    #    còn với tới được từ giao diện. Cửa máy chủ vẫn sống — nhưng bài này đo
    #    *"đường giao diện ĐANG gọi"*, không đo *"cửa còn mở"*. Thay bằng cửa
    #    palette v3, thứ giao diện thật sự gọi hôm nay (`paletteApi.ts`).
    for song in ("/agent/api/v3/workflows",
                 "/agent/api/v3/workflows/{}",
                 "/agent/api/v3/workflows/{}/publish",
                 "/agent/api/v3/palette"):
        assert song in duong_voi_toi_duoc, f"khong doc ra duong song {song}"
        assert song in bang_dinh_tuyen, f"{song} phai co trong bang dinh tuyen"


def test_bo_do_bat_duoc_mot_duong_CHET_duoc_tiem_vao(bang_dinh_tuyen):
    """🔑 Vế đối chứng 3: tiêm lỗi cũ. Đường v2 vừa gỡ phải bị bắt."""
    assert chuan_hoa("/agent/api/runs/${run.id}/tick") not in bang_dinh_tuyen
    # ⏭️ 24/09: `/snapshots` KHÔNG còn trong bảng định tuyến (P8 Task 5 đóng cả
    #    cụm v2 — `test_2934`). Thay bằng một cửa v2 **còn sống** mà giao diện
    #    v3 không gọi: vế đối chứng này cần một đường CÓ THẬT trong bảng, và ý
    #    nghĩa của nó không đổi.
    assert chuan_hoa("/agent/api/workflows/${id}") in bang_dinh_tuyen


def test_chuan_hoa_khop_hai_kieu_tham_so():
    """Nội suy TS `${x}` và tham số FastAPI `{x}` phải về cùng một hình dạng."""
    assert chuan_hoa("/agent/api/workflows/${workflow.id}/export") == \
        chuan_hoa("/agent/api/workflows/{workflow_id}/export")
    assert chuan_hoa("/agent/api/v3/runs/${runId}?sau=${sau}") == \
        "/agent/api/v3/runs/{}"
    assert chuan_hoa("/agent/api/palette") == "/agent/api/palette"


def test_bo_cat_chu_thich_GIU_loi_goi_va_GIU_so_dong():
    """🔑 Đối chứng cho bộ cắt chú thích: cắt quá tay thì một lời gọi thật biến
    mất khỏi phép đo, và phép kiểm im lặng đúng lúc cần nói."""
    mau = ("// noi ve '/agent/api/cu'\n"
           "const a = request('/agent/api/that')\n"
           "/* khoi\n   '/agent/api/cu2' */\n"
           "const b = 'https://x/y'\n")
    sach = bo_chu_thich(mau)
    assert "/agent/api/that" in sach
    assert "/agent/api/cu" not in sach and "/agent/api/cu2" not in sach
    assert "https://x/y" in sach, "`//` trong URL khong duoc coi la chu thich"
    assert len(sach.splitlines()) == len(mau.splitlines()), "lech so dong"


def test_bo_tach_than_ham_PHAN_BIET_duoc_hai_khai_bao():
    """Nếu bộ tách gộp cả tệp làm một thân, mọi đường chết đều 'với tới được'
    và phép kiểm đỏ vĩnh viễn — người sau sẽ nới nó ra."""
    mau = ("export function a() {\n  return '/agent/api/a'\n}\n"
           "export const b = () => request('/agent/api/b')\n")
    than = _than_ham(mau)
    assert set(than) == {"a", "b"}
    assert "/agent/api/a" in than["a"] and "/agent/api/b" not in than["a"]


# ── Bộ đo này ⛔ KHÔNG ĐƯỢC ÂM THẦM MÙ ─────────────────────────────────────────
#
# 🔴 Vì sao cần thêm hai bài dưới đây, khi tám bài trên đã xanh.
#
#    Bộ đo này ĐÃ mù một lần, và mù **im lặng**: UI-3 tách `CanvasShell` xuống
#    `features/editor/hooks/`, đường import thành ba cấp, và `_IMPORT` chỉ khớp
#    được một hoặc hai cấp. Nó tụt từ 22 tên hàm với tới được xuống **1** — bài
#    chính vẫn chạy mà ⛔ không còn canh gì.
#
#    Lần ấy ta biết **chỉ vì** hai bài đối chứng đỏ theo. Đó là may: hai bài ấy
#    được viết cho một mục đích khác (chống *"xanh vì tập rỗng"*), và chúng tình
#    cờ đủ nhạy. ⛔ Một lần may ⛔ không phải một cơ chế.
#
# ⚠️ Và mỗi lần kiến trúc frontend đổi lại là một cơ hội mù MỚI:
#      · UI-3   tách thư mục             -> import sâu hơn      (ĐÃ mù)
#      · UI-10a `React.lazy` + `import()` -> module chỉ nạp động
#    Lần sau sẽ là một cơ chế ta chưa nghĩ ra.
#
# ⇒ Hai bài dưới đây ⛔ không đo sản phẩm. Chúng đo **CHÍNH BỘ ĐO**, và mỗi bài
#   nhắm một loại mù khác nhau: một cái đo **hậu quả** (độ phủ tụt, bất kể cơ
#   chế), một cái đo **nguyên nhân đã biết** (một dạng import bộ đo không hiểu).


#: Sàn độ phủ. Đo 28/09/2026 trên `main` `b6a19a46`: **27** hàm với tới được
#: trên **28** hàm/const `export` của `workflowApi.ts`.
#:
#: ⭐ Đặt sàn thấp hơn số thật một khoảng rộng là CÓ Ý: bài này ⛔ không canh
#:    *"độ phủ phải đúng 27"* — một refactor hợp lệ có thể gộp hay tách vài hàm,
#:    và một sàn sát quá sẽ đỏ vì chuyện ⛔ không liên quan rồi bị nới ra cho tới
#:    khi vô dụng. Thứ nó canh là **một cú SỤP**: `22 -> 1` như lần UI-3.
SAN_DO_PHU = 20


def _ham_voi_toi_duoc() -> set[str]:
    """Tập tên hàm trong `workflowApi.ts` mà giao diện với tới được.

    ⚠️ Lặp lại logic của `duong_voi_toi_duoc` một cách CÓ Ý: hàm kia trả về
       *đường dẫn*, còn bài này cần *số HÀM*. Gọi hàm kia rồi đếm đường sẽ đo một
       đại lượng khác — hai hàm có thể cùng trỏ một đường, và một hàm có thể ⛔
       không chứa đường nào.
    """
    than = _than_ham(bo_chu_thich(API_TS.read_text(encoding="utf-8")))
    goc: set[str] = set()
    for tep in sorted(SRC.rglob("*.ts*")):
        if tep == API_TS:
            continue
        nguon = bo_chu_thich(tep.read_text(encoding="utf-8"))
        for khoi in _IMPORT.finditer(nguon):
            for phan in khoi.group(1).split(","):
                ten = phan.replace("type", " ").strip().split(" ")[-1].strip()
                if ten:
                    goc.add(ten)
    toi = {t for t in goc if t in than}
    while True:
        them = {g for t in toi for g in _GOI.findall(than[t])
                if g in than and g not in toi}
        if not them:
            break
        toi |= them
    return toi


def test_bo_do_KHONG_bi_mu_sau_mot_lan_refactor():
    """🔴 Đo **hậu quả**, nên nó bắt được MỌI cơ chế làm mù — kể cả cơ chế chưa
    ai nghĩ ra.

    Nếu bài này đỏ, ⛔ **đừng hạ `SAN_DO_PHU`**. Hãy hỏi: *đường import đã đổi
    dạng gì mà `_IMPORT` ⛔ không còn hiểu?* Lần trước câu trả lời là
    `'../../../workflowApi'` (ba cấp).
    """
    toi = _ham_voi_toi_duoc()
    assert len(toi) >= SAN_DO_PHU, (
        f"do phu cua bo do TUT xuong {len(toi)} ham (san {SAN_DO_PHU}). "
        "Bo do dang MU: bai chinh van chay ma khong con canh gi. "
        "DUNG ha san — kiem `_IMPORT` co con khop dang import hien tai khong; "
        "lan truoc la duong sau BA cap sau khi UI-3 tach thu muc. "
        f"Ham doc ra duoc: {sorted(toi)}")


#: `import('...workflowApi')` — dạng ĐỘNG. `_IMPORT` chỉ hiểu dạng TĨNH.
_IMPORT_DONG = re.compile(r"""import\s*\(\s*['"]([^'"]*workflowApi)['"]""")


def test_KHONG_ai_import_workflowApi_bang_import_DONG():
    """⚠️ Đo **nguyên nhân đã biết**, vì nó nói được cách sửa.

    `_IMPORT` chỉ khớp `import { x } from '...workflowApi'`. Một
    `await import('../../workflowApi')` sẽ **vô hình** với bộ đo — và làn UI-10a
    vừa đưa `React.lazy(() => import(...))` vào kho, nên khuôn ấy nay có tiền lệ
    và sẽ lan.

    ⭐ Bài này ⛔ KHÔNG cấm nạp động (nó là một kỹ thuật đúng, và UI-10a dùng nó
       để giảm byte thật). Nó chỉ đòi: **nếu dùng cho `workflowApi` thì sửa
       `_IMPORT` TRƯỚC** — nếu không, bộ đo mù mà ⛔ không ai biết.
    """
    thay: list[str] = []
    for tep in sorted(SRC.rglob("*.ts*")):
        nguon = bo_chu_thich(tep.read_text(encoding="utf-8"))
        for mo in _IMPORT_DONG.finditer(nguon):
            thay.append(f"{tep.relative_to(SRC).as_posix()} -> {mo.group(1)}")
    assert not thay, (
        "co noi import `workflowApi` bang `import()` DONG, ma `_IMPORT` chi hieu "
        "dang TINH ⇒ nhung loi goi trong do VO HINH voi bo do: "
        + " | ".join(thay)
        + ". Mo rong `_IMPORT` cho dang dong TRUOC, roi moi dung khuon nay.")
