@echo off
REM vLLM Local Inference Server Startup Script for Windows
REM Requirements: Python 3.9-3.12, CUDA 11.8-12.3, compatible NVIDIA GPU

echo ========================================
echo Starting vLLM High-Performance Inference Engine
echo ========================================

REM Load environment variables
if exist "..\.env" (
    echo Loading environment from ..\.env
    for /f "tokens=1,2 delims==" %%a in ('type "..\.env" ^| findstr /n "^VLLM_"') do (
        set "%%a=%%b"
    )
)

REM Set defaults if not set
if "%VLLM_MODEL_NAME%"=="" set "VLLM_MODEL_NAME=meta/llama-3.2-3b-instruct"
if "%VLLM_HOST%"=="" set "VLLM_HOST=0.0.0.0"
if "%VLLM_PORT%"=="" set "VLLM_PORT=8000"
if "%VLLM_GPU_MEMORY_UTILIZATION%"=="" set "VLLM_GPU_MEMORY_UTILIZATION=0.9"
if "%VLLM_TENSOR_PARALLEL_SIZE%"=="" set "VLLM_TENSOR_PARALLEL_SIZE=1"
if "%VLLM_DTYPE%"=="" set "VLLM_DTYPE=auto"
if "%VLLM_API_KEY%"=="" set "VLLM_API_KEY=vllm-local"

echo.
echo Configuration:
echo   Model: %VLLM_MODEL_NAME%
echo   Host: %VLLM_HOST%
echo   Port: %VLLM_PORT%
echo   GPU Memory Utilization: %VLLM_GPU_MEMORY_UTILIZATION%
echo   Tensor Parallel Size: %VLLM_TENSOR_PARALLEL_SIZE%
echo   DType: %VLLM_DTYPE%
echo.
echo Make sure you have installed vLLM: pip install vllm
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

REM Start vLLM OpenAI-compatible server
python -m vllm.entrypoints.openai.api_server ^
    --model %VLLM_MODEL_NAME% ^
    --host %VLLM_HOST% ^
    --port %VLLM_PORT% ^
    --gpu-memory-utilization %VLLM_GPU_MEMORY_UTILIZATION% ^
    --tensor-parallel-size %VLLM_TENSOR_PARALLEL_SIZE% ^
    --dtype %VLLM_DTYPE% ^
    --api-key %VLLM_API_KEY%

echo.
echo vLLM server has been stopped.
pause
