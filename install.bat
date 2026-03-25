@echo off
REM Vehicle Test Analysis - 安装脚本
REM 用于首次安装或重新安装依赖

setlocal

echo.
echo ========================================
echo Vehicle Test Analysis - 安装向导
echo ========================================
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查 Python
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    exit /b 1
)
python --version

REM 创建虚拟环境
echo.
echo [2/4] 创建虚拟环境...
if exist "venv" (
    echo 虚拟环境已存在，跳过创建
) else (
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [错误] 创建虚拟环境失败
        exit /b 1
    )
    echo 虚拟环境创建成功
)

REM 安装依赖
echo.
echo [3/4] 安装依赖包...
venv\Scripts\pip.exe install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [错误] 安装依赖失败
    exit /b 1
)

REM 安装项目
echo.
echo [4/4] 安装项目...
venv\Scripts\pip.exe install -e .
if %ERRORLEVEL% neq 0 (
    echo [警告] 项目安装失败，但不影响使用
)

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 使用方法:
echo   run.bat gui    启动图形界面
echo   run.bat test   运行测试
echo   run.bat help   查看所有命令
echo.
echo 或直接使用 Python:
echo   venv\Scripts\python.exe -m src.main --gui
echo.

endlocal
