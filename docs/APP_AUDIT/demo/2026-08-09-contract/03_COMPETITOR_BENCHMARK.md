# 03 — Benchmark hợp đồng nội bộ

Không có customer market cùng JTBD. M được chấm theo baseline synthetic canary:
định danh transaction, chạy lịch, đo latency, dependency health, alert,
artifact check, cleanup, no production side effect.

| Capability | LTT 0–3 | Baseline | Quyết định |
|---|---:|---:|---|
| deterministic zero-provider handler | 3 | 3 | KEEP |
| queue + credit settlement | 3 | 3 | KEEP |
| role isolation | 3 | 3 | KEEP |
| scheduled synthetic run | 0 | 2 | BUILD chọn lọc |
| artifact/storage verification | 0 | 2 | EXTEND |
| latency/SLO/alert | 1 | 3 | EXTEND |
| cleanup/idempotent fixture | 2 | 3 | FIX |

**M70** là fit của diagnostic contract, không phải vị thế sản phẩm customer.

