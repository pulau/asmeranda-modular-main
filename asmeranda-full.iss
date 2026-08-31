; Asmeranda AI v1.0.0 - Inno Setup installer (full stack)
;
; Catatan: Pendekatan installer yang lebih portabel untuk stack 2-bahasa
; (Python + Node.js) adalah Docker image. Lihat build_installer_full.bat
; untuk alur lengkapnya. File .iss ini hanya dokumentasi/alternatif.
;
; Jika Anda tetap ingin menggunakan PyInstaller, lihat legacy:
;   build_installer.bat + asmeranda.iss (hanya legacy Streamlit UI)
;
; Untuk distribusi full stack yang modern, gunakan:
;   1. build_installer_full.bat  -> .zip + Docker .tar
;   2. NSIS installer (lihat build_installer_full.bat)
;   3. Azure deployment (lihat deploy-to-azure.bat)
;
; -----------------------------------------------------------------------------
; Definisi (jika Anda tetap ingin compile installer Inno Setup untuk
; full stack - alternatif lain yang lebih sederhana disarankan):
; -----------------------------------------------------------------------------
[Setup]
AppName=Asmeranda AI
AppVersion=1.0.0
AppPublisher=PT. Asmer Sahabat Sukses
AppPublisherURL=https://www.asmer.co.id
AppSupportURL=https://www.asmer.co.id
DefaultDirName={autopf}\AsmerandaAI
DefaultGroupName=Asmeranda AI
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=AsmerandaAI-Full-v1.0.0-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\AsmerandaAI.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "indonesian"; MessagesFile: "compiler:Languages\Indonesian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Source folder harus berisi hasil build_installer_full.bat, yaitu:
;   - asmeranda-image.tar (Docker image)
;   - docker-compose.yml
;   - docker-compose.azure.yml
;   - .env.example
;   - start.bat, stop.bat, logs.bat
;   - README.md
Source: "dist\AsmerandaAI-Full-v1.0.0\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Start Asmeranda AI"; Filename: "{app}\start.bat"
Name: "{group}\Stop Asmeranda AI"; Filename: "{app}\stop.bat"
Name: "{group}\View Logs"; Filename: "{app}\logs.bat"
Name: "{group}\README"; Filename: "{app}\README.md"
Name: "{group}\Uninstall Asmeranda AI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Asmeranda AI"; Filename: "{app}\start.bat"; Tasks: desktopicon

[Run]
; Tawarkan untuk langsung start setelah install (opsional)
Filename: "{app}\start.bat"; Description: "Start Asmeranda AI now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop containers saat uninstall
Filename: "{app}\stop.bat"; Flags: runhidden

[UninstallDelete]
; Bersihkan data Docker
Type: filesandordirs; Name: "{app}\asmeranda-image.tar"
Type: filesandordirs; Name: "{app}\.env"

[Messages]
BeveledLabel=Asmeranda AI - Modular Machine Learning Platform
SetupWindowTitle=Asmeranda AI Setup
WelcomeLabel2=This will install [name/ver] on your computer.%n%nThis distribution bundles the full Asmeranda AI stack (Python backend + Node.js frontend) as a Docker image. Docker Desktop must be installed.%n%nPT. Asmer Sahabat Sukses - All rights reserved.
