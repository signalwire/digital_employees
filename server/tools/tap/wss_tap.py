#!/usr/bin/env python3
"""
WSS Media Tap - Raw Audio WebSocket Listener
Receives raw audio streams over WebSocket and plays them with PyAudio
"""

import asyncio
import json
import sys
import threading
import struct
from datetime import datetime
from typing import Dict, Optional, List
import websockets
import pyaudio
import numpy as np
from collections import deque

# μ-law decoding table (ITU-T G.711)
ULAW_TABLE = [
    -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
    -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
    -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
    -11900, -11388, -10876, -10364,  -9852,  -9340,  -8828,  -8316,
     -7932,  -7676,  -7420,  -7164,  -6908,  -6652,  -6396,  -6140,
     -5884,  -5628,  -5372,  -5116,  -4860,  -4604,  -4348,  -4092,
     -3900,  -3772,  -3644,  -3516,  -3388,  -3260,  -3132,  -3004,
     -2876,  -2748,  -2620,  -2492,  -2364,  -2236,  -2108,  -1980,
     -1884,  -1820,  -1756,  -1692,  -1628,  -1564,  -1500,  -1436,
     -1372,  -1308,  -1244,  -1180,  -1116,  -1052,   -988,   -924,
      -876,   -844,   -812,   -780,   -748,   -716,   -684,   -652,
      -620,   -588,   -556,   -524,   -492,   -460,   -428,   -396,
      -372,   -356,   -340,   -324,   -308,   -292,   -276,   -260,
      -244,   -228,   -212,   -196,   -180,   -164,   -148,   -132,
      -120,   -112,   -104,    -96,    -88,    -80,    -72,    -64,
       -56,    -48,    -40,    -32,    -24,    -16,     -8,      0,
     32124,  31100,  30076,  29052,  28028,  27004,  25980,  24956,
     23932,  22908,  21884,  20860,  19836,  18812,  17788,  16764,
     15996,  15484,  14972,  14460,  13948,  13436,  12924,  12412,
     11900,  11388,  10876,  10364,   9852,   9340,   8828,   8316,
      7932,   7676,   7420,   7164,   6908,   6652,   6396,   6140,
      5884,   5628,   5372,   5116,   4860,   4604,   4348,   4092,
      3900,   3772,   3644,   3516,   3388,   3260,   3132,   3004,
      2876,   2748,   2620,   2492,   2364,   2236,   2108,   1980,
      1884,   1820,   1756,   1692,   1628,   1564,   1500,   1436,
      1372,   1308,   1244,   1180,   1116,   1052,    988,    924,
       876,    844,    812,    780,    748,    716,    684,    652,
       620,    588,    556,    524,    492,    460,    428,    396,
       372,    356,    340,    324,    308,    292,    276,    260,
       244,    228,    212,    196,    180,    164,    148,    132,
       120,    112,    104,     96,     88,     80,     72,     64,
        56,     48,     40,     32,     24,     16,      8,      0
]

def decode_mulaw(mulaw_data: bytes) -> bytes:
    """
    Decode μ-law (PCMU) encoded audio to 16-bit PCM

    μ-law (PCMU/G.711) is a companding algorithm used in telephony
    It compresses 16-bit PCM to 8-bit, commonly used at 8kHz sampling
    """
    pcm_values = []
    for byte in mulaw_data:
        # Each μ-law byte maps to a 16-bit PCM value via the lookup table
        pcm_value = ULAW_TABLE[byte]
        pcm_values.append(pcm_value)

    # Pack as 16-bit little-endian integers
    return struct.pack('<%dh' % len(pcm_values), *pcm_values)

class RawAudioStream:
    """Represents a single raw audio stream"""

    def __init__(self, stream_id: str, content_type: str = "audio/mulaw;rate=8000"):
        self.stream_id = stream_id
        self.content_type = content_type
        self.connected_at = datetime.now()

        # Parse content type
        if "mulaw" in content_type or "PCMU" in content_type:
            self.encoding = "mulaw"
        else:
            self.encoding = "pcm"

        # Extract sample rate
        if "rate=" in content_type:
            rate_str = content_type.split("rate=")[1].split(";")[0]
            self.sample_rate = int(rate_str)
        else:
            self.sample_rate = 8000

        # Audio buffer - using deque for efficient FIFO operations
        self.audio_buffer = deque(maxlen=self.sample_rate * 10)  # 10 seconds max buffer

        # Statistics
        self.bytes_received = 0
        self.last_activity = datetime.now()
        self.is_active = True

    def add_audio(self, raw_audio: bytes, debug: bool = False):
        """Add raw audio data to the buffer"""
        # Decode based on format
        if self.encoding == "mulaw":
            pcm_data = decode_mulaw(raw_audio)

            if debug and len(pcm_data) >= 4:
                # Debug: Check conversion is working
                # μ-law 0xFF should decode to small values (silence)
                # μ-law 0x00 should decode to -32124 (max negative)
                # μ-law 0x80 should decode to 32124 (max positive)
                test_values = np.frombuffer(pcm_data[:10], dtype=np.int16)
                if all(abs(v) < 100 for v in test_values):
                    # Likely silence
                    pass
                else:
                    # Some audio content
                    print(f"    Audio samples (first 5): {test_values[:5]}")
        else:
            # Assume it's already PCM
            pcm_data = raw_audio

        # Convert to numpy array and add to buffer
        audio_array = np.frombuffer(pcm_data, dtype=np.int16)
        self.audio_buffer.extend(audio_array)

        self.bytes_received += len(raw_audio)
        self.last_activity = datetime.now()

    def get_audio_data(self, num_frames: int) -> bytes:
        """Get audio data for playback"""
        if len(self.audio_buffer) >= num_frames:
            # Get the requested number of frames
            frames = [self.audio_buffer.popleft() for _ in range(num_frames)]
            return np.array(frames, dtype=np.int16).tobytes()
        else:
            # Not enough data, return silence
            return np.zeros(num_frames, dtype=np.int16).tobytes()

class WSSRawMediaTap:
    """WebSocket server for raw audio streaming with integrated playback"""

    def __init__(self, host: str = '0.0.0.0', port: int = 3000, debug: bool = False, volume: float = 1.0):
        self.host = host
        self.port = port
        self.debug = debug
        self.volume = volume  # Volume multiplier (1.0 = normal, 2.0 = double, etc.)

        # Stream management
        self.streams: Dict[str, RawAudioStream] = {}
        self.stream_order: List[str] = []  # Track order of streams
        self.current_stream_index = 0
        self.lock = threading.Lock()

        # Audio playback
        self.pa = pyaudio.PyAudio()
        self.audio_stream = None
        self.audio_thread = None
        self.audio_running = False

        # UI state
        self.running = True
        self.first_stream_received = False

    async def handle_connection(self, websocket):
        """Handle incoming WebSocket connection"""
        remote_address = websocket.remote_address if hasattr(websocket, 'remote_address') else 'unknown'
        stream_id = f"{remote_address[0]}:{remote_address[1]}" if isinstance(remote_address, tuple) else str(remote_address)

        self.log_message(f"New connection from {remote_address}")

        # First message should be the content type
        content_type = "audio/mulaw;rate=8000"  # Default
        is_first_message = True
        audio_stream = None

        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    # Binary audio data
                    if audio_stream:
                        audio_stream.add_audio(message, debug=self.debug)
                        if self.debug:
                            buffer_size = len(audio_stream.audio_buffer)
                            # Show first few bytes in hex to verify it's μ-law
                            hex_preview = message[:8].hex() if len(message) >= 8 else message.hex()
                            self.log_message(f"📊 Received {len(message)} bytes (hex: {hex_preview}...) | Buffer: {buffer_size} samples")
                    else:
                        # No header received, assume default format
                        self.log_message(f"No format header received, using default: {content_type}")
                        audio_stream = self.create_stream(stream_id, content_type)
                        audio_stream.add_audio(message, debug=self.debug)
                else:
                    # Text message - should be content type
                    if is_first_message:
                        try:
                            # Try to parse as JSON
                            data = json.loads(message)
                            if "content-type" in data:
                                content_type = data["content-type"]
                                self.log_message(f"Audio format: {content_type}")
                            elif "format" in data:
                                content_type = data["format"]
                                self.log_message(f"Audio format: {content_type}")
                        except json.JSONDecodeError:
                            # Maybe it's just the content type string
                            if "audio" in message:
                                content_type = message.strip()
                                self.log_message(f"Audio format: {content_type}")

                        # Create the audio stream
                        audio_stream = self.create_stream(stream_id, content_type)
                        is_first_message = False
                    elif self.debug:
                        self.log_message(f"Received text message: {message}")

        except websockets.exceptions.ConnectionClosed:
            self.log_message(f"Connection closed from {remote_address}")
        except Exception as e:
            self.log_message(f"Error handling connection: {e}")
        finally:
            # Clean up stream
            if stream_id in self.streams:
                self.remove_stream(stream_id)

    def create_stream(self, stream_id: str, content_type: str) -> RawAudioStream:
        """Create and register a new audio stream"""
        with self.lock:
            # Create new stream
            stream = RawAudioStream(stream_id, content_type)
            self.streams[stream_id] = stream
            self.stream_order.append(stream_id)

            # Start audio playback on first stream OR if nothing is currently playing
            if not self.first_stream_received or not self.audio_running:
                self.first_stream_received = True
                self.current_stream_index = len(self.stream_order) - 1  # Play the new stream
                self.start_audio_playback(stream.sample_rate)
                self.log_message(f"🎵 Started playing stream: {stream_id}")
                self.log_message(f"   Audio format: {content_type}")
                self.log_message(f"   Playback rate: {stream.sample_rate}Hz")
            else:
                self.log_message(f"📞 New stream connected: {stream_id} (Stream {len(self.stream_order)})")

        return stream

    def remove_stream(self, stream_id: str):
        """Remove a stream"""
        with self.lock:
            if stream_id in self.streams:
                was_playing = (self.stream_order[self.current_stream_index] == stream_id) if self.stream_order else False

                self.streams[stream_id].is_active = False
                del self.streams[stream_id]

                if stream_id in self.stream_order:
                    idx = self.stream_order.index(stream_id)
                    self.stream_order.remove(stream_id)

                    # Adjust current index if needed
                    if self.current_stream_index >= len(self.stream_order) and self.stream_order:
                        self.current_stream_index = len(self.stream_order) - 1
                    elif not self.stream_order:
                        self.current_stream_index = 0
                        # Stop audio if no streams left
                        self.stop_audio_playback()
                        self.log_message("🔇 No active streams, stopping playback")
                    elif was_playing and self.stream_order:
                        # If we were playing this stream, switch to another
                        new_stream_id = self.stream_order[self.current_stream_index]
                        self.log_message(f"🔄 Auto-switching to stream: {new_stream_id}")

                self.log_message(f"📴 Stream disconnected: {stream_id}")

    def start_audio_playback(self, sample_rate: int = 8000):
        """Start audio playback thread"""
        # Stop existing playback if running
        if self.audio_running:
            self.stop_audio_playback()

        self.audio_running = True

        # Open audio stream
        try:
            self.audio_stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True,
                frames_per_buffer=160,  # 20ms at 8kHz
                output_device_index=None  # Use default output device
            )

            # Start playback thread
            self.audio_thread = threading.Thread(target=self.audio_playback_loop)
            self.audio_thread.daemon = True
            self.audio_thread.start()

            if self.debug:
                self.log_message(f"Audio playback started successfully at {sample_rate}Hz")
        except Exception as e:
            self.log_message(f"❌ Failed to start audio playback: {e}")
            self.audio_running = False

    def stop_audio_playback(self):
        """Stop audio playback"""
        self.audio_running = False
        if self.audio_thread:
            self.audio_thread.join(timeout=0.5)
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except:
                pass
            self.audio_stream = None

    def audio_playback_loop(self):
        """Continuous audio playback loop"""
        frames_played = 0
        last_report_time = datetime.now()

        while self.audio_running:
            with self.lock:
                if self.stream_order and 0 <= self.current_stream_index < len(self.stream_order):
                    stream_id = self.stream_order[self.current_stream_index]
                    if stream_id in self.streams:
                        stream = self.streams[stream_id]
                        audio_data = stream.get_audio_data(160)  # Get 20ms of audio

                        if self.audio_stream and audio_data:
                            # Apply volume adjustment if needed
                            if self.volume != 1.0:
                                # Convert to numpy, apply volume, clip to prevent overflow
                                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                                audio_array = np.clip(audio_array * self.volume, -32768, 32767).astype(np.int16)
                                audio_data = audio_array.tobytes()

                            try:
                                self.audio_stream.write(audio_data)
                                frames_played += 1

                                # Report playback status periodically in debug mode
                                if self.debug and (datetime.now() - last_report_time).seconds >= 5:
                                    self.log_message(f"🔊 Playing: {frames_played * 20}ms of audio from {stream_id}")
                                    last_report_time = datetime.now()

                            except Exception as e:
                                if self.debug:
                                    self.log_message(f"Audio playback error: {e}")

    def switch_stream(self, direction: str):
        """Switch to next/previous stream"""
        with self.lock:
            if not self.stream_order:
                return

            if direction == 'next' and self.current_stream_index < len(self.stream_order) - 1:
                self.current_stream_index += 1
            elif direction == 'prev' and self.current_stream_index > 0:
                self.current_stream_index -= 1

            stream_id = self.stream_order[self.current_stream_index]
            self.log_message(f"Switched to stream {self.current_stream_index + 1}/{len(self.stream_order)}: {stream_id}")

    def log_message(self, message: str):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def display_status(self):
        """Display current status"""
        with self.lock:
            if not self.stream_order:
                self.log_message("Waiting for incoming streams...")
            else:
                if self.current_stream_index < len(self.stream_order):
                    stream_id = self.stream_order[self.current_stream_index]
                    stream = self.streams.get(stream_id)
                    if stream:
                        self.log_message(f"Stream {self.current_stream_index + 1}/{len(self.stream_order)}: {stream_id} | Bytes: {stream.bytes_received}")

    async def run(self):
        """Run the main application"""
        print("\n" + "=" * 60)
        print("WSS Raw Media Tap - Raw Audio WebSocket Listener")
        print("=" * 60)
        print("\nProtocol:")
        print("  1. First message: {\"content-type\":\"audio/mulaw;rate=8000\"}")
        print("  2. Subsequent: Raw μ-law audio bytes")
        print("\nControls:")
        print("  ← / → : Navigate between streams")
        print("  q     : Quit")
        print("\n" + "-" * 60 + "\n")

        self.log_message(f"🚀 Starting server on ws://{self.host}:{self.port}")
        self.log_message("⏳ Waiting for audio streams...")
        self.log_message("🎯 Will auto-play the first stream that connects")
        if self.debug:
            self.log_message("🔍 DEBUG MODE ENABLED")
        print("")

        try:
            # Start WebSocket server
            server = await websockets.serve(self.handle_connection, self.host, self.port)

            self.log_message(f"✅ Server listening on {self.host}:{self.port}")
            self.log_message("")
            self.display_status()

            # Keep the server running
            while self.running:
                await asyncio.sleep(1)

                # Periodic status update
                if self.stream_order:
                    with self.lock:
                        if self.current_stream_index < len(self.stream_order):
                            stream_id = self.stream_order[self.current_stream_index]
                            stream = self.streams.get(stream_id)
                            if stream and self.debug:
                                buffered = len(stream.audio_buffer)
                                print(f"\r🔊 Playing: {stream_id} | Buffer: {buffered} samples | Received: {stream.bytes_received} bytes", end='', flush=True)

            # Close the server
            server.close()
            await server.wait_closed()

        except KeyboardInterrupt:
            self.log_message("Shutting down...")
        except Exception as e:
            self.log_message(f"Server error: {e}")
        finally:
            # Clean up audio
            self.audio_running = False
            if self.audio_thread:
                self.audio_thread.join(timeout=1)
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            self.pa.terminate()

            print("\n✅ Shutdown complete")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='WSS Raw Media Tap - Raw Audio WebSocket Listener')
    parser.add_argument('--host', default='0.0.0.0', help='Host to listen on (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=3000, help='Port to listen on (default: 3000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--volume', type=float, default=1.0, help='Volume multiplier (1.0=normal, 2.0=double, 0.5=half)')
    args = parser.parse_args()

    if args.volume != 1.0:
        print(f"🔊 Volume set to {args.volume * 100:.0f}%")

    app = WSSRawMediaTap(host=args.host, port=args.port, debug=args.debug, volume=args.volume)

    try:
        asyncio.run(app.run())
    except Exception as e:
        print(f"Application error: {e}")

if __name__ == "__main__":
    main()
