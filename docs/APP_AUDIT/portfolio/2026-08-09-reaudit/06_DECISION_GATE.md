# Decision Gate sau re-audit

Khuyến nghị A vẫn đúng nhưng phải thêm “Audit Integrity Gate” trước BUILD:

1. Dùng điểm E hiệu chỉnh; cấm viện dẫn E cũ 84–95.
2. Không gọi H27/H28 là audit triệt để khi A2/A4/E4 còn PARTIAL/UNKNOWN.
3. Dừng release ở 3 P0; thứ tự BUILD không đổi: Socialbot authorization →
   Agent exactly-once → Media SSRF → Chat provider/path/money.
4. Hai finding UI mới vào backlog của đúng app, không chen trước P0/P1.
5. M provisional không được dùng để duyệt feature parity.
6. Mọi BUILD sau này phải có targeted test + browser desktop/mobile; full gate
   ở release/high-risk shared contract.

H28 không cấp quyền BUILD hoặc DEPLOY.

