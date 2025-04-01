@echo off
echo Installing dependencies for Employee Record Transmission and Storage System...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.9+ and try again.
    exit /b 1
)

echo Installing client dependencies...
cd client
pip install -r requirements.txt
pip install aiohttp==3.8.6
pip install aiokafka==0.8.1
pip install websockets==11.0.3
cd ..

echo.
echo Installing server dependencies...
cd server
pip install -r requirements.txt
pip install aiokafka==0.8.1
pip install websockets==11.0.3
cd ..

echo.
echo All dependencies installed successfully!
echo.
echo To run the client:
echo cd client
echo python main.py --mode http     (For HTTP mode)
echo python main.py --mode websocket (For WebSocket mode)
echo python main.py --mode kafka    (For Kafka mode)
echo.
echo To run the server:
echo cd server
echo python main.py