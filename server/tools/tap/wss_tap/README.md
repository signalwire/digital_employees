# WSS Raw Media Tap - Web Interface

A real-time WebSocket audio streaming and monitoring interface with advanced audio playback features.

<img src="https://github.com/user-attachments/assets/fb63243a-f3f5-487e-be62-d13fce7d2f83" alt="image" width="50%" />

## Overview

This web interface provides a professional audio tap monitoring solution for WebSocket streams. It automatically detects audio encoding (μ-law, A-law, PCM), sample rates, and provides real-time visualization with configurable audio settings that persist across sessions.

## Features


<img src="https://github.com/user-attachments/assets/853b6f84-91b4-4181-bc2d-ca7c72e021a7" alt="image" width="50%" />



### Audio Playback
- **Scheduled Playback**: Uses Web Audio API's precise timing to eliminate gaps between audio chunks
- **Auto-Detection**: Automatically detects audio encoding and sample rate from stream headers
- **Supported Formats**:
  - μ-law (G.711)
  - A-law (G.711)
  - PCM/L16
- **Sample Rates**: 8kHz, 16kHz, 44.1kHz, 48kHz (auto-detected)

### Audio Quality Features
- **Gap-Free Playback**: Scheduled audio chunks prevent robotic/choppy sound
- **Buffer Management**:
  - Configurable startup buffer (default: 100ms)
  - Configurable recovery buffer (default: 50ms)
- **Volume Control**: Real-time volume adjustment with default 85% to prevent clipping
- **Anti-Clipping**: Reduced default volume leaves headroom for dynamic audio

### Real-Time Monitoring
- **Live Audio Visualization**: Waveform display using Web Audio API analyser
- **Connection Status**: Real-time WebSocket connection indicator
- **Audio Metrics**:
  - Sample rate display
  - Encoding type
  - Bytes received counter
  - Duration timer

### Persistent Settings
All settings are saved to browser localStorage and persist across sessions:
- Default volume (0-100%)
- Startup buffer delay (0-1000ms)
- Recovery buffer delay (0-500ms)

## Usage

### Basic Operation

1. **Open the Interface**
   ```bash
   # Start the WebSocket tap server first
   python wsstap_raw.py --cloudflared

   # Then open the web interface
   http://localhost:3000
   ```

2. **Connect and Play**
   - Click "Connect & Play" to start streaming
   - The interface auto-connects on page load
   - Audio plays automatically once connection is established

3. **Adjust Volume**
   - Use the volume slider for real-time volume control
   - Changes apply immediately without reconnecting

### Configuring Settings

1. **Open Settings Panel**
   - Scroll down to "Audio Settings" section

2. **Available Settings**:
   - **Default Volume**: 0-100% (recommended: 85%)
   - **Startup Buffer**: 0-1000ms (default: 100ms)
     - Initial buffer before playback starts
     - Higher values = more stable but delayed start
   - **Recovery Buffer**: 0-500ms (default: 50ms)
     - Buffer when playback falls behind schedule
     - Prevents audio glitches during network hiccups

3. **Save or Reset**
   - Click "Save Settings" to persist changes
   - Click "Reset to Defaults" to restore defaults
   - Note: Buffer changes require page refresh to take effect

## Technical Details

### Audio Pipeline

```
WebSocket Stream → Header Detection → Decoder (μ-law/A-law/PCM) →
Float32 PCM → AudioBuffer → Scheduled Playback → Gain Node →
Analyser → Audio Output
```

### Scheduled Playback

The interface uses Web Audio API's `AudioBufferSourceNode.start(time)` for precise scheduling:

```javascript
// Schedule chunk at exact time
source.start(this.nextPlayTime);

// Calculate next chunk time
const chunkDuration = audioBuffer.duration;
this.nextPlayTime += chunkDuration;

// Recovery if falling behind
if (this.nextPlayTime < currentTime) {
    this.nextPlayTime = currentTime + this.recoveryBuffer;
}
```

This eliminates gaps between chunks that would cause robotic/choppy audio.

### Audio Context

- **Source Sample Rate**: Detected from stream (typically 8kHz for telephony)
- **Output Sample Rate**: Browser's native rate (typically 48kHz or 44.1kHz)
- **Resampling**: Browser automatically handles resampling
- **Bit Depth**: 32-bit float internally, decoded from 16-bit PCM or 8-bit companded

### Buffer Strategy

1. **Startup Buffer** (100ms default):
   - Added before first chunk plays
   - Prevents initial underruns
   - Builds small audio queue

2. **Recovery Buffer** (50ms default):
   - Applied when playback falls behind
   - Gives network time to catch up
   - Prevents repeated glitches

## Supported Audio Formats

### μ-law (PCMU)
- **Header**: `content-type:audio/mulaw;rate=8000`
- **Common Use**: Telephony, VoIP
- **Sample Rate**: Typically 8kHz
- **Compression**: 8-bit logarithmic companding

### A-law
- **Header**: `content-type:audio/alaw;rate=8000`
- **Common Use**: European telephony
- **Sample Rate**: Typically 8kHz
- **Compression**: 8-bit logarithmic companding

### Linear PCM (L16)
- **Header**: `content-type:audio/l16;rate=16000`
- **Common Use**: High-quality audio
- **Sample Rate**: Variable (8k, 16k, 44.1k, 48k)
- **Format**: 16-bit linear PCM

## Troubleshooting

### Audio Quality Issues

**Problem**: Robotic/choppy audio
- **Solution**: Already fixed with scheduled playback
- **Check**: Ensure using latest version with scheduled playback

**Problem**: Static/clipping on loud sounds
- **Solution**: Reduce volume in settings (try 70-85%)
- **Check**: Current volume setting

**Problem**: Audio drops out
- **Solution**: Increase startup buffer (try 150-200ms)
- **Alternative**: Increase recovery buffer (try 75-100ms)

### Connection Issues

**Problem**: Cannot connect
- **Check**: WebSocket server is running
- **Check**: Correct WebSocket URL in console
- **Check**: Firewall/network settings

**Problem**: Auto-connect fails
- **Solution**: Manually click "Connect & Play"
- **Check**: Browser console for errors

### Settings Not Persisting

**Problem**: Settings reset on page reload
- **Check**: Browser localStorage is enabled
- **Check**: Not in private/incognito mode
- **Try**: Different browser

## Browser Compatibility

- **Chrome/Edge**: Full support ✓
- **Firefox**: Full support ✓
- **Safari**: Full support ✓ (requires user interaction for audio)
- **Mobile**: Supported but may require user gesture to start audio

### Required APIs
- Web Audio API
- WebSockets
- localStorage
- Canvas (for visualization)

## Performance

### Resource Usage
- **CPU**: Low (~2-5% on modern systems)
- **Memory**: ~50-100MB depending on buffer size
- **Network**: Matches stream bitrate (typically 64kbps for 8kHz μ-law)

### Optimization Tips
- Lower startup buffer = less latency but more risk of glitches
- Higher recovery buffer = more stability but longer catch-up delay
- Volume at 85% provides good headroom without being too quiet

## Development

### File Structure
```
web_interface.html
├── HTML Structure (lines 1-446)
│   ├── Controls & Status
│   ├── Audio Visualization Canvas
│   ├── Info Cards (encoding, sample rate, etc.)
│   └── Settings Panel
└── JavaScript (lines 447-991)
    ├── μ-law/A-law Decoding Tables
    ├── Settings Management (localStorage)
    ├── AudioStreamPlayer Class
    ├── Visualization Functions
    └── Event Listeners
```

### Key Components

**AudioStreamPlayer Class**:
- Manages WebSocket connection
- Handles audio decoding and playback
- Implements scheduled playback algorithm
- Manages audio queue and timing

**Settings Management**:
- `loadSettings()`: Loads from localStorage
- `saveSettings()`: Persists to localStorage
- `resetSettings()`: Restores defaults
- `applySettingsToUI()`: Updates form fields

### Current Version
- ✓ Scheduled playback for gap-free audio
- ✓ Configurable buffer settings
- ✓ Persistent settings via localStorage
- ✓ Anti-clipping volume defaults
- ✓ Auto-detection of encoding and sample rate
- ✓ Real-time visualization
- ✓ Recovery buffer for network issues

## Troubleshooting

For issues or questions:
1. Check console for error messages (F12 in most browsers)
2. Verify WebSocket server is running and accessible
3. Try resetting settings to defaults
4. Refresh the page and reconnect

## Related Files

- `wsstap_raw.py`: WebSocket tap server (backend)
- `test_client.py`: Test client for sending audio
- `test_tone.wav`: Test audio file
