# 11 — RELEASE GATE

> Nguồn: `docs/00_LTT_OPERATING_CONTRACT.md` §4, §7, §8 và
> `docs/16_CAP_NHAT_VA_DEPLOY.md`. Không suy diễn quy trình — chỉ trích và áp
> dụng cho nhánh sửa lỗi này.

## Điều kiện gate — đọc đúng nguồn, không chép số

`docs/00_LTT_OPERATING_CONTRACT.md` §4 định nghĩa ba cấp:

| Cấp | Lệnh | Dùng khi |
|---|---|---|
| **L1** | `gate.py --doi [--tu <sha>]` | giữa phiên khi cần · deploy giữa phiên · khép sau L3 đỏ · hoà `main` |
| **L2** | `gate.py --pham-vi <tp>[,<tp>…]` | giữa phiên khi cần · deploy giữa phiên · chứng nhận riêng một changeset lõi |
| **L3** | `gate.py` (không cờ) | **một lần, KẾT THÚC PHIÊN** (§4.2) — production (nghiệm thu thật §9) |

⛔ **MỘT L3 mỗi nhánh** (§4.6, máy `gate.py` tự từ chối thi hành) — nhánh đã có
một lượt L3 (xanh hay đỏ) trong 12 giờ thì không chạy L3 lần hai; L3 đỏ thì
sửa tại chỗ rồi khép bằng `gate.py --doi --tu <sha của lượt L3>`, không chạy
lại toàn bộ L3.

⚠️ **Khác biệt cần lưu ý**: `docs/00_LTT_OPERATING_CONTRACT.md` (bản đọc lúc
viết tệp này) dùng khung "phiên" (L1/L2 bất cứ lúc nào giữa phiên khi cần, L3
một lần khi **kết thúc phiên**). `CLAUDE.md` của worktree này (chốt 25/09,
mục 0 "Luật chết người") thu hẹp thêm một bậc: **không chạy gate (L1/L2/L3)
TRONG PHIÊN**, chỉ test nhắm; gate (L1 hoặc L2, không dùng thuật ngữ "L3" cho
bước này) chạy **đúng một lần ở CUỐI PLAN**. Tệp này áp dụng luật hẹp hơn của
CLAUDE.md cho nhánh sửa lỗi hiện tại, vì đó là bản chốt sau và cụ thể hơn cho
worktree này; nêu rõ cả hai để người đọc không nhầm giữa "phiên" và "plan".

## Điều kiện phải có TRƯỚC deploy (§8, §16 mục 1)

1. **Gate xanh trên đúng SHA sẽ deploy** của `main` — không phải SHA của
   worktree, không phải SHA đã gộp thêm về sau. `docs/16_CAP_NHAT_VA_DEPLOY.md`
   mục 1: giữa phiên là L1 (`gate.py --doi --tu <sha bản đang chạy>`, phủ mọi
   thay đổi kể từ `/health/version`) hoặc L2 (`--pham-vi <tp>[,<tp>…]`); ở
   CUỐI PLAN là gate đầy đủ theo CLAUDE.md mục 0.
   ⛔ Không chạy gate đầy đủ chỉ để deploy nếu chưa hết plan; test nhắm một
   mình KHÔNG đủ để deploy (§8).
2. `git status --porcelain` **RỖNG** ở cây chính `D:\LTTSTUDIOSAPP` — một dòng
   `??` lạ là phiên khác đang viết dở, không phải rác.
3. Đối chiếu `main` có head Alembic khác bản đang chạy không — đọc trước khi
   deploy (không tự động migrate qua đường copy).
4. Đối chiếu production có tệp mà `main` không có — `app\` bị thay TOÀN BỘ nên
   tệp lạ bị xoá lặng lẽ (trừ `$VAN_CHUYEN`).
5. Báo các phiên đang chạy trước khi deploy (deploy xuất HEAD **cây chính**,
   mang cả commit của họ) — báo, không chờ, không xin duyệt (§10b).

## ⭐ Cập nhật 2026-09-27 — nhánh này ĐÃ MỘT PHẦN LÊN PRODUCTION, qua deploy của phiên khác

Deploy xuất **toàn bộ HEAD cây chính** (`docs/16_CAP_NHAT_VA_DEPLOY.md` mục 0),
không lọc theo nhánh hay theo app. Một phiên khác đã deploy SHA `47b277ca`
(việc của phiên đó là ASV, không liên quan Upscale) — và vì các commit của
nhánh Upscale này **đã được gộp vào `main` trước đó**, chúng **đi theo** lượt
deploy ấy. Xác minh bằng git: `git merge-base --is-ancestor c365de02
47b277ca` → đúng (commit sửa lõi `c365de02` là tổ tiên của SHA đã deploy).

- **Đã lên production**: 15/16 commit của nhánh này, gồm commit sửa lõi
  `c365de02` (gỡ 10 tính năng giả + bug ngữ nghĩa, 8 tệp `apps/upscalevideo/`),
  các bộ test khoá bất biến, bộ đo `tools/bench_upscale.py`, và mọi tài liệu
  `docs/UPSCALE_V2_CORRECTION/` tới thời điểm đó.
- **Chưa lên production**: commit cuối `3350993a` (tile sweep Quality — quyết
  định giữ tile 512) và 2 tệp tài liệu này (`10_FINAL_SCORECARD.md`,
  `11_RELEASE_GATE.md`) + `13_TRA_LOI_27_CAU.md` — `git log main..HEAD` xác
  nhận chỉ đúng một commit chưa gộp tại thời điểm viết.
- **Trước khi các commit trên rời worktree**, phiên điều phối đã xác minh hàm
  tính credit (`apps/upscalevideo/cost.py`) **hành vi giống hệt byte-for-byte**
  qua 960 tổ hợp tham số — tức đợt sửa **không đổi giá** dù đã sửa lại lời
  khai lý do tính giá trong docstring `cost.py` (bị số đo bác ở
  `08_BENCHMARK_RESULTS.md` §G.2/§I.2). "Tính gì tiền" là đánh đổi sản phẩm,
  chủ dự án chốt giữ nguyên (`CLAUDE.md` luật 2, `cost.py` mục "⚠️ SỐ ĐO
  2026-09-27").

### Ba thay đổi hành vi KHÁCH NHÌN THẤY đã lên production

1. **Job có đầu ra hỏng nay FAIL thay vì thành-công-và-tính-tiền.** Cổng kỹ
   thuật mới (`quality_gate.kiem_tra_dau_ra`) đánh đỏ job khi khung/thời
   lượng/codec lệch thật (`jobs.py:547` `raise RuntimeError`) — trước đây
   cổng cũ luôn fail nhưng job vẫn `SUCCEEDED` (ISSUE H). Kill switch nếu cần
   cứu một job đang gấp: `LTT_UPSCALE_TECH_GATE=0` (`quality_gate.py:71-76`).
2. **Cảnh báo chất lượng giả trên mọi job đã biến mất.** Cổng PSNR/SSIM/VMAF
   cũ luôn thất bại (gọi sai công cụ, không tham chiếu, đọc MP4 vào RAM cho
   PIL) và dán `quality_warning` lên **mọi** job khách kể cả job tốt — đã bỏ.
3. **HEVC không có phần cứng nay báo lỗi rõ, không còn âm thầm trả H.264.**
   Đường CPU tôn trọng codec khách xin (`libx265` cho HEVC thay vì luôn
   `libx264`); trường `codec` trong kết quả job nay là codec THẬT, tách khỏi
   `codec_requested` (ý khách) — hết tình trạng API trả
   `{"codec":"hevc","encoder":"libx264"}`.

⇒ Không có thay đổi giá, không có thay đổi bề mặt API (field mới là bổ sung,
không phá schema cũ), rủi ro khách hàng của lượt deploy này là **thấp** —
nhưng đây là mô tả sau-sự-kiện, không phải một gate đã chạy cho riêng nhánh
Upscale trước khi deploy (xem mục dưới).

## Áp dụng cho phần CÒN LẠI của nhánh này (chưa deploy)

Nhánh `claude/upscale-video-v2-correction-5fa61a` sửa `apps/upscalevideo/*.py`
(8 tệp) + thêm nhiều tệp `tests/test_490{4,5,6}_*.py` + tài liệu dưới
`docs/UPSCALE_V2_CORRECTION/`. Phần đã deploy ở trên đã đi qua gộp `main` của
phiên khác — không có nghĩa nó đã qua **gate riêng cho Upscale**. Trước khi
phần còn lại (commit `3350993a` + 3 tệp tài liệu) được coi là sẵn sàng deploy:

- Test nhắm cụm `upscalevideo` phải xanh (`tools\thanh_phan.py --test upscalevideo`
  → `pytest tests/test_4904_upscale_correction.py tests/test_4905_upscale_cong_ky_thuat_that.py
  tests/test_4906_upscale_chot_tile_quality.py -q` và mọi test cũ của app,
  ví dụ `test_82_upscalevideo.py`, `test_171_upscale_h32.py`,
  `test_116_upscale_motion_features.py`) — **CHƯA CHẠY trong phiên viết tài
  liệu này** (phiên này chỉ đọc/ghi tài liệu, không chạy pytest/GPU/ffmpeg,
  theo đúng giới hạn được giao).
- Gate đầy đủ (L1/L2 hoặc bước cuối-plan tuỳ theo phase của plan) phải XANH
  trên đúng SHA gộp vào `main` trước khi deploy máy A — **CHƯA CHẠY**, vì lý do
  trên. Phần ĐÃ deploy (`47b277ca`) không thay thế nghĩa vụ này cho phần CÒN
  LẠI: mỗi SHA deploy cần gate xanh của chính nó (§4, §8 của hợp đồng).
- ⛔ Không dùng kết quả `tests/test_4904_upscale_correction.py` như một gate
  thay thế: nó khoá phần lớn bất biến bằng mock (không chạm GPU/ffmpeg thật),
  là điều kiện **cần**, không phải điều kiện **đủ**. `test_4905` chạy trên tệp
  thật (`testsrc`) nên bổ sung một phần của điều kiện đủ, nhưng không thay
  toàn bộ gate.

## Đường lùi (rollback)

`docs/16_CAP_NHAT_VA_DEPLOY.md`: mỗi lượt deploy giữ bản trước ở
`C:\LTTPlatform\app.previous\` cùng `dau_van_tay.json` của nó — **hỏi bản này
là gì TRƯỚC khi deploy**, không phải sau khi cần rollback. Sau deploy, nghiệm
thu bằng `tools/nghiem_thu_deploy.py` (so băm mọi tệp với `git show <sha>:...`,
không tự so với cây làm việc đang chuyển động) + `curl /health/ready` (200) +
`curl /health/version` (đúng SHA vừa deploy). Nếu cần lùi: khôi phục
`app.previous\` → `app\` (thao tác nâng quyền, `tools\nang_quyen.py`), rồi
nghiệm thu lại đúng quy trình trên với SHA của bản lùi.

⛔ Ba phép kiểm cố ý KHÔNG nằm trong gate (`scan_source_secrets.py`,
`check_cve.py`, `check_a11y.py`) — chạy riêng trước deploy vì cần mạng/máy chủ
đang chạy/phiên trình duyệt, không phù hợp làm gate đỏ-vì-môi-trường.

⚠️ **Rollback của bản đã deploy (`47b277ca`) là rollback TOÀN CÂY, không phải
rollback riêng Upscale.** `app.previous\` giữ HEAD cây chính **trước** lượt
deploy đó — tức lùi về `app.previous\` sẽ lùi **cả** phần sửa ASV của phiên
kia **lẫn** 15 commit Upscale đã đi kèm. Không có cơ chế lùi riêng một app
trong kiến trúc deploy hiện tại (`docs/16_CAP_NHAT_VA_DEPLOY.md` mục 0: bản
xuất `git archive` của HEAD, không tách theo app). Muốn lùi **chỉ** phần
Upscale mà giữ phần ASV thì phải tạo một commit `revert` mới trên `main` rồi
deploy lại — không phải khôi phục `app.previous\`.

## Tóm tắt điều kiện release cho nhánh này

| Điều kiện | Trạng thái tại thời điểm viết tài liệu (cập nhật 2026-09-27) |
|---|---|
| 15/16 commit đã deploy (đi kèm SHA `47b277ca` của phiên khác) | ✅ Đã deploy — xác minh bằng `git merge-base --is-ancestor c365de02 47b277ca` |
| Gate riêng cho Upscale trên đúng SHA đã deploy | **CHƯA CHẠY** — phần đã lên production đi qua gộp `main` + gate (nếu có) của phiên ASV kia, không phải một gate L1/L2/cuối-plan lập cho riêng nhánh Upscale |
| Commit còn lại (`3350993a`, tile sweep Quality) + 3 tệp tài liệu | **CHƯA gộp `main`, CHƯA deploy** |
| Test nhắm `upscalevideo` xanh cho phần còn lại | CHƯA CHẠY (ngoài phạm vi phiên viết docs — không chạy pytest/GPU/ffmpeg) |
| `git status --porcelain` rỗng ở cây chính | Không kiểm trong phiên này — phiên này chạy trong worktree, không phải cây chính |
| Bản lùi (`app.previous`) đã biết trước deploy tiếp theo | Chưa kiểm trong phiên này — phải hỏi lại trước khi gộp/deploy phần còn lại, vì `app.previous\` hiện tại là bản TRƯỚC `47b277ca` (xem cảnh báo rollback ở trên) |
| Báo các phiên đang chạy trước deploy tiếp theo | Chưa áp dụng — chưa tới bước deploy phần còn lại |

⇒ Phần lớn nhánh (15/16 commit) **đã lên production trên thực tế**, nhưng
**chưa từng qua một gate lập riêng cho Upscale** — rủi ro được giảm nhẹ bởi
bằng chứng hành vi không đổi (960 tổ hợp giá, test tiêm lỗi) chứ không phải
bởi một lượt gate xanh. Phần còn lại (1 commit + tài liệu) **chưa đủ điều
kiện deploy**: cần test nhắm xanh rồi gate đầy đủ trên đúng SHA trước khi gộp
tiếp — đây là mô tả điều kiện cần thoả, không phải xác nhận đã thoả.
