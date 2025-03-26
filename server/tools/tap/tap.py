import socket
import pyaudio
import struct
import time
import threading
import sys
import platform
if platform.system() != 'Windows':
    import termios
    import tty
else:
    import msvcrt
from collections import defaultdict

# RTP settings
RTP_IP = "0.0.0.0"  # Listen on all interfaces
RTP_PORT = 5004     # Port to listen on

# Audio settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
CHUNK = 160  # 20ms of audio at 8000Hz

# Initialize PyAudio
audio = pyaudio.PyAudio()
stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True)

# Create a socket to listen for RTP packets
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((RTP_IP, RTP_PORT))

print(f"Listening for RTP on {RTP_IP}:{RTP_PORT}")

# SSRC management
active_ssrcs = []  # List of active SSRCs
ssrc_last_activity = {}  # Track last packet time for each SSRC
current_ssrc_index = 0  # Index of currently selected SSRC
INACTIVE_TIMEOUT = 2  # Seconds before SSRC is considered inactive

# µ-law to linear 16-bit PCM conversion table
ULAW_TO_PCM_TABLE = [-32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
                     -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
                     -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
                     -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
                     -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
                     -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
                     -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
                     -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
                     -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
                     -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
                     -876, -844, -812, -780, -748, -716, -684, -652,
                     -620, -588, -556, -524, -492, -460, -428, -396,
                     -372, -356, -340, -324, -308, -292, -276, -260,
                     -244, -228, -212, -196, -180, -164, -148, -132,
                     -120, -112, -104, -96, -88, -80, -72, -64,
                     -56, -48, -40, -32, -24, -16, -8, 0,
                     32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
                     23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
                     15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
                     11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
                     7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
                     5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
                     3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
                     2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
                     1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
                     1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
                     876, 844, 812, 780, 748, 716, 684, 652,
                     620, 588, 556, 524, 492, 460, 428, 396,
                     372, 356, 340, 324, 308, 292, 276, 260,
                     244, 228, 212, 196, 180, 164, 148, 132,
                     120, 112, 104, 96, 88, 80, 72, 64,
                     56, 48, 40, 32, 24, 16, 8, 0]

# Add a global flag to control the main loop
running = True

def get_char():
    """Get a single character from stdin in a cross-platform way"""
    if platform.system() != 'Windows':
        # Unix-like systems (Mac, Linux)
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    else:
        # Windows
        ch = msvcrt.getch().decode('utf-8', errors='ignore')
        # Handle arrow keys in Windows
        if ch == '\xe0':  # Special key prefix
            ch = msvcrt.getch().decode('utf-8', errors='ignore')
            # Map Windows scan codes to our expected format
            ch = {
                'K': '\x1bD',  # Left arrow
                'M': '\x1bC',  # Right arrow
            }.get(ch, ch)
    return ch

def handle_keyboard_input():
    """Handle keyboard input for SSRC selection"""
    global current_ssrc_index, running
    while running:
        char = get_char()
        if char == '\x1b':  # Arrow key prefix on Unix
            if platform.system() != 'Windows':
                get_char()  # Skip the '['
                char = get_char()  # Get the actual arrow key
            else:
                char = char[1]  # On Windows, we already mapped to \x1bD or \x1bC
            if char == 'D':  # Left arrow
                if active_ssrcs:
                    current_ssrc_index = (current_ssrc_index - 1) % len(active_ssrcs)
                    print(f"\n\rSwitched to SSRC: {active_ssrcs[current_ssrc_index]}\n\r", end='')
            elif char == 'C':  # Right arrow
                if active_ssrcs:
                    current_ssrc_index = (current_ssrc_index + 1) % len(active_ssrcs)
                    print(f"\n\rSwitched to SSRC: {active_ssrcs[current_ssrc_index]}\n\r", end='')
        elif char.lower() == 'q':
            running = False
            print("\n\rExiting...\n\r", end='')
            break

def cleanup_inactive_ssrcs():
    """Remove SSRCs that haven't been active for INACTIVE_TIMEOUT seconds"""
    global current_ssrc_index
    current_time = time.time()
    inactive_ssrcs = []
    
    for ssrc in active_ssrcs:
        if current_time - ssrc_last_activity[ssrc] > INACTIVE_TIMEOUT:
            inactive_ssrcs.append(ssrc)
    
    for ssrc in inactive_ssrcs:
        idx = active_ssrcs.index(ssrc)
        active_ssrcs.remove(ssrc)
        del ssrc_last_activity[ssrc]
        print(f"\n\rSSRC {ssrc} removed due to inactivity\n\r", end='')
        
        # Adjust current_ssrc_index if necessary
        if active_ssrcs:
            current_ssrc_index = min(current_ssrc_index, len(active_ssrcs) - 1)
        else:
            current_ssrc_index = 0

def cleanup_timer():
    """Periodically check and remove inactive SSRCs"""
    while running:
        cleanup_inactive_ssrcs()
        time.sleep(1)  # Check every second

# Start both keyboard input and cleanup timer threads
keyboard_thread = threading.Thread(target=handle_keyboard_input, daemon=True)
cleanup_thread = threading.Thread(target=cleanup_timer, daemon=True)
keyboard_thread.start()
cleanup_thread.start()

try:
    while running:
        # Set a timeout on the socket to check running flag periodically
        sock.settimeout(0.5)
        try:
            # Receive RTP packet
            data, addr = sock.recvfrom(2048)
            
            # Extract and decode RTP header
            rtp_header = data[:12]
            version = (rtp_header[0] >> 6) & 0x03
            padding = (rtp_header[0] >> 5) & 0x01
            extension = (rtp_header[0] >> 4) & 0x01
            csrc_count = rtp_header[0] & 0x0F
            marker = (rtp_header[1] >> 7) & 0x01
            payload_type = rtp_header[1] & 0x7F
            sequence_number = (rtp_header[2] << 8) | rtp_header[3]
            timestamp = (rtp_header[4] << 24) | (rtp_header[5] << 16) | (rtp_header[6] << 8) | rtp_header[7]
            ssrc = (rtp_header[8] << 24) | (rtp_header[9] << 16) | (rtp_header[10] << 8) | rtp_header[11]
            
            # Update SSRC tracking
            if ssrc not in active_ssrcs:
                active_ssrcs.append(ssrc)
                print(f"\n\rNew SSRC detected: {ssrc}\n\r", end='')
                # If this is the only SSRC, automatically select it
                if len(active_ssrcs) == 1:
                    current_ssrc_index = 0
                    print(f"\n\rAutomatically switched to SSRC: {ssrc}\n\r", end='')
            ssrc_last_activity[ssrc] = time.time()
            
            print(f"\rRTP: PT={payload_type}, SEQ={sequence_number}, SSRC={ssrc} "
                  f"(Active SSRCs: {len(active_ssrcs)}, Current: {active_ssrcs[current_ssrc_index] if active_ssrcs else 'None'})",
                  end='', flush=True)
            
            # Only process audio for the currently selected SSRC
            if not active_ssrcs or ssrc != active_ssrcs[current_ssrc_index]:
                continue
            
            # Verify this is PCMU (payload type 0)
            if payload_type != 0:
                print(f"\n\rUnexpected payload type: {payload_type}\n\r", end='')
                continue
            
            # Extract and process PCMU payload
            pcmu_payload = data[12:]
            pcm_samples = [ULAW_TO_PCM_TABLE[byte] for byte in pcmu_payload]
            pcm_bytes = struct.pack(f"<{len(pcm_samples)}h", *pcm_samples)
            
            # Play the audio
            if pcm_bytes:
                try:
                    stream.write(pcm_bytes)
                except Exception as e:
                    print(f"\n\rError writing to audio stream: {e}\n\r", end='')

        except socket.timeout:
            continue
        except Exception as e:
            print(f"\n\rError receiving packet: {e}\n\r", end='')
            break

except KeyboardInterrupt:
    print("\n\rStopping...\n\r", end='')
finally:
    running = False
    stream.stop_stream()
    stream.close()
    audio.terminate()
    sock.close()
    print("\n\rExited.\n\r", end='')
