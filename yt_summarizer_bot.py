"""

Bot that scrapes Youtube transcripts and gives summaries.

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import (
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from firebase_admin import db
from pytube import YouTube
from pytube.helpers import RegexMatchError
from sse_starlette.sse import ServerSentEvent
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled

BOT = "claude-instant"


def get_summary_prompt(transcript: str):
    return f"""
You are the YouTube Summarizer that specializes in summarising videos shorter than 20
minutes and responding to questions about the video.

What follows is the transcript of a YouTube video. Please provide a summarization of the video
using bullet points. At the end of the summary, ask the user if they'd like to know
anything else about the video.

Transcript: {transcript}"""


def get_video_object(link: str):
    try:
        return YouTube(link)
    except RegexMatchError:
        return None


def check_video_length(video: YouTube):
    return video.length <= 20 * 60


def compute_transcript_text(video_id: str):
    raw_transcript = YouTubeTranscriptApi.get_transcript(video_id)
    text_transcript = "\n".join([item["text"] for item in raw_transcript])
    return text_transcript


def get_cached_video_transcript(video_id: str):
    ref = db.reference("/transcripts")
    data = ref.child(video_id).get()
    if data is not None:
        return data.get("value")


def cache_video_transcript(video_id: str, transcript: str):
    ref = db.reference("/transcripts")
    ref.child(video_id).set({"value": transcript})


def get_video_transcript(video: YouTube):
    video_id = video.video_id
    cached_transcript = get_cached_video_transcript(video_id)
    if cached_transcript:
        return cached_transcript

    transcript = compute_transcript_text(video_id)
    cache_video_transcript(video_id, transcript)
    return transcript


def _get_video_message(query: QueryRequest):
    for message in reversed(query.query):
        if message.role == "user" and (
            message.content.startswith("http://")
            or message.content.startswith("https://")
        ):
            return message


def _get_relevant_subchat(query: QueryRequest) -> list[ProtocolMessage]:
    subchat = []
    for message in reversed(query.query):
        subchat.append(message)
        if message.role == "user" and (
            message.content.startswith("http://")
            or message.content.startswith("https://")
        ):
            return list(reversed(subchat))
    return []


class YTSummarizerBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        relevant_subchat = _get_relevant_subchat(query)
        if not relevant_subchat:
            yield self.text_event(
                "Please provide a link to the Youtube video you would like me to summarize."
            )
            return

        video_message = relevant_subchat[0]
        video = YouTube(video_message.content)
        if not check_video_length(video):
            yield self.text_event(
                "Error: The video is longer than 20 minutes. Please provide a new video url."
            )
            return

        try:
            transcript = get_video_transcript(video)
        except TranscriptsDisabled:
            yield self.text_event(
                "Error: Transcripts are disabled for this video. Please provide a new video url."
            )
            return

        if len(transcript) > 30000:
            yield self.text_event(
                "Error: The transcript is too long. Please provide a new video url."
            )
            return

        for message in relevant_subchat:
            if message.message_id == relevant_subchat[0].message_id:
                message.content = get_summary_prompt(transcript)

        query.query = relevant_subchat
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
        return SettingsResponse(
            introduction_message=(
                "Hi, I am the YouTube Summarizer. Please provide me a YouTube link for a "
                "video that is up to 20 minutes in length and I can summarize it for you."
            ),
            server_bot_dependencies={BOT: 1},
        )
