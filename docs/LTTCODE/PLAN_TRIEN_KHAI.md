# LTTCODE — KẾ HOẠCH TRIỂN KHAI CHI TIẾT (living)

> Cập nhật 2026-09-15 (phiên tiếp quản). "Thời gian XD" = ước tính **giờ làm việc của agent** trên
> máy này (không phải người). Cột % theo effort-share.
> **Tổng tiến độ ≈ 37% · Còn lại ≈ 82 giờ XD** (chưa gồm logistics: cert EV, R2/CDN, khóa LIVE).
> ⭐ 14/09: baseline Tauri **build (5m09s) + installer NSIS/MSI + app CHẠY** (title LTTCODE, WebView2 OK).
> ⭐⭐ 14/09: **DSH sidecar integration PROVEN** — `dsh web --profile lttcode` boot ~10s, nạp plugin `llm-ltt`, provider mặc định `ltt-official`, in ready-line handshake. Đóng gói = bundle node.exe thật (SEA/pkg không dùng được).
> ⚠️ 15/09: test key `ltt_tk_` **mất** (scratchpad dọn) — mint lại qua `setup/khoa_thu_api.ps1` (elevated); chỉ chặn ca model P03/P04.
> ⭐ 15/09: **webview CHẠY DSH UI** (P06) — WebView2 bỏ cookie `Strict` qua redirect 303 → trang 401; sửa bằng patch DSH mint `SameSite=Lax` (`patch-dsh-cookies.mjs` qua `postinstall`).
> Nguồn: `MASTER_IMPLEMENTATION_PLAN.md`, `DECISION_LOCK.md`, `PROGRESS.md`.

## Tổng quan hạng mục

| # | Hạng mục | % | Còn (giờ) | Trạng thái |
|---|---|---:|---:|---|
| P00 | Research & Baseline | 100% | 0 | ✅ |
| P01 | Decision Lock + Architecture | 100% | 0 | ✅ |
| P02 | Harness Pin & Reproducible Baseline | 90% | ~0.5 | 🟢 |
| P03 | LTT Compatibility Harness | 55% | ~3 | 🟡 |
| P04 | LTT Provider Adapter `llm-ltt` | 92% | ~4 | 🟢 |
| P05 | LTT Auth & Bootstrap (MVP) | 15% | ~10 | 🟡 |
| P06 | Desktop Runtime / Sidecar (Tauri) | 75% | ~4 | 🟡 build+run+DSH-boot+Rust spawn+**webview CHẠY UI** OK; còn bundle resources+Job Object |
| P07 | Core Coding Agent UX | 0% | ~12 | ⬜ |
| P08 | Session / Sandbox / Approval | 5% | ~9 | ⬜ |
| P09 | Release Control Plane (server) | 5% | ~15 | ⬜ (chờ R2/CDN) |
| P10 | Updater / Signing / Migration | 5% | ~13 | ⬜ (chờ cert EV) |
| P11 | Security / Supply Chain | 10% | ~8 | 🟡 |
| P12 | Beta Acceptance (§38 + §39) | 0% | ~9 | ⬜ |
| P13 | Stable Release | 0% | ~2 | ⬜ |
| | **TỔNG** | **~29%** | **~100** | |

---

## Chi tiết theo hạng mục

### P02 — Harness Pin & Reproducible Baseline · 70% · còn ~1h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Tạo repo LTTCODEAPP + baseline | 100% | 0 | ✅ pushed |
| `dsh.pin.json` pin `dsh-v0.1.5-rc.2` (fb2c4b9e) | 100% | 0 | ✅ |
| CI skeleton | 100% | 0 | ✅ |
| Scaffold Tauri v2 host | 100% | 0 | ✅ (create-tauri-app) |
| Build tái lập xác thực | 40% | 1 | 🟡 build baseline đang chạy |

### P03 — LTT Compatibility Harness · 55% · còn ~3h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Runner `collect()` + test-plan 15 ca | 100% | 0 | ✅ |
| Ca protocol (text/stream/order/auth) — test mode | 100% | 0 | ✅ XANH thật 2 model |
| Đủ 15 ca (code) | 40% | 2 | 🟡 |
| Ca model thật (tools/reasoning/vision/credit) | 0% | 1 | ⬜ **cần khóa LIVE** |

### P04 — LTT Provider Adapter `llm-ltt` · 92% · còn ~4h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| stream()/translate/sse/messages/errors/plugin | 100% | 0 | ✅ typecheck + probe e2e |
| Catalog enrich (resolveModel/listModels ← /models, D16) | 0% | 2 | ⬜ cần shape LlmModelInfo |
| Vision content mapping (image/file block) | 0% | 1.5 | ⬜ VERIFY |
| Verify tool-call thật | 0% | 0.5 | ⬜ cần khóa LIVE |

### P05 — LTT Auth & Bootstrap (MVP) · 15% · còn ~10h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Credential resolve trong adapter | 100% | 0 | ✅ |
| Lưu key DPAPI/Credential Manager (Tauri) | 0% | 3 | ⬜ |
| UI dán key + logout | 0% | 2 | ⬜ |
| `/client/bootstrap` (backend LTTSTUDIOSAPP + gate) | 0% | 4 | ⬜ chạm platform |
| Đấu bootstrap vào app (min-version/flags/models) | 0% | 1 | ⬜ |
| *(nợ) Device-flow OAuth backend* | 0% | ~16 | ⬜ sau MVP |

### P06 — Desktop Runtime / Sidecar (Tauri) · 75% · còn ~4h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Scaffold + rename LTTCODE + config NSIS | 100% | 0 | ✅ |
| Build baseline (xác thực toolchain) | 100% | 0 | ✅ 5m09s, NSIS+MSI, app chạy (14/09) |
| DSH sidecar boot PROVEN (recipe) | 100% | 0 | ✅ `0ba745c`; pkg/SEA loại bỏ — bundle node.exe thật |
| Rust spawn + parse ready-line (sidecar.rs) | 100% | 0 | ✅ spawn `node.exe`, parse `dsh web:` line, không có `/health` (ready-line = handshake) |
| Lifecycle: crash-recovery + shutdown sạch | 100% | 0 | ✅ backoff restart (max 5) + kill-on-exit; ⚠️ Job Object chưa (deviation, ghi ở PROGRESS) |
| Webview trỏ authenticated URL + capability 127.0.0.1 | 100% | 0 | ✅ Lax-cookie patch (`patch-dsh-cookies.mjs`); webview CHẠY UI thật (DOM 50KB); csp null |
| Vendor node.exe + stage cây sidecar vào resources | 0% | 2 | ⬜ offline installer; node.exe gitignored, provision ở staging |
| Logs tách user-data + multi-instance | 0% | 1 | ⬜ |

### P07 — Core Coding Agent UX · 0% · còn ~12h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Quyết định tái dùng Web UI của DSH vs custom | 0% | 2 | ⬜ (ưu tiên tái dùng) |
| Chat + tool-call/kết quả + streaming/reasoning | 0% | 6 | ⬜ phần lớn tái dùng DSH |
| Diff/approve + mở repo/cây file | 0% | 2 | ⬜ |
| Branding LTTCODE | 0% | 2 | ⬜ |

### P08 — Session / Sandbox / Approval · 5% · còn ~9h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Session persist (lưu ý format DSH forward-incompat) | 0% | 3 | ⬜ |
| Sandbox + shell approval mặc định (D19) | 0% | 4 | ⬜ đối chiếu cộng đồng |
| Workspace trust | 0% | 2 | ⬜ |

### P09 — Release Control Plane (server) · 5% · còn ~15h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Dựng LTT Release Server (API + R2) | 0% | 8 | ⬜ **cần R2/CDN** |
| Kênh dev/beta/stable + % rollout ladder + kill switch | 0% | 5 | ⬜ |
| Cohort ẩn danh ổn định + min-supported | 0% | 2 | ⬜ |

### P10 — Updater / Signing / Migration · 5% · còn ~13h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Tauri updater plugin (notify-only, trỏ server) | 0% | 3 | ⬜ |
| Minisign keygen + ký updater | 0% | 3 | ⬜ |
| Authenticode ký installer | 0% | 3 | ⬜ **cần cert EV** |
| Migration backup→verify→migrate→mark | 0% | 4 | ⬜ |

### P11 — Security / Supply Chain · 10% · còn ~8h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Secret handling (.gitignore, không log key) | 60% | 1 | 🟡 |
| Audit Tauri capabilities/IPC/localhost | 0% | 3 | ⬜ |
| SBOM + SHA256 + provenance mỗi release | 0% | 3 | ⬜ |
| Audit npm/crate/license | 0% | 1 | ⬜ |

### P12 — Beta Acceptance · 0% · còn ~9h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Chuỗi §38 đầu-cuối trên máy sạch | 0% | 4 | ⬜ |
| Bộ failure §39 (17 ca) | 0% | 5 | ⬜ |

### P13 — Stable Release · 0% · còn ~2h
| Mục triển khai | % | Giờ | Ghi chú |
|---|---:|---:|---|
| Promote qua ladder + scorecard §40 | 0% | 2 | ⬜ |

---

## Đường tới hạn (critical path) & mốc
1. **P06** sidecar+host (build được app chạy) → **P07** UX → **P08** session/approval
   ⇒ MVP chạy được cục bộ. (~35h)
2. **P05** auth + bootstrap ⇒ đăng nhập + server-driven. (~10h)
3. **P09+P10** release server + updater/ký ⇒ auto-update. (~28h, chờ R2 + cert EV)
4. **P12** nghiệm thu §38/§39 ⇒ đủ điều kiện beta→stable. (~11h)

## Logistics chặn (không phải giờ code — cần ông)
| Cần | Cho | Ảnh hưởng |
|---|---|---|
| **Khóa LIVE** `ltt_sk_`/`ltt_tk_` live | P03/P04 ca model thật | verify tool-calling/reasoning |
| **Cert EV** Authenticode | P10 | ký installer, bỏ SmartScreen |
| **R2 bucket + domain CDN** | P09 | release server + phân phối |
| **Backend device-flow OAuth** | P05 (nợ) | nâng auth sau MVP |

## Ước lượng lịch
- **~100 giờ XD** còn lại. Chạy tự động liên tục trên máy này (có xen build nặng),
  ước ~**2–3 tuần lịch** nếu logistics (R2, cert EV) sẵn sàng song song; phần
  MVP-chạy-cục-bộ (P06+P07+P08, ~35h) có thể xong trước, ~**1 tuần**.
