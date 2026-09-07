# 00 — RUNTIME TRUTH (2026-09-05)

## OBSERVED

Triệu chứng được báo: *"kho ghi 100.000 nhưng giao diện hiện 1500"*.

Đo thật, theo thứ tự nguồn chân lý (runtime → source → docs):

| Thứ | EXPECTED | SOURCE (`admin-mvp-v3`) | DEPLOYED (`C:\LTTPlatform\app`) | BROWSER NHẬN | STATUS |
|---|---|---|---|---|---|
| git SHA | `72a484c5` | `72a484c5` | *không phải kho git* | — | ⛔ không hỏi được |
| `TRAN_KY_TU_CONG_KHAI` | 100.000 | **100.000** | **1.500** | 1.500 | ⛔ LỆCH |
| `TRAN_MOI_LUOT_SINH` | 1.500 | 1.500 | 1.500 | — | ✅ |
| `voice.js` md5 | — | `ddb12423…` | `7ace0b84…` | **`7ace0b84…`** | ⛔ LỆCH |
| `voice.js` cỡ | — | 91.281 B | 79.040 B | 79.040 B | ⛔ thiếu 12 KB |
| Studio `maxlength` | không có | không có | `{{ tran_ky_tu }}` | 1500 | ⛔ LỆCH |
| Studio ô đếm | `0 / 100.000` | `0 / 100.000` | `0 / 1500` | `0 / 1500` | ⛔ LỆCH |

Nhánh: `master` ↔ `admin-mvp-v3` = **0 sau / 94 trước**, merge-base `d225a480`.

## ROOT CAUSE

**Bản deploy đứng ở thời `master`.** Không phải cache — bằng chứng phân biệt được
hai giả thuyết ấy là md5 của `/static/voice.js` mà máy chủ **phục vụ** khớp
**chính xác** bản trên đĩa ở `C:\LTTPlatform\app`, không khớp bản trong kho. Nếu
là cache (trình duyệt hay Cloudflare) thì bản trên đĩa đã phải mới còn bản phục
vụ mới cũ; ở đây cả hai cùng cũ.

⭐ Điều đáng ghi không phải "quên deploy". Là: **không có chỗ nào hỏi được máy
chủ đang chạy mã nào.** `/health/version` khi ấy trả `"v1.0"` — đọc từ
`version.py` của *LTTStudios VideoBot*, một hằng số gõ tay từ 2025 không đổi qua
bất kỳ lần deploy nào. Nên câu hỏi chỉ trả lời được bằng cách so md5 hai thư mục
bằng tay, và đó là lý do nó tốn gần trọn một buổi.

## DECISION

1. **Không sửa gì cho khớp triệu chứng.** Mã nguồn đã đúng; thứ sai là bản đang
   chạy. Hạ `TRAN_KY_TU_CONG_KHAI` hay đụng vào template để "hết hiện 1500" là
   sửa cái bóng.
2. **Dựng dấu vân tay runtime** để lớp lỗi này không bao giờ còn vô hình.
   `/health/version` nay trả ba trường bắt **ba kiểu trôi độc lập**:

   | trường | bắt kiểu trôi |
   |---|---|
   | `commit` | mã nguồn (bản deploy cũ hơn kho) |
   | `asset_ver` | tài sản tĩnh (Cloudflare giữ CSS/JS cũ) |
   | `hop_dong` | hợp đồng (trần sản phẩm nói một đằng, chạy một nẻo) |

   Gộp thành một trường thì không phân biệt được — mà phân biệt chính là toàn bộ
   giá trị của nó.
3. **Deploy** nhánh đã QA. Xem `07_RELEASE_REPORT.md`.

## 🔴 BẢN VÁ ĐẦU PHÁ LUẬT PHÂN TẦNG, VÀ CỔNG BẮT ĐƯỢC

`health.py` bản đầu viết thẳng:

    from apps.ltt_voice.tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI, ...

`tests/test_147_layering.py` đỏ ở lượt gate đầy đủ — và nó đúng. `registry.py`
mở đầu bằng: *"Nền tảng KHÔNG được biết tên app nào tồn tại."*

⭐ Điều đáng ghi: phép kiểm ấy **không chỉ chặn, nó chỉ ra bản sửa tốt hơn**.
Một endpoint chẩn đoán biết tên `ltt_voice` là một endpoint phải sửa mỗi lần
thêm app — tức đúng cái ràng buộc mà hợp đồng app sinh ra để gỡ. Bản sửa đúng:

    AppManifest.hop_dong_cong_khai   — app KHAI
    registry.discover()              — nền tảng ĐỌC

Nay app nào khai, app ấy hiện ra trong `/health/version`, kể cả app viết sau
`health.py`. Trường `ltt_voice` cứng nhắc đã thành `hop_dong` tổng quát.

⚠️ Và bản sửa lại có một cái bẫy thứ hai: `discover()` trả `LoadedApp`, **không**
phải `AppManifest`. `LoadedApp.slug` là một `@property` uỷ quyền, nên `a.slug`
chạy được và khiến `a.hop_dong_cong_khai` *trông như* cũng chạy được. Nó không —
`getattr` trả `None` lặng lẽ, và endpoint báo "không app nào khai" một cách rất
tự tin. Phải đi qua `.manifest`.

⭐ Hai lỗi này cùng một họ với lỗi `!AudioContext` ở `03_LONGFORM_FRONTEND.md`:
**mã chạy, không ai ném, và câu trả lời sai trông y hệt câu trả lời đúng.**

## VERIFIED — hai máy chủ đứng cạnh nhau, cùng một câu hỏi

    $ curl -s http://127.0.0.1:8100/health/version      # BAN DEPLOY (cu)
    {"version":"v1.0"}

    $ curl -s http://127.0.0.1:8127/health/version      # CAY NGUON (moi)
    {"version":"v1.0","commit":"72a484c5f281","commit_nguon":"git",
     "build_luc":"","asset_ver":"6a39aff9",
     "hop_dong":{"ltt_voice":{"tran_ky_tu_cong_khai":100000,
                              "tran_moi_luot_sinh":1500}}}

    $ git rev-parse --short=12 HEAD
    72a484c5f281

⭐ Ba điều đọc được ngay từ dòng thứ hai mà trước đây phải so md5 mới biết:

  · `commit` khớp `HEAD` ⇒ bản này đúng là cây đang sửa
  · `commit_nguon: "git"` ⇒ **đây là cây nguồn, không phải bản deploy**. Một máy
    chủ production trả `"git"` là một máy chủ đang chạy sai chỗ.
  · `asset_ver` **6a39aff9** ≠ **1574b6c6** mà bản deploy đang phục vụ
    (`<link href="/static/ltt.css?v=1574b6c6">`) ⇒ cache-bust hoạt động: CSS đổi
    ⇒ hash đổi ⇒ URL đổi ⇒ khách nhận bản mới ngay, không chờ TTL của Cloudflare.

## FILES CHANGED

- `platform_core/dau_van_tay.py` — mới. Đọc marker; ở cây nguồn thì hỏi git.
- `platform_core/registry.py` — `AppManifest.hop_dong_cong_khai`: app tự khai
  hằng số hợp đồng, nền tảng chỉ đọc.
- `apps/ltt_voice/manifest.py` — khai hai trần (tham chiếu hằng số, không gõ lại).
- `server/routes/health.py` — `/health/version` trả dấu vân tay thật,
  **app-agnostic**.
- `setup/2-cai-dat.ps1` — ghi `dau_van_tay.json` sau robocopy, bằng `Write-NoBom`.

## TESTS

`tests/test_398_dau_van_tay_ban_chay.py` — 7 phép kiểm. Chốt cả việc marker
**hỏng** phải cho `khong-ro` chứ không được ném: một endpoint chẩn đoán mà chết
vì thứ nó chẩn đoán là một endpoint chỉ chạy khi không ai cần nó.

## REMAINING RISK

- `.git` không có trong bản deploy (cố ý). Nên `commit` phụ thuộc **hoàn toàn**
  vào marker do script ghi. Nếu ai deploy bằng robocopy tay thay vì chạy
  `2-cai-dat.ps1`, marker sẽ cũ — nên script **xoá** marker khi không đọc được
  git, vì một marker cũ là câu trả lời SAI trông như thật, tệ hơn không có.
- Dấu vân tay chỉ trả lời cho **tiến trình web**. Worker và sidecar chạy tiến
  trình riêng và chưa khai gì; chúng có thể lệch với web sau một lần restart
  từng phần. Chưa xử lý.

## STATUS

✅ Nguyên nhân xác định bằng đo, không bằng suy luận. Cơ chế chống tái phát đã
dựng và có phép kiểm.
