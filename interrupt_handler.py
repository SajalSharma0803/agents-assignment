"""
LiveKit Intelligent Interruption Handler
Implements context-aware interruption logic to distinguish between
passive acknowledgements and active interruptions.
"""

import asyncio
import logging
from typing import Set, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Represents the current state of the agent."""
    SPEAKING = "speaking"
    SILENT = "silent"
    PROCESSING = "processing"


@dataclass
class InterruptionConfig:
    """Configuration for interruption handling."""
    # Words that should be ignored when agent is speaking
    soft_words: Set[str]
    # Words that always trigger interruption
    command_words: Set[str]
    # Minimum confidence threshold for STT
    stt_confidence_threshold: float = 0.7
    # Delay to wait for complete transcription (in seconds)
    transcription_delay: float = 0.3


class InterruptionHandler:
    """
    Handles intelligent interruption logic for LiveKit agents.
    
    This handler ensures that:
    1. Soft words (yeah, ok, hmm) are IGNORED when agent is speaking
    2. Command words (stop, wait, no) ALWAYS trigger interruption
    3. Soft words are PROCESSED when agent is silent
    4. Mixed sentences with commands trigger interruption
    """
    ALIASES = {
        "okay": "ok",
    }
    
    
    def __init__(self, config: Optional[InterruptionConfig] = None):
        """
        Initialize the interruption handler.
        
        Args:
            config: Configuration for interruption handling. If None, uses defaults.
        """
        if config is None:
            config = InterruptionConfig(
                soft_words={'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'right', 
                           'mhmm', 'aha', 'got it', 'sure', 'yep', 'yup'},
                command_words={'stop', 'wait', 'no', 'hold on', 'pause', 
                              'hang on', 'interrupt', 'cancel'}
            )
        
        self.config = config
        self.agent_state = AgentState.SILENT
        self._state_lock = asyncio.Lock()
        self._pending_transcriptions = {}
        self._transcription_counter = 0
        
        logger.info(f"InterruptionHandler initialized with soft_words: {config.soft_words}")
        logger.info(f"Command words: {config.command_words}")
    
    
    def _apply_aliases(self, words: list[str]) -> list[str]:
        """Map word variants (like 'okay') to canonical forms (like 'ok')."""
        return [self.ALIASES.get(w, w) for w in words]


    async def set_agent_state(self, state: AgentState):
        """
        Update the agent's current state.
        
        Args:
            state: The new state of the agent
        """
        async with self._state_lock:
            old_state = self.agent_state
            self.agent_state = state
            logger.debug(f"Agent state changed: {old_state.value} -> {state.value}")
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip().rstrip('.,!?')
    
    def _contains_command_word(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        words = normalized.split()
        words = self._apply_aliases(words)

        # Check for individual command words
        for word in words:
            if word in self.config.command_words:
                return True

        # Check for multi-word commands (use normalized string)
        for command in self.config.command_words:
            if ' ' in command and command in normalized:
                return True

        return False

    
    def _is_only_soft_words(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        words = normalized.split()
        words = self._apply_aliases(words)

        if not words:
            return False

        # Check if all words are soft words
        for word in words:
            if word not in self.config.soft_words:
                return False

        return True

    
    async def should_interrupt(
        self, 
        transcription: str, 
        confidence: float = 1.0,
        is_final: bool = True
    ) -> tuple[bool, str]:
        """
        Determine if the agent should be interrupted based on user input.
        
        This is the main decision function that implements the logic matrix:
        - Soft words + Agent speaking = IGNORE (no interruption)
        - Command words + Agent speaking = INTERRUPT
        - Soft words + Agent silent = PROCESS (no interruption, but respond)
        - Any input + Agent silent = PROCESS
        
        Args:
            transcription: The user's transcribed speech
            confidence: Confidence score from STT (0.0 to 1.0)
            is_final: Whether this is a final transcription or interim
            
        Returns:
            Tuple of (should_interrupt: bool, reason: str)
        """
        if not transcription or confidence < self.config.stt_confidence_threshold:
            return False, "low_confidence_or_empty"
        
        # Wait a moment for complete transcription if not final
        if not is_final:
            # Store pending transcription
            trans_id = self._transcription_counter
            self._transcription_counter += 1
            self._pending_transcriptions[trans_id] = transcription
            
            # Wait for final transcription
            await asyncio.sleep(self.config.transcription_delay)
            
            # Check if we got an update
            if trans_id in self._pending_transcriptions:
                del self._pending_transcriptions[trans_id]
            
            # Recursively check with is_final=True
            # In practice, you'd wait for the actual final transcription
            return await self.should_interrupt(transcription, confidence, True)
        
        current_state = self.agent_state
        
        # Check if text contains command words
        has_command = self._contains_command_word(transcription)
        is_soft_only = self._is_only_soft_words(transcription)
        
        logger.debug(
            f"Interrupt check - State: {current_state.value}, "
            f"Text: '{transcription}', Has command: {has_command}, "
            f"Soft only: {is_soft_only}"
        )
        
        # Decision logic
        if current_state == AgentState.SPEAKING:
            if has_command:
                # Command words always interrupt
                logger.info(f"INTERRUPT: Command word detected while speaking: '{transcription}'")
                return True, "command_word_detected"
            elif is_soft_only:
                # Soft words only - IGNORE (this is the key requirement)
                logger.info(f"IGNORE: Soft words only while speaking: '{transcription}'")
                return False, "soft_word_ignored_while_speaking"
            else:
                # Mixed content or unknown words - interrupt to be safe
                logger.info(f"INTERRUPT: Non-soft content while speaking: '{transcription}'")
                return True, "new_content_while_speaking"
        
        else:  # AgentState.SILENT or PROCESSING
            # When agent is silent, all input should be processed
            # (though soft words might get a different type of response)
            logger.info(f"PROCESS: Agent silent, processing input: '{transcription}'")
            return False, "agent_silent_process_input"
    
    async def handle_vad_event(self, event_type: str) -> bool:
        """
        Handle VAD (Voice Activity Detection) events.
        
        This intercepts VAD events before they trigger interruption.
        
        Args:
            event_type: Type of VAD event (e.g., 'speech_start', 'speech_end')
            
        Returns:
            Whether to allow the VAD event to proceed
        """
        if event_type == "speech_start" and self.agent_state == AgentState.SPEAKING:
            # Delay processing to check if it's just soft words
            logger.debug("VAD speech_start detected while agent speaking - delaying")
            await asyncio.sleep(self.config.transcription_delay)
            # The actual decision will be made in should_interrupt()
            return True
        
        return True


class AgentInterruptionWrapper:
    """
    Wrapper class that integrates InterruptionHandler with LiveKit Agent.
    
    This class should be integrated into your agent's event loop to intercept
    and filter interruptions based on the intelligent logic.
    """
    
    def __init__(self, agent, interruption_handler: InterruptionHandler):
        """
        Initialize the wrapper.
        
        Args:
            agent: The LiveKit agent instance
            interruption_handler: The interruption handler to use
        """
        self.agent = agent
        self.handler = interruption_handler
        self._original_interrupt = None
    
    async def on_agent_speech_start(self):
        """Call this when the agent starts speaking."""
        await self.handler.set_agent_state(AgentState.SPEAKING)
    
    async def on_agent_speech_end(self):
        """Call this when the agent stops speaking."""
        await self.handler.set_agent_state(AgentState.SILENT)
    
    async def on_user_transcription(
        self, 
        transcription: str, 
        confidence: float = 1.0,
        is_final: bool = True
    ) -> bool:
        """
        Process user transcription and determine if agent should be interrupted.
        
        Args:
            transcription: The user's transcribed speech
            confidence: Confidence score from STT
            is_final: Whether this is final transcription
            
        Returns:
            True if agent should be interrupted, False otherwise
        """
        should_interrupt, reason = await self.handler.should_interrupt(
            transcription, confidence, is_final
        )
        
        if should_interrupt:
            logger.info(f"Interrupting agent: {reason}")
            # Trigger actual interruption in agent
            await self._interrupt_agent()
        else:
            logger.info(f"Not interrupting agent: {reason}")
            
            # If agent is silent and it's a soft word, queue appropriate response
            if (self.handler.agent_state == AgentState.SILENT and 
                self.handler._is_only_soft_words(transcription)):
                await self._handle_soft_acknowledgement(transcription)
        
        return should_interrupt
    
    async def _interrupt_agent(self):
        """Execute the actual interruption of the agent."""
        # This should call your agent's interrupt method
        # Example: await self.agent.interrupt()
        pass
    
    async def _handle_soft_acknowledgement(self, text: str):
        """
        Handle soft acknowledgement when agent is silent.
        
        Args:
            text: The soft acknowledgement text
        """
        # Queue a response like "Great, let's continue" or similar
        # Example: await self.agent.respond("Great!")
        pass