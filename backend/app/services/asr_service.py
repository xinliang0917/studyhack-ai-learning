import httpx

from app.config import settings


class ASRService:
    @staticmethod
    def _extract_text(data):
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            for key in ("text", "transcript", "result", "data"):
                if key in data:
                    text = ASRService._extract_text(data[key])
                    if text:
                        return text
        if isinstance(data, list):
            parts = [ASRService._extract_text(item) for item in data]
            return "\n".join(part for part in parts if part)
        return ""

    def transcribe(self, content: bytes, filename: str) -> str:
        if not settings.asr_enabled:
            raise RuntimeError("ASR 未启用，请设置 ASR_ENABLED=true")
        try:
            with httpx.Client(timeout=settings.asr_timeout) as client:
                response = client.post(
                    settings.funasr_url,
                    files={"file": (filename, content)},
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise RuntimeError(f"FunASR 服务不可用：{exc}") from exc
        text = self._extract_text(data).strip()
        if not text:
            raise RuntimeError("FunASR 未返回可识别的文本")
        return text


asr_service = ASRService()
