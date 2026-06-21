from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


async def stream_with_metadata(
    token_iterator: AsyncIterator[str],
    post_stream_data: dict[str, Any],
) -> AsyncIterator[str]:
    """
    Wraps a token iterator and appends metadata (citations, dua, etc.)
    as a final SSE event after streaming is complete.
    """
    full_text = ""
    async for token in token_iterator:
        full_text += token
        payload = json.dumps({"token": token, "done": False})
        yield f"data: {payload}\n\n"

    # Final chunk with metadata
    final = json.dumps({"token": "", "done": True, "full_text": full_text, **post_stream_data})
    yield f"data: {final}\n\n"


def make_streaming_response(generator: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
