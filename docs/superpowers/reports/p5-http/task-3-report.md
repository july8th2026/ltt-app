# P5/T3 — Node `core.http`

## Nguồn đã tra

- `platform_core/workflow/nut.py:17-30` — `KIND`, `CATEGORY` (có `NETWORK`),
  `QUYEN`, `RESOURCE_CLASS`, và khuôn `MA_LOI_APP`.
- `platform_core/workflow/nut_loi/ai_llm.py` + `ai_loi.py` — khuôn một node lõi:
  khai `MA_LOI_*` **riêng**, `publish_duoc=False` cho tới khi `bien_dich._node`
  biết dịch `core.*`.
- `platform_core/workflow/he_kieu.py:22-33` — `KIEU_CO_BAN`; `any` đúng dành cho
  node `core.*` đi qua giá trị mà không diễn giải.
- T1 `an_toan_mang` + T2 `http_an_toan` — ⛔ không viết lại bộ kiểm URL.

## Dòng đỏ → dòng xanh

```
ĐỎ   E ImportError: cannot import name 'http' from 'platform_core.workflow.nut_loi'
     1 error in 0.55s
XANH 23 passed in 15.27s          (tests/test_2912_nut_core_http.py)
```

Bánh cóc **cắn thật** — ba phép tiêm lỗi, ba tập thất bại **khác nhau**:

```
TIÊM A  dùng `httpx.Client` trần thay client có bộ gác -> 17 failed, 6 passed
TIÊM B  bỏ trần kích thước phản hồi                    ->  1 failed, 22 passed
TIÊM C  mặc định THEO chuyển hướng                     ->  1 failed, 22 passed
GỠ                                                     -> 23 passed
```

## Cơ chế đăng ký — chứng minh, không hứa

⛔ Không sửa `nut_loi/__init__.py` (làn p3 đang ở đó). Một tệp mới trong `nut_loi/`
**không** tự được nạp — `dang_ky()` chỉ chạy khi mô-đun được import.
`test_import_mo_dun_LA_DU_de_node_co_mat_trong_so` khẳng định `"core.http" in
nut_loi.tat_ca()` **và** `tat_ca()["core.http"] is nut_http.CORE_HTTP` — cùng một
đối tượng, không phải một bản trùng tên.

Tệp nằm dưới tiền tố `platform_core/workflow/nut_loi/` đã khai trong
`thanh_phan.toml` (`core:wf_soan`) ⇒ **không** phải sửa tệp đó cho T3.

## Một quyết định an ninh không có trong brief: mặc định KHÔNG theo chuyển hướng

Theo 3xx là gửi **lại** header người soạn khai — rất hay là một `Authorization` —
tới host mà **đích kia** chọn trong `Location`. Không cần tấn công tinh vi: một API
đối tác bị chiếm quyền trả một `302` là đủ. `theo_chuyen_huong` mặc định `False`;
bật lên thì mỗi hop vẫn qua bộ gác (T2), nhưng đó là quyết định của người soạn.
`test_mac_dinh_KHONG_theo_chuyen_huong` + `test_bat_theo_chuyen_huong_*` đo cả hai
chiều.

## Hai chỗ cố ý **không** biến thành FAILED

- **Thân không phải JSON** → trả về chuỗi. Một API trả HTML không phải lỗi của người
  soạn; biến nó thành FAILED là bắt họ trả giá cho quyết định của bên kia.
- **`ma_chap_nhan`** → có API dùng `404` làm câu trả lời bình thường. Trống ⇒ mọi mã
  `< 400`. Thân lỗi vẫn đi kèm `LoiHttp.than`, nếu không người soạn không cách nào
  biết API kia phàn nàn gì.

## Chưa làm được

- **Chưa nối `LoiHttp` → trạng thái FAILED của node.** Việc đó ở
  `platform_core/workflow/cau_noi.py` — tệp làn p5 bị cấm chạm. `thuc_thi()` là hàm
  thuần; cầu nối dịch sau.
- **Chưa đăng ký trong `nut_loi/__init__.py`**, nên Canvas chưa thấy node cho tới khi
  p3 gộp và ai đó nối một dòng import.
- **Chưa có OAuth và chưa có kho credential** — ngoài phạm vi theo brief. Header
  `Authorization` hôm nay do người soạn tự gõ vào tham số, tức **nó nằm trong
  `WorkflowVersion`**. Đó là chỗ một kho credential phải thay thế; cần làm trước khi
  mở node này cho khách.
