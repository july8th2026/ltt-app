# P5c / Task 5 — Bật `core.http` + câu hỏi palette

**Đã làm.**

- `nut_loi/__init__.py` import `http` (kèm ghi chú **vì sao** nó từng bị giữ
  lại — một mô-đun đăng ký mà không ai import là mô-đun chết).
- `CHUA_BAT` trong `tests/test_1789_wf_node_khai_toolspec.py` nay **rỗng**.
  Danh sách rỗng là trạng thái hợp lệ *và* mong muốn: phép kiểm vẫn chạy (mô-đun
  mới không được import vẫn ĐỎ), và phép đối chứng của chính nó vẫn chặn việc
  liệt kê lại một mô-đun **đã** bật.
- `publish_duoc=True`, `credential=("api_key","bearer","basic")`,
  `quyen={"network","credential"}`, `ma_loi += ("credential_bi_thu_hoi",
  "khong_thay")` — một node FAILED với mã không nằm trong `ma_loi` là một mã
  không ai dịch được ở giao diện.
- `test_2912::test_dinh_nghia_node_hop_le` viết lại cho khớp (nó chốt
  `publish_duoc is False` và `quyen == {"network"}`).

## ⚠️ Câu hỏi được giao: nó có **lọt** palette khi `publish_duoc=False` không?

**Đã kiểm — KHÔNG có lỗ, và nó khác hẳn tiền lệ `customer_visible`.**

`apps/agent/routes/palette_v3.sang_json` trả node kèm **cờ tường minh**
`publish_duoc`, và frontend đọc cờ đó:

- `frontend/agent-canvas/src/palette/PaletteV2.tsx:36-37` —
  `disabled={!nd.publish_duoc}` và `draggable={nd.publish_duoc}`;
- dòng 54 và `nodes/NodeKhung.tsx:40` — nhãn **"Sắp có"**;
- `tests/CanvasShell.test.tsx:139` và `PaletteV2.test.tsx:22` chốt hành vi đó.

Tức node **xuất hiện nhưng vô hiệu**, và đó là thiết kế cố ý (docstring
`nut_loi/__init__.py`): hiện ở trạng thái vô hiệu thay vì mời khách kéo một
node mà publish sẽ từ chối. Tiền lệ 5 tool `customer_visible=False` lọt palette
là **loại khác**: ở đó **không có** cờ nào ra tới client, và bộ lọc phải nằm ở
route (`palette_v3.py:193`) — quên một dòng là lọt im lặng. Ở đây cờ đi ra,
client đọc, và có phép kiểm ở cả hai đầu.

```
XANH  14 passed in 90.62s      tests/test_2921_credential_gan_node.py
      36 passed                tests/test_1789 + tests/test_2912 (trong lô 213)
```

**Chưa làm được.** ⛔ Không chạy vitest của `frontend/agent-canvas` (làn p9 sở
hữu frontend) — kết luận trên đọc từ mã + phép kiểm đã có, không từ một lượt
chạy trong lượt này.
