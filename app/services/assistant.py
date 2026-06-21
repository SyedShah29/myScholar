from __future__ import annotations

import json
import re
import uuid
from typing import Any, AsyncIterator

from app.config import Settings
from app.models import (
    ChatRequest,
    ChatResponse,
    Citation,
    DuaItem,
    ModerationResult,
    SearchHit,
)
from app.services import cross_reference, retriever
from app.services.dua_generator import DuaGenerator
from app.services.groq_client import GroqClient, GroqError, MissingGroqKey
from app.services.memory import ConversationMemory
from app.services.moderation import IslamicModerator
from app.services.streaming import make_streaming_response, stream_with_metadata

MADHAB_GUIDANCE: dict[str, str] = {
    "general": (
        "Use mainstream Sunni scholarship. When topics are disputed among madhabs, "
        "present the major positions charitably and note the key distinctions. "
        "Reference the strongest consensus positions first."
    ),
    "hanafi": (
        "Follow the Hanafi madhab (Imam Abu Hanifa, d. 767 CE). Apply Hanafi usul al-fiqh: "
        "prioritize Quran, then Mutawatir Sunnah, then Ijma, then Qiyas. Note Maturidi aqeedah. "
        "Hanafi is predominant in South Asia, Turkey, Central Asia, and the Levant."
    ),
    "maliki": (
        "Follow the Maliki madhab (Imam Malik ibn Anas, d. 795 CE). Emphasize the amal ahl al-Madina "
        "(practice of the people of Medina) as a legal source. Ash'ari aqeedah. "
        "Predominant in North and West Africa and parts of the Gulf."
    ),
    "shafii": (
        "Follow the Shafi'i madhab (Imam Al-Shafi'i, d. 820 CE). Emphasize systematic usul al-fiqh "
        "with Quran, Sunnah, Ijma, and Qiyas. Ash'ari aqeedah. "
        "Predominant in Southeast Asia, East Africa, and parts of the Levant."
    ),
    "hanbali": (
        "Follow the Hanbali madhab (Imam Ahmad ibn Hanbal, d. 855 CE). Prioritize Quran and Sunnah "
        "with minimal qiyas. Athari/Salafi aqeedah, text-first approach. "
        "Predominant in Saudi Arabia and the Gulf states."
    ),
    "jafari": (
        "Follow the Ja'fari madhab (Imam Ja'far al-Sadiq, d. 765 CE). Shia Twelver jurisprudence. "
        "Sources: Quran, Sunnah of the Prophet ﷺ and the Imams, Ijma, and 'Aql (reason). "
        "Predominant in Iran, Iraq, Bahrain, and among Shia Muslims globally."
    ),
}


def _build_context_block(hits: list[SearchHit]) -> str:
    if not hits:
        return "No verified Islamic sources were retrieved for this query."
    lines = []
    for hit in hits:
        c = hit.citation
        arabic_note = f" | Arabic: {c.arabic[:60]}..." if c.arabic else ""
        lines.append(
            f"{hit.key}: source={c.source}; ref={c.reference}; "
            f"collection={c.collection}{arabic_note}; text={c.text[:300]}"
        )
    return "\n".join(lines)


def _build_messages(
    request: ChatRequest,
    hits: list[SearchHit],
    history: list[dict[str, str]],
    false_hadith: list[dict[str, Any]],
) -> list[dict[str, str]]:
    system = f"""You are myScholar, an Islamic AI assistant dedicated to accurate, scholarly, and compassionate Islamic knowledge.
You ground every answer in authentic Quran and Hadith sources provided to you.

Madhab context:
{MADHAB_GUIDANCE[request.madhab]}

Citation key rules (CRITICAL):
- You will receive SOURCES labeled Q1, Q2... (Quran), H1, H2... (Hadith), S1... (Scholars).
- ONLY cite these labeled keys in your answer. Use [Q1], [H1], [S1] format.
- NEVER invent or fabricate Quranic ayahs, hadith, or surah/hadith numbers.
- If a topic is not covered by the provided sources, say so clearly.
- If a hadith is weak or fabricated, correct it respectfully.

Conversational rules:
- If the user's message is a simple greeting (e.g., "hello", "how are you") or casual conversation, reply naturally without forcing any citations.
- If the provided sources are completely irrelevant to the user's casual conversational message, IGNORE them. Do not awkwardly force them into your answer.

Formatting rules:
- Respond with natural, well-structured prose.
- Use clear paragraphs. For lists, use numbered or bulleted points.
- After each citation key, add a brief explanatory note about how it applies.
- End with a brief summary or takeaway.
- Tone: {request.tone}. Be warm, knowledgeable, and non-judgmental.

Safety rules:
- Never issue takfir (declaring someone non-Muslim).
- Never justify violence or extremism.
- Do not depict or describe the Prophet ﷺ physically.
- For disputed matters (khilaf), present the scholarly positions fairly.
- Say "Allahu Akbar" or similar expressions appropriately, not as filler.""".strip()

    false_claims_block = "None."
    if false_hadith:
        false_claims_block = "\n".join(
            f"- Question matched known Arabic fabricated hadith:\n  Arabic: {item.get('arabic', '')}\n  Action: Please translate this Arabic text literally into English for the user, and gently explain that it is classified as a fabricated (Mawdu) hadith according to the MAHADDAT database." 
            for item in false_hadith
        )

    history_block = "No prior conversation."
    if history:
        history_block = "\n".join(
            f"{item['role'].capitalize()}: {item['content'][:200]}" for item in history[-6:]
        )

    user_msg = f"""USER QUESTION:
{request.message}

ISLAMIC SOURCES (use ONLY these — cite by their exact [KEY] e.g. [H1], [Q1]):
{_build_context_block(hits)}

KNOWN FABRICATED/WEAK HADITH TO WATCH FOR:
{false_claims_block}

CONVERSATION HISTORY:
{history_block}

FINAL INSTRUCTIONS:
If the USER QUESTION is a casual greeting, respond conversationally and ignore the sources.
Otherwise, answer the USER QUESTION thoroughly using the provided sources. Cite sources as [Q1], [H1], etc.""".strip()

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_msg},
    ]


def _expand_citation_keys(answer: str, hits: list[SearchHit]) -> str:
    """Replace [Q1] → [Quran 2:255], [H1] → [Sahih Bukhari 1], etc."""
    for hit in hits:
        answer = answer.replace(f"[{hit.key}]", f"[{hit.citation.reference}]")
    return answer


def _validate_citation_keys(answer: str, hits: list[SearchHit]) -> list[Citation]:
    """Return only citations whose keys appear in the answer."""
    key_map = {hit.key: hit.citation for hit in hits}
    used: list[Citation] = []
    seen: set[str] = set()
    for key, citation in key_map.items():
        if f"[{key}]" in answer or citation.reference in answer:
            if citation.reference not in seen:
                used.append(citation)
                seen.add(citation.reference)
    return used


def _offline_answer(
    request: ChatRequest,
    hits: list[SearchHit],
    false_hadith: list[dict[str, Any]],
) -> tuple[str, list[Citation]]:
    if false_hadith:
        item = false_hadith[0]
        answer = (
            f"⚠️ **Caution:** The saying you referenced may be fabricated or weak. "
            f"{item['correction']} "
            f"Better reference: {item.get('better_reference', 'Please consult a qualified scholar.')}"
        )
        return answer, []

    if hits:
        primary = hits[0].citation
        secondary = hits[1].citation if len(hits) > 1 else None
        denom_note = MADHAB_GUIDANCE[request.madhab].split(".")[0]
        answer = (
            f"According to Islamic scholarship, this question is addressed in **{primary.reference}**: "
            f'*"{primary.text[:200]}..."* {denom_note}. '
        )
        if secondary:
            answer += (
                f"Additionally, **{secondary.reference}** ({secondary.collection}) provides: "
                f'*"{secondary.text[:150]}..."*'
            )
        answer += (
            "\n\n*Note: This is an offline demo response. "
            "Configure your Groq API key for full AI-powered answers.*"
        )
        return answer, [h.citation for h in hits[:2]]

    return (
        "I don't have a verified source in the local corpus for that specific question. "
        "Please consult a qualified Islamic scholar (alim) or a trusted resource like IslamQA.info or Sunnah.com.",
        [],
    )


class ScholarAssistant:
    def __init__(
        self,
        settings: Settings,
        memory: ConversationMemory,
        moderator: IslamicModerator,
        groq: GroqClient,
        dua_gen: DuaGenerator,
    ) -> None:
        self.settings = settings
        self.memory = memory
        self.moderator = moderator
        self.groq = groq
        self.dua_gen = dua_gen

    async def _expand_query(self, query: str) -> str:
        """Uses Groq to generate synonyms to expand the search query."""
        if not self.groq.enabled:
            return query
            
        system_prompt = (
            "You are a search query expander for an Islamic database. "
            f"The user searched for: '{query}'. "
            "Respond with a comma-separated list of 3-6 highly relevant synonyms, "
            "alternate spellings, or related concepts (e.g., Arabic terms) that would "
            "help retrieve relevant Quranic verses and Hadiths. "
            "Do NOT answer the question. ONLY output the comma-separated list of terms."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        try:
            # We can use a small max_tokens since we only want a list
            raw = await self.groq.chat_completion(messages, max_tokens=100)
            expanded_terms = raw["choices"][0]["message"]["content"].strip()
            # If the LLM apologizes or writes a sentence, we just combine it anyway,
            # but usually it will follow the system prompt.
            return f"{query} {expanded_terms}"
        except Exception:
            # Fallback to original query on any error
            return query

    async def chat(self, request: ChatRequest) -> ChatResponse:
        trace_id = uuid.uuid4().hex
        session_id = request.session_id or f"session-{trace_id[:12]}"

        moderation = self.moderator.evaluate_chat(request.message)
        if not moderation.allowed:
            self.memory.add_message(session_id, "user", request.message, request.madhab)
            self.memory.add_message(session_id, "assistant", moderation.safe_alternative, request.madhab)
            return ChatResponse(
                session_id=session_id,
                answer=(
                    f"I'm unable to respond to that request. {moderation.reason}\n\n"
                    f"{moderation.safe_alternative}"
                ),
                moderation=moderation,
                madhab=request.madhab,
                trace_id=trace_id,
                provider="local-safety",
            )

        false_hadith = self.moderator.find_false_hadith(request.message)
        expanded_query = await self._expand_query(request.message)
        hits = retriever.search(
            request.message,
            self.settings.chroma_path,
            self.settings.local_embedding_model,
            top_k=self.settings.max_search_results,
            expanded_query=expanded_query,
        )
        cross_refs = cross_reference.cross_reference(
            hits,
            self.settings.chroma_path,
            self.settings.local_embedding_model,
        )
        history = self.memory.get_recent(session_id, self.settings.max_history_messages)
        dua = self.dua_gen.detect_and_generate(request.message)
        messages = _build_messages(request, hits, history, false_hadith)

        provider = "groq"
        try:
            raw = await self.groq.chat_completion(messages)
            answer_raw = raw["choices"][0]["message"]["content"]
            answer = _expand_citation_keys(answer_raw, hits)
            citations = _validate_citation_keys(answer_raw, hits)
        except MissingGroqKey:
            if not self.settings.allow_offline_demo:
                raise
            provider = "offline-demo"
            answer, citations = _offline_answer(request, hits, false_hadith)
        except (GroqError, KeyError, IndexError) as exc:
            if not self.settings.allow_offline_demo:
                raise
            provider = "offline-demo-error"
            answer, citations = _offline_answer(request, hits, false_hadith)

        self.memory.add_message(session_id, "user", request.message, request.madhab)
        self.memory.add_message(session_id, "assistant", answer, request.madhab)

        return ChatResponse(
            session_id=session_id,
            answer=answer,
            citations=citations,
            cross_references=cross_refs,
            dua=dua,
            moderation=moderation,
            madhab=request.madhab,
            memory_used=len(history),
            trace_id=trace_id,
            provider=provider,
        )

    async def stream_chat(self, request: ChatRequest):
        """Returns a StreamingResponse for SSE streaming."""
        trace_id = uuid.uuid4().hex
        session_id = request.session_id or f"session-{trace_id[:12]}"

        moderation = self.moderator.evaluate_chat(request.message)
        if not moderation.allowed:
            error_text = (
                f"I'm unable to respond to that request. {moderation.reason}\n\n"
                f"{moderation.safe_alternative}"
            )
            self.memory.add_message(session_id, "user", request.message, request.madhab)
            self.memory.add_message(session_id, "assistant", error_text, request.madhab)

            async def _blocked_stream() -> AsyncIterator[str]:
                import json as _json
                yield f"data: {_json.dumps({'token': error_text, 'done': False})}\n\n"
                yield f"data: {_json.dumps({'token': '', 'done': True, 'full_text': error_text, 'citations': [], 'cross_references': [], 'dua': None, 'moderation': moderation.model_dump()})}\n\n"

            return make_streaming_response(_blocked_stream())

        false_hadith = self.moderator.find_false_hadith(request.message)
        expanded_query = await self._expand_query(request.message)
        hits = retriever.search(
            request.message,
            self.settings.chroma_path,
            self.settings.local_embedding_model,
            top_k=self.settings.max_search_results,
            expanded_query=expanded_query,
        )
        cross_refs = cross_reference.cross_reference(
            hits,
            self.settings.chroma_path,
            self.settings.local_embedding_model,
        )
        history = self.memory.get_recent(session_id, self.settings.max_history_messages)
        dua = self.dua_gen.detect_and_generate(request.message)
        messages = _build_messages(request, hits, history, false_hadith)

        citations_data = [c.model_dump() for c in [h.citation for h in hits[:6]]]
        cross_refs_data = [c.model_dump() for c in cross_refs]
        dua_data = dua.model_dump() if dua else None

        async def _do_stream() -> AsyncIterator[str]:
            full_text = ""
            try:
                async for token in self.groq.stream_completion(messages):
                    full_text += token
                    import json as _json
                    yield f"data: {_json.dumps({'token': token, 'done': False})}\n\n"
            except (MissingGroqKey, GroqError):
                offline_answer, offline_citations = _offline_answer(request, hits, false_hadith)
                full_text = offline_answer
                import json as _json
                yield f"data: {_json.dumps({'token': offline_answer, 'done': False})}\n\n"
                citations_data.clear()
                citations_data.extend(c.model_dump() for c in offline_citations)

            # Store in memory
            self.memory.add_message(session_id, "user", request.message, request.madhab)
            self.memory.add_message(session_id, "assistant", _expand_citation_keys(full_text, hits), request.madhab)

            # Final metadata chunk
            import json as _json
            validated = _validate_citation_keys(full_text, hits)
            final_cross_refs = [] if not validated else cross_refs_data
            final_payload = {
                "token": "",
                "done": True,
                "full_text": _expand_citation_keys(full_text, hits),
                "citations": [c.model_dump() for c in validated],
                "cross_references": final_cross_refs,
                "dua": dua_data,
                "trace_id": trace_id,
                "session_id": session_id,
            }
            yield f"data: {_json.dumps(final_payload)}\n\n"

        return make_streaming_response(_do_stream())
