# LTT VIDEO V2.1 — WanGP ONE ENGINE

Chương trình xây lại đường video của LTT quanh **một engine duy nhất: WanGP**
chạy trên C-CLOUD, GUI và mọi trạng thái sản phẩm ở lại A-CONTROL.

## Đọc theo thứ tự này

| # | Tệp | Trả lời câu gì |
|---|---|---|
| 1 | **`PROJECT_STATE.md`** | đang ở phase nào, nhánh/worktree nào, việc kế tiếp chính xác là gì |
| 2 | `LEGACY_INVENTORY.md` | legacy nằm ở đâu, phân loại, bằng chứng path-level |
| 3 | `DECISIONS.md` | quyết định đã chốt + quyết định phát sinh ở kho này |
| 4 | `PACK_V2_1/` | bản gốc của pack (kiến trúc, 10 prompt, checklist) |

## `PACK_V2_1/` là bản chép **nguyên văn**

Nguồn: `G:\My Drive\AI\A LTT AII\LTT_VIDEO_WANGP_ONE_ENGINE_PROMPT_PACK_V2_1`.

Chép vào kho ở P00 vì pack nói *state phải nằm trên filesystem, không nằm trong
trí nhớ chat* — mà một ổ Google Drive không phải filesystem của kho này.

22 tệp, **byte-for-byte y hệt bản gốc**. `SHA256SUMS.txt` đi kèm vẫn kiểm được
tại chỗ (21/21 khớp lúc chép, 2026-09-06):

```bash
cd docs/VIDEO_AI_V2/PACK_V2_1 && sha256sum -c SHA256SUMS.txt
```

⛔ Đừng sửa gì trong `PACK_V2_1/`. Nó là **đầu vào**, không phải trạng thái.
Thứ trôi theo thời gian sống ở ba tệp trên.

## Luật một-phase-một-chat

Pack yêu cầu mỗi phase một chat mới. Bộ nhớ giữa các phase là
`PROJECT_STATE.md` + Git, **không** phải lịch sử chat.

```
P00 audit legacy        ->  P01 ghim WanGP vanilla      ->  P02 nghiem thu engine
->  P03 khoa mot engine  ->  P04 dung app LTT + client   ->  P05 E2E that + R2 + cancel
->  P06 cutover + xoa legacy  ->  P07 quality + Deepy    ->  P08 vong doi cloud
->  P09 E2E noi bo cuoi
```

⛔ **Xoá legacy ở P06, không sớm hơn.** WanGP tự chạy được chưa chứng minh
auth/R2/cancel/hợp đồng job của LTT đã chạy thật.

## Ba ranh giới cứng

- **B-LAN không đụng** (`D-V2-008`) — máy B ngoài phạm vi chương trình này.
- **Không fallback sang legacy** (`D-V2-010`) — mã V2 không được gọi/cascade sang
  runtime cũ, kể cả trong lúc đang xây.
- **Cổng thương mại ĐÓNG** (`D-V2-011`) — nội bộ, `public=False`,
  `api_exposed=False`.
