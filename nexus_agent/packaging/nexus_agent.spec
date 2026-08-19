# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec cho agent Nexus — one-dir, KHÔNG UPX (N3.3b).

Ba lựa chọn ở đây đều có test chốt trong `tests/test_234_nexus_packaging.py`,
vì chúng là loại quyết định "đổi cho tiện" mà hệ quả chỉ hiện trên máy khách:

* **one-dir, không one-file.** one-file giải nén ra thư mục tạm rồi chạy từ đó
  mỗi lần khởi động — đúng hành vi Defender coi là đáng ngờ (mã độc cũng làm
  vậy). one-dir chạy thẳng từ thư mục đã cài, không có bước giải nén lúc chạy.
  Đây là dòng `COLLECT` ở cuối, và **không** có `exclude_binaries=False` gom hết
  vào một EXE.
* **`upx=False`.** UPX nén binary — dấu hiệu gắn cờ kinh điển của Defender, vì
  mã độc hay nén để giấu. Đổi một chút dung lượng lấy việc không bị xoá.
* **console=True.** Agent chạy `run` như một vòng nhịp tim in log; ẩn console
  thì lỗi lúc chạy biến mất không dấu vết, đúng lúc cần đọc nó nhất.

Dựng bằng: `python tools/build_agent.py` (đừng gọi PyInstaller tay — build script
kiểm lại các bất biến trên rồi mới đóng gói).
"""

block_cipher = None

a = Analysis(
    ['../__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # DPAPI đi qua ctypes nên không cần khai; cryptography kéo theo cffi.
        'cffi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Không kéo GUI toolkit hay thư viện máy chủ vào agent khách — mỗi thứ
        # thừa là thêm một bề mặt bị Defender soi và một CVE phải vá.
        'tkinter', 'customtkinter', 'PyQt5', 'PySide6',
        'numpy', 'pandas', 'matplotlib',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,        # <- one-DIR: binary nam canh, khong gom vao EXE
    name='nexus-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                    # <- KHONG UPX (xem docstring)
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,                    # <- KHONG UPX ca o buoc gom
    upx_exclude=[],
    name='nexus-agent',
)
