# 03 — Competitor Benchmark

## Phạm vi bằng chứng

Benchmark hands-on vòng này tập trung PlenX vì đây là sản phẩm người dùng chỉ định và đã đăng nhập. Tài liệu lịch sử có đối chiếu FLORA/InvokeAI/ComfyUI nhưng chưa được browser re-verify ngày 2026-08-04; do đó không dùng chúng để nâng Evidence Confidence.

## Capability matrix (0 vắng · 1 yếu · 2 ngang chuẩn · 3 tốt hơn)

| Capability/JTBD | Loại | Trọng số | PlenX | LTT hiện tại | LTT đích |
|---|---|---:|---:|---:|---:|
| Visual DAG editor | TABLE_STAKES | 10 | 3 | 2 | 3 |
| Typed graph/validation | TABLE_STAKES | 10 | 1 | 3 | 3 |
| Inline node composer | TABLE_STAKES | 8 | 3 | 1 | 3 |
| Multi-model capability schema | TABLE_STAKES | 9 | 3 | 1 | 3 |
| Node/media breadth | TABLE_STAKES | 10 | 3 | 2 | 3 |
| Run node/frame/workflow | TABLE_STAKES | 8 | 3 | 1 | 3 |
| Artifacts/log/history | TABLE_STAKES | 8 | 3 | 2 | 3 |
| Pages/frames/templates | TABLE_STAKES | 7 | 3 | 1 | 3 |
| Assistant/pattern grounding | TABLE_STAKES | 8 | 3 | 1 | 3 |
| Share/clone/collaboration | TABLE_STAKES | 5 | 2 | 0 | 3 |
| Quote/approval/atomic credit | DIFFERENTIATOR | 7 | 1 | 3 | 3 |
| Bounded verify/retry/error branch | DIFFERENTIATOR | 5 | 1 | 3 | 3 |
| Specialized LTT tools | DIFFERENTIATOR | 5 | 1 | 3 | 3 |
| Ownership/conflict/recovery | DIFFERENTIATOR | 5 | 1 | 3 | 3 |

## Kết luận thị trường

- PlenX thắng rõ ở breadth và direct-manipulation UX.
- LTT thắng rõ ở correctness, money safety và deterministic execution.
- Xây lại runtime theo PlenX sẽ làm mất lợi thế; đúng hướng là **đưa trải nghiệm PlenX lên trên runtime LTT**.
- “100%” nên đo bằng coverage của capability đã khóa và acceptance test, không bằng số model marketing hoặc pixel giống nhận diện PlenX.

## Unknown cần benchmark tiếp

- Chất lượng output/cost/P95 của cùng model/provider vì vòng này không tiêu credit.
- Mobile/tablet thực tế của PlenX.
- ACL share, revoke, clone ownership và abuse limits.
- Assistant thực sự gọi 5 tool/RAG patterns ở phiên bản hiện tại; tài liệu lịch sử có E1 nhưng thao tác nút bị panel ngoài viewport, chưa phát sinh paid call.
- Marketplace/template monetization và team collaboration.
