"""Tầng nghiệp vụ của app VPS.

`routes.py` chỉ lo HTTP; mọi quy tắc sống ở đây (AGENTS §8.1). App có nhiều miền
rõ rệt — nói chuyện với Proxmox, xếp chỗ, cấp cổng, vòng đời, tiền — nên dùng
`services/` chứ không dồn vào một `features.py`.
"""
