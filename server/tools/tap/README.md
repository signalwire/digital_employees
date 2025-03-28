# Listening (tap) to RTP Audio Streams with Python and SWML

<img src="https://github.com/user-attachments/assets/11558fc8-9fc5-449d-9a9a-4f495f9d140b" alt="image" style="width:20%;">

---

**Table of Contents**

- [Core Functionality](#core-functionality)
- [Using tap.py](#using-tap)
- [Using web_tap.py](#using-web-tap)
- [Utilizing the `tap` Method in SWML](#utilizing-the-tap-method-in-swml)

---

The `tap` Python script is designed to listen to Real-time Transport Protocol (RTP) audio streams, decode PCMU (μ-law) audio, and play it using PyAudio, with support for multiple streams.

---

## Core Functionality

`Tap` script handles the following tasks:

- **RTP Packet Reception**:  
  Listens for UDP-based RTP packets on a specified IP and port (e.g., `0.0.0.0:5004`).

- **Audio Decoding**:  
  Converts PCMU audio (payload type 0) to 16-bit PCM using a μ-law lookup table for playback.

- **Multi-Stream Support**:  
  Tracks multiple Synchronization Sources (SSRCs) and allows switching between them with arrow keys.

- **Stream Cleanup**:  
  Removes inactive SSRCs after a 2-second timeout.

---

## Using tap

- **Run the Script**: Execute it in a Windows command prompt or terminal.
- **Controls**:
  - **Left Arrow**: Switch to the previous active SSRC.
  - **Right Arrow**: Switch to the next active SSRC.
  - **'q'**: Exit the script.
- **Requirements**: Ensure PyAudio is installed (`pip install pyaudio`) and your system has an audio output device.

---

## Using web tap

- **Run the Script**: Execute it in a Windows command prompt or terminal.
- **View Webpage**: Goto `http://ip:8080` Use the ip of where the python script is running. For example: `http://192.168.100.50:8080`
- **Start Listening**: Click to start listening for the incoming rtp stream
- **Listen/Listening**: If you have more than 1 stream you can click "Listen". This will turn to "Listening" and hear the rtp stream via your web browser.



![image](https://github.com/user-attachments/assets/e964f1bf-21a3-4b6f-9561-a4a562aa5204)


---

## Utilizing the `tap` Method in SWML

The `tap` method in SignalWire Markup Language (SWML) enables developers to stream call audio to an external destination via WebSocket or RTP. This functionality is essential for applications requiring real-time audio processing, such as call monitoring or recording.

### Key Parameters

- **uri** (string, required): Specifies the destination for the audio stream. Supported formats include:
  - `rtp://IP:port`
  - `ws://example.com`
  - `wss://example.com`

- **control_id** (string, optional): An identifier for the tap session, useful for managing or stopping the tap later. If not provided, a unique ID is auto-generated and stored in the `tap_control_id` variable.

- **direction** (string, optional): Defines which part of the audio to tap:
  - `speak`: Audio sent from the party.
  - `listen`: Audio received by the party.
  - `both`: Both incoming and outgoing audio.

  Default is `speak`.

- **codec** (string, optional): Specifies the audio codec, either `PCMU` or `PCMA`. Default is `PCMU`.

- **rtp_ptime** (integer, optional): Applicable for RTP streams; sets the packetization time in milliseconds. Default is 20 ms.

### Example Usage

Add to your SWML script to enable (RTP) tap:

```json
{
  "version": "1.0.0",
  "sections": {
    "main": [
      {
        "tap": {
          "uri": "rtp://127.0.0.1:5004",
          "direction": "both"
        }
      }
    ]
  }
}
```

**Note:** Update `uri` ip address to your public ip address.
