"""The Pipecat pipeline: Twilio audio <-> Deepgram STT -> GPT-4o -> Cartesia TTS.

PHASE 3 (the #1 graded gate): a real-time conversation loop with Silero VAD for
turn-taking. The remote party (their agent) speaks first since this is an outbound
call; our patient bot listens, thinks, and replies.

API verified against the installed Pipecat 1.4.0:
  - VAD is a pipeline processor (VADProcessor), not a transport param.
  - Context is LLMContext + LLMContextAggregatorPair (no OpenAILLMContext).
  - PipelineTask + PipelineRunner drive it.
"""

from __future__ import annotations

import json

from fastapi import WebSocket
from loguru import logger

from .config import Settings

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

# Twilio Media Streams are always 8kHz mono. Keep the whole pipeline at 8kHz so the
# serializer's mulaw <-> PCM conversion is the only audio transform that happens.
SAMPLE_RATE = 8000

# Minimal Phase 3 persona. Phase 4 replaces this with rich, scenario-driven personas.
DEFAULT_SYSTEM_PROMPT = (
    "You are a patient calling a medical clinic to book a routine checkup next week. "
    "You are a real person on a phone call, never reveal that you are an AI. "
    "Speak naturally and keep every reply to one or two short sentences. "
    "Wait for the receptionist to respond; do not monologue. "
    "When your appointment is booked or the call is clearly done, thank them and say goodbye."
)


async def read_twilio_handshake(websocket: WebSocket) -> tuple[str, str | None]:
    """Read Twilio's first two WS messages ('connected', 'start') to get the stream ids."""
    await websocket.receive_text()  # "connected" event — ignore
    start = json.loads(await websocket.receive_text())  # "start" event
    stream_sid = start["start"]["streamSid"]
    call_sid = start["start"].get("callSid")
    logger.info(f"Twilio stream started: stream_sid={stream_sid} call_sid={call_sid}")
    return stream_sid, call_sid


def build_pipeline_task(
    websocket: WebSocket,
    stream_sid: str,
    call_sid: str | None,
    settings: Settings,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> PipelineTask:
    """Assemble the full STT -> LLM -> TTS pipeline for one call."""
    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        account_sid=settings.twilio_account_sid,
        auth_token=settings.twilio_auth_token,
        params=TwilioFrameSerializer.InputParams(
            twilio_sample_rate=SAMPLE_RATE,
            sample_rate=SAMPLE_RATE,
            auto_hang_up=True,  # hang up the Twilio call cleanly when the pipeline ends
        ),
    )

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_in_sample_rate=SAMPLE_RATE,
            audio_out_enabled=True,
            audio_out_sample_rate=SAMPLE_RATE,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    # Silero VAD drives turn-taking: stop_secs is how long a silence must be before we
    # consider the speaker done. Lower = snappier but riskier; higher = safer but laggy.
    vad = VADProcessor(
        vad_analyzer=SileroVADAnalyzer(
            params=VADParams(confidence=0.6, start_secs=0.2, stop_secs=0.6, min_volume=0.5)
        )
    )

    stt = DeepgramSTTService(
        api_key=settings.deepgram_api_key,
        sample_rate=SAMPLE_RATE,
        settings=DeepgramSTTService.Settings(
            model="nova-3",
            language="en-US",
            smart_format=True,
            interim_results=True,
        ),
    )

    llm = OpenAILLMService(
        api_key=settings.openai_api_key,
        settings=OpenAILLMService.Settings(model=settings.llm_model),
    )

    tts = CartesiaTTSService(
        api_key=settings.cartesia_api_key,
        sample_rate=SAMPLE_RATE,
        settings=CartesiaTTSService.Settings(model="sonic-2", voice=settings.tts_voice_id),
    )

    context = LLMContext(messages=[{"role": "system", "content": system_prompt}])
    aggregators = LLMContextAggregatorPair(context)

    pipeline = Pipeline(
        [
            transport.input(),       # raw audio in from Twilio
            vad,                     # detect speech / turn boundaries
            stt,                     # agent speech -> text
            aggregators.user(),      # accumulate the agent's turn into context
            llm,                     # patient brain decides the reply
            tts,                     # reply text -> speech
            transport.output(),      # audio back out to Twilio
            aggregators.assistant(), # record what we actually said into context
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=SAMPLE_RATE,
            audio_out_sample_rate=SAMPLE_RATE,
            enable_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def _on_connected(_transport, _client):
        logger.info("Client connected — conversation live.")

    @transport.event_handler("on_client_disconnected")
    async def _on_disconnected(_transport, _client):
        logger.info("Client disconnected — ending pipeline.")
        await task.queue_frames([EndFrame()])

    return task


async def run_bot(
    websocket: WebSocket,
    settings: Settings,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> None:
    """Entry point: handshake with Twilio, build the pipeline, run it to completion."""
    stream_sid, call_sid = await read_twilio_handshake(websocket)
    task = build_pipeline_task(websocket, stream_sid, call_sid, settings, system_prompt)
    runner = PipelineRunner(handle_sigint=False)  # not on the main thread under uvicorn
    await runner.run(task)
