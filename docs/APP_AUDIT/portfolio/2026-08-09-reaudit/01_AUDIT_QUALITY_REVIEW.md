# Kiểm định chất lượng chính cuộc audit H27

## Sai lệch trọng yếu

| ID | Sev | Phát hiện | Bằng chứng | Kết luận |
|---|---|---|---|---|
| RA-001 | P1 | Source/test/browser từng bị ghi là E4 | Hai `evidence/INDEX.md` của Upscale và Seedance | Sai taxonomy; đã sửa E1/E2/E3 |
| RA-002 | P1 | E84–95 không thể có khi không có telemetry/user test E4 | LTT-AQA §5; scorecard 12 hồ sơ | Recompute E38–61 |
| RA-003 | P1 | `DONE` được suy từ đủ file, không từ PASS A0–A10 | Dashboard H27 và plan H27.10 | H27 chỉ first-pass baseline |
| RA-004 | P2 | A2 của Social/Demo/Kịch bản/Media quá mỏng để nói “mọi control” | Registry lần lượt 12/9/11/11 dòng bảng | PARTIAL; phải lập control-level ledger |
| RA-005 | P2 | A4 maintenance/runtime thiếu snapshot matrix có nguồn | Social 3 dòng URL; ba hồ sơ còn lại 0 | M của bốn hồ sơ là provisional |
| RA-006 | P2 | Route crawl đếm cả control shell | Browser DOM | Không dùng số lượng DOM làm coverage A2 |
| RA-007 | P2 | Fixture navigation time không phải Core Web Vitals P75 | Local route crawl | G7 vẫn UNKNOWN |
| RA-008 | P2 | 404 Demo phát console resource error dự kiến | `/demo` trả 404 | Không coi là JS regression |
| RA-009 | P2 | Hồ sơ chưa có E4 nhưng diễn đạt confidence gần tuyệt đối | 12 scorecard | Cấm dùng “production verified” |
| RA-010 | P3 | Tên trường Q/E không nhất quán giữa hồ sơ | `04_SCORECARD.md` | Chuẩn hóa ở lần audit kế |

## Công thức E được áp lại

`E = Σ(weight × evidence_level / 4) / Σ(weight)`.

- E1: source/tài liệu chính thức.
- E2: unit/integration/API test đã chạy.
- E3: browser hoặc local runtime thật.
- E4: telemetry production/canary có đại diện hoặc user test thật.

Không có app nào trong H27 có E4 đủ để dùng cho toàn nhóm. Do đó E tối đa lý
thuyết của hồ sơ hiện tại là 75, và thực tế thấp hơn vì market/provider/ops chỉ
có E1/E2. Q và finding không bị tự động thay đổi bởi việc sửa E.

