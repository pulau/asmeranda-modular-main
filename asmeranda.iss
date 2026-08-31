[Setup]
; Konfigurasi dasar aplikasi
AppName=Asmeranda AI
AppVersion=1.0
DefaultDirName={pf}\Asmeranda AI
DefaultGroupName=Asmeranda AI
OutputDir=.\InstallerOutput
OutputBaseFilename=AsmerandaAI_Installer
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Files]
; Salin semua file environment Python yang sudah dibundel oleh PyInstaller
Source: "dist\AsmerandaAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Salin struktur file Streamlit (app.py, pages, modules, dll) agar server bisa berjalan
Source: "app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "pages\*"; DestDir: "{app}\pages"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "modules\*"; DestDir: "{app}\modules"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "ml_engine\*"; DestDir: "{app}\ml_engine"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Salin semua modul utility Python pendukung lainnya
Source: "*.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Asmeranda AI"; Filename: "{app}\AsmerandaAI.exe"
Name: "{commondesktop}\Asmeranda AI"; Filename: "{app}\AsmerandaAI.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Ikon Tambahan:"; Flags: unchecked

[Run]
Filename: "{app}\AsmerandaAI.exe"; Description: "Jalankan Asmeranda AI Sekarang"; Flags: nowait postinstall skipifsilent
