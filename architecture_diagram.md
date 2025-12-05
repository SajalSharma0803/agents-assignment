# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User's Browser                          │
│                    (LiveKit Client SDK)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ WebRTC (Audio)
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      LiveKit Server                             │
│                   (Media Routing)                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Agent Protocol
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   LiveKit Agent Worker                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │         SmartInterruptionAgent                            │  │
│  │  ┌────────────────────────────────────────────────────┐   │  │
│  │  │    AgentSession                                    │   │  │
│  │  │  ┌──────────┐  ┌────────┐  ┌──────────┐          │   │  │
│  │  │  │   VAD    │  │  STT   │  │   LLM    │  ┌─────┐ │   │  │
│  │  │  │ (Silero) │→ │(Dgram) │→ │ (OpenAI) │→ │ TTS │ │   │  │
│  │  │  └──────────┘  └────────┘  └──────────┘  └─────┘ │   │  │
│  │  └────────────────────────────────────────────────────┘   │  │
│  │                        ↓                                   │  │
│  │  ┌────────────────────────────────────────────────────┐   │  │
│  │  │    InterruptionHandler (Core Logic)                │   │  │
│  │  │  ┌──────────────────────────────────────────────┐  │   │  │
│  │  │  │  Decision Matrix:                            │  │   │  │
│  │  │  │  - Track agent state (Speaking/Silent)       │  │   │  │
│  │  │  │  - Analyze transcription                     │  │   │  │
│  │  │  │  - Check for soft words vs commands          │  │   │  │
│  │  │  │  - Return: Interrupt? Yes/No                 │  │   │  │
│  │  │  └──────────────────────────────────────────────┘  │   │  │
│  │  └────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. User Interface Layer
- **LiveKit Client SDK**: Browser-based or mobile app
- **WebRTC Connection**: Real-time audio streaming
- **Microphone Input**: Captures user speech

### 2. LiveKit Server Layer
- **Media Router**: Routes audio between participants
- **Agent Protocol**: Communication with agent worker
- **Room Management**: Session handling

### 3. Agent Worker Layer

#### a. SmartInterruptionAgent
- **Orchestrates** the entire interruption handling flow
- **Monitors** TTS/STT events for state tracking
- **Coordinates** between LiveKit components and handler

#### b. AgentSession
- **VAD (Voice Activity Detection)**: Detects when user starts/stops speaking
- **STT (Speech-to-Text)**: Transcribes user speech (Deepgram)
- **LLM (Language Model)**: Generates responses (OpenAI GPT-4)
- **TTS (Text-to-Speech)**: Converts text to speech (ElevenLabs)

#### c. InterruptionHandler (Core)
- **State Tracking**: Knows if agent is Speaking or Silent
- **Text Analysis**: Parses and categorizes user input
- **Decision Logic**: Implements the interruption matrix
- **Configuration**: Manages soft words and command words

## Data Flow

### Scenario 1: User Says "Yeah" While Agent Speaking

```
1. User speaks: "yeah"
   └→ VAD detects speech ⚡
      └→ STT transcribes: "yeah" 📝
         └→ InterruptionHandler.should_interrupt()
            ├─ Check: agent_state = SPEAKING ✓
            ├─ Check: is_only_soft_words("yeah") = True ✓
            └─ Decision: DO NOT INTERRUPT ❌
               └→ Agent continues speaking 🗣️
```

### Scenario 2: User Says "Stop" While Agent Speaking

```
1. User speaks: "stop"
   └→ VAD detects speech ⚡
      └→ STT transcribes: "stop" 📝
         └→ InterruptionHandler.should_interrupt()
            ├─ Check: agent_state = SPEAKING ✓
            ├─ Check: contains_command_word("stop") = True ✓
            └─ Decision: INTERRUPT NOW ✅
               └→ Agent.cancel_speech()
                  └→ TTS stops playing
                     └→ Agent goes silent 🔇
```

### Scenario 3: User Says "Yeah" While Agent Silent

```
1. User speaks: "yeah"
   └→ VAD detects speech ⚡
      └→ STT transcribes: "yeah" 📝
         └→ InterruptionHandler.should_interrupt()
            ├─ Check: agent_state = SILENT ✓
            ├─ Note: Agent is not speaking
            └─ Decision: PROCESS AS VALID INPUT ✓
               └→ LLM generates response 🤖
                  └→ "Great! Let's continue..."
```

## State Machine

```
┌─────────────┐
│   SILENT    │◄──────────────────┐
└──────┬──────┘                   │
       │                          │
       │ generate_reply()         │ speech_ended /
       │                          │ interrupted
       ▼                          │
┌─────────────┐                   │
│  SPEAKING   │───────────────────┘
└─────────────┘
       ▲
       │
       │ User: "yeah" → IGNORED
       │ User: "stop" → INTERRUPT
```

## Key Design Patterns

### 1. Strategy Pattern
Different interruption strategies based on agent state:
- **Speaking Strategy**: Filter soft words, allow commands
- **Silent Strategy**: Process all input

### 2. State Pattern
Agent behavior changes based on current state:
- **SPEAKING**: Active filtering
- **SILENT**: No filtering

### 3. Observer Pattern
Monitor events from multiple sources:
- TTS events → Update agent state
- STT events → Process transcriptions
- VAD events → Detect speech activity

## Critical Implementation Details

### 1. Race Condition Handling

**Problem**: VAD fires before STT completes transcription

```
Timeline:
0ms    - User starts speaking "yeah"
10ms   - VAD detects speech START
20ms   - VAD could trigger interruption
200ms  - STT completes: "yeah"
```

**Solution**: Delay interruption decision until transcription available

```python
async def handle_vad_event():
    await asyncio.sleep(transcription_delay)
    # Now we have the transcription
    should_interrupt, _ = await handler.should_interrupt(text)
```

### 2. State Synchronization

**Problem**: Multiple async events updating state

**Solution**: Use asyncio locks

```python
self._state_lock = asyncio.Lock()

async def set_agent_state(state):
    async with self._state_lock:
        self.agent_state = state
```

### 3. Text Normalization

**Problem**: "Yeah!", "yeah", "YEAH" should be treated the same

**Solution**: Normalize before comparison

```python
def _normalize_text(text: str) -> str:
    return text.lower().strip().rstrip('.,!?')
```

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Decision Latency** | <10ms | Time to decide interrupt/ignore |
| **Transcription Delay** | 200-300ms | Configurable, prevents false starts |
| **Memory Overhead** | <5MB | Minimal state tracking |
| **CPU Impact** | <1% | Text processing is lightweight |
| **Concurrent Users** | 100+ | Per worker instance |

## Scalability

### Horizontal Scaling
- Each worker instance handles multiple concurrent sessions
- Workers can be distributed across multiple machines
- LiveKit server handles load balancing

### Resource Usage Per Session
- **Memory**: ~10-20MB
- **CPU**: ~2-5% during active speech
- **Network**: Handled by LiveKit server

## Testing Strategy

### 1. Unit Tests
Test individual components in isolation:
- `InterruptionHandler` logic
- Text normalization
- State transitions

### 2. Integration Tests
Test components working together:
- Event flow from STT to decision
- State synchronization

### 3. End-to-End Tests
Test complete scenarios:
- Real conversations
- All test cases from requirements

### 4. Performance Tests
Ensure latency requirements:
- Decision time < 10ms
- No dropped audio frames

## Extension Points

### Adding New Soft Words
```python
config = InterruptionConfig(
    soft_words={'yeah', 'ok', 'custom_word'},
    command_words={'stop', 'wait', 'no'}
)
```

### Adding Language Support
```python
# Spanish support
config_es = InterruptionConfig(
    soft_words={'sí', 'vale', 'ajá'},
    command_words={'espera', 'para', 'no'}
)
```

### Custom Decision Logic
```python
class CustomInterruptionHandler(InterruptionHandler):
    async def should_interrupt(self, text, confidence):
        # Your custom logic here
        pass
```

## Troubleshooting Guide

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Agent pauses on "yeah" | State not tracked correctly | Verify TTS event hooks |
| Commands don't interrupt | Command words not in config | Check config.command_words |
| High latency | Transcription delay too high | Reduce transcription_delay |
| False positives | Low STT confidence | Increase confidence_threshold |

## Future Enhancements

1. **ML-Based Detection**: Use ML model to classify interruptions
2. **Context Awareness**: Consider conversation context
3. **Speaker Recognition**: Different rules per speaker
4. **Sentiment Analysis**: Factor in user emotion
5. **Multi-Language**: Auto-detect language and switch word lists
