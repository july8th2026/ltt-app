# P2 Task 8 — `/bieu-thuc/goi-y` + autocomplete Inspector

Cây `D:\LTTSTUDIOSAPP-p2`, nhánh `phien/p2-bieu-thuc`. Điều kiện ra thứ hai của P2.

## Gợi ý sinh từ đâu — và bằng chứng nó KHÔNG phải bảng chép tay

| Phần gợi ý | Nguồn duy nhất | Đọc ở |
|---|---|---|
| 49 hàm §6.3 + nhóm | `ham_bieu_thuc.NHOM_HAM` (và `BANG_HAM` **dựng từ** nó) | `goi_y.bang_ham()` |
| chữ ký hàm | `inspect.signature()` của chính hàm Python | `goi_y._chu_ky()` |
| bảy gốc namespace §6.2 | `chinh_sach.NAMESPACE` | `goi_y._goc()` |
| node đọc được + cổng | `bien_dich.cau_truc()` = đồ thị × `CongCu.returns` | `goi_y._cua_node()` |
| ba mặt node | `bien_dich.MAT_NODE` | `goi_y._cua_node()` |

`BANG_HAM` đổi từ bảy `dict` rời sang **dựng từ `NHOM_HAM`** — một nguồn, không hai.

**Tiêm lỗi (bắt buộc), ba lượt, cả ba ĐỎ đúng chỗ:**

1. `test_bo_mot_ham_khoi_nguon_thi_goi_y_MAT_ham_do` — bỏ `upper` khỏi nguồn ⇒ gợi ý mất
   `upper`, **vẫn còn `lower`** (đối chứng: không phải cả bảng biến mất). Một bảng chép tay
   xanh ở đây ⇒ bài viết theo kiểu tiêm lỗi chứ không so với một danh sách thứ hai.
2. `_cua_node` duyệt **mọi node** thay vì tổ tiên ⇒ **7/16 đỏ**, gồm cả ba tham số của bài
   đối chứng tổ tiên. Đã hoàn nguyên, 16/16 xanh lại.
3. Thêm hai tên gõ tay (`nodes.d.output.text`, `slugify`) vào `ungVien()` của component ⇒
   **2/13 vitest đỏ**. Đã hoàn nguyên.
4. Không tiêm mà vẫn bắt: `test_969::test_MUOI_route_v3_deu_duoc_dang_ky` **đỏ thật** khi
   route thứ 11 xuất hiện — bánh cóc của plan 02 làm đúng việc. Đã cập nhật số (10 → 11).

## Vế đối chứng tổ tiên — CẢ HAI CHIỀU

Đồ thị đo: `a → b → c`, cộng `d` rời.

- **Khẳng định**: `nodes.a.output.text`, `nodes.b.output.image_keys`, `nodes.b.output.prompt`
  **có** trong gợi ý của `c`.
- **Phủ định**: không một `nodes.d.*` nào (không tổ tiên), không một `nodes.c.*` nào (chính nó),
  không `nodes.a.output.image_keys` (cổng không có trong registry).
- **Một luật, không hai** (`test_moi_goi_y_QUA_duoc_cong_publish_va_node_ngoai_thi_KHONG`,
  3 tham số): mỗi gợi ý được **đưa ngược vào cổng publish thật** (`bien_dich.bien_dich`) và
  phải qua; node **không** được gợi ý thì cổng ấy ném `tham_chieu_khong_phai_to_tien`.
  Luật tổ tiên chỉ còn MỘT bản: `bien_dich.cau_truc()` — `bien_dich()` và `goi_y()` cùng gọi.

## ⚠️ Khoảng cách THẬT giữa ngôn ngữ §6 và cổng publish — đã khai, không giấu

`bien_dich._doi` hôm nay chỉ nhận `{{ nodes.<id>.output.<cổng> }}`. Nghĩa là `{{ upper(x) }}`,
`{{ trigger.body }}`, `{{ nodes.a.status }}` **publish không được** — dù §6.3/§6.2 đã có đủ.
Nới `_doi` không nằm trong Task 8 (nó là cổng tiền, và động cơ chưa tính biểu thức §6).

⇒ Mỗi mục gợi ý mang `qua_publish`, **đo bằng chính cổng ấy** (`bien_dich.cong_params_nhan`),
không bằng một bảng mô tả. Giao diện hiện mục ấy MỜ + nhãn *"chưa publish được"*.
`test_moi_muc_khai_THAT_ve_viec_no_qua_duoc_cong_publish_hay_khong` đo lại **từng mục** bằng
`bien_dich.bien_dich` end-to-end. Ngày ai đó nới `_doi`, các cờ tự đổi — không bảng nào phải sửa.

## Kiểm trình duyệt — cổng 8199, fixture cô lập (⛔ không đụng 8100)

`tools/agent_browser_server.py` + Playwright MCP, `agent-a@example.com`, CSDL scratchpad.

**Lỗi THẬT tìm ra ở đây** (không bài viết-trước nào bắt được): gõ `"Vẽ: {{ nodes"` vào ô
`prompt` ⇒ `cau_truc()` chạy `_doi` NGHIÊM trên params đang gõ dở, ném `bieu_thuc_chua_ho_tro`,
và **cả phần `nodes.*` biến mất đúng giây người dùng cần nó**. Sửa: tách phán quyết hình dạng
biểu thức ra khỏi bước dựng cấu trúc (`cau_truc(..., nghiem=False)`); cổng publish vẫn nghiêm,
đo bằng vế đối chứng trong `test_bieu_thuc_DANG_GO_DO_khong_duoc_lam_mat_goi_y`.

Sau khi sửa, đo lại trên trình duyệt:

- node `b` (có tổ tiên `a`): hộp gợi ý **hiện thật** (334×125 px), đúng ba cổng thật của
  `app.text.chat` (`content`, `tool_calls`, `usage`) + `status`/`error` có nhãn cảnh báo.
  ⛔ Không có `nodes.roi.*` (không tổ tiên) và không có `nodes.b.*` (chính nó).
- bấm một gợi ý ⇒ ô thành `Vẽ: {{ nodes.a.output.content` (CHÈN, không thay cả chuỗi).
- node `roi` (không tổ tiên): gõ `{{ nodes` ⇒ **không hộp nào** — đúng.
- **0 console error/warning**, **0 request hỏng** (mọi lượt 200, kể cả hai lượt `/bieu-thuc/goi-y`).

## Số đo

| Phép | Kết quả |
|---|---|
| `tests/test_1769_wf_goi_y_bieu_thuc.py` (mới) | **17 xanh** |
| Lô nhắm 17 tệp (`wf_soan` + bánh cóc canvas) | **729 xanh** |
| `tests/test_1761_*` (hợp đồng `timeout_expr`) | **79 xanh, y nguyên** |
| `npm test` (agent-canvas) | **126 xanh / 8 tệp** (thêm 14 bài mới) |
| `npm run typecheck` · `npm run build` | xanh · bundle dựng lại |
| Bánh cóc `fetch(` thô trong `workflowApi.ts` | vẫn **== 1** (client mới đi qua `apiFetch`) |

## ⛔ Phép đo này KHÔNG phủ cái gì

1. **Khoá con của `trigger` / `run` / `loop` / `workflow.input`.** Hôm nay **không có mã nào
   dựng các payload đó** — `moi_truong_wf` chỉ NHẬN chúng, và chưa bên gọi nào tồn tại (kết
   luận âm, đo 24/09). Nên gợi ý dừng ở tên gốc; bịa `trigger.body`, `run.id`… là dựng đúng
   cái bảng chép tay mà task này cấm. Có nguồn ở P4 và khi `graph.inputs` thôi rỗng.
2. **`vars` có những biến nào.** §6.5 nói `vars` = output của `core.set` tổ tiên; `core.set`
   là node của P3 và `bien_dich` còn từ chối nó. `vars` ra như một gốc trống.
3. **Ngữ cảnh ô đang gõ.** Cửa trả cả bảy gốc: nó không biết ô nào là `timeout_expr` (chỗ
   duy nhất có `params`) hay ô nào nằm trong thân ForEach (chỗ duy nhất có `loop`).
4. **Kiểu của cổng không được kiểm.** Gợi ý nói cổng TỒN TẠI, không nói cắm vào tham số này
   có đúng kiểu không (`he_kieu` chưa được hỏi ở đường này).
5. **Không đo trên Cloudflare.** Cả hai lượt đều loopback; rủi ro 302 của `da7fce81` chỉ
   được chặn bằng `Accept: application/json` tường minh + một bài kiểm client, không phải
   bằng một phép đo qua CDN thật.
6. **Không đo đồ thị lớn.** Ba–bốn node; chưa đo độ trễ hay kích thước phản hồi khi một
   workflow có hàng trăm node × nhiều cổng.
7. **jsdom không đọc CSS** — hộp gợi ý có thể vô hình mà 13 bài vitest vẫn xanh. Chỉ lượt
   trình duyệt thật ở trên mới nói được nó hiện ra (rect 334×125).
