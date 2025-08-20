# IO Services - Discord Bot Integration

This directory contains IO (Input/Output) services for the VtuberMiku application, including Discord bot integration for voice channel interaction and user tracking.

## Discord Service Overview

The Discord service allows the VtuberMiku bot to:
- Connect to Discord servers as a bot
- Join and monitor voice channels
- Track users joining/leaving voice channels
- Detect basic voice activity (mute/unmute states)
- Send messages to text channels
- Play audio in voice channels

## ⚠️ Important Limitations

**Current Implementation Status:**
- ✅ Bot connection and authentication
- ✅ Voice channel joining/leaving
- ✅ User presence tracking (join/leave events)
- ✅ Basic speaking state detection (mute/unmute)
- ❌ **Actual audio capture from Discord users**
- ❌ **Real-time voice activity detection**
- ❌ **Audio transcription from Discord calls**

**Why Audio Capture is Complex:**
Discord's API and discord.py library have significant limitations for audio capture:
1. **No Direct Audio Access**: Discord doesn't provide direct access to user audio streams
2. **Voice Gateway Complexity**: Real audio capture requires implementing Discord's voice gateway protocol
3. **Additional Dependencies**: Requires FFmpeg, PyNaCl, and complex audio processing
4. **Privacy Concerns**: Audio recording requires explicit user consent and careful handling

## Setup Instructions

### 1. Install Dependencies

```bash
# Install discord.py with voice support
pip install discord.py[voice]

# Additional dependencies for full voice functionality (optional)
pip install PyNaCl
```

### 2. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot"
5. Copy the bot token (keep this secret!)
6. Enable required intents:
   - ✅ Server Members Intent
   - ✅ Message Content Intent (if reading messages)

### 3. Invite Bot to Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands` (if using slash commands)
3. Select bot permissions:
   - ✅ View Channels
   - ✅ Connect (voice)
   - ✅ Speak (voice)
   - ✅ Send Messages
   - ✅ Read Message History
4. Use the generated URL to invite the bot to your server

### 4. Configure Environment

Add your bot token to your environment configuration:

```bash
# In your .env file
DISCORD_BOT_TOKEN=your_bot_token_here
```

Or set it programmatically in your application.

## Usage Examples

### Basic Setup

```python
from src.backend.chat_app.services.core_services.service_manager import get_discord_service
from src.backend.chat_app.services.io_services.discord_service import DiscordConfig

# Configure the service
config = DiscordConfig(
    bot_token="your_bot_token_here",
    auto_join_voice=True,
    track_speaking=True
)

# Get service instance
discord_service = get_discord_service()

# Start the bot
success = await discord_service.start("your_bot_token_here")
if success:
    print("Discord bot connected!")
```

### Voice Channel Operations

```python
# Join a specific voice channel
channel_id = 123456789012345678  # Your voice channel ID
success = await discord_service.join_voice_channel(channel_id)

# Leave voice channel
await discord_service.leave_voice_channel()

# Get users in voice channels
users = await discord_service.get_connected_users()
for user in users:
    print(f"User: {user.display_name}, Speaking: {user.is_speaking}")

# Get currently speaking users
speaking_users = await discord_service.get_speaking_users()
```

### User Activity Monitoring

```python
# Set up callbacks for voice activity
async def on_user_speaking(user):
    print(f"🎤 {user.display_name} started speaking")
    # Here you could trigger other services like STT

async def on_user_stopped(user):
    print(f"🔇 {user.display_name} stopped speaking")

# Register callbacks
await discord_service.set_callbacks(
    on_user_start_speaking=on_user_speaking,
    on_user_stop_speaking=on_user_stopped
)
```

### Playing Audio

```python
from pathlib import Path

# Play an audio file in the voice channel
audio_path = Path("path/to/your/audio.wav")
success = await discord_service.play_audio(audio_path)
```

### Sending Messages

```python
# Send a message to a text channel
channel_id = 987654321098765432  # Your text channel ID
await discord_service.send_message(channel_id, "Hello from VtuberMiku!")
```

## Integration with VtuberMiku Services

### Event System Integration

The Discord service integrates with the VtuberMiku event system:

```python
from event_system import get_event_system, EventType

event_system = get_event_system()

# Listen for Discord events
async def handle_discord_event(event):
    if event.event_type == EventType.AUDIO_CAPTURED:
        print(f"Discord activity: {event.message}")

await event_system.subscribe(EventType.AUDIO_CAPTURED, handle_discord_event)
```

### Service Manager Integration

```python
from src.backend.chat_app.services.core_services.service_manager import (
    get_service_factory, 
    DiscordConfig
)

# Get service through factory
factory = get_service_factory()
discord_service = factory.get_service('discord', DiscordConfig(
    bot_token="your_token",
    voice_channel_id=123456789
))
```

## Current Voice Detection Capabilities

### What Works Now:
- **Mute/Unmute Detection**: Detects when users mute/unmute themselves
- **Channel Join/Leave**: Tracks when users join or leave voice channels
- **Presence Monitoring**: Knows who is in which voice channel

### What's Missing:
- **Audio Stream Capture**: Cannot capture actual audio data from users
- **Real Voice Activity**: Cannot detect when someone is actually speaking (only mute state)
- **Audio Processing**: No built-in transcription or audio analysis

### Speaking Detection Logic:
```python
# Current implementation only detects mute state
is_speaking = (
    not after.self_deaf and      # User is not deafened
    not after.self_mute          # User is not muted
)
# This doesn't mean they're actually speaking, just that they CAN speak
```

## Extending for Real Audio Capture

To implement actual audio capture, you would need to:

### 1. Implement Voice Receiver
```python
# This is a complex implementation requiring:
import discord
from discord.ext import commands

class VoiceReceiver(discord.VoiceClient):
    def __init__(self, client, channel):
        super().__init__(client, channel)
        # Custom implementation needed
```

### 2. Add Audio Processing Pipeline
- Implement Discord's voice protocol
- Handle opus audio decoding
- Add voice activity detection (VAD)
- Integrate with existing STT services

### 3. Additional Dependencies
```bash
pip install PyNaCl          # For Discord voice encryption
pip install opus-python     # For audio decoding
pip install webrtcvad       # For voice activity detection
```

## Troubleshooting

### Common Issues

**Bot doesn't connect:**
- Check if bot token is correct
- Verify bot has necessary permissions
- Ensure intents are enabled in Discord Developer Portal

**Can't join voice channel:**
- Check if bot has "Connect" permission in the voice channel
- Verify the channel ID is correct
- Make sure the channel exists and bot can see it

**No speaking detection:**
- Remember: current implementation only detects mute state
- Voice activity detection requires additional implementation
- Consider using external VAD solutions

**Audio playback fails:**
- Ensure FFmpeg is installed on the system
- Check audio file format (WAV recommended)
- Verify bot has "Speak" permission

### Debug Information

```python
# Get service status
status = await discord_service.get_service_status()
print(f"Status: {status}")

# Check if discord.py is available
from discord_service import DISCORD_AVAILABLE
print(f"Discord available: {DISCORD_AVAILABLE}")
```

## Performance Considerations

- Discord bots have rate limits - avoid excessive API calls
- Voice connections use significant bandwidth
- Audio processing is CPU intensive
- Consider using separate processes for audio handling

## Security Notes

- **Never commit bot tokens to version control**
- Store tokens in environment variables or secure configuration
- Implement proper error handling for connection failures
- Consider implementing reconnection logic for production use
- Be aware of Discord's Terms of Service regarding audio recording

## Future Enhancements

To make this a fully functional voice input system:

1. **Implement proper voice receiver** using Discord's voice gateway
2. **Add real-time audio transcription** integration
3. **Implement voice activity detection** beyond mute states
4. **Add audio buffering and processing** for better quality
5. **Create user permission system** for audio recording consent
6. **Add configuration for audio quality** and processing options

## Example: Complete Integration

Here's how you might integrate this with the existing VtuberMiku voice pipeline:

```python
async def setup_discord_voice_integration():
    # Get services
    discord_service = get_discord_service()
    whisper_service = get_whisper_service()
    
    # Start Discord bot
    await discord_service.start("your_token")
    await discord_service.join_voice_channel(your_channel_id)
    
    # Set up voice processing pipeline
    async def process_user_audio(user):
        # This would be implemented with real audio capture
        print(f"Processing audio from {user.display_name}")
        
        # Placeholder for audio transcription
        # audio_data = capture_user_audio(user)
        # transcript = await whisper_service.transcribe(audio_data)
        # await handle_voice_input(transcript, user)
    
    await discord_service.set_callbacks(
        on_user_start_speaking=process_user_audio
    )
```

This README provides a realistic overview of what's currently possible and what would be needed for full audio capture functionality.