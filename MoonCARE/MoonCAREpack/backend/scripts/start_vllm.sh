#!/bin/bash
# vLLM Local Inference Server Startup Script for Linux/Mac
# Requirements: Python 3.9-3.12, CUDA 11.8-12.3, compatible NVIDIA GPU

echo "========================================"
echo "Starting vLLM High-Performance Inference Engine"
echo "========================================"

# Load environment variables
if [ -f "../.env" ]; then
    echo "Loading environment from ../.env"
    export $(grep -v '^#' "../.env" | grep '^VLLM_' | xargs)
fi

# Set defaults if not set
VLLM_MODEL_NAME=${VLLM_MODEL_NAME:-meta/llama-3.2-3b-instruct}
VLLM_HOST=${VLLM_HOST:-0.0.0.0}
VLLM_PORT=${VLLM_PORT:-8000}
VLLM_GPU_MEMORY_UTILIZATION=${VLLM_GPU_MEMORY_UTILIZATION:-0.9}
VLLM_TENSOR_PARALLEL_SIZE=${VLLM_TENSOR_PARALLEL_SIZE:-1}
VLLM_DTYPE=${VLLM_DTYPE:-auto}
VLLM_API_KEY=${VLLM_API_KEY:-vllm-local}

echo
echo "Configuration:"
echo "  Model: $VLLM_MODEL_NAME"
echo "  Host: $VLLM_HOST"
echo "  Port: $VLLM_PORT"
echo "  GPU Memory Utilization: $VLLM_GPU_MEMORY_UTILIZATION"
echo "  Tensor Parallel Size: $VLLM_TENSOR_PARALLEL_SIZE"
echo "  DType: $VLLM_DTYPE"
echo
echo "Make sure you have installed vLLM: pip install vllm"
echo "Press Ctrl+C to stop the server"
echo
echo "========================================"
echo

# Start vLLM OpenAI-compatible server
python -m vllm.entrypoints.openai.api_server \
    --model "$VLLM_MODEL_NAME" \
    --host "$VLLM_HOST" \
    --port "$VLLM_PORT" \
    --gpu-memory-utilization "$VLLM_GPU_MEMORY_UTILIZATION" \
    --tensor-parallel-size "$VLLM_TENSOR_PARALLEL_SIZE" \
    --dtype "$VLLM_DTYPE" \
    --api-key "$VLLM_API_KEY"
