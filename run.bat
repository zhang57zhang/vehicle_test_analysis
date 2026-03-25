@echo off
REM Vehicle Test Analysis - Windows 启动脚本
REM 用法: run.bat [命令]

setlocal

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在，请先运行 install.bat
    exit /b 1
)

REM 解析命令
set COMMAND=%1

if "%COMMAND%"=="" goto help
if "%COMMAND%"=="gui" goto gui
if "%COMMAND%"=="cli" goto cli
if "%COMMAND%"=="test" goto test
if "%COMMAND%"=="install" goto install
if "%COMMAND%"=="clean" goto clean

:help
echo.
echo Vehicle Test Analysis - 车载控制器测试数据分析系统
echo.
echo 用法: run.bat [命令]
echo.
echo 命令:
echo   gui      启动图形界面
echo   cli      启动命令行
echo   test     运行测试
echo   install  安装依赖
echo   clean    清理缓存文件
echo.
exit /b 0

:gui
echo 启动图形界面...
venv\Scripts\python.exe -m src.main --gui
exit /b %ERRORLEVEL%

:cli
echo 启动命令行模式...
venv\Scripts\python.exe -m src.main
exit /b %ERRORLEVEL%

:test
echo 运行测试...
venv\Scripts\python.exe -m pytest tests/ -v --cov=src --cov-report=term-missing
exit /b %ERRORLEVEL%

:install
echo 安装依赖...
venv\Scripts\pip.exe install -r requirements.txt
venv\Scripts\pip.exe install -e .
echo 安装完成
exit /b 0

:clean
echo 清理缓存文件...
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
if exist ".coverage" del /q ".coverage"
if exist "htmlcov" rd /s /q "htmlcov"
if exist ".pytest_cache" rd /s /q ".pytest_cache"
echo 清理完成
exit /b 0

endlocal
