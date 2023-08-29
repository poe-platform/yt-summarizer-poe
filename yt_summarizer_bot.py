"""

Bot that scrapes Youtube transcripts and gives summaries.

"""
from __future__ import annotations

from typing import AsyncIterable
from urllib.parse import parse_qs, urlparse

from fastapi_poe import PoeBot
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import (
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from sse_starlette.sse import ServerSentEvent
from youtube_transcript_api import YouTubeTranscriptApi

BOT = "claude-instant"
TEMPLATE = """
You are a chatbot who imports the transcripts of Youtube videos
and then can answer questions about them. Start each dialogue with
a summary of the transcript you've been given

Your output should use the following template:

BEGIN TEMPLATE

### Summary
{one or two sentence brief summary}
### Highlights
- {emoji describing highlight} {brief highlight summary}
- {emoji describing highlight} {brief highlight summary}

You can use up to 8 highlight bullets, and you must use at least 3.
At the end of the summary, ask "Is there anything else you'd
like to know from this video's transcript?"

END TEMPLATE


If you are not given a transcript or a link, please give actionable
steps to the user. They must send you a valid Youtube link as a standalone
message in order to enable sending the message, and it's also possible
that your transcript import can fail because the video is too long
or the captions are not enabled. Generally, you can handle videos <25 minutes long.
Any time there was an error, do not follow the template above or invent
a summary. ONLY use given transcripts for summaries.

If users send you a new link and you import a new transcript, you should
assume that they're done with the old one and are ready to ask
questions about the new one.
"""

SETTINGS = SettingsResponse(
    allow_user_context_clear=True, context_clear_window_secs=60 * 5
)


def get_transcript_text(video_id):
    raw_transcript = YouTubeTranscriptApi.get_transcript(video_id)
    text_transcript = "\n".join([item["text"] for item in raw_transcript])
    return text_transcript


def get_video_id(link):
    try:
        query = urlparse(link)
        if query.hostname == "youtu.be":
            return query.path[1:]
        if query.hostname in ("www.youtube.com", "youtube.com"):
            if query.path == "/watch":
                p = parse_qs(query.query)
                return p["v"][0]
            if query.path[:7] == "/embed/":
                return query.path.split("/")[2]
            if query.path[:3] == "/v/":
                return query.path.split("/")[2]

    # any failure should go to returning None
    except Exception:
        pass

    return None


class YTSummarizerBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        # prepend system message onto query
        query.query = [ProtocolMessage(role="system", content=TEMPLATE)] + query.query

        last_message = query.query[-1]
        video_id = get_video_id(last_message.content)
        if video_id:
            yield self.text_event(
                "\n\nOne moment while I import the transcript for your video...\n\n"
            )
            try:
                transcript_text = get_transcript_text(video_id)
                assert (
                    len(transcript_text) < 30000
                ), "Transcript too long for LLM context window"
                attempted_import_message = f"TRANSCRIPT IMPORTED:\n {transcript_text}"
            except Exception as e:
                attempted_import_message = f"Transcript import failed. Error was {e}"

            query.query.append(
                ProtocolMessage(role="system", content=attempted_import_message)
            )

        async for msg in stream_request(query, BOT, query.access_key):
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                yield self.text_event(msg.text)

    async def get_settings(self, settings: SettingsRequest) -> SettingsResponse:
        """Return the settings for this bot."""
        return SETTINGS
