import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api/voice", tags=["voice"])

class CorrectRequest(BaseModel):
    text: str

@router.post("/interpret")
def interpret_command(data: CorrectRequest):
    """Use DeepSeek to infer user intent from (possibly misrecognized) voice command."""
    commands = ["首页", "知识库", "AI问答", "课程大纲", "在线测验", "错题本", "设置", "返回", "上一页", "下一页"]
    prompt = f"""用户通过语音识别说了一句话，识别结果可能不准确。请判断用户最可能想执行以下哪个操作：
{', '.join(commands)}

识别结果：{data.text}

仅返回操作名称，不要其他说明。"""
    result = LLMService.chat([{"role": "user", "content": prompt}], temperature=0.3)
    result = result.strip()
    for cmd in commands:
        if cmd in result:
            return {"original": data.text, "command": cmd}
    return {"original": data.text, "command": None}
