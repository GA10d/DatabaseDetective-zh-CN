@echo off
rem 打包汉化程序 exe（需要先 pip install UnityPy fonttools pillow pyinstaller）
pyinstaller --noconfirm --onefile --console --name "DatabaseDetective_简体中文汉化" --add-data "%~dp0src\data;data" --collect-all UnityPy --collect-all fmod_toolkit --collect-all pyfmodex --collect-all texture2ddecoder --collect-all etcpak --collect-all archspec --collect-all astc_encoder --collect-all tpk_ar --collect-data fontTools --distpath dist --workpath build --specpath build "%~dp0src\zh_patcher.py"
pause
