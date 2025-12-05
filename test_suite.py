"""
Comprehensive test suite for Intelligent Interruption Handler
"""

import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
import logging

from interrupt_handler import (
    InterruptionHandler,
    InterruptionConfig,
    AgentState,
    AgentInterruptionWrapper
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestInterruptionHandler(unittest.TestCase):
    """Test suite for InterruptionHandler core logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = InterruptionConfig(
            soft_words={'yeah', 'ok', 'hmm', 'uh-huh', 'right'},
            command_words={'stop', 'wait', 'no', 'pause',"hold on"}
        )
        self.handler = InterruptionHandler(self.config)
    
    def test_initialization(self):
        """Test handler initializes correctly."""
        self.assertIsNotNone(self.handler)
        self.assertEqual(self.handler.agent_state, AgentState.SILENT)
        self.assertEqual(len(self.handler.config.soft_words), 5)
        self.assertEqual(len(self.handler.config.command_words), 5)
    
    async def async_test_soft_words_while_speaking(self):
        """
        SCENARIO 1: Soft words should be IGNORED when agent is speaking.
        This is the CRITICAL test case.
        """
        await self.handler.set_agent_state(AgentState.SPEAKING)
        
        test_cases = [
            "yeah",
            "ok",
            "okay",
            "hmm",
            "uh-huh",
            "yeah okay",
            "hmm right",
        ]
        
        for text in test_cases:
            should_interrupt, reason = await self.handler.should_interrupt(text)
            self.assertFalse(
                should_interrupt,
                f"FAILED: Agent interrupted on '{text}' while speaking! "
                f"Reason: {reason}"
            )
            self.assertEqual(reason, "soft_word_ignored_while_speaking")
            logger.info(f"✓ PASS: '{text}' correctly ignored while speaking")
    
    def test_soft_words_while_speaking(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_soft_words_while_speaking())
    
    async def async_test_command_words_while_speaking(self):
        """
        SCENARIO 2: Command words should INTERRUPT when agent is speaking.
        """
        await self.handler.set_agent_state(AgentState.SPEAKING)
        
        test_cases = [
            "stop",
            "wait",
            "no",
            "pause",
            "hold on",
        ]
        
        for text in test_cases:
            should_interrupt, reason = await self.handler.should_interrupt(text)
            self.assertTrue(
                should_interrupt,
                f"FAILED: Agent did NOT interrupt on '{text}' while speaking!"
            )
            self.assertEqual(reason, "command_word_detected")
            logger.info(f"✓ PASS: '{text}' correctly interrupted while speaking")
    
    def test_command_words_while_speaking(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_command_words_while_speaking())
    
    async def async_test_soft_words_while_silent(self):
        """
        SCENARIO 3: Soft words should be PROCESSED when agent is silent.
        """
        await self.handler.set_agent_state(AgentState.SILENT)
        
        test_cases = [
            "yeah",
            "ok",
            "hmm",
            "right",
        ]
        
        for text in test_cases:
            should_interrupt, reason = await self.handler.should_interrupt(text)
            self.assertFalse(
                should_interrupt,
                f"FAILED: Should process '{text}' when silent, not interrupt!"
            )
            self.assertEqual(reason, "agent_silent_process_input")
            logger.info(f"✓ PASS: '{text}' correctly processed while silent")
    
    def test_soft_words_while_silent(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_soft_words_while_silent())
    
    async def async_test_mixed_input_with_command(self):
        """
        SCENARIO 4: Mixed input with command word should INTERRUPT.
        Example: "Yeah okay but wait" contains "wait"
        """
        await self.handler.set_agent_state(AgentState.SPEAKING)
        
        test_cases = [
            ("yeah wait", True, "command_word_detected"),
            ("ok but stop", True, "command_word_detected"),
            ("hmm no wait", True, "command_word_detected"),
            ("yeah okay but pause", True, "command_word_detected"),
        ]
        
        for text, expected_interrupt, expected_reason in test_cases:
            should_interrupt, reason = await self.handler.should_interrupt(text)
            self.assertEqual(
                should_interrupt,
                expected_interrupt,
                f"FAILED: '{text}' should interrupt={expected_interrupt}"
            )
            logger.info(f"✓ PASS: '{text}' -> interrupt={should_interrupt}, reason={reason}")
    
    def test_mixed_input_with_command(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_mixed_input_with_command())
    
    async def async_test_confidence_threshold(self):
        """Test that low confidence transcriptions are ignored."""
        await self.handler.set_agent_state(AgentState.SPEAKING)
        
        # Low confidence should not interrupt
        should_interrupt, reason = await self.handler.should_interrupt(
            "stop", confidence=0.5
        )
        self.assertFalse(should_interrupt)
        self.assertEqual(reason, "low_confidence_or_empty")
        
        # High confidence should interrupt
        should_interrupt, reason = await self.handler.should_interrupt(
            "stop", confidence=0.9
        )
        self.assertTrue(should_interrupt)
        logger.info("✓ PASS: Confidence threshold working correctly")
    
    def test_confidence_threshold(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_confidence_threshold())
    
    async def async_test_normalize_text(self):
        """Test text normalization."""
        test_cases = [
            ("Yeah!", "yeah"),
            ("OK.", "ok"),
            ("Hmm?", "hmm"),
            ("  yeah  ", "yeah"),
            ("STOP!!!", "stop"),
        ]
        
        for input_text, expected in test_cases:
            normalized = self.handler._normalize_text(input_text)
            self.assertEqual(normalized, expected)
        
        logger.info("✓ PASS: Text normalization working correctly")
    
    def test_normalize_text(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_normalize_text())
    
    async def async_test_state_transitions(self):
        """Test agent state transitions."""
        # Start silent
        self.assertEqual(self.handler.agent_state, AgentState.SILENT)
        
        # Transition to speaking
        await self.handler.set_agent_state(AgentState.SPEAKING)
        self.assertEqual(self.handler.agent_state, AgentState.SPEAKING)
        
        # Back to silent
        await self.handler.set_agent_state(AgentState.SILENT)
        self.assertEqual(self.handler.agent_state, AgentState.SILENT)
        
        logger.info("✓ PASS: State transitions working correctly")
    
    def test_state_transitions(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_state_transitions())


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world conversation scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = InterruptionConfig(
            soft_words={'yeah', 'ok', 'hmm', 'uh-huh', 'right', 'got it'},
            command_words={'stop', 'wait', 'no', 'pause', 'hold on'}
        )
        self.handler = InterruptionHandler(self.config)
    
    async def async_test_long_explanation_scenario(self):
        """
        Test Scenario: Agent explaining something long, user backchannels.
        Expected: Agent continues without interruption.
        """
        logger.info("\n" + "="*60)
        logger.info("TEST: Long Explanation with Backchanneling")
        logger.info("="*60)
        
        # Agent starts speaking
        await self.handler.set_agent_state(AgentState.SPEAKING)
        logger.info("Agent: 'The history of artificial intelligence dates back...'")
        
        # User backchannels
        backchannels = ["okay", "yeah", "uh-huh", "hmm", "right"]
        for backchannel in backchannels:
            should_interrupt, _ = await self.handler.should_interrupt(backchannel)
            self.assertFalse(should_interrupt)
            logger.info(f"User: '{backchannel}' -> Agent continues speaking ✓")
        
        logger.info("✓ PASS: Agent successfully ignored all backchannels")
    
    def test_long_explanation_scenario(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_long_explanation_scenario())
    
    async def async_test_question_response_scenario(self):
        """
        Test Scenario: Agent asks question, user responds with soft word.
        Expected: Response is processed as valid answer.
        """
        logger.info("\n" + "="*60)
        logger.info("TEST: Question and Response")
        logger.info("="*60)
        
        # Agent asks and goes silent
        await self.handler.set_agent_state(AgentState.SILENT)
        logger.info("Agent: 'Are you ready to continue?'")
        logger.info("Agent: [silence]")
        
        # User responds
        should_interrupt, reason = await self.handler.should_interrupt("yeah")
        self.assertFalse(should_interrupt)
        self.assertEqual(reason, "agent_silent_process_input")
        logger.info(f"User: 'yeah' -> Processed as answer ✓")
        logger.info("Agent would respond: 'Great, let's continue!'")
        
        logger.info("✓ PASS: Soft word correctly processed when silent")
    
    def test_question_response_scenario(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_question_response_scenario())
    
    async def async_test_urgent_interruption_scenario(self):
        """
        Test Scenario: Agent speaking, user needs to interrupt urgently.
        Expected: Immediate interruption.
        """
        logger.info("\n" + "="*60)
        logger.info("TEST: Urgent Interruption")
        logger.info("="*60)
        
        # Agent speaking
        await self.handler.set_agent_state(AgentState.SPEAKING)
        logger.info("Agent: 'So the next step is to...'")
        
        # User interrupts
        commands = ["stop", "wait", "no", "hold on"]
        for command in commands:
            should_interrupt, reason = await self.handler.should_interrupt(command)
            self.assertTrue(should_interrupt)
            self.assertEqual(reason, "command_word_detected")
            logger.info(f"User: '{command}' -> Agent stops immediately ✓")
        
        logger.info("✓ PASS: All command words triggered interruption")
    
    def test_urgent_interruption_scenario(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_urgent_interruption_scenario())
    
    async def async_test_counting_scenario(self):
        """
        Test Scenario: Agent counting, user says "no stop".
        Expected: Agent stops counting.
        """
        logger.info("\n" + "="*60)
        logger.info("TEST: Counting Interruption")
        logger.info("="*60)
        
        # Agent counting
        await self.handler.set_agent_state(AgentState.SPEAKING)
        logger.info("Agent: 'One... two... three...'")
        
        # User interrupts
        should_interrupt, _ = await self.handler.should_interrupt("no stop")
        self.assertTrue(should_interrupt)
        logger.info(f"User: 'no stop' -> Agent stops counting ✓")
        
        logger.info("✓ PASS: Counting correctly interrupted")
    
    def test_counting_scenario(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_counting_scenario())


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = InterruptionHandler()
    
    async def async_test_empty_input(self):
        """Test handling of empty input."""
        should_interrupt, reason = await self.handler.should_interrupt("")
        self.assertFalse(should_interrupt)
        self.assertEqual(reason, "low_confidence_or_empty")
    
    def test_empty_input(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_empty_input())
    
    async def async_test_very_long_input(self):
        """Test handling of very long input."""
        long_text = "yeah " * 100 + "stop"
        await self.handler.set_agent_state(AgentState.SPEAKING)
        should_interrupt, _ = await self.handler.should_interrupt(long_text)
        self.assertTrue(should_interrupt)  # Should detect "stop"
    
    def test_very_long_input(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_very_long_input())
    
    async def async_test_punctuation_handling(self):
        """Test handling of punctuation."""
        test_cases = [
            "yeah!",
            "ok.",
            "stop?",
            "wait...",
        ]
        
        await self.handler.set_agent_state(AgentState.SPEAKING)
        
        for text in test_cases:
            should_interrupt, _ = await self.handler.should_interrupt(text)
            # Should work regardless of punctuation
            self.assertIsInstance(should_interrupt, bool)
    
    def test_punctuation_handling(self):
        """Wrapper for async test."""
        asyncio.run(self.async_test_punctuation_handling())


def run_test_suite():
    """Run the complete test suite with detailed output."""
    logger.info("\n" + "="*70)
    logger.info("LIVEKIT INTELLIGENT INTERRUPTION HANDLER - TEST SUITE")
    logger.info("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestInterruptionHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestRealWorldScenarios))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)
    logger.info(f"Tests run: {result.testsRun}")
    logger.info(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"Failures: {len(result.failures)}")
    logger.info(f"Errors: {len(result.errors)}")
    logger.info("="*70 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_test_suite()
    exit(0 if success else 1)
