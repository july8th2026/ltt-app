# 26 — KHU VỰC "WORKFLOW" — quyết định UX

## Yêu cầu

Người dùng muốn **một trải nghiệm rõ tên "Workflow"** chứa: Agent/Canvas hiện
hành · bốn App mới · các Node/Tool liên quan.

## Quyết định: KHÔNG build Hub. Khai `group="Workflow"`.

Pack cho phép build một *"minimal generic Workflow Hub"* — nhưng kèm điều kiện:
*"Nếu UX hiện tại chưa tạo được tab/area Workflow đúng nghĩa"*. Điều kiện ấy
**không đúng**, và đo được ngay trên mã:

```python
# platform_core/registry.py:476
group: str = "Ứng dụng"
# "nhóm hiển thị ở HEADER (dropdown theo nhóm) … nền tảng gom app theo `group`.
#  Chỉ ảnh hưởng ĐIỀU HƯỚNG/hiển thị, không đụng logic app."
```

Sáu nhóm đang chạy thật: `AI Studio` · `Chat` · `Video` · `Ảnh` · `AI` · `VPS`.

⇒ Khu vực Workflow = **bốn chữ trong bốn bản khai**:

```python
group="Workflow"     # apps/transcript · audio_pause · gem · video_assembly
```

`apps/agent` (Canvas) khai thêm cùng một chữ ⇒ Agent/Canvas đứng cùng chỗ với
bốn App. Không tệp mới, không route mới, không sửa `server/` hay `platform_core/`.

## Vì sao đây là câu trả lời đúng, không phải câu trả lời lười

🔑 **Một Hub là một chỗ thứ hai để danh sách app bị sai.** Nền tảng đã có đúng
một nguồn: `registry.discover()` quét `apps/`. Một trang Hub liệt kê "các app
Workflow" hoặc phải hỏi lại registry — lúc đó nó không thêm gì — hoặc giữ danh
sách riêng, và **một danh sách chép tay không có cách nào tự biết nó đã cũ**.

⭐ Kho này đã trả giá cho đúng cơ chế ấy. `CLAUDE.md` §*Hiện giờ cái gì đang
sống* từng là một bảng 280 dòng chép tay; nó nói **sai năm lần**, và **cả năm
đều về phía nguy hiểm** — báo một thứ đang TẮT trong khi nó đang BẬT và **đang
thu tiền thật**. Bốn lần được sửa bằng cách viết lại bảng; lần thứ năm vẫn xảy
ra. Thứ đổi được vấn đề không phải người viết cẩn thận hơn, mà là **nơi câu trả
lời đến từ**.

⇒ Một Hub V1 sẽ lặp lại đúng cơ chế đó, chỉ khác là nằm trong mã.

## Cái Hub sẽ thêm được — và vì sao vẫn hoãn

| Hub có thể cho | Hôm nay có gì | Phán quyết |
|---|---|---|
| liệt kê Macro Node từ registry | palette của Agent đã đọc `ToolSpec` | **thừa** |
| lifecycle/health/visibility | trang admin đã có; `suc_khoe` đã ở manifest | **thừa** |
| tóm tắt I/O có kiểu | `params_schema` / `returns` đã hiện ở Canvas | **thừa** |
| liên kết App ↔ Canvas ↔ Runs | ba đường đi riêng, chưa nối một chỗ | **cái DUY NHẤT còn thiếu** |

⇒ Một dòng liên kết không đáng một trang mới. Xét lại **sau** khi có ≥2 App
chạy thật và có người dùng thật đi qua ba đường ấy — lúc đó mới biết họ cần nối
gì với gì.

## Điều kiện để mở lại quyết định này

Build Hub khi **và chỉ khi** một trong ba điều sau đo được:

1. `group` **không** gom được Agent/Canvas cùng bốn App (đo trên giao diện thật,
   không đọc mã);
2. có ≥2 phản hồi người dùng thật rằng không tìm thấy đường từ App sang Canvas;
3. số App nhóm `Workflow` vượt ~8 và dropdown header thành không dùng được.

⛔ Và khi build thì **registry-driven**, không hardcode một slug nào — đó là bất
biến #1 của MASTER-GUARDRAILS và `test_60` đã cưỡng chế nó.

## Nghiệm thu

Đổi `group` là đổi điều hướng ⇒ hợp đồng vận hành §9 áp: mở trình duyệt, xem
header có nhóm **Workflow**, và chốt trên **URL công khai**
`https://app.lttstudios.com`, không chỉ loopback — loopback bỏ qua Cloudflare.
