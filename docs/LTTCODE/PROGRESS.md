# LTTCODE — BẢNG TIẾN ĐỘ (living)

> Cập nhật 2026-09-14. % là ước lượng theo effort-share (cột "Trọng số").
> Nguồn: `MASTER_IMPLEMENTATION_PLAN.md`, `DECISION_LOCK.md`.
> **Tổng tiến độ ≈ 29%.**
>
> ⭐ 14/09: **khóa thử `ltt_tk_` đã mint** (tool `khoa_thu_api.py`, mode test),
> **đo wire thật** + **probe adapter end-to-end XANH** trên `/api/v1/messages`
> qua Cloudflare (ltt-3.8 & ltt-3.5): đúng chuỗi StreamChunk, usage-before-finish,
> khóa sai → AUTH. Test mode không chạm GPU/tiền nên chưa kiểm nội dung model
> (tools/reasoning) — cần khóa LIVE cho các ca đó.

| Phase / Hạng mục | Trọng số | % | Trạng thái | Bằng chứng / Ghi chú |
|---|---:|---:|---|---|
| **P00** Research & Baseline | 6 | 100% | ✅ xong | `RESEARCH_BASELINE.md` + ma trận tương thích |
| **P01** Decision Lock + Architecture Freeze | 5 | 100% | ✅ xong | `DECISION_LOCK.md` (D01–D19) + `MASTER_ARCHITECTURE.md` |
| **P02** Harness Pin & Reproducible Baseline | 4 | 70% | 🟡 đang | Repo LTTCODEAPP + `dsh.pin.json` (fb2c4b9e) + CI skeleton pushed; **còn:** scaffold Tauri thật + build tái lập |
| **P03** LTT Compatibility Harness | 6 | 55% | 🟡 đang | ca protocol (text/stream/order/auth) **XANH thật** ở test mode 2 model; **còn:** ca model (tools/reasoning/vision/credit) cần khóa LIVE |
| **P04** LTT Provider Adapter `llm-ltt` | 8 | 92% | 🟢 gần xong | **typecheck + probe end-to-end XANH** (dsh-llm@0.1.5-rc.2, API sống); **còn:** catalog enrich (D16), vision map, verify tool-call với khóa LIVE |
| **P05** LTT Auth & Bootstrap (MVP) | 7 | 15% | 🟡 đang | credential-resolve đã code trong adapter; **còn:** UI dán key, `/client/bootstrap`, DPAPI |
| **P06** Desktop Runtime / Sidecar (Tauri) | 12 | 0% | ⬜ chưa | thiết kế xong (ARCH §4); build trên máy này (đã được phép) |
| **P07** Core Coding Agent UX | 12 | 0% | ⬜ chưa | — |
| **P08** Session / Sandbox / Approval | 8 | 5% | ⬜ chưa | quyết định D19; chưa code |
| **P09** Release Control Plane (server) | 8 | 5% | ⬜ chưa | thiết kế D14; cần R2/CDN |
| **P10** Updater / Signing / Migration | 9 | 5% | ⬜ chưa | CI skeleton + D13; cần cert EV |
| **P11** Security / Supply Chain | 5 | 10% | 🟡 đang | .gitignore/secret rules; SBOM/audit sau |
| **P12** Beta Acceptance (§38 + failure §39) | 6 | 0% | ⬜ chưa | chuỗi nghiệm thu đầu-cuối |
| **P13** Stable Release | 4 | 0% | ⬜ chưa | promote qua ladder |

## Workstream ngang (không tính trùng vào tổng)
| Hạng mục | % | Ghi chú |
|---|---:|---|
| Tài liệu (docs/LTTCODE) | 75% | 5 tài liệu + progress; cập nhật theo phase |
| CI/CD | 20% | typecheck job xanh; build/sign job chờ P06/P10 |
| Repo & hạ tầng | 50% | LTTCODEAPP private tạo + baseline; R2/CDN chưa |

## Chặn hiện tại
1. **Khóa thử `ltt_tk_`** cho P03 live (đang mint bằng `tools/khoa_thu_api.py`).
2. **Cert EV** (P10) · **R2/CDN** (P09) — logistics.
3. Backend **device-flow OAuth** (P05 nợ, không chặn MVP).

## Cột mốc tiếp theo
P03 chạy thật (khóa) → P06 Tauri host + sidecar (build trên máy này) → P07 UX →
chuỗi nghiệm thu §38.
