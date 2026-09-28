# Kết quả của một lượt chạy ⛔ không có cửa ra — đo 28/09/2026

**Khách chạy một workflow có `core.output`, và ⛔ không có đường nào xem kết
quả — trừ khi chạy lượt THỨ HAI rồi mở "So sánh".**

Phát hiện này rơi ra từ phép đo `doi_dau_ra` (dưới), không phải từ một lượt rà
soát. Nên nó có một giá trị phụ: nó cho thấy bề mặt *"khách xem kết quả ở đâu"*
chưa từng bị một phép đo nào đi qua.

## Ba mảnh, và mảnh nào cũng đúng một mình

| Mảnh | Sự thật |
|---|---|
| `platform_core/workflow/ket_qua_run.py::doc` | Trả `{tên: giá trị}` của mọi `core.output` đã `SUCCEEDED`. **Đúng.** |
| Ai gọi nó | **Chỉ** `platform_core/workflow/run_con.py:194` (run con). ⛔ Không route nào. |
| `apps/agent/routes/runs_v3.py::_run_json_v3` | 11 trường: `id · workflow_id · version_id · status · credit_max · credit_charged · settled · created_at · nodes · su_kien · seq_cuoi`. ⛔ Không trường kết quả. |

`output_ref` của node **có** ra tới trình duyệt — nhưng chỉ qua
`GET /api/v3/runs/{id}/so-sanh`, và cửa ấy đòi `voi: str = Query(..., min_length=1)`:
**một id run thứ hai**. Frontend đã ghi đúng hình dạng này từ trước, ở
`frontend/agent-canvas/src/features/editor/ExecutionPanel/buocCuaRun.ts:22`:

> đầu ra · artifact | ⛔ Không trong `RunV3`; chỉ cửa SO SÁNH trả `output_ref`

⇒ Cái giá khách trả để xem **một** câu trả lời là **hai** lượt chạy.

## ⭐ Vì sao KHÔNG chữa bằng một cột `output_data`

`ket_qua_run.py` mở đầu bằng đúng lập luận ấy và bác nó: *"một cột thứ hai giữ
cùng sự thật là một chỗ để hai câu trả lời lệch nhau"*. Cùng luật với `tien.py`
và `api_prod_canary` (*"không bảng chép tay"*). ⇒ Chỗ thiếu là một **cửa đọc**,
⛔ không phải một chỗ lưu. `ket_qua_run.doc` đã làm sẵn phần tính.

Hình dạng tối thiểu: `_run_json_v3` thêm `"ket_qua": ket_qua_run.doc(db, run)`.
⚠️ Nhưng `_run_json_v3` chạy **mỗi giây trong luồng SSE**, và `doc()` tốn một
truy vấn ảnh chụp **mỗi node `core.output`** — đúng lý do `_nodes_so_sanh` bị
giữ ngoài `_nodes_json` (chú thích tại chỗ). ⇒ Cửa riêng
`GET /api/v3/runs/{id}/ket-qua`, hoặc chỉ nhúng khi `status` đã kết thúc.

⛔ Chưa triển khai: đây là một quyết định **sản phẩm** (khách thấy gì sau khi
chạy), thuộc loại phải hỏi chủ dự án theo `CLAUDE.md` luật 2.

---

# Phép đo đã lộ ra nó: `doi_dau_ra` CÓ chạy trên production

Run `45fe0012-cffc-402a-8356-23e9d263f648` · workflow `abfc2396` ·
28/09/2026 · tài khoản `khach1.thu` · `trigger.manual → ai.llm → core.output` ·
14 giây · 1 credit.

```
bat_dau   SUCCEEDED  {"event": {"nguon": "thu_cong"}}
y_tuong   SUCCEEDED  {"text": "The cat takes a bath and then sleeps on the
                       windowsill.", "json": null, "credit_cost": 1}
ra        SUCCEEDED  {"ten": "ban_dich", "gia_tri": "The cat takes a bath and
                       then sleeps on the windowsill."}
```

Ba điều cùng lúc, mỗi điều loại trừ một cách giải thích khác:

1. **Cổng tên `text` tồn tại** ⇒ `doi_dau_ra_llm` đã chạy. Job thô của
   `ltt_llm.chat` trả `content`; không có phép dịch thì đây là `{"content": …}`.
2. **`credit_cost: 1` còn nguyên** ⇒ `KHOA_HE_THONG_GIU_QUA_PHEP_DICH` giữ được
   khoá hệ thống qua phép dịch. Đây là chỗ tôi lo nhất khi vá: `ap_ket_qua` đọc
   `credit_cost` **sau** phép dịch, nên một phép dịch "sạch sẽ" trả đúng cổng
   khai báo sẽ **âm thầm làm nền tảng chạy không công**.
3. **`gia_tri` không rỗng** ⇒ `nodes.y_tuong.output.text` giải được.

## 🔴 `ra:SUCCEEDED` một mình ⛔ KHÔNG BAO GIỜ là bằng chứng

`chay_output` (`nut_loi/du_lieu.py:125`) chỉ `FAILED` khi biểu thức **lỗi**. Một
đường dẫn không tồn tại trả `None` và node vẫn `SUCCEEDED` với
`gia_tri: null`. ⇒ Phép đo phải đọc **giá trị**, ⛔ không đọc trạng thái. Đây là
lần thứ tư trong ngày cùng một họ lỗi (`memory/phep-kiem-xanh-tren-thu-da-hong.md`).

## Bốn cửa tôi gõ sai trước khi gõ đúng

Ghi ra vì mỗi cửa sai **trông giống một câu trả lời**, và ba trong bốn cửa sai
về phía *"tính năng không chạy"* — phía nguy hiểm, vì nó sẽ làm người sau đi vá
một thứ không hỏng.

| Tôi đọc | Nhận được | Vì sao |
|---|---|---|
| `GET /agent/api/v3/mau` | 404 | đường không tồn tại |
| `POST …/workflows/{id}/run` | 404 | thật là `/runs` |
| `n.outputs` · `n.output_ref` trên `_nodes_json` | `undefined` · `null` | `_nodes_json` **CÓ Ý** không trả output |
| `run.outputs` · `run.output` · `run.ket_qua` | `(không có trường)` | kết quả run là **dẫn xuất**, không có cột |

⭐ Kịch bản `tests/browser/agent_ui_v2_doi_dau_ra_tren_production.js` in
`Object.keys(run)` chứ không chỉ một tên đoán — nên lượt cuối **tự nói ra** 11
trường thật thay vì im lặng trả `undefined`. Đó là thứ đã cắt chuỗi đoán.

## Cạnh là bắt buộc, và cửa publish nói thẳng

`edges: []` ⇒ `422 tham_chieu_khong_phai_to_tien: node 'ra' đọc
nodes.y_tuong.output.text nhưng 'y_tuong' KHÔNG phải tổ tiên của nó theo
thứ_tự`. Thứ tự thực thi suy từ **cạnh**, ⛔ không từ vị trí trong danh sách
`nodes`. Cửa này từ chối ở `publish` — **trước** khi khách bấm Chạy và **trước**
khi tiêu credit — kèm tên node và tên biểu thức. So với bốn cửa 404/`null` ở
trên, đây là cửa duy nhất hôm nay nói đúng cái đang thiếu.

## Không phải phát hiện: `tam the` → `takes a bath`

`prompt` của tôi viết **không dấu** (`con meo tam the ngu tren bau cua so`), nên
mô hình đọc `tam` thành `tắm`. Lỗi của phép đo, ⛔ không phải của sản phẩm.
`windowsill` giữ được — chi tiết khó nhất của câu vẫn qua.
