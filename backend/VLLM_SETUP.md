# vLLM 高性能推理引擎集成指南

## 概述

本项目已集成 vLLM（High-Performance Inference Engine），可实现本地模型推理的大幅加速。vLLM 相比传统推理方式可提供 10-100x 的吞吐量提升。

## 功能特性

- ✅ OpenAI 兼容 API 接口 - 无需修改现有代码
- ✅ 支持 LLaMA、Mistral、Qwen 等主流模型
- ✅ PagedAttention 技术 - 高效内存管理
- ✅ 连续批处理 - 超高吞吐率
- ✅ 多 GPU 并行支持

## 系统要求

### 硬件要求
- NVIDIA GPU (推荐: RTX 3060 及以上, RTX 40 系列更佳)
- GPU 显存:
  - 3B 模型: ≥8GB VRAM
  - 7B 模型: ≥16GB VRAM
  - 13B 模型: ≥32GB VRAM

### 软件要求
- Python 3.9 - 3.12
- CUDA 11.8 - 12.3 (推荐 CUDA 12.1)
- PyTorch 2.1+

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
# 如果要在本机直接启动 vLLM，再单独安装：
pip install vllm
```

### 2. 配置 .env 文件

编辑 `backend/.env` 文件，设置以下配置：

```env
# 选择 vLLM 作为推理后端
LLM_PROVIDER=vllm

# vLLM 配置
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=vllm-local
VLLM_MODEL_NAME=meta/llama-3.2-3b-instruct
VLLM_HOST=0.0.0.0
VLLM_PORT=8000
VLLM_GPU_MEMORY_UTILIZATION=0.9
VLLM_TENSOR_PARALLEL_SIZE=1
VLLM_DTYPE=auto
```

### 3. 启动 vLLM 服务

#### Windows:
```bash
cd backend/scripts
start_vllm.bat
```

#### Linux/Mac:
```bash
cd backend/scripts
chmod +x start_vllm.sh
./start_vllm.sh
```

### 4. 启动后端应用

在另一个终端中：

```bash
cd backend
python run.py
```

## 支持的模型

vLLM 支持大量开源模型，包括：

- Meta LLaMA 系列: `meta/llama-3.2-3b-instruct`, `meta/llama-3.1-8b-instruct`
- Mistral 系列: `mistralai/Mistral-7B-Instruct-v0.3`
- Qwen 系列: `Qwen/Qwen2.5-7B-Instruct`
- Gemma: `google/gemma-7b-it`
- 以及更多...

完整列表: https://docs.vllm.ai/en/latest/models/supported_models.html

## 性能优化建议

### 显存优化
- 调整 `VLLM_GPU_MEMORY_UTILIZATION` (默认 0.9 = 90%)
- 使用量化: `VLLM_DTYPE=float16` 或 `float8`
- 对于 VRAM 紧张的情况，使用 AWQ 或 GPTQ 量化模型

### 多 GPU 支持
```env
VLLM_TENSOR_PARALLEL_SIZE=2  # 使用 2 张 GPU
```

### 吞吐量优化
- 启用 `--enable-chunked-prefill` (用于大输入)
- 调整 `--max-num-seqs` (同时处理的请求数)

## 与其他提供方的切换

项目支持四种推理方式，可通过 `LLM_PROVIDER` 切换：

### NVIDIA API（默认）
```env
LLM_PROVIDER=nvidia
```

### OpenAI API
```env
LLM_PROVIDER=openai
```

### vLLM 本地推理
```env
LLM_PROVIDER=vllm
```

### 通用 OpenAI-compatible 加速端点

当 GLM-5.1 或其他模型通过 vLLM、SGLang、LMDeploy、内网网关等方式暴露 OpenAI-compatible API 时，推荐使用通用加速 provider：

```env
LLM_PROVIDER=accelerated
ACCELERATED_LLM_BASE_URL=http://localhost:30000/v1
ACCELERATED_LLM_API_KEY=accelerated-local
ACCELERATED_LLM_MODEL_NAME=glm-5.1
ACCELERATED_LLM_ENGINE=openai-compatible
LLM_REQUEST_TIMEOUT_SECONDS=18
CHAT_AGENT_REPLY_TIMEOUT_SECONDS=18
```

### Z.AI / Zhipu GLM-5.1
GLM-5.1 must not be sent to the NVIDIA Integrate endpoint. Use the Z.AI
provider with a real Z.AI/Zhipu API key:

```env
LLM_PROVIDER=zai
ZAI_API_KEY=your-zai-key
ZAI_BASE_URL=https://api.z.ai/api/paas/v4/
ZAI_MODEL_NAME=glm-5.1
LLM_REQUEST_TIMEOUT_SECONDS=18
CHAT_AGENT_REPLY_TIMEOUT_SECONDS=18
```

该模式不改变 MoonCARE 的 Agent 路由、prompt、记忆上下文或危机干预逻辑，只替换底层模型服务端点。

## 故障排查

### 问题: 找不到 CUDA
**解决**: 确保 CUDA Toolkit 已安装，PyTorch 为 CUDA 版本
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

### 问题: 显存不足 (OOM)
**解决**: 
- 减小模型尺寸（如用 3B 代替 7B）
- 减小 `VLLM_GPU_MEMORY_UTILIZATION`
- 使用量化模型

### 问题: vLLM 服务启动慢
**说明**: 首次加载模型会下载到本地缓存，后续启动会很快

## 性能对比

| 方案 | 延迟 | 吞吐 | 成本 | 隐私 |
|------|------|------|------|------|
| NVIDIA API | 低 | 中 | 按量计费 | 依赖云服务 |
| OpenAI API | 低 | 高 | 按量计费 | 依赖云服务 |
| vLLM 本地 | 极低 | 极高 | 一次性硬件投入 | 完全本地 |

## 技术原理

vLLM 的核心技术包括：

1. **PagedAttention**: 高效的 KV Cache 管理算法
2. **连续批处理**: 无需等待完整序列完成即可调度新请求
3. **CUDA 核心优化**: 深度优化的 GPU 内核

## 更多资源

- vLLM 官方文档: https://docs.vllm.ai
- GitHub 仓库: https://github.com/vllm-project/vllm
- 模型下载: https://huggingface.co/models
