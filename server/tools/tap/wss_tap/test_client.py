#!/usr/bin/env python3
"""
Test client that sends WAV audio to the WebSocket tap server
Simulates SignalWire sending audio
"""
import asyncio
import websockets
import wave
import audioop
import sys

async def send_test_audio():
    """Send test audio to the WebSocket server"""

    # Read the test WAV file
    with wave.open('test_tone.wav', 'rb') as wav:
        print(f"📂 Reading test_tone.wav...")
        print(f"   Channels: {wav.getnchannels()}")
        print(f"   Sample width: {wav.getsampwidth()} bytes")
        print(f"   Frame rate: {wav.getframerate()} Hz")
        print(f"   Frames: {wav.getnframes()}")

        # Read all audio data
        pcm_data = wav.readframes(wav.getnframes())
        print(f"   PCM data size: {len(pcm_data)} bytes")

    # Convert PCM to μ-law
    print(f"\n🔄 Converting PCM to μ-law...")
    ulaw_data = audioop.lin2ulaw(pcm_data, 2)  # 2 = 16-bit
    print(f"   μ-law data size: {len(ulaw_data)} bytes")

    # Connect to WebSocket server
    uri = "ws://localhost:3000"
    print(f"\n📡 Connecting to {uri}...")

    async with websockets.connect(uri) as websocket:
        print(f"✅ Connected!")

        # Send content-type header as first message
        header = "content-type:audio/mulaw;rate=8000"
        await websocket.send(header)
        print(f"📤 Sent header: {header}")

        # Send audio in chunks (simulate streaming)
        chunk_size = 160  # 20ms of audio at 8kHz
        total_sent = 0

        print(f"\n🎵 Streaming audio in {chunk_size}-byte chunks...")
        for i in range(0, len(ulaw_data), chunk_size):
            chunk = ulaw_data[i:i+chunk_size]
            await websocket.send(chunk)
            total_sent += len(chunk)

            # Print progress every 50 chunks
            if (i // chunk_size) % 50 == 0:
                progress = (total_sent / len(ulaw_data)) * 100
                print(f"   Progress: {progress:.1f}% ({total_sent}/{len(ulaw_data)} bytes)")

            # Small delay to simulate real-time streaming
            await asyncio.sleep(0.02)  # 20ms

        print(f"\n✅ Finished sending {total_sent} bytes")
        print(f"⏱️  Waiting 1 second before closing...")
        await asyncio.sleep(1)

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 WebSocket Audio Test Client")
    print("=" * 60)
    print()

    try:
        asyncio.run(send_test_audio())
        print("\n✅ Test completed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
