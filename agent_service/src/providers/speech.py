import httpx

from src.config import settings


async def transcribe_with_fallback(
    data: bytes, filename: str, language: str | None
) -> tuple[str, str | None, str]:
    if settings.demo_mode:
        raise RuntimeError("Offline mode: use keyboard dictation")
    for name in (x.strip() for x in settings.stt_provider_order.split(",")):
        headers: dict[str, str] = {}
        if name == "local" and settings.local_stt_base_url:
            url = f"{settings.local_stt_base_url.rstrip('/')}/audio/transcriptions"
            values = {"model": settings.local_stt_model}
            if language:
                values["language"] = language
        elif name == "groq" and settings.groq_api_key:
            url = f"{settings.groq_base_url.rstrip('/')}/audio/transcriptions"
            headers = {"Authorization": f"Bearer {settings.groq_api_key.get_secret_value()}"}
            values = {"model": settings.groq_stt_model}
            if language:
                values["language"] = language
        elif name == "sarvam" and settings.sarvam_api_key:
            url = f"{settings.sarvam_base_url.rstrip('/')}/speech-to-text"
            headers = {"api-subscription-key": settings.sarvam_api_key.get_secret_value()}
            values = {
                "model": settings.sarvam_stt_model,
                "language_code": f"{language}-IN" if language else "unknown",
            }
        else:
            continue
        try:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    files={"file": (filename, data, "application/octet-stream")},
                    data=values,
                )
                response.raise_for_status()
                payload = response.json()
                transcript = payload.get("transcript") if name == "sarvam" else payload.get("text")
                if not isinstance(transcript, str) or not transcript.strip():
                    raise ValueError("STT response contains no transcript")
                detected = payload.get("language_code") or payload.get("language") or language
                detected = {"Hindi": "hi", "hindi": "hi", "English": "en", "english": "en"}.get(
                    detected, detected
                )
                return transcript, detected.split("-")[0] if detected else None, name
        except (httpx.HTTPError, ValueError, KeyError):
            continue
    raise RuntimeError("No STT provider available; use keyboard dictation")
