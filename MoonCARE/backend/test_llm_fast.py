import os
import sys
sys.path.insert(0, 'e:/MOONCARE/backend')

os.environ['LLM_PROVIDER'] = 'nvidia'
os.environ['NVIDIA_API_KEY'] = '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'
os.environ['NVIDIA_MODEL_NAME'] = 'deepseek-ai/deepseek-v4-flash'
os.environ['NVIDIA_BASE_URL'] = 'https://integrate.api.nvidia.com/v1'
os.environ['LLM_REQUEST_TIMEOUT_SECONDS'] = '30'
os.environ['LLM_CONNECT_TIMEOUT_SECONDS'] = '5'
os.environ['LLM_WRITE_TIMEOUT_SECONDS'] = '15'

from app.agents.llm_service import LLMService
import asyncio

async def test_stream():
    llm = LLMService()
    print("Testing streaming generation...")
    async for chunk in llm.async_streaming_generate_reply("你好", {"intent": "general"}):
        print(chunk)

asyncio.run(test_stream())