# LTT Voice RC1 — Nghiệm thu **Tầng 2** (sau deploy)

> Tầng 1: `TANG1_RC1.md` (`READY_FOR_DEPLOYMENT`, 99/100).
> Ô của Tầng 2 định nghĩa ở spec §10.2.

| | |
|---|---|
| SHA được cổng chứng nhận | `e2676aaa194d0e781c92c2ec9bdac3fb3166ce47` |
| ff vào | **`main`** (không phải `admin-mvp-v3` — xem §1) |
| Deploy | 12/09/2026 02:39:33 → 02:41:21, `EXITCODE=0`, `deploy-20260912-023933.ket.txt` |
| Đường lui | `C:\LTTPlatform\app.previous` = `7cde3c9d4dac` (build 12/09 00:42) |

---

## 1. Đích ff đã đổi — và vì sao

Kế hoạch viết `admin-mvp-v3`. Hỏi máy chủ trước khi chạm vào nó (luật 5 của
`CLAUDE.md`) cho kết quả khác:

```
/health/version truoc deploy  ->  commit 7cde3c9d4dac  (build 2026-09-12T00:42:28)
admin-mvp-v3                  ->  34b4626e             (CU HON production 7 commit)
git merge-base --is-ancestor 7cde3c9d <RC>  ->  KHONG
```

Trong 7 commit ấy có `3a6da723 refactor: make main the live branch authority`,
và `docs/16_CAP_NHAT_VA_DEPLOY.md` **của chính nó** ghi *"Nhánh trunk: `main`
(Q123)"*. ff vào `admin-mvp-v3` rồi deploy sẽ **lùi** 7 commit đang chạy thật.

⇒ Hoà `main` vào RC (`f98be1be`, ba xung đột đều giải theo hướng **giữ cả hai
bên**), rồi ff vào `main`. Sau khi hoà, `7cde3c9d` là tổ tiên của SHA deploy ⇒
**không commit nào bị lùi**.

Kiểm chắn trước deploy (§3 của tài liệu deploy):

```
tep .py chi co o production ma commit KHONG co  ->  0
```

---

## 2. Bảng ô Tầng 2

| # | Ô (spec §10.2) | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | SHA tested = SHA ff = SHA deploy | **PASS** | cả ba đều `e2676aaa` |
| 2 | `/health/version` = SHA ấy | **PASS** | `{"commit":"e2676aaa194d","asset_ver":"de7fdfe7","build_luc":"2026-09-12T02:40:47"}` |
| 3 | `nghiem_thu_deploy` 0/0/0 **và** tệp không `.py` 0/0/0 | **PASS** | 922 tệp trong commit, **266 tệp không `.py`**; lệch 0 · thiếu 0 · thừa 0; tài sản ngoài commit đã khai (`van_chuyen`) = 9 → `DAT` |
| 4 | `alembic upgrade head` một head | **PASS** | CSDL production: `alembic_version = d9a1f6c2b3e5`; cột `voice_profile.ngon_ngu_nguon` và bảng `voice_lich_su` đều có mặt |
| 5 | Di trú ASR thật trên production | 🔴 **BLOCKED** | §3 |
| 6 | Bộ Playwright trên URL công khai | 🟡 **MỘT PHẦN — phần còn lại BLOCKED** | §4 |
| 7 | Public API live bằng khoá đọc | **PASS** | §5 |

⇒ **RC1 KHÔNG được gọi là `RELEASED`.** Hai ô chưa đạt, và không ô nào trong số
đó được viết thành PASS.

---

## 3. Ô 5 — di trú ASR: **BLOCKED**, và nguyên nhân nằm ngoài RC1

Chạy khô trên production (`tools/di_tru_lan_asr.py`, ngưỡng 0.9, 2 luồng):

```
Xet: 28   Se doi: 0   Da ghi: 0   Khong chac: 28
28/28 dong:  "khong doc duoc kho (voice/<owner>/<voice>/source.wav): R2 khong doc duoc"
```

### Truy tới gốc, không dừng ở thông báo lỗi

| Câu hỏi | Đo được |
|---|---|
| Cấu hình R2 có đúng không? | `LTT_STORAGE=r2`, backend `R2Storage`, bucket `fb-video-storage` |
| Bucket có truy cập được không? | **Có** — `list_objects_v2` trả `KeyCount=15`, thấy `anhnoibo/…`, `thumbnail/…` |
| Tiền tố `voice/` có gì? | **Chỉ `voice/mau/…`** (nghe thử của 20 giọng mẫu). `voice/chung/` = 0 khoá |
| `voice/<owner>/…/source.wav` của 28 giọng khách? | `exists=False` — **không có khoá nào** |
| Có nằm trên đĩa máy chủ không? | Không: `C:\LTTPlatform\data\files\` chỉ còn `taovideo`, `thumbnail`; tìm `source.wav` và `repr-*.npz` trên cả `C:\LTTPlatform` → **0 tệp** |
| Có phải đổi bucket giữa chừng? | Không: **mọi** bản `secrets/app.env.bak-*` đều ghi cùng `LTT_STORAGE=r2` và cùng bucket |
| Dữ liệu ấy sinh khi nào? | `voice_profile`/`voice_ref` tạo **31/08 12:21 → 01/09 12:58** |

**Kết luận đo được:** CSDL production có **28 hàng `voice_ref` + 28 hàng
`voice_repr`** trỏ tới các khoá kho mà **không khoá nào còn tồn tại**. Tức 28
giọng riêng của khách hiện **không có clip nguồn và không có biểu diễn giọng**.

⛔ **Đây KHÔNG do lần deploy này.** Dữ liệu sinh 31/08–01/09; lượt deploy hôm nay
chỉ thay mã và chạy migration (chỉ **thêm** cột/bảng); không lệnh ghi nào của
lượt nghiệm thu này chạm tới kho. Trạng thái ấy đã có sẵn **trước** khi deploy.

⇒ Ô 5 **BLOCKED** cho tới khi việc mất tệp kho được điều tra riêng. Công cụ di
trú đã được chứng minh chạy đúng ở Tầng 1 (đo `vi -> en`, `do_tin=0.998`, trên
một clip tiếng Anh thật) — **cái thiếu là dữ liệu, không phải công cụ**.

---

## 4. Ô 6 — Playwright trên URL công khai: một phần

**Đạt** (trang công khai, không cần đăng nhập):

| Kiểm | Kết quả |
|---|---|
| `GET /` qua `https://app.lttstudios.com` | **200**, render đủ danh mục app (có thẻ "Giọng nói LTT") |
| `console.error` / `pageerror` | **0** |
| Yêu cầu mạng hỏng | **0** — 9/9 request trả 200 |
| **Cache-bust** (luật 18) | `static/ltt.css?v=**de7fdfe7**` — khớp đúng `asset_ver` mới của `/health/version` ⇒ CSS mới đã ra tới biên Cloudflare |
| `/ltt-voice` (chưa đăng nhập) | **303** → đăng nhập, đúng thiết kế |
| `/gia-api`, `/health/ready` | **200** |
| Dịch vụ | `LTTStudioWeb`, `LTTStudioWorker`, `LTTStudioVoice` — cả ba **Running** |

**BLOCKED** (các luồng cần đăng nhập — D002/D003/D004/D005/T-08 trên
production):

1. Không có `LTT_SMOKE_USER`/`LTT_SMOKE_PASS` của tài khoản test vận hành
   (`akakenly.design@gmail.com`); chúng không nằm trong kho lẫn `secrets/app.env`.
   Dùng `admin@` để thay là **sai** (memory `tai-khoan-test-van-hanh`).
2. Lượt điều hướng thứ hai bằng trình duyệt tự động bị **Cloudflare bot-check**
   chặn (`403`, trang *"Just a moment…"*). Vượt bot-detection là việc **không
   được phép làm**.

⚠️ Đây là hạn chế của **lượt kiểm**, không phải kết luận về ứng dụng: cùng các
luồng ấy đã PASS ở Tầng 1 trên máy chủ E2E.

---

## 5. Ô 7 — Public API live: PASS

`tools/api_prod_canary.py trang-thai --token-file …` (khoá chỉ đọc, scope
`tools:read` + `jobs:read`; token ghi thẳng ra tệp, **không in ra**):

```
/health/ready 200 · / 200 · /vps 200 · /gia-api 200 · /developers 303
KHU API /api/v1 — 5 tool dang mo:
  image.ltt · speech.ltt · text.chat · video.subtitle · video.upscale
```

`speech.ltt` — cửa Public API của Voice — **đang mở và trả lời thật**.

⚠️ Hook kiểm-trước D007 **chưa** được thử trên production: khoá canary chỉ có
scope đọc, không tạo được quote/job. Nó đã được chốt bằng `test_524` và bằng
lượt Tầng 1.

---

## 6. Một điều Tầng 1 đã chứng minh mà bảng trên không thể hiện

Cổng giọng dùng cho lượt "tổng hợp THẬT" của Tầng 1 là `127.0.0.1:8120` —
**chính là dịch vụ `LTTStudioVoice` của production**. Nên engine giọng đang
phục vụ khách đã được chứng minh, trong chính phiên này, là tổng hợp được **cả
hai làn**: VI qua preset và EN qua một giọng ghi danh từ clip tiếng Anh thật.

---

## 7. Việc còn nợ

| Việc | Mức |
|---|---|
| **Điều tra mất tệp kho Voice**: 28 `voice_ref` + 28 `voice_repr` trỏ tới khoá R2 không tồn tại (dữ liệu 31/08–01/09) | 🔴 cao — 28 giọng khách hiện không dùng được |
| Lấy `LTT_SMOKE_USER`/`LTT_SMOKE_PASS` để chạy bộ Playwright đầy đủ trên URL công khai | trung bình |
| Thử hook D007 trên production bằng một khoá có scope ghi | thấp |
| `tools/restore_drill_schema.py` còn giữ tên ràng buộc của bảng đã xoá 24/08 (`uq_vps_port_map_cong`); `test_155` chỉ kiểm một chiều | thấp, thuộc hệ VPS |
