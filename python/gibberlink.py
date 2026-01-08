import ggwave
import pyaudio
import time
import sys
import numpy as np

# Configuration
PROTOCOL_ID = 0  # Audible Normal
PAYLOAD_LENGTH = -1 # Variable length
FRAMES_PER_BUFFER = 2048
SAMPLE_RATE = 48000
CHANNELS = 1
FORMAT = pyaudio.paFloat32

def listen_for_data():
    """
    Continuously listens to the microphone and decodes ggwave signals.
    """
    p = pyaudio.PyAudio()

    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=SAMPLE_RATE,
                        input=True,
                        frames_per_buffer=FRAMES_PER_BUFFER)
    except OSError as e:
        print(f"Error opening audio stream: {e}")
        print("Please ensure a microphone is connected and accessible.")
        return

    print("Listening for messages... (Press Ctrl+C to stop)")
    print(f"Protocol ID: {PROTOCOL_ID} (Audible Fast)")

    try:
        # Init specific for Int16 input if possible, but python binding usually takes default.
        # However, passing int16 bytes to default init (which expects f32) might be bad.
        # Let's try to convert to float manually OR assume binding handles it.
        # Actually, let's Stick to paFloat32 for now as it's the default expectation of ggwave python examples.
        # Reverting to Float32? No, let's keep Int16 and convert, or use Float32.
        # The user was using Float32 and it failed. 
        # Let's try Float32 again with volume check.
        
        instance = ggwave.init()
        
        # Ensure we are using the correct protocol on the receiving end if possible,
        # otherwise ggwave attempts to detect.
        # ggwave-python binding might not expose strict protocol setting for decoding easily 
        # without digging into C++ instance details, but default decode handles it.

        while True:
            data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
            # Convert raw bytes to numpy array of floats if using paFloat32, 
            # but ggwave.decode expects bytes or specific buffer format.
            # PyAudio read returns bytes. 
            
            # ggwave.decode() takes the audio buffer.
            # We need to pass the raw data.
            # VU Meter
            # Calculate volume
            data_np = np.frombuffer(data, dtype=np.float32) 
            volume_norm = np.linalg.norm(data_np)
            print("." if volume_norm < 1 else "#" if volume_norm < 10 else "!", end="", flush=True)

            res = ggwave.decode(instance, data)

            if res:
                try:
                    # data is received as bytes, try decoding to utf-8 string
                    text = res.decode('utf-8')
                    print(f"\n[RECEIVED]: {text}")
                except UnicodeDecodeError:
                    print(f"\n[RECEIVED - RAW]: {res}")

    except KeyboardInterrupt:
        print("\nStopping listener...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        ggwave.free(instance)

def send_data(text):
    """
    Encodes the text to a waveform and plays it via speakers.
    """
    print(f"Encoding message: '{text}'")
    
    # Encode text to waveform
    # ggwave.encode returns valid audio samples
    waveform = ggwave.encode(text, protocolId=PROTOCOL_ID, volume=50)
    
    if not waveform:
        print("Error: Failed to encode message.")
        return

    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(format=pyaudio.paFloat32, 
                        channels=CHANNELS,
                        rate=SAMPLE_RATE,
                        output=True)
        
        # Play the waveform
        stream.write(waveform)
        
        # Wait a bit to ensure playback finishes if needed, or just close
        time.sleep(0.5) 

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("Message sent.")

def main():
    while True:
        print("\n--- Gibberlink (Python) ---")
        print("1. Listen Description")
        print("2. Send Message")
        print("3. Exit")
        
        choice = input("Select mode (1/2/3): ").strip()

        if choice == '1':
            listen_for_data()
        elif choice == '2':
            text = input("Enter message: ")
            if text:
                send_data(text)
        elif choice == '3':
            print("Exiting.")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
