import tkinter as tk
from tkinter import ttk, scrolledtext
import pyaudio
import ggwave
import numpy as np
import threading
import time
import sys

# Configuration
SAMPLE_RATE = 48000
CHANNELS = 1
FORMAT = pyaudio.paFloat32  # ggwave usually likes Float32
FRAMES_PER_BUFFER = 2048

# Protocols map
PROTOCOLS = {
    "Normal": 0,
    "Fast": 1,
    "Fastest": 2,
    "Ultra Fast": 3,
    "DT": 4,
    "MT": 5,
    "DT Fast": 6,
    "MT Fast": 7
}

class GibberlinkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GibberChat PC")
        self.root.geometry("400x600")
        
        # Audio State
        self.p = pyaudio.PyAudio()
        self.ggwave = ggwave.init()
        self.is_listening = True
        self.lock = threading.Lock()
        
        # UI Setup
        self.setup_ui()
        
        # Start Listener Thread
        self.listen_thread = threading.Thread(target=self.listener_loop, daemon=True)
        self.listen_thread.start()

    def setup_ui(self):
        # 1. Header Frame (Settings)
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)
        
        # Name Input
        ttk.Label(header_frame, text="Name:").pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value="PC User")
        self.entry_name = ttk.Entry(header_frame, textvariable=self.name_var, width=10)
        self.entry_name.pack(side=tk.LEFT, padx=5)
        
        # Protocol Selector
        ttk.Label(header_frame, text="Speed:").pack(side=tk.LEFT)
        self.protocol_var = tk.StringVar(value="Normal")
        self.combo_protocol = ttk.Combobox(header_frame, textvariable=self.protocol_var, values=list(PROTOCOLS.keys()), width=8, state="readonly")
        self.combo_protocol.pack(side=tk.LEFT, padx=5)
        
        # 2. Chat History (Scrollable)
        self.chat_display = scrolledtext.ScrolledText(self.root, state='disabled', wrap=tk.WORD, font=("Segoe UI", 10))
        self.chat_display.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
        
        # Configure tags for colors/alignment
        self.chat_display.tag_config("received", foreground="black", background="#F0F0F0", lmargin1=10, lmargin2=10, rmargin=50)
        self.chat_display.tag_config("sent", foreground="black", background="#DCF8C6", lmargin1=50, lmargin2=50, rmargin=10, justify='right')
        self.chat_display.tag_config("system", foreground="gray", justify='center', font=("Segoe UI", 8))
        self.chat_display.tag_config("sender_name", font=("Segoe UI", 8, "bold"), foreground="#555555")

        # 3. Input Area
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill=tk.X)
        
        self.msg_entry = ttk.Entry(input_frame)
        self.msg_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())
        
        self.btn_send = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.btn_send.pack(side=tk.LEFT)
        
        # Vu Meter Label (Simple text based)
        self.lbl_status = ttk.Label(self.root, text="Status: Ready", font=("Consolas", 8))
        self.lbl_status.pack(side=tk.BOTTOM, anchor=tk.W, padx=10, pady=2)

    def append_message(self, name, text, is_sent):
        self.chat_display.configure(state='normal')
        
        tag = "sent" if is_sent else "received"
        
        # Insert Name (Optional usually for chat, but good for group)
        # self.chat_display.insert(tk.END, f"{name}\n", (tag, "sender_name")) 
        
        # Create a "Bubble" effect with text
        display_text = f"{name}:\n{text}\n\n"
        self.chat_display.insert(tk.END, display_text, tag)
        
        self.chat_display.configure(state='disabled')
        self.chat_display.see(tk.END)

    def append_system(self, text):
        self.chat_display.configure(state='normal')
        self.chat_display.insert(tk.END, f"{text}\n", "system")
        self.chat_display.configure(state='disabled')
        self.chat_display.see(tk.END)

    def send_message(self):
        text = self.msg_entry.get().strip()
        if not text:
            return
        
        name = self.name_var.get().strip().replace("|", "") # sanitize
        full_payload = f"{name}|{text}"
        
        protocol_name = self.protocol_var.get()
        protocol_id = PROTOCOLS[protocol_name]
        
        # Encode
        threading.Thread(target=self._send_thread, args=(full_payload, text, protocol_id)).start()
        self.msg_entry.delete(0, tk.END)

    def _send_thread(self, payload, original_text, protocol_id):
        try:
            # Pause listening while sending to avoid self-hearing/echo (optional, but good)
            # self.is_listening = False 
            
            waveform = ggwave.encode(payload, protocolId=protocol_id, volume=50)
            if waveform:
                self.root.after(0, lambda: self.append_message("Me", original_text, True))
                
                # Play
                stream = self.p.open(format=pyaudio.paInt16, # Encode returns Int16 usually! Check gibberlink.py history.
                                   channels=CHANNELS,
                                   rate=SAMPLE_RATE,
                                   output=True)
                stream.write(waveform)
                stream.stop_stream()
                stream.close()
                self.root.after(0, lambda: self.lbl_status.configure(text="Status: Sent"))
            else:
                self.root.after(0, lambda: self.append_system("Error: Could not encode message"))
                
        except Exception as e:
             self.root.after(0, lambda: self.append_system(f"Error sending: {e}"))
        finally:
            # self.is_listening = True
            pass

    def listener_loop(self):
        try:
            stream = self.p.open(format=FORMAT,
                               channels=CHANNELS,
                               rate=SAMPLE_RATE,
                               input=True,
                               frames_per_buffer=FRAMES_PER_BUFFER) # Use 4096 if needed
        except Exception as e:
            self.root.after(0, lambda: self.append_system(f"Mic Error: {e}"))
            return

        print("Listener started...")
        
        while True:
            try:
                if not self.is_listening:
                    time.sleep(0.1)
                    continue
                
                data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                
                # Update VU Meter (every few frames to save UI calls)
                # data_np = np.frombuffer(data, dtype=np.float32)
                # vol = np.linalg.norm(data_np)
                # self.root.after(0, lambda v=vol: self.lbl_status.configure(text=f"Vol: {v:.2f}"))

                # Lock to prevent race conditions if needed, though ggwave object should be thread safe enough for one caller
                res = ggwave.decode(self.ggwave, data)
                
                if res and not self.ggwave.rxData is None:
                    # Message received!
                    try:
                        payload = res.decode("utf-8")
                        # Parse Name|Message
                        if "|" in payload:
                            parts = payload.split("|", 1)
                            name = parts[0]
                            msg = parts[1]
                        else:
                            name = "Unknown"
                            msg = payload
                        
                        # Avoid duplicates/echoes if needed (simple timestamp check?)
                        self.root.after(0, lambda n=name, m=msg: self.append_message(n, m, False))
                    except:
                        pass # Binary or invalid utf-8
                        
            except Exception as e:
                print(f"Listener error: {e}")
                time.sleep(1)

    def on_close(self):
        self.is_listening = False
        self.p.terminate()
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    root = tk.Tk()
    app = GibberlinkApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
