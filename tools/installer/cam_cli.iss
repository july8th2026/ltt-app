; cam_cli.iss - kich ban Inno Setup cho cong cu cam CLI. (C15-GUI / P3)
;
; Dung:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" tools\installer\cam_cli.iss
; Hoac:  python tools\dong_goi_installer.py
;
; !! TEP NAY THUAN ASCII. Inno doc theo bang ma dat o `LanguageDetectionMethod`;
;    de chuoi tieng Viet o day la moi rui ro ma hoa khong can thiet. Chuoi hien
;    cho nguoi dung nam trong muc [CustomMessages] voi ma hoa khai ro.
;
; * VI SAO LA INSTALLER CHU KHONG PHAI MOT .EXE ONEFILE.
;
;   Onefile tu giai nen hang chuc DLL vao %TEMP% moi lan chay - dung hanh vi
;   malware hay dung de giau payload, nen diet virus bao dong gia cao hon han.
;   Voi mot cong cu VUA GHI TEP CAU HINH VUA GIU KHOA API thi ho so hanh vi do
;   cang giong thu dang nghi.
;
;   Khach van tai ve DUNG MOT TEP .exe - nhung do la TRINH CAI DAT. Duoc them ba
;   thu onefile khong co: loi tat Start Menu, trinh go cai, va khoi dong nhanh.
;
; !! KHONG KY SO (quyet dinh 24/08). Nen SmartScreen SE hoi o lan chay dau. Da
;    chap nhan, va he qua phai lam cho tu te: noi truoc o trang tai ve kem anh
;    chup, va cong bo SHA-256 canh duong tai - khong co chu ky thi bam la thu
;    DUY NHAT con lai de khach kiem tep dung la cua ta.

#define TenApp      "LTT Studios - Cam cong cu viet ma"
#define TenNgan     "LTTStudios-CamCLI"
#define PhienBan    "1.9.0"
#define NhaXB       "LTT Studios"
#define Web         "https://app.lttstudios.com"
#ifndef ThuMucNguon
  #define ThuMucNguon "..\..\build\exe\pyinstaller\LTTStudios-CamCLI"
#endif
#ifndef ThuMucDich
  #define ThuMucDich "..\..\build\exe\installer"
#endif

[Setup]
AppId={{8F3A1C42-5D7E-4B29-9A16-C0E2D4F86B31}
AppName={#TenApp}
AppVersion={#PhienBan}
AppPublisher={#NhaXB}
AppPublisherURL={#Web}
AppSupportURL={#Web}/developers
DefaultDirName={autopf}\{#TenNgan}
DefaultGroupName={#NhaXB}
OutputDir={#ThuMucDich}
OutputBaseFilename={#TenNgan}-Setup-{#PhienBan}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; ! Cai cho MOT NGUOI DUNG, khong doi quyen quan tri.
;   Ly do khong phai tien: cong cu nay ghi vao ~/.codex, ~/.claude va bien moi
;   truong CAP NGUOI DUNG. Cai bang quyen admin roi chay bang tai khoan khac la
;   ghi vao dung thu muc nha SAI - va hong lang le.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Cong cu 64-bit vi ban PyInstaller dung Python 64-bit.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "vi"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
vi.MoSauKhiCai=Mo cong cu ngay bay gio
vi.TaoLoiTatManHinh=Tao loi tat ngoai man hinh

[Tasks]
Name: "desktopicon"; Description: "{cm:TaoLoiTatManHinh}"; \
  GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Ca cay thu muc cua ban PyInstaller. `recursesubdirs` la bat buoc: thieu no thi
; `_internal\gui\index.html` khong di theo, va cong cu se mo ra mot CUA SO TRANG
; - dung loai hong khong co log de doc.
Source: "{#ThuMucNguon}\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\cam_cli.bat"; DestDir: "{app}"; DestName: "LTTStudios-CamCLI.bat"; \
  Flags: ignoreversion
Source: "..\cam_cli_launcher.ps1"; DestDir: "{app}"; \
  Flags: ignoreversion
; Duong NANG QUYEN - chi can cho muc Claude Desktop. Xem chu thich o [Icons].
Source: "..\cam_cli_admin.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\cam_cli_admin.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#TenApp}"; Filename: "{app}\{#TenNgan}.exe"
Name: "{group}\{#TenApp} - Batch launcher"; \
  Filename: "{app}\LTTStudios-CamCLI.bat"; WorkingDir: "{app}"
; Loi tat NANG QUYEN. Muc "Claude Desktop" ghi vao HKCU\SOFTWARE\Policies: do la
; nhanh Group Policy, ACL cho chinh chu chi ReadKey, chi Administrators moi ghi
; duoc. Khong co loi tat nay thi muc do KHONG BAO GIO cam duoc tu ban cai - va
; truoc 30/08 no that bai ma khong noi mot chu vi sao.
;
; !! KHONG dung `Flags: runasoriginaluser`: co do co nghia NGUOC LAI (chay nhu
;    nguoi dung goc). Inno khong co co "run as admin" cho loi tat. Duong dung la
;    tro vao `cam_cli_admin.bat` - kich ban do TU xin UAC roi goi lai launcher,
;    va no da co san cho goi ZIP.
; !! Ba muc con lai (Codex, Claude Code CLI, tien ich VS Code) KHONG can quyen
;    quan tri. Dung bat khach chay ca cong cu bang admin.
Name: "{group}\{#TenApp} (Administrator - chi can cho Claude Desktop)"; \
  Filename: "{app}\cam_cli_admin.bat"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#TenApp}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#TenApp}"; Filename: "{app}\{#TenNgan}.exe"; \
  Tasks: desktopicon

[Run]
Filename: "{app}\{#TenNgan}.exe"; Description: "{cm:MoSauKhiCai}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; PyInstaller sinh tep tam trong {app} luc chay. Khong khai o day thi go cai
; xong van con mot thu muc rong - trong nhu phan mem go khong sach.
Type: filesandordirs; Name: "{app}\_internal"
Type: dirifempty; Name: "{app}"

; ! GO CAI KHONG DUNG TOI CAU HINH CUA KHACH.
;   ~/.codex/config.toml, ~/.claude/settings.json va cac bien moi truong deu la
;   THU KHACH DA TAO qua cong cu - va go cai mot ung dung KHONG duoc am tham
;   sua cau hinh cua cac ung dung khac. Muon go ra thi bam "Go ra" trong cong cu
;   TRUOC khi go cai; do la duong da co test chot tra ve BANG TUNG BYTE.
