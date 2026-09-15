# LTTCODE — BẢNG TIẾN ĐỘ (living)

> Cập nhật 2026-09-15 (phiên tiếp quản). % là ước lượng theo effort-share (cột "Trọng số").
> Nguồn: `MASTER_IMPLEMENTATION_PLAN.md`, `DECISION_LOCK.md`.
> **Tổng tiến độ ≈ 39%.**
>
> ⭐ 15/09: **offline installer** (P06, LTTCODEAPP `5e69a24`). `bundle.resources`
> (map) gom `node.exe` + `node_modules` + `profile-template` vào
> `resources/sidecar/`; `beforeBuildCommand` chạy `stage:sidecar` (build plugin
> + `npm install` sidecar + materialize). Phát hiện + sửa bug thật: npm để
> `@ltt/dsh-llm-ltt` là **symlink** (`file:` dep), Tauri bundler KHÔNG theo
> symlink nên plugin bị **loại khỏi bundle** → DSH boot chết "Cannot find
> package". `materialize-plugin.mjs` thay symlink bằng bản copy thật của files
> runtime. Verify `tauri build` (exit 0): NSIS gom đủ 4 anchor
> (node.exe, dsh/lib/bin.js, @ltt/dsh-llm-ltt 50 file, profile-template/lttcode).
> `resource_dir()` trên Windows = thư mục exe ($INSTDIR) → khớp layout.
>
> ⭐ 14/09: **khóa thử `ltt_tk_` đã mint** (tool `khoa_thu_api.ps1`, mode test),
> **đo wire thật** + **probe adapter end-to-end XANH** trên `/api/v1/messages`
> qua Cloudflare (ltt-3.8 & ltt-3.5): đúng chuỗi StreamChunk, usage-before-finish,
> khóa sai → AUTH. Test mode không chạm GPU/tiền nên chưa kiểm nội dung model
> (tools/reasoning) — cần khóa LIVE cho các ca đó.
>
> ⭐ 14/09: **DSH sidecar integration PROVEN** (LTTCODEAPP `0ba745c`):
> `dsh web --profile lttcode` boot ~10s, nạp plugin `@ltt/dsh-llm-ltt`,
> provider mặc định `ltt-official/ltt-3.8`, in ready-line
> `dsh web: http://127.0.0.1:<port>/?token=`. Đóng gói = bundle node.exe thật
> (SEA/pkg KHÔNG dùng được — DSH ESM + import plugin động từ đĩa).
> ⚠️ 15/09: **test key `ltt_tk_` đã mất** (scratchpad dọn) — mint lại được qua
> `setup/khoa_thu_api.ps1` (elevated). Không chặn P06, chỉ chặn ca model P03/P04.
>
> ⭐ 15/09: **webview CHẠY DSH UI** (P06 milestone). WebView2 KHÔNG gửi cookie
> `SameSite=Strict` qua redirect 303 (token URL → `/`) nên webview dính trang
> 401. Sửa: patch DSH mint cookie `SameSite=Lax` (`patch-dsh-cookies.mjs`,
> chạy qua `postinstall`) — Lax được gửi qua redirect same-site. Không cần
> `set_cookie` từ host (gọi COM đồng bộ từ thread nền = deadlock). Verify:
> DOM probe body 50KB (UI thật) ≠ 133B (trang 401).

| Phase / Hạng mục | Trọng số | % | Trạng thái | Bằng chứng / Ghi chú |
|---|---:|---:|---|---|
| **P00** Research & Baseline | 6 | 100% | ✅ xong | `RESEARCH_BASELINE.md` + ma trận tương thích |
| **P01** Decision Lock + Architecture Freeze | 5 | 100% | ✅ xong | `DECISION_LOCK.md` (D01–D19) + `MASTER_ARCHITECTURE.md` |
| **P02** Harness Pin & Reproducible Baseline | 4 | 95% | 🟢 gần xong | Repo LTTCODEAPP + `dsh.pin.json` (fb2c4b9e) + CI pushed; Tauri scaffold + baseline build 5m09s + NSIS/MSI + app CHẠY; **còn:** ghi nhận build tái lập cuối |
| **P03** LTT Compatibility Harness | 6 | 55% | 🟡 đang | ca protocol (text/stream/order/auth) **XANH thật** ở test mode 2 model; **còn:** ca model (tools/reasoning/vision/credit) cần khóa LIVE |
| **P04** LTT Provider Adapter `llm-ltt` | 8 | 92% | 🟢 gần xong | **typecheck + probe end-to-end XANH** (dsh-llm@0.1.5-rc.2, API sống); **còn:** catalog enrich (D16), vision map, verify tool-call với khóa LIVE |
| **P05** LTT Auth & Bootstrap (MVP) | 7 | 15% | 🟡 đang | credential-resolve đã code trong adapter; **còn:** UI dán key, `/client/bootstrap`, DPAPI |
| **P06** Desktop Runtime / Sidecar (Tauri) | 12 | 92% | 🟢 gần xong | Scaffold + build + **sidecar boot PROVEN** (`0ba745c`) + **Rust spawn/parse ready-line** + **webview CHẠY DSH UI** (Lax-cookie patch, DOM probe 50KB body ≠ 401) + capability 127.0.0.1 (csp null) + **offline installer** (`5e69a24`: `bundle.resources` gom node.exe+node_modules+profile+plugin vào `resources/sidecar/`, `stage:sidecar`, materialize plugin symlink→copy thật, verify NSIS 4 anchor); **còn:** logs tách user-data + multi-instance, Job Object (no-orphan crash-case) |
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

## Chặn hiện tại (15/09)
1. **Test key `ltt_tk_` MẤT** — mint lại qua `setup/khoa_thu_api.ps1` (elevated);
   chỉ chặn ca model P03/P04, KHÔNG chặn P06.
2. **Cert EV** (P10) · **R2/CDN** (P09) — logistics của chủ.
3. **Không đọc được GitHub Actions qua MCP** — CI Tauri/Rust chỉ verify ở CI;
   cần chủ xem Actions hoặc chạy build local (đã chạy local được 14/09).
4. Backend **device-flow OAuth** (P05 nợ, không chặn MVP).

## Cột mốc tiếp theo (15/09, phiên tiếp quản)
**P06 xong** (bundle node.exe + Rust spawn + webview) → **P05** auth MVP →
**P03/P04 ca model** (sau khi mint lại khóa) → **P07** UX → **P08** → chuỗi
nghiệm thu §38. Chi tiết: `PLAN_TRIEN_KHAI.md`.
