# 06 — Options & Decision Gate

## Ba phương án

| Tiêu chí (trọng số) | A — Restyle | B — Functional parity + LTT safety | C — Clone-all một lần |
|---|---:|---:|---:|
| Giá trị người dùng 25% | 5 | 9 | 9 |
| Coverage 20% | 3 | 10 | 10 |
| Reuse nội tại 15% | 8 | 10 | 5 |
| Rủi ro thấp 15% | 9 | 8 | 3 |
| Time-to-value 10% | 9 | 8 | 3 |
| Cost/ops 10% | 8 | 8 | 3 |
| Confidence 5% | 8 | 8 | 4 |
| **Điểm /10** | **6.7** | **9.0** | **5.9** |

**Khuyến nghị:** B. Triển khai tuần tự, parity bằng acceptance matrix; giữ runtime, safety và các differentiator LTT.

## Quyết định cần khóa trước BUILD

| ID | Câu hỏi | A | B | C | Khuyến nghị |
|---|---|---|---|---|---|
| D1 | “Giống 100%” nghĩa gì? | pixel clone | functional parity, LTT brand/safety | toàn bộ model/provider | **B** |
| D2 | Canvas schema | vá v1 | v2 lossless + migration | thay runtime | **B** |
| D3 | Run scope | full workflow | node/frame/selection/full | node tự chạy không quote | **B** |
| D4 | Composer | Inspector | inline compact + Inspector advanced | node card khổng lồ | **B** |
| D5 | Provider rollout | khai hết ngay | capability/licence/quality/cost gate từng provider | chỉ provider hiện tại | **B** |
| D6 | Audio | bỏ | TTS/voice first, music later | full audio studio ngay | **B** |
| D7 | Collaboration | public link mặc định | private + ACL/revoke/audit | hoãn toàn bộ | **B** |
| D8 | Assistant apply | tự sửa graph | preview diff + user apply | chỉ chat | **B** |
| D9 | Mobile | full editor | inspect/approve/run first | chỉ desktop | **B** |
| D10 | Templates | chỉ local JSON | page/frame/workflow library | marketplace ngay | **B** |
| D11 | Compatibility | copy PlenX JSON | LTT v2 + importer adapter | bỏ import/export | **B** |
| D12 | Release | big-bang | feature flags + canary theo phase | deploy trực tiếp | **B** |

Nếu người dùng không đổi lựa chọn, plan mặc định dùng toàn bộ phương án **B**. Đây là logic đề xuất, chưa phải quyết định kiến trúc có hiệu lực trong `QUYET_DINH_NEN_TANG.md`.
