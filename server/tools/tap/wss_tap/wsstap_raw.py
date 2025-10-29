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
import subprocess
import signal
import re
import time
import os
import http
from datetime import datetime
from typing import Dict, Optional, List
import websockets
from websockets.http11 import Response
from websockets.datastructures import Headers
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

    def __init__(self, host: str = '0.0.0.0', port: int = 3000, debug: bool = False, volume: float = 1.0, enable_cloudflared: bool = False):
        self.host = host
        self.port = port
        self.debug = debug
        self.volume = volume  # Volume multiplier (1.0 = normal, 2.0 = double, etc.)
        self.enable_cloudflared = enable_cloudflared

        # Stream management
        self.streams: Dict[str, RawAudioStream] = {}
        self.stream_order: List[str] = []  # Track order of streams
        self.current_stream_index = 0
        self.lock = threading.Lock()

        # WebSocket client tracking for broadcasting
        self.websocket_clients: Set = set()  # Track all connected clients

        # Audio playback - DISABLED to prevent hanging in headless environments
        # PyAudio initialization can hang when no audio devices are available
        print("Info: Audio playback is disabled (web interface only mode)")
        self.pa = None
        self.audio_stream = None
        self.audio_thread = None
        self.audio_running = False

        # Cloudflared tunnel
        self.cloudflared_process = None
        self.cloudflared_url = None

        # UI state
        self.running = True
        self.first_stream_received = False

    async def broadcast_audio(self, audio_data: bytes, sender_websocket, stream_id: str):
        """Broadcast audio data to all connected clients except the sender, but only if this is the active stream"""
        if not self.websocket_clients:
            return

        # Check if this stream is the currently selected one
        with self.lock:
            if not self.stream_order or stream_id not in self.stream_order:
                return

            stream_index = self.stream_order.index(stream_id)
            if stream_index != self.current_stream_index:
                # This is not the active stream, don't broadcast
                return

        # Create list of clients to broadcast to (all except sender)
        clients_to_send = [ws for ws in self.websocket_clients if ws != sender_websocket]

        if not clients_to_send:
            return

        # Send to all clients concurrently
        await asyncio.gather(
            *[ws.send(audio_data) for ws in clients_to_send],
            return_exceptions=True  # Don't fail if one client has an error
        )

    async def handle_connection(self, websocket):
        """Handle incoming WebSocket connection"""
        remote_address = websocket.remote_address if hasattr(websocket, 'remote_address') else 'unknown'
        stream_id = f"{remote_address[0]}:{remote_address[1]}" if isinstance(remote_address, tuple) else str(remote_address)

        # Register this client
        self.websocket_clients.add(websocket)
        self.log_message(f"New connection from {remote_address} (Total clients: {len(self.websocket_clients)})")

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

                        # Broadcast audio to all other connected clients (only if this is the active stream)
                        await self.broadcast_audio(message, websocket, stream_id)
                    else:
                        # No header received, assume default format
                        self.log_message(f"No format header received, using default: {content_type}")
                        audio_stream = self.create_stream(stream_id, content_type)
                        audio_stream.add_audio(message, debug=self.debug)
                        # Broadcast audio to all other connected clients (only if this is the active stream)
                        await self.broadcast_audio(message, websocket, stream_id)
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
            # Remove this client from the set
            self.websocket_clients.discard(websocket)
            self.log_message(f"Client disconnected: {remote_address} (Total clients: {len(self.websocket_clients)})")

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

    def start_cloudflared(self):
        """Start cloudflared tunnel"""
        try:
            # Check if cloudflared is available
            result = subprocess.run(['which', 'cloudflared'], capture_output=True)
            if result.returncode != 0:
                self.log_message("⚠️  cloudflared not found - continuing without tunnel")
                return False

            self.log_message("🌐 Starting cloudflared tunnel...")

            # Start cloudflared in the background
            self.cloudflared_process = subprocess.Popen(
                ['cloudflared', 'tunnel', '--url', f'http://localhost:{self.port}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Function to read cloudflared output in a thread
            def read_cloudflared_output():
                try:
                    for line in iter(self.cloudflared_process.stdout.readline, ''):
                        if not line:
                            break
                        # Look for the tunnel URL
                        match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
                        if match and not self.cloudflared_url:
                            self.cloudflared_url = match.group(0)
                            break
                except:
                    pass

            # Start reading thread
            reader_thread = threading.Thread(target=read_cloudflared_output, daemon=True)
            reader_thread.start()

            # Wait up to 10 seconds for URL to be found
            for i in range(20):
                time.sleep(0.5)
                if self.cloudflared_url:
                    break
                if self.cloudflared_process.poll() is not None:
                    break

            # Check results
            if self.cloudflared_process.poll() is None:  # Process is still running
                if self.cloudflared_url:
                    # Save URL to file
                    try:
                        with open('/tmp/wsstap_cloudflared_url.txt', 'w') as f:
                            f.write(f"{self.cloudflared_url}\n")
                    except:
                        pass

                    # Display the URL prominently
                    print("\n" + "=" * 70)
                    print("🎉 CLOUDFLARED TUNNEL ESTABLISHED")
                    print("=" * 70)
                    print(f"📍 Local Server:    ws://localhost:{self.port}")
                    print(f"🔗 Public HTTPS:    {self.cloudflared_url}")
                    wss_url = self.cloudflared_url.replace('https://', 'wss://')
                    print(f"📡 Public WSS:      {wss_url}")
                    print(f"🔌 Port:            {self.port}")
                    print("=" * 70)
                    print("")
                else:
                    self.log_message("⚠️  Cloudflared started but URL not detected yet")
                    self.log_message(f"   Local server running on ws://localhost:{self.port}")

                return True
            else:
                self.log_message("❌ cloudflared failed to start")
                return False

        except Exception as e:
            self.log_message(f"❌ Error starting cloudflared: {e}")
            return False

    def stop_cloudflared(self):
        """Stop cloudflared tunnel"""
        if self.cloudflared_process:
            try:
                self.log_message("🔌 Stopping cloudflared tunnel...")
                self.cloudflared_process.terminate()
                try:
                    self.cloudflared_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.cloudflared_process.kill()
                self.log_message("✅ Cloudflared tunnel stopped")
            except Exception as e:
                if self.debug:
                    self.log_message(f"Error stopping cloudflared: {e}")

    def log_message(self, message: str):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    async def process_request(self, connection, request):
        """Handle HTTP requests before WebSocket upgrade - serves the web interface"""
        # Check if this is a WebSocket upgrade request
        upgrade_header = request.headers.get('Upgrade', '').lower()

        # If it's a WebSocket upgrade, return None to proceed
        if upgrade_header == 'websocket':
            return None

        # Handle HTTP requests (not WebSocket upgrades)
        if request.path == "/":
            html_path = os.path.join(os.path.dirname(__file__), 'web_interface.html')
            try:
                with open(html_path, 'r') as f:
                    html_content = f.read()

                # Return HTTP response using Response object
                headers = Headers([('Content-Type', 'text/html; charset=utf-8')])
                return Response(
                    200,
                    'OK',
                    headers,
                    html_content.encode('utf-8')
                )
            except FileNotFoundError:
                headers = Headers([('Content-Type', 'text/plain')])
                return Response(
                    404,
                    'Not Found',
                    headers,
                    b'Web interface not found'
                )

        # Test audio endpoint - triggers test_client.py
        elif request.path == "/test-audio":
            try:
                # Run test_client.py in the background
                script_path = os.path.join(os.path.dirname(__file__), 'test_client.py')
                venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'python')

                # Use venv python if it exists, otherwise use system python
                python_cmd = venv_python if os.path.exists(venv_python) else 'python3'

                # Run test client
                subprocess.Popen([python_cmd, script_path],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)

                # Return success response
                headers = Headers([('Content-Type', 'application/json')])
                response_data = json.dumps({'status': 'success', 'message': 'Test audio started'})
                return Response(
                    200,
                    'OK',
                    headers,
                    response_data.encode('utf-8')
                )
            except Exception as e:
                headers = Headers([('Content-Type', 'application/json')])
                response_data = json.dumps({'status': 'error', 'message': str(e)})
                return Response(
                    500,
                    'Internal Server Error',
                    headers,
                    response_data.encode('utf-8')
                )

        # API endpoint to list active streams
        elif request.path == "/api/streams":
            with self.lock:
                streams_list = []
                for idx, stream_id in enumerate(self.stream_order):
                    stream = self.streams.get(stream_id)
                    if stream:
                        duration = (datetime.now() - stream.connected_at).total_seconds()
                        streams_list.append({
                            'id': stream_id,
                            'index': idx,
                            'encoding': stream.encoding,
                            'sample_rate': stream.sample_rate,
                            'bytes_received': stream.bytes_received,
                            'duration': int(duration),
                            'is_playing': idx == self.current_stream_index,
                            'connected_at': stream.connected_at.isoformat()
                        })

                response_data = {
                    'streams': streams_list,
                    'current_index': self.current_stream_index,
                    'total_streams': len(streams_list)
                }

                headers = Headers([
                    ('Content-Type', 'application/json'),
                    ('Access-Control-Allow-Origin', '*')
                ])
                return Response(
                    200,
                    'OK',
                    headers,
                    json.dumps(response_data).encode('utf-8')
                )

        # API endpoint to get WebSocket URL
        elif request.path == "/api/ws-url":
            headers = Headers([
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*')
            ])

            # Determine the WebSocket URL
            if self.cloudflared_url:
                ws_url = self.cloudflared_url.replace('https://', 'wss://')
            else:
                ws_url = f'ws://localhost:{self.port}'

            response_data = json.dumps({
                'ws_url': ws_url,
                'cloudflared': bool(self.cloudflared_url)
            })
            return Response(
                200,
                'OK',
                headers,
                response_data.encode('utf-8')
            )

        # API endpoint to select/switch stream
        elif request.path.startswith("/api/select-stream"):
            try:
                # Parse query string for stream index
                if '?' in request.path:
                    query_string = request.path.split('?')[1]
                    params = dict(param.split('=') for param in query_string.split('&'))
                    stream_index = int(params.get('index', 0))

                    with self.lock:
                        if 0 <= stream_index < len(self.stream_order):
                            self.current_stream_index = stream_index
                            stream_id = self.stream_order[stream_index]
                            self.log_message(f"Switched to stream {stream_index + 1}: {stream_id}")

                            headers = Headers([
                                ('Content-Type', 'application/json'),
                                ('Access-Control-Allow-Origin', '*')
                            ])
                            response_data = json.dumps({
                                'status': 'success',
                                'message': f'Switched to stream {stream_index}',
                                'stream_id': stream_id
                            })
                            return Response(
                                200,
                                'OK',
                                headers,
                                response_data.encode('utf-8')
                            )
                        else:
                            raise ValueError(f'Invalid stream index: {stream_index}')
                else:
                    raise ValueError('Missing index parameter')
            except Exception as e:
                headers = Headers([
                    ('Content-Type', 'application/json'),
                    ('Access-Control-Allow-Origin', '*')
                ])
                response_data = json.dumps({'status': 'error', 'message': str(e)})
                return Response(
                    400,
                    'Bad Request',
                    headers,
                    response_data.encode('utf-8')
                )

        # For other paths, return None to let websockets handle it
        return None

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

        # Start cloudflared tunnel if enabled
        if self.enable_cloudflared:
            self.start_cloudflared()
            print("")

        self.log_message(f"🚀 Starting WebSocket server on ws://{self.host}:{self.port}")
        self.log_message("⏳ Waiting for audio streams...")
        self.log_message("🎯 Will auto-play the first stream that connects")
        if self.debug:
            self.log_message("🔍 DEBUG MODE ENABLED")
        print("")

        try:
            # Start WebSocket server with HTTP request handler
            server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                process_request=self.process_request
            )

            self.log_message(f"✅ WebSocket server listening on {self.host}:{self.port}")
            self.log_message(f"📱 Web interface available at: http://{self.host}:{self.port}")
            if self.cloudflared_url:
                self.log_message(f"🌐 Public URL: {self.cloudflared_url}")
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

            # Stop cloudflared tunnel
            self.stop_cloudflared()

            print("\n✅ Shutdown complete")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='WSS Raw Media Tap - Raw Audio WebSocket Listener')
    parser.add_argument('--host', default='0.0.0.0', help='Host to listen on (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=3000, help='WebSocket port to listen on (default: 3000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--volume', type=float, default=1.0, help='Volume multiplier (1.0=normal, 2.0=double, 0.5=half)')
    parser.add_argument('--cloudflared', action='store_true', help='Enable cloudflared tunnel for public access')
    args = parser.parse_args()

    if args.volume != 1.0:
        print(f"🔊 Volume set to {args.volume * 100:.0f}%")

    app = WSSRawMediaTap(host=args.host, port=args.port, debug=args.debug, volume=args.volume, enable_cloudflared=args.cloudflared)

    try:
        asyncio.run(app.run())
    except Exception as e:
        print(f"Application error: {e}")

if __name__ == "__main__":
    main()
