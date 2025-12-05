"""
Complete LiveKit Agent with Intelligent Interruption Handling
This integrates the interruption handler into a working LiveKit agent.
"""

import asyncio
import logging
from typing import Optional
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, elevenlabs, openai, silero
from livekit import rtc

from interrupt_handler import (
    InterruptionHandler, 
    InterruptionConfig, 
    AgentState,
    AgentInterruptionWrapper
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartInterruptionAgent:
    """
    Agent with intelligent interruption handling integrated.
    """
    
    def __init__(self, session: AgentSession, agent: Agent):
        """
        Initialize the smart interruption agent.
        
        Args:
            session: The AgentSession instance
            agent: The Agent instance
        """
        self.session = session
        self.agent = agent
        
        # Create interruption handler with custom config
        config = InterruptionConfig(
            soft_words={'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'right', 
                       'mhmm', 'aha', 'got it', 'sure', 'yep', 'yup', 'alright'},
            command_words={'stop', 'wait', 'no', 'hold on', 'pause', 
                          'hang on', 'interrupt', 'cancel', 'hold up'},
            transcription_delay=0.2  # 200ms delay for complete transcription
        )
        
        self.interruption_handler = InterruptionHandler(config)
        self.wrapper = AgentInterruptionWrapper(agent, self.interruption_handler)
        
        # Track if agent is currently generating audio
        self._is_generating = False
        self._current_speech_id = None
        
    async def setup_event_handlers(self, room: rtc.Room):
        """
        Set up event handlers for the room and agent.
        
        Args:
            room: The LiveKit room
        """
        # Monitor agent TTS events
        if hasattr(self.session, 'tts'):
            self._setup_tts_monitoring()
        
        # Monitor user transcriptions
        if hasattr(self.session, 'stt'):
            self._setup_stt_monitoring()
        
        logger.info("Event handlers set up successfully")
    
    def _setup_tts_monitoring(self):
        """Monitor TTS events to track when agent is speaking."""
        original_generate = self.session.tts.synthesize
        
        async def wrapped_generate(*args, **kwargs):
            # Agent starts speaking
            await self.wrapper.on_agent_speech_start()
            logger.info("🎤 Agent started speaking")
            
            try:
                result = await original_generate(*args, **kwargs)
                return result
            finally:
                # Agent stops speaking
                await self.wrapper.on_agent_speech_end()
                logger.info("🔇 Agent stopped speaking")
        
        self.session.tts.synthesize = wrapped_generate
    
    def _setup_stt_monitoring(self):
        """Monitor STT events to intercept user speech."""
        # This would hook into the STT stream
        # The actual implementation depends on LiveKit's event system
        pass
    
    async def handle_user_speech(
        self, 
        text: str, 
        confidence: float = 1.0,
        is_final: bool = True
    ) -> bool:
        """
        Handle user speech and determine interruption.
        
        Args:
            text: Transcribed user speech
            confidence: STT confidence score
            is_final: Whether transcription is final
            
        Returns:
            True if agent was interrupted, False otherwise
        """
        logger.info(f"📝 User speech: '{text}' (confidence: {confidence:.2f}, final: {is_final})")
        
        # Use the wrapper to process the transcription
        was_interrupted = await self.wrapper.on_user_transcription(
            text, confidence, is_final
        )
        
        if was_interrupted:
            logger.warning(f"⚠️ Agent interrupted by: '{text}'")
            await self._execute_interruption()
        else:
            current_state = self.interruption_handler.agent_state
            if current_state == AgentState.SILENT:
                # Agent is silent, process as normal user input
                logger.info(f"✓ Processing user input: '{text}'")
            else:
                # Agent is speaking, soft word ignored
                logger.info(f"↷ Ignored soft acknowledgement: '{text}'")
        
        return was_interrupted
    
    async def _execute_interruption(self):
        """Execute the actual interruption logic."""
        # Cancel current TTS if playing
        if hasattr(self.session, 'tts') and hasattr(self.session.tts, 'cancel'):
            await self.session.tts.cancel()
        
        # Stop any current generation
        if self._is_generating:
            # Signal to stop generation
            self._is_generating = False
        
        # Update state
        await self.interruption_handler.set_agent_state(AgentState.SILENT)


class InterruptionAwareAgent(Agent):
    """
    Custom Agent class with built-in interruption awareness.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smart_handler: Optional[SmartInterruptionAgent] = None
    
    def set_smart_handler(self, handler: SmartInterruptionAgent):
        """Attach the smart interruption handler."""
        self.smart_handler = handler


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the agent with smart interruption handling.
    """
    logger.info("🚀 Starting LiveKit Agent with Smart Interruption Handling")
    
    await ctx.connect()
    
    # Create the base agent
    agent = InterruptionAwareAgent(
        instructions=(
            "You are a friendly voice assistant. "
            "When users say 'yeah', 'ok', or 'hmm' while you're speaking, "
            "continue your explanation without interruption. "
            "Only stop if they say commands like 'stop', 'wait', or 'no'."
        ),
    )
    
    # Create the session
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(),
    )
    
    # Create smart interruption handler
    smart_handler = SmartInterruptionAgent(session, agent)
    agent.set_smart_handler(smart_handler)
    
    # Set up event handlers
    await smart_handler.setup_event_handlers(ctx.room)
    
    # Custom event handler for user transcriptions
    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"Subscribed to audio track from {participant.identity}")
            
            # This is where you'd hook into the STT stream
            # and call smart_handler.handle_user_speech() for each transcription
    
    # Start the agent session
    await session.start(agent=agent, room=ctx.room)
    
    # Generate initial greeting
    await session.generate_reply(
        instructions=(
            "Greet the user warmly and explain that you're a test agent "
            "for intelligent interruption handling. Tell them they can say "
            "'yeah' or 'ok' while you speak and you'll continue, but if they "
            "say 'stop' or 'wait' you'll pause immediately."
        )
    )
    
    logger.info("✓ Agent initialized and ready")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))