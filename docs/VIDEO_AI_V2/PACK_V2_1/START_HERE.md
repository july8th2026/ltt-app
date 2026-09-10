# LTT VIDEO + WanGP — ONE ENGINE V2.1

## Khuyến nghị sử dụng với Claude

**Bắt đầu bằng CHAT MỚI.** Không tiếp tục phiên Video V3 cũ.

Lý do vận hành:
- V2.1 thay đổi kiến trúc gốc: `WanGP = engine duy nhất`;
- legacy worker/ComfyUI path chỉ còn đối tượng audit/delete;
- state phải nằm trên filesystem, không nằm trong trí nhớ chat;
- mỗi phase lớn có thể tiêu tốn rất nhiều context khi audit repo/cloud.

### Cách chạy tối ưu

```text
CHAT MỚI #1 → P00
CHAT MỚI #2 → P01
CHAT MỚI #3 → P02
...
CHAT MỚI #10 → P09
```

Sau mỗi phase:
1. Claude cập nhật `docs/VIDEO_AI_V2/PROJECT_STATE.md`;
2. commit state/code;
3. báo `SAFE TO COMPACT / SAFE FOR Pxx`;
4. chat mới đọc state rồi tiếp tục.

Không gửi cả 10 prompt vào một chat để Claude “làm một lượt”.

---

## Kiến trúc cuối

```text
LTT VIDEO GUI
    ↓
A-CONTROL
    ↓
WanGP Client
    ↓
C-CLOUD WanGP
    ↓
GPU / Models
    ↓
LTT R2 / History
```

### Một đường duy nhất
Sau cutover:
- không `lttvideo-worker` runtime;
- không `video_gateway` runtime;
- không custom ComfyUI video worker;
- không provider cascade sang legacy;
- không fallback engine.

### Boundary
LTT sở hữu:
- GUI;
- auth/role;
- job queue;
- media ownership;
- R2/history;
- Quality Profiles;
- cloud lifecycle;
- budget/release policy.

WanGP/C-CLOUD sở hữu:
- model runtime;
- model metadata/capability;
- preprocess/postprocess;
- inference;
- progress/cancel primitive;
- Deepy;
- selected models/GPU.

WanGP WebUI chỉ là **operator/debug console**, không nằm trên user production path.

---

## Luật xóa legacy — đã sửa ở V2.1

Không xóa legacy ngay sau khi WanGP tự chạy.

Thứ tự đúng:

```text
WanGP engine acceptance
        ↓
Lock One Engine
        ↓
Build LTT WanGP path
        ↓
REAL LTT↔WanGP E2E PASS
        ↓
Cutover
        ↓
DELETE legacy runtime
```

Lý do: WanGP tự generate được chưa chứng minh LTT auth/R2/cancel/job contract đã chạy thật.

Legacy có thể tồn tại **tạm thời trong source branch** trong giai đoạn xây replacement,
nhưng replacement **không được fallback/cascade sang legacy**.

---

## Commercial gate

WanGP hiện dùng cho private/internal LTT.
Giữ:
- `public=False`;
- `api_exposed=False`;
- external paid access = disabled;
- commercial gate = CLOSED.

Model/weight licenses vẫn audit riêng.
