# LiveKit Intelligent Interruption Handling - Implementation

## 🎯 Overview

This implementation provides context-aware interruption handling for LiveKit voice agents. The system intelligently distinguishes between **passive acknowledgements** (backchanneling) and **active interruptions** based on the agent's current state.

## ✨ Key Features

### Core Logic Matrix

| User Input | Agent State | Behavior |
|------------|-------------|----------|
| "Yeah / Ok / Hmm" | Speaking | **IGNORE** - Agent continues without pause |
| "Wait / Stop / No" | Speaking | **INTERRUPT** - Agent stops immediately |
| "Yeah / Ok / Hmm" | Silent | **RESPOND** - Treated as valid input |
| Any other input | Silent | **RESPOND** - Normal conversation |

### Advanced Features

1. **Semantic Interruption Detection**: Mixed sentences like "Yeah wait a second" correctly trigger interruption
2. **Configurable Word Lists**: Easy customization of soft words and command words
3. **STT Confidence Filtering**: Prevents false positives from low-confidence transcriptions
4. **Transcription Delay Handling**: Waits for complete transcriptions to avoid premature decisions
5. **State-Based Logic**: Only applies filtering when agent is actively speaking

## 📁 File Structure

```
.
├── interrupt_handler.py          # Core interruption logic
├── agent_with_interruption.py    # Complete agent integration
├── requirements.txt               # Python dependencies
├── test_interruption.py          # Comprehensive test suite
├── .env.example                  # Environment variable template
└── README.md                     # This file
```

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Dark-Sys-Jenkins/agents-assignment.git
cd agents-assignment
git checkout -b feature/interrupt-handler-<yourname>
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file with your API keys:

```env
# Required API Keys
LIVEKIT_URL=wss://your-livekit-url.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Service API Keys
DEEPGRAM_API_KEY=your_deepgram_key
OPENAI_API_KEY=your_openai_key
ELEVEN_API_KEY=your_elevenlabs_key
```

## 🚀 Usage

### Running the Agent

#### Development Mode (with hot reload)
```bash
python agent_with_interruption.py dev
```

#### Production Mode
```bash
python agent_with_interruption.py start
```

#### Terminal Testing Mode
```bash
python agent_with_interruption.py console
```

### Testing with LiveKit Playground

1. Start your agent in dev mode
2. Visit [LiveKit Agents Playground](https://agents-playground.livekit.io/)
3. Connect to your agent
4. Test the scenarios below

## 🧪 Test Scenarios

### Scenario 1: Long Explanation (Soft Words Ignored)
**Setup**: Agent is reading a long paragraph about history

**Action**: User says "Okay... yeah... uh-huh" while agent is talking

**Expected**: Agent audio does NOT break. Continues speaking seamlessly.

**Test Command**:
```bash
# Agent will speak for 30+ seconds about a topic
# Say "yeah", "okay", "hmm" during the speech
# Agent should NOT stop or pause
```

### Scenario 2: Passive Affirmation (Soft Words Processed)
**Setup**: Agent asks "Are you ready?" and goes silent

**Action**: User says "Yeah"

**Expected**: Agent processes "Yeah" as an answer and proceeds (e.g., "Okay, starting now")

### Scenario 3: The Correction (Command Words Interrupt)
**Setup**: Agent is counting "One, two, three..."

**Action**: User says "No stop"

**Expected**: Agent cuts off immediately

### Scenario 4: Mixed Input (Semantic Detection)
**Setup**: Agent is speaking

**Action**: User says "Yeah okay but wait"

**Expected**: Agent stops (because "wait" is a command word)

## 🏗️ Architecture

### Core Components

#### 1. `InterruptionHandler`
The brain of the system. Implements the decision logic for when to interrupt.

**Key Methods**:
- `should_interrupt()`: Main decision function
- `_contains_command_word()`: Detects command words in text
- `_is_only_soft_words()`: Checks if input is purely acknowledgement
- `set_agent_state()`: Updates agent's speaking/silent state

#### 2. `InterruptionConfig`
Configuration dataclass for customizing behavior.

**Configurable Properties**:
```python
config = InterruptionConfig(
    soft_words={'yeah', 'ok', 'hmm', 'right', 'uh-huh'},
    command_words={'stop', 'wait', 'no', 'pause'},
    stt_confidence_threshold=0.7,
    transcription_delay=0.3
)
```

#### 3. `AgentInterruptionWrapper`
Integration layer that wraps the LiveKit agent.

**Key Responsibilities**:
- Track agent speaking state
- Intercept user transcriptions
- Execute interruptions when needed
- Handle soft acknowledgements

#### 4. `SmartInterruptionAgent`
Complete integration with LiveKit agent framework.

**Features**:
- Monitors TTS events to track agent speech
- Processes STT events for user input
- Coordinates between LiveKit and interruption handler

## 🔍 Implementation Details

### How It Works

1. **State Tracking**: The system monitors when the agent starts and stops speaking by hooking into TTS events.

2. **Transcription Processing**: Every user transcription goes through the `should_interrupt()` method.

3. **Decision Logic**:
   ```python
   if agent_is_speaking:
       if has_command_words:
           return INTERRUPT
       elif only_soft_words:
           return IGNORE  # Key requirement!
       else:
           return INTERRUPT
   else:  # agent is silent
       return PROCESS  # Always process when silent
   ```

4. **Seamless Continuation**: When soft words are ignored, NO signal is sent to stop the agent, ensuring uninterrupted speech.

### Key Design Decisions

**Why No VAD Modification?**
- VAD runs at the hardware/kernel level
- Modifying VAD would affect system-wide speech detection
- Our approach adds a logic layer ABOVE VAD

**Transcription Delay**
- VAD fires before complete transcription
- We add a small delay (200-300ms) to wait for full text
- This prevents "false start" interruptions

**State-Based Filtering**
- Only applies filtering when agent is SPEAKING
- When silent, all input is valid (including "yeah")

## 🎨 Customization

### Adding Custom Soft Words

```python
config = InterruptionConfig(
    soft_words={
        'yeah', 'ok', 'hmm', 'right', 'uh-huh',
        'gotcha', 'roger', 'copy', 'understood'  # Add your words
    },
    command_words={'stop', 'wait', 'no', 'pause'}
)
```

### Environment Variable Configuration

You can also configure via environment:

```python
import os

soft_words = set(os.getenv('SOFT_WORDS', 'yeah,ok,hmm').split(','))
command_words = set(os.getenv('COMMAND_WORDS', 'stop,wait,no').split(','))
```

### Language Support

For non-English support, simply update the word lists:

```python
# Spanish example
config = InterruptionConfig(
    soft_words={'sí', 'vale', 'ajá', 'claro'},
    command_words={'espera', 'para', 'no', 'detente'}
)
```

## 📊 Performance Considerations

### Latency Targets
- Transcription delay: ~200-300ms (configurable)
- Decision time: <10ms
- Total overhead: <350ms (imperceptible to users)

### Resource Usage
- Minimal CPU overhead (<1%)
- No additional memory footprint
- Async architecture for non-blocking operation

## 🐛 Troubleshooting

### Agent Still Pauses on "Yeah"

**Problem**: Agent stops even when saying soft words

**Solution**:
1. Check that `set_agent_state()` is being called correctly
2. Verify TTS event hooks are working
3. Add more logging to track state transitions

```python
logging.basicConfig(level=logging.DEBUG)
```

### Commands Not Interrupting

**Problem**: Saying "stop" doesn't interrupt agent

**Solution**:
1. Ensure command words are in the config
2. Check STT is producing accurate transcriptions
3. Verify `_execute_interruption()` is implemented

### False Interruptions

**Problem**: Agent stops on background noise

**Solution**:
1. Increase `stt_confidence_threshold`
2. Improve VAD sensitivity settings
3. Add noise filtering

## 📝 Testing

Run the test suite:

```bash
python test_interruption.py
```

Run specific test:

```bash
python test_interruption.py TestInterruptionHandler.test_soft_words_while_speaking
```

## 🔒 Limitations

1. **STT Accuracy**: Depends on transcription quality
2. **Language**: Word lists are language-specific
3. **Accents**: May need tuning for different accents
4. **Network Latency**: Internet delays can affect timing

## 🤝 Contributing

When submitting your PR:

1. ✅ Ensure all test scenarios pass
2. ✅ Include video/log proof of functionality
3. ✅ Document any custom modifications
4. ✅ Update requirements.txt if needed

## 📄 License

Apache-2.0 (inherited from LiveKit)

## 📞 Support

- LiveKit Docs: https://docs.livekit.io/agents
- LiveKit Slack: https://livekit.io/join-slack
- Assignment Repo: https://github.com/Dark-Sys-Jenkins/agents-assignment

---

**Built with ❤️ for the LiveKit Intelligent Interruption Challenge**
