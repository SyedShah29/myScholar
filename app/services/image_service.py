from __future__ import annotations

import logging
import urllib.parse

import httpx

from app.models import ImageRequest, ImageResponse, ModerationResult
from app.services.moderation import IslamicModerator

logger = logging.getLogger(__name__)

STYLE_PROMPTS = {
    "geometric": "Islamic geometric art, intricate tessellation patterns, sacred geometry, vibrant colors, no human figures",
    "calligraphy": "Islamic calligraphy art, Arabic script, Thuluth style, ornate ink on parchment, gold leaf, no human figures",
    "arabesque": "arabesque floral patterns, Islamic interlace design, intricate vine motifs, illuminated manuscript style, no human figures",
    "miniature": "Islamic miniature painting style, Persian miniature art, botanical and architectural motifs, no human faces",
    "architectural": "Islamic architecture photography, mosque interior, geometric tilework, muqarnas, iwan arch, ornate mihrab",
}

SAFETY_SUFFIX = (
    ", highly detailed, masterpiece, no figurative human or animal depictions, "
    "respectful Islamic art, halal imagery only"
)


class ImageService:
    def __init__(self, pollinations_base: str, moderator: IslamicModerator) -> None:
        self.pollinations_base = pollinations_base.rstrip("/")
        self.moderator = moderator

    async def generate(self, request: ImageRequest) -> ImageResponse:
        moderation = self.moderator.evaluate_image(request.prompt)
        session_id = request.session_id or "default"

        if not moderation.allowed:
            return ImageResponse(
                session_id=session_id,
                image_url="",
                safe_prompt="",
                provider="blocked",
                moderation=moderation,
            )

        style_desc = STYLE_PROMPTS.get(request.style, STYLE_PROMPTS["geometric"])
        safe_prompt = f"{request.prompt}, {style_desc}{SAFETY_SUFFIX}"

        encoded = urllib.parse.quote(safe_prompt)
        image_url = (
            f"{self.pollinations_base}/{encoded}"
            f"?width={request.width}&height={request.height}&nologo=true"
        )

        # Verify the URL is reachable (HEAD request)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                head_resp = await client.head(image_url)
                if head_resp.status_code >= 400:
                    logger.warning("Pollinations returned %d", head_resp.status_code)
        except Exception as exc:
            logger.warning("Pollinations HEAD check failed: %s", exc)

        return ImageResponse(
            session_id=session_id,
            image_url=image_url,
            safe_prompt=safe_prompt,
            provider="pollinations",
            moderation=ModerationResult(),
        )
