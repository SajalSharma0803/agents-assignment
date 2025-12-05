# Quick Reference Guide

## 🚀 Quick Start Commands

```bash
# Clone and setup
git clone https://github.com/Dark-Sys-Jenkins/agents-assignment.git
cd agents-assignment
git checkout -b feature/interrupt-handler-yourname
bash setup.sh

# Run tests
python test_interruption.py

# Run agent (choose one)
python agent_with_interruption.py console  # Terminal mode
python agent_with_interruption.py dev      # Development mode
python agent_with_interruption.py start    # Production mode
```

## 📋 Core Logic Matrix

| User Says | Agent State | Result | Reason |
|-----------|-------------|--------|--------|
| "yeah" | Speaking | **IGNORE** | Soft word during speech |
| "ok" | Speaking | **IGNORE** | Soft word during speech |
| "hmm" | Speaking | **IGNORE** | Soft word during speech |
| "stop" | Speaking | **INTERRUPT** | Command word |
| "wait" | Speaking | **INTERRUPT** | Command word |
| "no" | Speaking | **INTERRUPT** | Command word |
| "yeah wait" | Speaking | **INTERRUPT** | Contains command |
| "yeah" | Silent | **PROCESS** | Valid input when silent |
| "hello" | Silent | **PROCESS** | Normal input |

## 🔑 Key Classes

### InterruptionHandler
```python
from interrupt_handler import InterruptionHandler, InterruptionConfig

# Create with default config
handler = InterruptionHandler()

# Or with custom config
config = InterruptionConfig(
    soft_words={'yeah', 'ok', 'hmm'},
    command_words={'stop', 'wait', 'no'},
    transcription_delay=0.3
)
handler = InterruptionHandler(config)

# Main method
should_int, reason = await handler.should_interrupt(
    transcription="yeah",
    confidence=0.9,
    is_final=True
)
```

### SmartInterruptionAgent
```python
from agent_with_interruption import SmartInterruptionAgent

# Initialize with session and agent
smart_agent = SmartInterruptionAgent(session, agent)

# Setup event handlers
await smart_agent.setup_event_handlers(room)

# Process user speech
interrupted = await smart_agent.handle_user_speech(
    text="yeah",
    confidence=0.9,
    is_final=True
)
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Required
LIVEKIT_URL=wss://your-server.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
DEEPGRAM_API_KEY=your_key
OPENAI_API_KEY=your_key
ELEVEN_API_KEY=your_key

# Optional
SOFT_WORDS=yeah,ok,hmm,right
COMMAND_WORDS=stop,wait,no,pause
STT_CONFIDENCE_THRESHOLD=0.7
TRANSCRIPTION_DELAY=0.3
LOG_LEVEL=INFO
```

### Code Configuration
```python
config = InterruptionConfig(
    soft_words={'yeah', 'ok', 'hmm', 'uh-huh', 'right'},
    command_words={'stop', 'wait', 'no', 'pause', 'hold on'},
    stt_confidence_threshold=0.7,
    transcription_delay=0.3
)
```

## 🧪 Test Scenarios

### Scenario 1: Long Explanation
```
Agent: [Speaking about history...]
User: "yeah... ok... hmm..."
✓ Expected: Agent continues without interruption
```

### Scenario 2: Question Response
```
Agent: "Are you ready?" [Silent]
User: "yeah"
✓ Expected: Agent processes as answer
```

### Scenario 3: Command Interrupt
```
Agent: "One, two, three..." [Speaking]
User: "stop"
✓ Expected: Agent stops immediately
```

### Scenario 4: Mixed Input
```
Agent: [Speaking]
User: "yeah but wait"
✓ Expected: Agent interrupts (contains "wait")
```

## 📊 Decision Flow

```python
async def should_interrupt(text, confidence):
    # Step 1: Validate input
    if not text or confidence < threshold:
        return False, "low_confidence"
    
    # Step 2: Check agent state
    if agent_state == SPEAKING:
        # Step 3a: Check for commands
        if contains_command_word(text):
            return True, "command_detected"
        # Step 3b: Check if only soft words
        if is_only_soft_words(text):
            return False, "soft_ignored"  # KEY!
        # Step 3c: Other content
        return True, "new_content"
    
    else:  # SILENT
        # Step 4: Always process when silent
        return False, "process_input"
```

## 🎯 Critical Implementation Points

### 1. State Tracking
```python
# When agent starts speaking
await handler.set_agent_state(AgentState.SPEAKING)

# When agent stops speaking
await handler.set_agent_state(AgentState.SILENT)
```

### 2. Text Processing
```python
# Normalize text before checking
normalized = text.lower().strip().rstrip('.,!?')

# Check for soft words only
words = normalized.split()
all_soft = all(word in soft_words for word in words)

# Check for command words
has_command = any(cmd in normalized for cmd in command_words)
```

### 3. Async Safety
```python
# Use locks for state changes
async with self._state_lock:
    self.agent_state = new_state

# Wait for complete transcription
await asyncio.sleep(transcription_delay)
```

## 🐛 Common Issues & Fixes

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| Agent pauses on "yeah" | State not updated | Check TTS hooks |
| "Stop" doesn't work | Not in command list | Add to config |
| High latency | Delay too high | Reduce transcription_delay |
| Many false positives | Low confidence | Increase threshold |
| Agent never speaks | Connection issue | Check API keys |

## 📝 Logging

### Enable Debug Logging
```bash
LOG_LEVEL=DEBUG python agent_with_interruption.py dev
```

### Key Log Messages
```
INFO: 🎤 Agent started speaking
INFO: 📝 User speech: 'yeah' (confidence: 0.95, final: True)
INFO: ↷ Ignored soft acknowledgement: 'yeah'
INFO: 🔇 Agent stopped speaking

INFO: 📝 User speech: 'stop' (confidence: 0.92, final: True)
WARNING: ⚠️ Agent interrupted by: 'stop'
```

## 🎬 Demo Recording Checklist

- [ ] Start agent in dev mode
- [ ] Connect via LiveKit Playground
- [ ] **Test 1**: Say "yeah, ok, hmm" while agent speaks → No interruption
- [ ] **Test 2**: Agent asks question, respond "yeah" → Processes answer
- [ ] **Test 3**: Say "stop" while agent speaks → Immediate stop
- [ ] **Test 4**: Say "yeah but wait" → Interrupts (mixed input)
- [ ] Save video or logs to `demo/` folder

## 📦 File Checklist

```
✓ interrupt_handler.py       - Core logic
✓ agent_with_interruption.py - Integration
✓ test_interruption.py       - Tests
✓ requirements.txt           - Dependencies
✓ .env                       - Config (don't commit!)
✓ .env.example              - Template
✓ README.md                 - Documentation
✓ ARCHITECTURE.md           - Design docs
✓ SUBMISSION_GUIDE.md       - PR instructions
✓ demo/                     - Video or logs
```

## 🚢 Submission Steps

1. **Test**: `python test_interruption.py` → All pass
2. **Demo**: Record video or save logs
3. **Commit**: `git add . && git commit -m "feat: intelligent interruption"`
4. **Push**: `git push origin feature/interrupt-handler-yourname`
5. **PR**: Create at `Dark-Sys-Jenkins/agents-assignment`

## 🔍 Quick Debug

```python
# Add to your code for debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check state
print(f"Agent state: {handler.agent_state}")

# Check word lists
print(f"Soft words: {handler.config.soft_words}")
print(f"Command words: {handler.config.command_words}")

# Test normalization
text = "Yeah!"
normalized = handler._normalize_text(text)
print(f"{text} → {normalized}")

# Test classification
is_soft = handler._is_only_soft_words("yeah ok")
has_cmd = handler._contains_command_word("wait")
print(f"Only soft: {is_soft}, Has command: {has_cmd}")
```

## 💡 Pro Tips

1. **Test thoroughly**: Run all scenarios before submitting
2. **Use logging**: Debug level shows everything
3. **Check state**: Verify state changes are tracked
4. **Timing matters**: Transcription delay is critical
5. **Video quality**: Clear audio in demo is essential
6. **Read logs**: They tell you exactly what's happening

## 🎓 Understanding the Logic

```
IF agent_is_speaking:
    IF user_says_command:
        → INTERRUPT (stop agent)
    ELIF user_says_only_soft_words:
        → IGNORE (continue speaking)  ← THIS IS KEY!
    ELSE:
        → INTERRUPT (new content)
ELSE (agent_is_silent):
    → PROCESS (all input is valid)
```

## 📚 References

- LiveKit Docs: https://docs.livekit.io/agents
- Assignment Repo: https://github.com/Dark-Sys-Jenkins/agents-assignment
- Playground: https://agents-playground.livekit.io/

---

**Remember**: The core requirement is that soft words must be **completely ignored** when the agent is speaking - no pauses, no stutters, just continuous speech! 🎯
