# Task 2 — gỡ hẳn `previewAssistant` (cụm v2 đã chết)

Nợ §5 của `docs/superpowers/plans/2026-09-24-wf-v2-MASTER.md`. Lằn `p10-don`.

## Chứng minh KHÔNG còn đường gọi — trước khi gỡ

Chạy lại **chính bộ đo khả-năng-với-tới** của `tests/test_1728_canvas_khong_goi_duong_chet.py`
(gốc = tên được `src/**` import, bao đóng theo lời gọi trong thân hàm) trên cây này:

- `previewAssistant` **không** nằm trong bao đóng ⇒ không tệp nào import nó, không hàm với
  tới được nào gọi nó.
- `grep` toàn kho: chỉ 4 chỗ — định nghĩa (`workflowApi.ts:369`) và **ba chú thích**
  (`CanvasShell.tsx:22`, `workflowApi.ts:612`, `apps/agent/routes/runs_v3.py:77`).
- Cửa máy chủ `POST /agent/api/workflows/{id}/assistant/preview` **không còn trong bảng định
  tuyến** — `tests/test_2934_dong_cua_cum_v2.py::DA_DONG` chốt điều đó (P8 task 5).

⇒ Nhận định nợ cũ (*"sửa header `Accept` cho SSE"*) **sai**: sửa header cho một hàm gọi vào
cửa không tồn tại là sửa nhầm chỗ. **Gỡ hẳn.**

## Đã gỡ — cả cụm, không chỉ một hàm

Gỡ một hàm mà để tám hàm anh em cùng trỏ vào cửa đã đóng thì bánh cóc mới sẽ đỏ ngay. Chín
hàm bị xoá khỏi `frontend/agent-canvas/src/workflowApi.ts` (67 dòng), tất cả đều nằm ngoài
bao đóng với-tới-được và đều gọi vào `DA_DONG`:

`previewAssistant` · `applyAssistant` · `loadSnapshots` · `restoreSnapshot` · `createShare`
· `cloneWorkflow` · `exportWorkflow` · `importWorkflow` · `planWorkflow`
(+ kiểu mồ côi `AssistantResult`, `WorkflowSnapshot`).

## Bánh cóc mới — `tests/test_3521_frontend_khong_mo_lai_cum_v2.py`

Cùng khuôn `test_2934`, và lấp đúng khoảng trống `test_1728` **cố ý** để lại:

> `test_1728` đo theo **khả năng với tới** ⇒ một hàm chết nằm im trong `workflowApi.ts`, trỏ
> vào cửa đã bị gỡ, **không bị tính**. Đó là khẩu súng đã nạp đạn — chỉ cách sống lại đúng
> một dòng `import`. (Chính lý do `test_2934` đòi **xoá** `assistant.py`, không chỉ gỡ khỏi
> `__init__`.)

Bài này đo **mọi đường `/agent/...` VIẾT trong `src/**`**, kể cả trong hàm không ai gọi.

🔑 **Nguồn, không bản chép**: bảng định tuyến `apps.agent.routes.router` thật · danh sách cửa
đóng import thẳng từ `test_2934.DA_DONG` · bộ đọc đường / cắt chú thích / chuẩn hoá dùng lại
của `test_1728`. Không một danh sách tên hàm nào gõ cứng.

**Bánh cóc CẮN THẬT — tiêm lỗi ở mức nguồn, không chỉ mức bộ dò:**

```
# them lai mot `previewAssistant` KHONG AI IMPORT vao cuoi workflowApi.ts
FAILED test_KHONG_ham_nao_trong_src_con_tro_vao_cum_v2_da_dong
FAILED test_KHONG_them_duong_chet_nao_ngoai_MOC
   /agent/api/workflows/{}/assistant/preview  <- workflowApi.ts:612
2 failed, 6 passed
# hoan nguyen
8 passed in 0.99s
```

⭐ `test_1728` **xanh** trong cả hai lượt tiêm ấy — đó chính là khoảng trống được lấp.

**Đối chứng** (5 bài): bộ dò đọc ≥ 12 đường · `DA_DONG` không rỗng **và** không còn trong
bảng định tuyến · một cửa **còn sống** không bị báo · chú thích chỉ **nhắc tên** cụm v2
không bị tính (nếu không, luật ⛔ trong `CanvasShell.tsx` sẽ tự làm test đỏ).

## Đỏ trước → xanh sau

```
pytest tests/test_3521_frontend_khong_mo_lai_cum_v2.py -q -p no:randomly
  ĐỎ   2 failed, 5 passed   (18 đường chết, gồm cả 9 đường cụm v2)
  XANH 8 passed in 1.02s
```

## Thay đổi kèm

- `frontend/agent-canvas/src/CanvasShell.tsx:22-38` — chú thích đổi từ *"⛔ không import lại"*
  sang *"⛔ cụm v2 ĐÃ BỊ XOÁ, đừng viết lại"*, ghi rõ **hai** bánh cóc đo **hai** thứ khác nhau.
- `frontend/agent-canvas/tests/workflowApi.test.ts` — bỏ ba vế `cloneWorkflow`/`exportWorkflow`/
  `importWorkflow` khỏi bài `loads owner run history/detail`; ba vế run v2 còn lại giữ nguyên.

## ⚠️ Chưa làm được / khai ra

**Chín đường `/agent/api/runs*` + `/validate` VẪN CHẾT trong `src/`.** Bộ dò tìm ra thêm cụm
**run v2** (`createRun`, `approveRun`, `tickRun`, `cancelRun`, `runAgain`, `loadRun`,
`loadRunHistory`, `restoreRunAsWorkflow`, `validateWorkflow`) — cùng bệnh, khác cụm, và
`test_1728` cũng bỏ qua vì không ai gọi.

⇒ Không gỡ trong lượt này: việc của lằn là nợ §5, và gỡ chín hàm nữa kéo theo viết lại một
mảng `tests/workflowApi.test.ts`. Thay vào đó chúng được ghim thành **mốc chỉ-được-co-lại**
(`MOC_DUONG_CHET`, khuôn `tools/check_so_test.py`) với **cả hai vế**: thêm một đường chết mới
⇒ đỏ; gỡ được một đường mà quên hạ mốc ⇒ cũng đỏ (`test_MOC_phai_duoc_HA_khi_don_duoc`),
để cái mốc không thành danh sách ma.

**Phạm vi hẹp hơn lời tuyên bố**: so **đường dẫn**, không so **phương thức** (y `test_1728`);
và đọc `src/**`, nên một bản dựng cũ trong `server/static/agent-canvas/assets/` không bị
tính — thứ chặn chuyện ấy là bước `npm run build` ở cuối phiên.
