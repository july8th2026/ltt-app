# `ban_ghi/` — WanGP tự khai, ta chỉ chép lại

## Đây là gì

Đầu ra **nguyên văn** của bốn đường tra cứu WanGP, đóng gói trong một phong bì:

```json
{
  "nguon": "ghi_tu_may",
  "sha_wangp": "1e1dd2757f24923f008593d9d4ec09062234be20",
  "luc": "2026-09-07T21:00:00+07:00",
  "goi": "get_model_schema('vace_14B')",
  "du_lieu": { ... nguyên văn WanGP trả về ... }
}
```

| Tệp | Từ lời gọi |
|---|---|
| `liet_ke_model.json` | `list_model_metadata()` |
| `so_do__<model>.json` | `get_model_schema(<model>)` |
| `mac_dinh__<model>.json` | `get_default_settings(<model>)` |
| `kha_dung__<model>.json` | `get_model_availability(<model>)` |

## ⛔ Ba điều tuyệt đối không làm

**1. Không sửa tay `du_lieu`.** Đây là bản chép của một sự thật ở nơi khác. Sửa
nó là dựng một sự thật thứ hai, và hai sự thật thì một cái sai. Cần đổi thì sửa
ở WanGP rồi **ghi lại**.

**2. Không ghi tệp mới vào đây lúc chạy.** Thư mục này nằm trong kho. Một tệp lạ
sinh ra giữa lượt gate làm chính lượt gate ấy mất giá trị
(`cay_da_doi_giua_chung`) — và mất 10 phút để biết. `MayGiaLap` ghi đầu ra vào
thư mục tạm, có `test_738` canh.

**3. Không bỏ trường `nguon`.** Nó là thứ duy nhất phân biệt:

- `"khuon"` — ta dựng tạm cho **đúng hình dạng**, nội dung chưa chắc đúng
- `"ghi_tu_may"` — chạy `tools/wangp/ghi_ban_ghi.py` trên pod thật

Một khuôn sót lại **trông y hệt** dữ liệu thật. `test_738` từ chối bản ghi thiếu
`nguon`; HM-7/B4 chốt không còn `"khuon"` nào trước khi đóng chương trình.

## Ghi lại thế nào

```bash
python tools/wangp/ghi_ban_ghi.py --pod $LTTV_POD_ID
```

⭐ Bốn đường trên **không nhân một ma trận nào** — chúng đọc bản khai JSON và
quét hệ tệp. Nên chúng chạy được **cả khi stack CUDA đang hỏng**, và đó là lý do
HM-7 không phải chờ HM-9.

## Vì sao thư mục này thay `ho_so_data/`

`ho_so_data/*.json` là **hai** hồ sơ rút tay cho **hai** model — đúng cơ chế đã
giữ V2.1 ở độ phủ 2/46: chi phí tuyến tính theo số model, nên không ai mở tới
model thứ ba. Ở đây một lượt ghi lấy về cả bảng, và sổ đăng ký **sinh ra** từ nó
thay vì được gõ.
