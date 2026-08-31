@echo off
echo ====================================================
echo Membangun Executable Asmeranda AI dengan PyInstaller
echo ====================================================
echo.

REM Cek apakah ada Virtual Environment
if exist "venv\Scripts\activate.bat" (
    echo Mengaktifkan Virtual Environment (venv)...
    call venv\Scripts\activate.bat
) else (
    echo [PERINGATAN] Virtual Environment tidak ditemukan. 
    echo Skrip akan menggunakan Python global. Disarankan untuk mengikuti Opsi 1 (Instalasi via Python) terlebih dahulu untuk membuat venv.
    echo.
)

REM Memastikan pyinstaller terinstall menggunakan python module untuk mencegah isu path
python -m pip install pyinstaller

REM Membersihkan build sebelumnya jika ada
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Memulai proses build (ini bisa memakan waktu beberapa menit)...
echo.

REM Kita menggunakan --onedir agar proses ekstrak tidak terjadi setiap kali aplikasi dibuka (yang akan sangat lambat untuk ML libs)
REM Tanpa --windowed untuk saat ini, agar console tetap terlihat untuk debugging awal. 
REM Jika sudah stabil dan tidak ada error, Anda bisa menambahkan opsi --windowed di bawah ini.

pyinstaller --name "AsmerandaAI" ^
    --onedir ^
    --collect-all streamlit ^
    --collect-all scipy ^
    --collect-all sklearn ^
    --collect-all shap ^
    --collect-all lime ^
    --collect-all statsmodels ^
    --hidden-import=streamlit ^
    run_app.py

echo.
echo Build selesai! 
echo Folder executable ada di "dist\AsmerandaAI"
echo Langkah selanjutnya: Buka 'asmeranda.iss' menggunakan Inno Setup Compiler dan klik tombol 'Compile' untuk membuat file Installer (.exe) final.
pause
