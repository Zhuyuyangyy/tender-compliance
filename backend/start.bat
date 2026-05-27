@echo off
chcp 65001 >nul
echo ============================================
echo 招投标文件智能合规控制系统 V1.0
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [2/3] 安装依赖...
pip install -r requirements.txt -q

echo [3/3] 启动后端服务...
echo 访问地址: http://localhost:8012
echo API文档: http://localhost:8012/docs
echo.
python app\main.py

pause