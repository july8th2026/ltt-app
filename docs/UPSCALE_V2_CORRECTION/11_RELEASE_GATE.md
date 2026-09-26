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

## Áp dụng cho nhánh sửa lỗi này

Nhánh `claude/upscale-video-v2-correction-5fa61a` sửa `apps/upscalevideo/*.py`
(8 tệp) + thêm `tests/test_4904_upscale_correction.py` + tài liệu dưới
`docs/UPSCALE_V2_CORRECTION/`. Trước khi nhánh này (hoặc plan chứa nó) được
coi là sẵn sàng deploy:

- Test nhắm cụm `upscalevideo` phải xanh (`tools\thanh_phan.py --test upscalevideo`
  → `pytest tests/test_4904_upscale_correction.py -q` và mọi test cũ của app,
  ví dụ `test_82_upscalevideo.py`, `test_171_upscale_h32.py`) — **CHƯA CHẠY
  trong phiên viết tài liệu này** (phiên này chỉ đọc/ghi tài liệu, không chạy
  pytest/GPU/ffmpeg, theo đúng giới hạn được giao).
- Gate đầy đủ (L1/L2 hoặc bước cuối-plan tuỳ theo phase của plan) phải XANH
  trên đúng SHA gộp vào `main` trước khi deploy máy A — **CHƯA CHẠY**, vì lý do
  trên.
- ⛔ Không dùng kết quả `tests/test_4904_upscale_correction.py` như một gate
  thay thế: nó khoá 8/13 bất biến bằng mock (không chạm GPU/ffmpeg thật), là
  điều kiện **cần**, không phải điều kiện **đủ**.

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

## Tóm tắt điều kiện release cho nhánh này

| Điều kiện | Trạng thái tại thời điểm viết tài liệu (2026-09-26) |
|---|---|
| Test nhắm `upscalevideo` xanh | CHƯA CHẠY (ngoài phạm vi phiên viết docs) |
| Gate (L1/L2/cuối-plan) xanh trên SHA deploy | CHƯA CHẠY |
| `git status --porcelain` rỗng ở cây chính | Không kiểm — phiên này chạy trong worktree, không phải cây chính |
| Bản lùi (`app.previous`) đã biết trước deploy | Chưa áp dụng — chưa tới bước deploy |
| Báo các phiên đang chạy trước deploy | Chưa áp dụng |

⇒ Nhánh **chưa đủ điều kiện deploy** tại thời điểm viết tệp này; đây là mô tả
điều kiện cần thoả, không phải xác nhận đã thoả.
