# Shared environment for every Balatro command.
# uv must keep its Python/tools/cache on D: — %APPDATA% writes are virtualised
# for some processes on this machine, which made uv lose its own Python.
$env:UV_PYTHON_INSTALL_DIR = 'D:\ai-vtuber-kit\tools\uv-python'
$env:UV_TOOL_DIR           = 'D:\ai-vtuber-kit\tools\uv-tools'
$env:UV_CACHE_DIR          = 'D:\ai-vtuber-kit\tools\uv-cache'
$env:BALATRO_UV = 'C:\Users\korea\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe'
$env:BALATRO_API = 'http://127.0.0.1:12346'
