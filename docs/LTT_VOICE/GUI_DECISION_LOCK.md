# GUI_DECISION_LOCK — LTT Voice (chốt 15/09/2026)

Quy tắc (prompt §13): sau khi khoá, **không đổi** quyết định nào ở tệp này
trừ khi có bằng chứng MỚI — khi đó ghi **Decision Amendment** kèm Evidence +
Impact, không sửa im lặng. Số D001–D016 đúng thứ tự quy định trong prompt.

Bằng chứng runtime: xem `GUI_RUNTIME_DIAGNOSIS.md` (đo 15/09, PROVEN/LIKELY
đánh dấu tại chỗ).

---

## D001 — Catalog taxonomy (preset / shared / owned)

**Problem:** Ba loại giọng (20 preset engine, VoiceProfile shared, VoiceProfile
owned) được phân loại **riêng lẻ ở từng template** — ví dụ nghi ngờ
`data-loai="{{ 'mau' if la_mau else 'toi' }}"` ở `/giong` (bị loại nhị phân,
sai vì 25 shared bị nhét vào nhóm "của tôi"). Không có hàm chuẩn.

**Options considered:**
- A: Mỗi template tự suy (trạng thái hiện tại) — loại: 2 nguồn sự thật, bug
  lan thêm.
- B: Một hàm chuẩn server-side `voice_catalog_kind(voice) → "preset"|"shared"|"owned"`
  dùng ở TẤT CẢ 5 màn — **chọn**.

**Evidence:**
- DB thật 15/09: 25 profile `dung_chung=True` + 4 `dung_chung=False` (cùng
  owner tài khoản thử) — shared/owned phân biệt đúng bằng cờ `dung_chung`;
  preset nằm ở `giong_mau_engine.json` (20 mục, không phải VoiceProfile).
- Nghi vấn template hai nhóm: Wave 3 **PHẢI xác minh** tại HEAD trước khi
  tuyên bố bug (hiện trạng: LIKELY, chưa PROVEN).

**Decision:** Một hàm chuẩn server-side (đặt trong `apps/ltt_voice/`, ví dụ
`ho_so_giong.py` hoặc module riêng `catalog.py`), nhận đối tượng giọng (preset
HOẶC profile) trả `preset|shared|owned`. Mọi route/template/JS nhận kind từ
server, không tự suy.

**Reason:** Một nguồn sự thật cho cả 5 màn (Studio/Library/Dự án/Lịch
sử/API); bug loại hai nhóm biến mất vĩnh viễn; test L1 đơn giản.

**Rejected alternatives:** suy ở client (A) — 2 nguồn sự thật; enum riêng
từng screen — lặp.

**Files affected:** `apps/ltt_voice/ho_so_giong.py` (hoặc module mới),
`apps/ltt_voice/routes/_p_giong.py`, `_p_tao.py`, templates
`_voice_chon.html`, `_voice_the.html`, `ltt_voice_studio.html`,
`ltt_voice_giong.html`, `voice.js`.

**Acceptance test:** L1: hàm trả đúng 3 giá trị cho 3 loại fixture; grep toàn
app không còn template tự tính kind; browser: Library hiển thị 3 nhóm đúng
với dữ liệu DB (V01).

---

## D002 — Shared voice visibility (+ lưu trữ 25 giọng)

**Problem:** 25 shared voice phải hiện trong VOICE LIBRARY (tab "Kho chung"),
đếm số từ dữ liệu thật; hiện chúng (a) bị nhóm sai ở template, (b) **25/25
không usable** vì mất tệp R2.

**Options considered (lưu trữ — chi tiết trong GUI_RUNTIME_DIAGNOSIS §2.4):**
- A: đọc thẳng file repo, bỏ seam storage — ❌
- B: giữ R2, "bảo vệ" prefix — ❌
- **C: repo = nguồn chân lý bền + manifest.json (sha256) + seed idempotent
  vào prefix hệ thống `voice/he_thong/<public_id>/…` + self-heal khi khởi
  động + DB migration trỏ lại 25 profile + guard L1** — ✅

**Evidence:** R2 HEAD 15/09: 56/58 key của 29 profile KHÔNG tồn tại; duy nhất
còn = hồ sơ owned ghi danh 12/09. Kích thước đo: ~0.1MB wav + ~0.001MB npz
⇒ ~3MB/25 giọng, không cần LFS. Bucket xoá theo tuổi ~7 ngày (hành vi PROVEN,
cơ chế LIKELY).

**Decision:**
1. Visibility: Library có 4 tab **Tất cả / Giọng mẫu / Kho chung / Giọng của
   tôi**; số đếm mỗi tab = số record thật (không hardcode 25). Voice không
   usable vẫn **hiển thị** kèm lý do chính xác từng voice (đúng §6/V03).
2. Lưu trữ: phương án C. **Điều chặn:** cần chủ dự án cung cấp lại 25 clip
   nguồn (đã mất khỏi R2/đĩa/repo) — cho tới khi có clip, 25 giọng hiển thị
   ở tab Kho chung với trạng thái "tệp gốc đã mất — chờ cung cấp lại".

**Reason:** Durable copy nằm trong repo (không phụ thuộc trạng thái bucket —
đáp an toàn cảnh báo MAT_TEP §7); seed qua `get_storage().put` đúng với mọi
backend; self-heal làm bucket chỉ còn là cache kể cả khi luật 7 ngày vẫn còn.

**Rejected alternatives:** A (phá seam storage, 2 đường đọc ⇒ lệch); B
(phụ thuộc cơ chế bên ngoài đã chứng minh phá huỷ, không tự hồi phục —
chính prefix hiện tại KHÔNG được bảo vệ).

**Files affected:** `apps/ltt_voice/data/voices/` (mới: manifest.json +
tệp), `apps/ltt_voice/ho_so_giong.py`, `server/` (hook khởi động seed —
đặt đúng chỗ app, không sửa platform_core), DB migration (25 profile),
`tests/` (guard L1), templates Library.

**Acceptance test:** V03: 25 voice hiện ở Kho chung HOẶC lý do chính xác từng
voice; L1: mọi profile `dung_chung=True` có repr key đúng prefix hệ thống +
tồn tại + sha256 khớp manifest; seed chạy 2 lần không nhân bản (idempotent).

---

## D003 — Language behavior

**Problem:** Hợp đồng ngôn ngữ: VI+VI và EN+EN cho phép; VI+EN và EN+VI
**chặn ở backend** (không cho qua DevTools/API). `Auto` chỉ trợ giúp phát
hiện, không thay thế kiểm; `target_language` phải chốt **trước** khi tạo job.

**Evidence:** Dữ liệu thật: 18 hồ sơ en + 11 vi; có 1 job error thật 04/09
do lỗi voice/ownership. Chặn phía client chỉ = giả an toàn (bỏ qua được).

**Decision:**
- Hàm kiểm duy nhất server-side (trong luồng tạo job + validate public API):
  `ngon_ngu_hop(voice, target) → ok|lo_i` với luật:
  `voice.vi & target=vi → ALLOW`, `voice.en & target=en → ALLOW`,
  còn lại `BLOCK` với mã lỗi `loi_khop_ngon_ngu` + câu an toàn.
- `Auto`: server tự quyết target trước job; GUI chỉ gợi ý; request gửi lên
  KHÔNG bao giờ chứa cặp cross-lane hợp lệ để chạy.
- Kiểm chạy ở **tất cả** cửa: route web, public API, (sau này) API nội bộ.

**Reason:** An toàn ngôn ngữ là chuyện chất lượng âm + tiền credit (job chạy
lãng phí sai ngôn ngữ) — phải cơ học, một chỗ.

**Rejected alternatives:** kiểm client-only (lách DevTools được); cảnh báo
mềm (người dùng bỏ qua được); kiểm 2 chỗ khác nhau (lệch luật).

**Files affected:** `apps/ltt_voice/routes/_p_tao.py`,
`apps/ltt_voice/tham_so_cong_khai.py` (luật + thông báo công khai),
`apps/ltt_voice/jobs.py` (pre-check), `platform_core/public_api/` (nếu voice
mở API — Wave 7 xác minh), templates + `voice.js`.

**Acceptance test:** G03 (VI voice + EN target) và G04 (EN voice + VI
target) BLOCK trước khi job tồn tại (0 job mới trong DB) — bằng fetch thật
không cần login; L1: bảng 4+1 trường hợp (4 cặp + Auto).

---

## D004 — Filter semantics

**Problem:** Một chính sách lọc duy nhất cho mọi màn. Option A (nghiêm: ẩn
khi không biết thuộc tính + ghi chú) vs Option B (giữ cái không biết; lọc
chỉ áp dụng với cái có thuộc tính). Rào cản thật đo được: cột `gioi` trong
`voice_profile` **RỖNG 29/29** (15/09) — lọc "giới" không có dữ thật;
preset có `vung/phong_cach` nhưng VoiceProfile không có 2 cột đó.

**Decision:** **Option B** — giọng KHÔNG có thuộc tính không bị ẩn khi lọc
thuộc tính đó; nhãn bộ lọc khai rõ "chỉ áp dụng cho giọng có thuộc tính
này". Ngoại lệ: lọc **ngôn ngữ** được phép nghiêm (mọi hồ sơ có `ngon_ngu`)
— nhưng không ẩn khi user chưa chọn.

**Reason:** Option A với dữ liệu thật = chọn lọc "vùng" sẽ ẩn 25/25 shared
(giọng profile không có `vung`) → tái diễn đúng tri giác "25 voice biến
mất" của P0-2. Option B không bao giờ giấu dữ liệu; cái thiếu được khai
thành lời thay vì im lặng.

**Rejected alternatives:** Option A (ẩn-đi = giấu); tạo cột `vung/phong_cach`
mặc định giả (dữ liệu giả — cấm theo prompt).

**Files affected:** filter logic trong `routes/_p_giong.py` + JS của Library
(`voice.js`/`ltt_voice_giong.html`), 1 hàm dùng chung cho Library + Studio
picker (không mỗi màn một luật).

**Acceptance test:** V08: chọn lọc giới ⇒ giọng rỗng `gioi` vẫn hiện; lọc
ngôn ngữ EN ⇒ chỉ hiện EN; cùng bộ lọc 2 màn cho cùng kết quả (L1 so hàm).

---

## D005 — Queue UX

**Problem:** Người dùng thấy "Xếp hàng" vô thời hạn (chính là P0-1 live ở
production: 2 job queued từ 10:16 và 14:21 ngày 15/09). Không có spinner vô
tận; có câu thông báo theo **tuổi hàng đợi thật**.

**Evidence:** DB thật có đủ: `created_at`, `status`, `attempts`,
`progress`, `progress_msg` → `queue_age_s = now - created_at` (khi
`status=queued`) là **số thật**, không suy diễn. `worker_available` **KHÔNG**
là dữ liệu GUI có thật (thuộc env dịch vụ) → không hiển thị, không suy ra.

**Decision:** Trạng thái tối giản, đúng DB: `queued → running → done |
error | cancelled`. Trong `queued`, GUI xoay vòng thông báo theo tuổi thật:
- `<10s`: "Đang chờ xử lý…"
- `10–60s`: "Đang chờ máy xử lý…"
- `>60s`: cảnh báo "Hàng đợi lâu hơn bình thường. Bạn có thể chờ tiếp hoặc
  thử lại sau." + nút **Thử lại** / **Hủy** — KHÔNG có spinner vòng vô tận.
Polling: theo chu kỳ, đọc `status` thật; không invent thêm trạng thái.

**Reason:** Trạng thái thêm = phải có dữ liệu thật cho nó (prompt §4). Tuổi
hàng đợi là số thật duy nhất GUI nắm được; câu cảnh báo >60s là ngưỡng an
toàn UX (job voice thật đo được ~9.6–11s — 13/09).

**Rejected alternatives:** thêm trạng thái "đang tìm máy"/"đang vào hàng
GPU" (không có dữ thật riêng cho từng giai đoạn); spinner vô hạn (cấm);
ẩn cảnh báo (che P0-1).

**Files affected:** `apps/ltt_voice/ltt_voice_studio.html`,
`apps/ltt_voice/voice.js` (chuỗi poll + bảng câu), route poll trả
`queue_age_s` (tính server-side, 1 chỗ).

**Acceptance test:** G05 (worker không khả dụng): không spinner vô tận,
cảnh báo + nút hiện sau ~60s; L1: hàm chọn câu thông báo theo 3 ngưỡng tuổi.

---

## D006 — Job diagnostics

**Problem:** Support/admin phải tra được (prompt §20): job id · created ·
status · age · attempt · claimed? · worker id · capability · matching worker
exists? · admission resource · lease state · latest event. Hiện: **không có
event nào** khi không có matching worker (đo 15/09: job 15/09 chỉ có
`submitted` + `credit_held` rồi im).

**Decision:**
1. Worker: job `queued` vượt ngưỡng (ví dụ 5 phút, hằng số trong app) mà
   chưa được claim ⇒ ghi `job_events` warning "chưa có worker nhận job"
   (idempotent theo chu kỳ). **Không** ghi thông tin env vào event (bí mật).
2. `do_sau_khoi_dong.py`: mở rộng cảnh báo hiện có (đã có cho voice
   `tools/do_sau_khoi_dong.py:246-261`) thành **theo từng app có
   `requires`**: liệt kê app bị "vô hình" (requires ⊄ pools).
3. GUI user **không** thấy raw diagnostics — chỉ câu an toàn của D005.

**Reason:** Lỗ quan sát chính của P0-1 là "không có gì để thấy khi không có
worker đủ điều kiện"; event warning biến sự im lặng thành dữ liệu tra được,
đúng 12 trường §20.

**Rejected alternatives:** chỉ dashboard admin (vẫn không tự phát hiện);
in env vào log event (rò cấu hình nội bộ).

**Files affected:** `job_worker.py` (chu kỳ kiểm tuổi),
`tools/do_sau_khoi_dong.py`, `tests/test_501_*` (mở rộng),
`tests/test_216_*`.

**Acceptance test:** L2: job queued giả + pools thiếu lane ⇒ sau ngưỡng có
event warning; chạy `do_sau_khoi_dong` với env thiếu lane ⇒ in tên app vô
 hình; G05/G06 browser: GUI không lộ diagnostics.

---

## D007 — Studio layout

**Problem:** Có nên Studio 2 cột không? Prompt §12: CHỈ sau
đo → so → quyết → khóa → làm, bằng trình duyệt thật; CTA "Tạo tiếng nói"
phải thấy ở 1280×720 / 1366×768 / 1440×900 / 1920×1080.

**Evidence:** **Chưa đo layout hiện tại** — NOT TESTED. (Dữ liệu có sẵn:
màn hình Studio hiện là bố cục 1 cột — xác nhận hình thực ở Wave 5.)

**Decision (quá trình):** Wave 5 đo 4 viewport + ảnh chụp màn hiện tại → so
với bản 2 cột → ghi **Decision Amendment D007-A** với lựa chọn cụ thể + ảnh,
rồi mới implement. Cho tới Amendment: layout KHÔNG đổi.

**Reason:** Đổi layout không có phép đo là đoán; prompt §12 bắt buộc đo
trước.

**Rejected alternatives:** đổi ngay (vi phạm §12); bỏ hẳn (không — đo xong
mới loại được).

**Files affected:** (chưa chốt — Amendment D007-A sẽ liệt kê).

**Acceptance test:** Wave 5: ảnh 4 viewport + bảng so; Amendment ghi lựa
chọn; sau implement: CTA nhìn thấy (không scroll) ở 4 viewport — Playwright.

---

## D008 — Voice preview

**Problem:** Không preload 25+45 audio (45 = 25 shared + 20 preset). Preview
phải lazy.

**Evidence:** Route preview hiện có sẵn (serve file qua storage key —
`tham_chieu.py` + rule preview); kích thước audio nhỏ (~0.1MB) nhưng 45 file
preload vẫn là 45 request + ~4.5MB vô cớ. 25 shared hiện tại mất tệp (D002)
→ preview của chúng phải ra trạng thái "không có preview — lý do", không
404 im lặng.

**Decision:**
- `<audio>` gắn `preload="none"` (hoặc sinh URL chỉ khi bấm); 1 lúc 1 preview
  đang chạy (bấm cái mới dừng cái cũ).
- Voice thiếu tệp: nút preview hiện nhãn "Chờ cung cấp lại tệp" (từ trạng
  thái thật D002), không gọi URL sẽ 404.
- Không tạo audio element cho 45 voice cùng lúc — list vẽ tên, preview theo
  yêu cầu.

**Reason:** Performance (prompt §24) + không 404 im lặng + không chi phí
tải trống không.

**Rejected alternatives:** preload tất cả (cấm); `preload="metadata"` cho
tất cả (vẫn là 45 request).

**Files affected:** `voice.js`, `ltt_voice_giong.html`,
`_voice_chon.html`, `ltt_voice_studio.html`.

**Acceptance test:** Playwright: tải trang Library → 0 request audio; bấm 1
preview → đúng 1 request audio; bấm cái khác → request cũ bị dừng; voice
thiếu tệp → nhãn đúng, 0 request.

---

## D009 — Result state machine

**Problem:** Kết quả job sau "Tạo" phải đi đúng chu kỳ, có player + download
+ lưu vào project.

**Decision:** `queued → running → done | error | cancelled`.
- `done`: player + nút tải WAV + (MP3 nếu app có) + "Lưu vào dự án".
- `running`: % tiến độ **chỉ** khi DB có `progress` thật (job voice hiện có
  progress_msg — kiểm Wave 5; không có thì chỉ hiện "Đang tạo…").
- `error`: vào phân loại D012.
- Không state giả, không "gần xong" khi DB chưa nói vậy.

**Reason:** Đủ 3 luồng kết thúc + 2 trạng thái trung gian đúng DB (prompt
§4: tối giản, không invent).

**Rejected alternatives:** thêm state "đang xuất file"/"đang chuyển mã"
(chưa có dữ thật riêng).

**Files affected:** `voice.js`, `ltt_voice_studio.html`, route poll.

**Acceptance test:** G01 (VI, shared voice, artifact thật) đi đủ
queued→running→done + player phát + file tải được; L1: máy trạng thái.

---

## D010 — Responsive behavior

**Problem:** Không tràn ngang, CTA không bị ẩn, modal/picker đúng cao, tên dài
không vỡ, chữ VI/EN không cắt.

**Evidence:** Chưa đo — NOT TESTED (Wave 8 đo 6 viewport: 1280×720,
1366×768, 1440×900, 1920×1080, 768×1024, 390×844).

**Decision:** Kiểm Playwright 6 viewport: `scrollWidth <= clientWidth` ở
mọi viewport (không tràn ngang), CTA trong khung nhìn, dialog không ra khỏi
màn, tên 30+ ký tự không vỡ layout. Sửa CSS theo phát hiện thực đo.

**Files affected:** `ltt.css` (chỗ voice), templates.

**Acceptance test:** 6 viewport × {Studio, Library} qua Playwright, 0 lỗi
tràn, CTA visible ở 4 viewport desktop.

---

## D011 — Accessibility

**Problem:** Bàn phím, focus, modal trap, ESC, aria-live, label, audio
controls, trạng thái "bấm" của filter.

**Decision:**
- Mọi nút/bộ lọc = control thật có `aria-pressed` (filter) / focusable;
- Modal: trap focus + ESC đóng + trả focus về nơi mở;
- Trạng thái job đọc bằng `aria-live="polite"` (thay "Đang chờ xử lý…" →
  "Đang chờ máy xử lý…" đọc được);
- `<audio>` kèm nút có label; icon-only button có `aria-label`;
- Focus ring nhìn thấy được.

**Files affected:** templates 5 màn + `voice.js`.

**Acceptance test:** Wave 8: walkthrough bàn phím thật qua 1 luồng Studio
mở → tạo → kết quả (Playwright keyboard-only); kiểm `aria-pressed` của bộ
lọc; trap focus + ESC của dialog.

---

## D012 — Error handling

**Problem:** Không bao giờ hiện raw exception cho user. Mỗi lỗi = 1 phân
loại + câu an toàn + hành động tiếp.

**Evidence (lỗi thật trong DB):** `LoiGiongNoi: Không tìm thấy giọng này
trong tài khoản của bạn.` (job `16931066…`, 04/09) → phân loại
**voice not owned/unavailable**.

**Decision — bảng phân loại (server map mã lỗi → (phân loại, câu, hành
động)):**

| Phân loại | Trigger thật | Hành động user |
|---|---|---|
| validation | tham số sai (tốc độ, độ dài…) | sửa form |
| language mismatch | D003 | đổi giọng/đổi ngôn ngữ |
| voice unavailable | voice thiếu tệp (25 shared hiện tại) | chờ cung cấp lại (D002) |
| voice not owned | chọn voice không của mình (lỗi thật 04/09) | đổi giọng |
| credit | không đủ credit | nạp credit |
| worker unavailable | không worker lane voice (P0-1) | chờ/thử lại (D005) |
| resource wait | GPU đang bận (vieneu_gpu lease) | chờ tiếp (D005) |
| sidecar/model | sidecar 8120/model lỗi | thử lại; nếu lặp → support |
| artifact | file kết quả mất | thử lại |
| network | mạng client | thử lại |
| session expired | đăng nhập hết hạn | đăng nhập lại |
| unknown | mọi exception chưa map | câu an toàn + mã tham chiếu job |

Server trả `error_class` (không trả chuỗi exception thô) — GUI chỉ render
bảng.

**Rejected alternatives:** hiện message lỗi thô (cấm); 1 câu chung cho mọi
lỗi (không chỉ được cách sửa).

**Files affected:** `apps/ltt_voice/jobs.py` (map), route poll (trả
`error_class`), `voice.js`, templates.

**Acceptance test:** L1: bảng map (mỗi phân loại ≥1 fixture); G05/G06
browser: UI hiện đúng phân loại, không chứa chữ `Traceback`/tên class Python.

---

## D013 — Retry behavior

**Problem:** Nút "Thử lại" chỉ hợp lệ với lỗi tạm thời; với lỗi chặn (ngôn
ngữ, not owned, credit) retry là spam + đốt credit.

**Decision:** Retry (tạo job MỚI — không "revive" job cũ):
- **Cho phép:** worker unavailable, resource wait, sidecar/model, artifact,
  network — sau khi job về `error` hoặc quá tuổi queued.
- **Không cho phép** (nút retry ẩn, hiện hành động đúng của D012):
  language mismatch, voice not owned, credit, validation.
- Hủy job queued + tạo job mới = "Thử lại" hợp lệ (job cũ `cancelled`).

**Reason:** Credit là sổ sách thật (CLAUDE.md) — retry với lỗi chặn = giữ
credit vô nghĩa rồi error lại.

**Files affected:** `voice.js` (nút theo `error_class`), route tạo job.

**Acceptance test:** L1: bảng retry-allowed theo error_class; browser: job
error do language → không có nút Thử lại, có gợi ý đúng.

---

## D014 — Project consistency

**Problem:** Màn Dự án (Projects) chọn giọng phải dùng đúng catalog + quyền
của D001–D004: không nút Xóa/Vô hiệu cho shared (user thường), không loại hai
nhóm, cùng luật ngôn ngữ.

**Evidence:** Chưa audit màn Projects — Wave 7 đọc code + đo browser. Prompt
§11: "Không redesign mạnh nếu hiện đã tốt."

**Decision:** Sửa CHẶT theo phát hiện thật ở Wave 7: cùng hàm
`voice_catalog_kind`, cùng filter policy D004, cùng kiểm D003, quyền V06
(shared không có Delete/Disable cho user thường — admin-only nếu có).

**Files affected:** (Wave 7 chốt danh sách sau audit).

**Acceptance test:** V06: user thường không thấy nút Xóa/Vô hiệu trên shared
ở Library VÀ Dự án; cùng giọng cùng phân loại ở 2 màn (L1).

---

## D015 — History consistency

**Problem:** Màn Lịch sử phải hiện đủ trạng thái thật (queued/running/done/
error/cancelled) bằng đúng câu của D005/D012; artifact hết hạn → trạng thái
"file không còn" rõ ràng, không 404 im lặng.

**Decision:** Mỗi hàng lịch sử = `status` thật + câu theo D005 (khi queued)
hoặc D012 (khi error); file download dùng token/URL có hạn; hết hạn hoặc
không tồn tại ⇒ nhãn "File không còn khả dụng" + (nếu voice vẫn usable)
"Chạy lại". Không hiện lại spinner cho job queued cũ — hiện tuổi + cảnh
báo theo D005.

**Files affected:** route + template màn Lịch sử, `voice.js`.

**Acceptance test:** Browser: lịch sử hiện 2 job queued thật của 15/09 với
tuổi + cảnh báo (không spinner vô hạn); job done → tải file được.

---

## D016 — API GUI consistency

**Problem:** Màn API (E) — thông số giọng/tốc độ/hạn mức phải khớp GUI,
cùng ID (public_id), cùng nguồn `tham_so_cong_khai.py`.

**Evidence:** `tham_so_cong_khai.py` là nguồn chân lý công khai của LTT VOICE
(CLAUDE.md — bảng "Luật của từng hệ con"). GUI và API hiện khai ở 2 nơi —
kiểm Wave 7.

**Decision:** Màn API đọc thông số TỪ `tham_so_cong_khai.py` (import), không
hardcode; danh sách giọng ở màn API = cùng nguồn catalog (D001) với Library —
không liệt kê 25 voice không usable như thể dùng được (gắn nhãn theo D002).

**Files affected:** `server/` màn API của ltt_voice (Wave 7 định vị),
`apps/ltt_voice/tham_so_cong_khai.py`.

**Acceptance test:** L1: màn API + Library trả cùng tập public_id + cùng giá
trị tham số cho trường hợp so được; browser: màn API không hardcode số.

---

## Quy tắc Amendment

Đổi bất kỳ D0xx nào ⇒ thêm mục mới ở cuối tệp:

```
## D0xx-A (Amendment, <ngày>)
- Trigger: <bằng chứng MỚI, liên kết/tệp>
- Sửa: <câu cụ thể đổi>
- Impact: <files + tests bị ảnh hưởng>
```

Không sửa đè câu Decision gốc.

---

## Chú thích số hiệu (16/09/2026)

Code HEAD đã dùng "D002/D003/D004" từ ngày **11/09** cho quyết định **làn ngôn
ngữ** (`_p_giong.py`, `lan_ngon_ngu.py`). Tệp này dùng D001–D016 theo prompt GUI.
Khi trích trong code/commit của chương trình GUI, viết **`GUI-D0xx`** để không
lẫn với số cũ.

## D001-A (Amendment, 16/09/2026)
- **Trigger:** `apps/ltt_voice/tham_chieu.py:53-129` — điều kiện "kho chung" đã có
  MỘT nguồn: `_dieu_kien_kho_chung()` / `du_dieu_kien_kho_chung()` =
  `dung_chung AND license_status ∈ LICENSE_CHO_PHEP ("ok",)`, và
  `tach_rieng_chung` thêm `trang_thai == "active"`. Bản `catalog.py` (15/09) chỉ
  xét `dung_chung` ⇒ nguồn chân lý thứ hai (đã gỡ 16/09).
- **Sửa:** hàm phân loại đặt trong `tham_chieu.py`, suy từ
  `du_dieu_kien_kho_chung` + `owner_id == uid`; không tạo module luật riêng.
  Phải định nghĩa tường minh ô "chủ xem giọng `dung_chung` của chính mình" và ô
  "`dung_chung=True` nhưng license chưa ok".
- **Impact:** W3' của `GUI_DOI_SOAT_VA_PLAN_V2.md`; test L1 phải có fixture ORM,
  license chưa ok, disabled, người xem ≠ chủ.

## D002-A (Amendment, 16/09/2026)
- **Trigger:** 25 giọng dùng chung `license_status=cho_soat` (đo 15/09) ⇒ không
  qua `_dieu_kien_kho_chung` ⇒ **vô hình với mọi khách không phải chủ**. Nguyên
  nhân này độc lập với việc mất tệp R2. Phép kiểm browser 15/09 đo bằng chính tài
  khoản chủ nên không phát hiện được.
- **Sửa:** (1) Visibility phụ thuộc quyết định license của chủ dự án
  (`tools/soat_giong.py duyet`), không phải của code. (2) Phương án C (seed tệp
  vào repo + hook khởi động + migration) **tách khỏi chương trình GUI** thành
  chương trình hạ tầng riêng. GUI chỉ hiển thị trạng thái thật.
- **Impact:** W2', W6' của plan V2; bỏ mọi tệp `server/`/migration khỏi phạm vi GUI.

## D003-B (Amendment, 16/09/2026) — Nghe thử lệch làn thì CHẶN
- **Trigger:** audit W4' — `/nghe-thu-van-ban` vẫn gọi sidecar khi
  `quyet_dinh` trả `cho_phep=False` (quyết định D006 cũ ngày 11/09, `test_526`
  ghim). Prompt GUI §9 chốt một luật BLOCK cho mọi cửa; chủ dự án duyệt 16/09.
- **Sửa:** chặn trước `xin_luot` và trước GPU; 400 `voice_language_mismatch` +
  câu đã dịch + `phan_quyet`. D006 cũ hết hiệu lực.
- **Impact:** `_p_nghe_thu.py`, `test_526` (đảo mệnh đề, thêm "không trừ lượt,
  không chạm GPU").

## D003-A (Amendment, 16/09/2026)
- **Trigger:** backend đã cưỡng chế làn: `lan_ngon_ngu.quyet_dinh`
  (`lan_ngon_ngu.py:277`) → `voice_language_mismatch` (`lan_ngon_ngu.py:110`),
  gọi ở `features.py:301`, `_p_nghe_thu.py:66`.
- **Sửa:** KHÔNG thêm `ngon_ngu_hop` / `loi_khop_ngon_ngu`. W4' audit các cửa đã
  đi qua `quyet_dinh`, chỉ vá cửa thiếu, dùng lại mã `voice_language_mismatch`.
- **Impact:** D012 bảng lỗi dùng mã `voice_language_mismatch`; W4' plan V2.
