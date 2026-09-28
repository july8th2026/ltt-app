# W4 — Cái giá thật của việc bỏ MỘT giai đoạn khỏi `pipeline.CHUOI`

> Viết theo yêu cầu điều phối viên (28/09): đo, ⛔ không sửa `pipeline.py`. Đối
> tượng đo: bỏ `edit_plan` khỏi `CHUOI`, `image_finish.sau` đổi từ
> `(EDIT_PLAN,)` sang `(RENDER,)`. Đối chiếu với cảnh báo tại
> `giai_doan_ban_bien_tap.py:11-18` (28/09, B14): *"⛔ KHÔNG rip giai đoạn khỏi
> `pipeline.CHUOI`"*.

## Baseline đo được (chưa sửa gì, `python` nạp `pipeline` thật)

```
len(pipeline.CHUOI) = 13
ha_nguon_cua('render')       = ['edit_plan','image_finish','qc','qc_do_luong','qc_ai']
ha_nguon_cua('edit_plan')    = ['image_finish','qc','qc_do_luong','qc_ai']
ha_nguon_cua('image_finish') = ['qc','qc_do_luong','qc_ai']
```

## 1. `ha_nguon_cua` — `pipeline.py:573-611`

Đọc `g.sau` theo thứ tự khai trong `CHUOI`, ⛔ không đọc vị trí/chỉ số. Gọi
thật ngoài `pipeline.py` và test: **1 nơi sản xuất** (`features.py:361`, dùng
trong `vo_hieu_ha_nguon`), **6 tệp test** tham chiếu trực tiếp.

Bỏ `edit_plan` + đổi `image_finish.sau=(RENDER,)`: `ha_nguon_cua('render')`
mất đúng 1 phần tử (`'edit_plan'` tự nó biến mất, vì nó không còn trong
`CHUOI`), còn `image_finish/qc/qc_do_luong/qc_ai` **vẫn có mặt đủ** — độ phủ
"downstream" không thủng lỗ. ⇒ Cơ chế này **không gãy**, chỉ ngắn đi 1 phần tử
đúng như kỳ vọng.

## 2. Vân tay (`thi_hanh.py:249-307,526`) — **GÃY, nhưng tự phục hồi**

`van_tay(ten, run, dau_vao)` băm `{stage, contract, settings, dau_vao, engine}`;
`dau_vao = _gom_dau_vao()` đọc `pipeline.THEO_TEN[ten].sau` **tại thời điểm
gọi** (không cache theo lần chạy cũ) và với mỗi `truoc` lấy `fingerprint` của
giai đoạn đó. Đổi `image_finish.sau` từ `(EDIT_PLAN,)` sang `(RENDER,)` đổi
CHÍNH XÁC 1 khoá trong dict `dau_vao` (`"edit_plan"` → `"render"`) ⇒ hash khác
100% cho **mọi** run đã có `image_finish` ở trạng thái `succeeded` trước khi
deploy.

`van_tay()` được gọi ở đúng 2 chỗ (`thi_hanh.py:331`, `:526`) — cả hai đều
dùng `_gom_dau_vao` giống nhau, nên không có đường nào né được.

## 3. Lineage CSDL — **không đo được từ worktree này**

`_khoa_cha` (`thi_hanh.py:336-349`) đọc cùng `g.sau`, nên `image_finish`'s
`parent_keys` cho các run submit MỚI sau deploy sẽ trỏ tới `render` thay vì
`edit_plan` — nhất quán với #2, không phải lỗi riêng.

Câu hỏi thật ("có job `job_type=auto_scan_video.edit_plan` đang `queued`/
`running` không") cần kết nối CSDL sản phẩm; worktree này **không có**
`data/config.json`/`secrets/` (đúng luật CLAUDE.md — không copy sang worktree).
⛔ Không tự tạo kết nối để dò. Cần chạy từ cây chính hoặc qua công cụ vận hành.

**Đọc được bằng code** (không cần CSDL): nếu một job như vậy vẫn chạy xong sau
deploy, nó ghi `AsvStage(stage="edit_plan")` mà **không ai đọc lại** — 4 nơi
gọi `_khoa_theo_duoi(..., pipeline.EDIT_PLAN, ...)`
(`giai_doan_hinh_anh.py:231`, `giai_doan_qc_ai.py:453`) đều `if khoa_ep:` —
thiếu thì trả `""`/`None` và **đi tiếp bình thường** (đã xác minh: kết quả
giống hệt trường hợp `edit_plan` chạy và trả kế hoạch rỗng, vì B14 đã ép
`hieu_canh=()` vô điều kiện). ⇒ Orphan **không crash, không hỏng ngầm** — chỉ
là ghi phí mất, đúng nghĩa "mồ côi".

## 4. `giai_doan_lech_van_tay` (`thi_hanh.py:310-333`) — LỆCH, không phải THIẾU

So `van_tay()` **mới tính** với `s.fingerprint` **đã lưu**; khác thì trả về
tên giai đoạn trong danh sách "lệch" — đây luôn là tín hiệu **LỆCH**
(mismatch), never "thiếu". Gọi tại **1 nơi**: `jobs.py:419`, bên trong
`_vo_hieu_giai_doan_da_lech`, chạy **đầu MỌI lượt advance** (`jobs.py:86`,
trước khi tính `da_xong`) — tức **không có cửa né**: run nào chưa `done` tại
lúc deploy mà đã có `image_finish=succeeded` sẽ bị phát hiện LỆCH ở lượt
advance kế tiếp, `_dat_lai_giai_doan` (reset) + `vo_hieu_ha_nguon` (dây
chuyền) đè lên `image_finish, qc, qc_do_luong, qc_ai` → 4 giai đoạn bị buộc
chạy lại, kể cả `image_finish` (render GPU lại). Run đã `done` (không advance
nữa) thì **không bị đụng** — hàng đã giao giữ nguyên.

## `len(CHUOI)` cho phần trăm tiến độ — AN TOÀN, tự điều chỉnh

`jobs.py:100,127` và `quan_sat.py:561-562` đều đọc `len(pipeline.CHUOI)`
**động**, không ghim số `13`. Bỏ 1 phần tử ⇒ các chỗ này tự còn `12`, không
gãy. Đã kiểm nguyên văn 5 tệp test đọc `len(pipeline.CHUOI)`
(`test_403:493`, `test_417:333,413`, `test_450:317-318`, `test_478:245`) —
**cả 5 đều đọc động**, an toàn. Riêng **`test_402_asv_mach_doc_gia.py:267`
ghim cứng `assert len(ds) == len(pipeline.CHUOI) == 13`** — đây là chỗ DUY
NHẤT sẽ đỏ (đã đọc nguyên văn, ⛔ không suy từ trí nhớ). Bình luận cạnh
`test_450:305-311` từng nhắc một bản ghim `== 12` cũ, nhưng đó là nợ đã được
SỬA (nay đọc `list(pipeline.TEN_GIAI_DOAN)` động) — ⛔ không còn là chỗ gãy.

## Kết luận

**Bốn con số**: (1) `ha_nguon_cua` 1 nơi sản xuất/6 tệp test, mất đúng 1 phần
tử, không thủng downstream. (2) Vân tay: 2 lời gọi `van_tay()`, GÃY 100% cho
mọi run có `image_finish=succeeded` chưa `done`. (3) Lineage: không đo được số
job mồ côi từ worktree này (thiếu quyền CSDL) nhưng code xác nhận orphan
harmless (4 điểm đọc `EDIT_PLAN` đều `if khoa_ep:` graceful). (4)
`giai_doan_lech_van_tay`: 1 nơi gọi, chạy **mọi** lượt advance, không có cửa
né — LỆCH (không phải THIẾU), tự phục hồi bằng reset+rerun, ⛔ không hỏng ngầm.

**Về mặt cơ chế: bỏ được** — cả 4 đường đều tự phục hồi đúng thiết kế (LECH →
reset → chạy lại đúng, không giao sai hàng), và runtime đã có sẵn đường lui
graceful cho `EDIT_PLAN` thiếu (giống hệt kết quả rỗng B14 ép sẵn). **Cái giá
thật, có thể đo bằng số**: mọi run đang chạy dở qua khỏi `image_finish` tại
đúng lúc deploy sẽ bị buộc render GPU lại đúng 1 lần (4 giai đoạn:
`image_finish/qc/qc_do_luong/qc_ai`) — một chi phí vận hành thật nhưng
**bounded, một lần, tự lành**, ⛔ không phải hỏng vĩnh viễn.

Đây là **quyết định kiến trúc rủi ro cao chủ dự án đã chốt NGƯỢC LẠI trong
CHÍNH ngày hôm nay** (B14, `giai_doan_ban_bien_tap.py:11-13`). Số đo ở trên
làm rõ "rủi ro" cụ thể là gì (chi phí GPU một lần cho run dở dang), ⛔ không tự
đảo ngược quyết định đó — để chủ dự án/điều phối viên cân đối chi phí đó với
lý do ban đầu ("rủi ro của việc BỎ lớn hơn rủi ro nó đang gây") rồi quyết.
