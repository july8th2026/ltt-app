# 05 — Findings

| ID | Sev | Finding | Trạng thái/acceptance |
|---|---|---|---|
| LA-01 | P1 | H16 giữ header/footer, ba cột cố định, stage ~43% tại 1366×768 | RESOLVED H17: stage toàn viewport |
| LA-02 | P1 | toolbar tràn ngang, control ngoài viewport | RESOLVED: topbar 48 px + run drawer |
| LA-03 | P1 | form nằm trong node, eye travel và card phình | RESOLVED: visual-first + composer/advanced |
| LA-04 | P1 | ReactFlow handle 6 px khó thao tác | RESOLVED: port 44×44 + picker typed |
| LA-05 | P2 | Palette thiếu discovery nhanh | RESOLVED: drawer + search catalog |
| LA-06 | P2 | Glyph rail tối giản; người mới phụ thuộc tooltip | ACCEPT controlled launch; đo rage-click/tooltip rồi cân nhắc SVG icon set |
| LA-07 | P1 | Bundle H17 chưa authenticated-smoke trên production | OPEN release gate; không mở rộng rollout trước PASS |
| LA-08 | P2 | Chưa có usability study bên ngoài | OPEN measurement; không chặn controlled launch, chặn tuyên bố ≥90% task success |

P0 = 0. Không có finding cho phép bỏ quote/approval, nới validation hay tải model
không qua provider gate.
