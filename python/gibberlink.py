import tkinter as tk
from tkinter import ttk, scrolledtext, colorchooser
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

# Theme (black interface)
BG_MAIN = "#000000"      # window background
BG_PANEL = "#0D0D0D"     # header / input bars
BG_CHAT = "#000000"      # chat area
BG_FIELD = "#1A1A1A"     # text fields
BG_RECEIVED = "#1F1F1F"  # received bubble
BG_SENT = "#333333"      # sent bubble
FG_MUTED = "#8A8A8A"     # secondary text
ACCENT = "#2A2A2A"       # buttons
ACCENT_HOVER = "#444444"

# Selectable text colors
TEXT_COLORS = {
    "White": "#FFFFFF",
    "Green": "#39FF14",
    "Cyan": "#00E5FF",
    "Yellow": "#FFEB3B",
    "Orange": "#FF9800",
    "Pink": "#FF69B4",
    "Red": "#FF5252",
    "Blue": "#4FC3F7",
    "Purple": "#CE93D8",
}
CUSTOM_LABEL = "Custom..."

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
        self.root.geometry("400x620")
        self.root.configure(bg=BG_MAIN)

        # Audio State
        self.p = pyaudio.PyAudio()
        self.ggwave = ggwave.init()
        self.is_listening = True
        self.lock = threading.Lock()

        # Text color state
        self.text_color = TEXT_COLORS["White"]

        # UI Setup
        self.setup_style()
        self.setup_ui()
        self.apply_text_color(self.text_color)

        # Start Listener Thread
        self.listen_thread = threading.Thread(target=self.listener_loop, daemon=True)
        self.listen_thread.start()

    def setup_style(self):
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")  # clam respects custom colors

        self.style.configure("TFrame", background=BG_PANEL)
        self.style.configure("TLabel", background=BG_PANEL)
        self.style.configure("Status.TLabel", background=BG_MAIN, foreground=FG_MUTED)
        self.style.configure("TEntry", fieldbackground=BG_FIELD, bordercolor=BG_FIELD)
        self.style.configure("TCombobox", fieldbackground=BG_FIELD, background=ACCENT,
                             bordercolor=BG_FIELD)
        self.style.configure("TButton", background=ACCENT, bordercolor=ACCENT,
                             focuscolor=ACCENT, padding=4)
        self.style.map("TButton", background=[("active", ACCENT_HOVER)])

        # Dropdown list colors for the combobox
        self.root.option_add("*TCombobox*Listbox.background", BG_FIELD)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_HOVER)

    def setup_ui(self):
        # 1. Header Frame (Settings)
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)

        row1 = ttk.Frame(header_frame)
        row1.pack(fill=tk.X)

        # Name Input
        ttk.Label(row1, text="Name:").pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value="PC User")
        self.entry_name = ttk.Entry(row1, textvariable=self.name_var, width=10)
        self.entry_name.pack(side=tk.LEFT, padx=5)

        # Protocol Selector
        ttk.Label(row1, text="Speed:").pack(side=tk.LEFT)
        self.protocol_var = tk.StringVar(value="Normal")
        self.combo_protocol = ttk.Combobox(row1, textvariable=self.protocol_var, values=list(PROTOCOLS.keys()), width=8, state="readonly")
        self.combo_protocol.pack(side=tk.LEFT, padx=5)

        row2 = ttk.Frame(header_frame)
        row2.pack(fill=tk.X, pady=(8, 0))

        # Text Color Selector
        ttk.Label(row2, text="Text color:").pack(side=tk.LEFT)
        self.color_var = tk.StringVar(value="White")
        self.combo_color = ttk.Combobox(row2, textvariable=self.color_var,
                                        values=list(TEXT_COLORS.keys()) + [CUSTOM_LABEL],
                                        width=10, state="readonly")
        self.combo_color.pack(side=tk.LEFT, padx=5)
        self.combo_color.bind("<<ComboboxSelected>>", self.on_color_selected)

        # Small swatch showing the current color
        self.swatch = tk.Label(row2, width=3, bg=self.text_color, relief=tk.FLAT)
        self.swatch.pack(side=tk.LEFT, padx=5)

        # 2. Chat History (Scrollable)
        self.chat_display = scrolledtext.ScrolledText(
            self.root, state='disabled', wrap=tk.WORD, font=("Segoe UI", 10),
            bg=BG_CHAT, insertbackground="#FFFFFF",
            relief=tk.FLAT, borderwidth=0, highlightthickness=0
        )
        self.chat_display.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        # Configure tags for colors/alignment (foreground is set in apply_text_color)
        self.chat_display.tag_config("received", background=BG_RECEIVED, lmargin1=10, lmargin2=10, rmargin=50)
        self.chat_display.tag_config("sent", background=BG_SENT, lmargin1=50, lmargin2=50, rmargin=10, justify='right')
        self.chat_display.tag_config("system", foreground=FG_MUTED, justify='center', font=("Segoe UI", 8))
        self.chat_display.tag_config("sender_name", font=("Segoe UI", 8, "bold"), foreground=FG_MUTED)

        # 3. Input Area
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill=tk.X)

        self.msg_entry = ttk.Entry(input_frame)
        self.msg_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        self.btn_send = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.btn_send.pack(side=tk.LEFT)

        # Vu Meter Label (Simple text based)
        self.lbl_status = ttk.Label(self.root, text="Status: Ready", font=("Consolas", 8), style="Status.TLabel")
        self.lbl_status.pack(side=tk.BOTTOM, anchor=tk.W, padx=10, pady=2)

    # ---- Text color handling ----
    def on_color_selected(self, event=None):
        choice = self.color_var.get()
        if choice == CUSTOM_LABEL:
            picked = colorchooser.askcolor(color=self.text_color, title="Choose text color")[1]
            if picked:
                self.apply_text_color(picked)
            else:
                # Cancelled: revert the dropdown to the current named color, if any
                current = next((n for n, c in TEXT_COLORS.items() if c.lower() == self.text_color.lower()), CUSTOM_LABEL)
                self.color_var.set(current)
        else:
            self.apply_text_color(TEXT_COLORS[choice])

    def apply_text_color(self, color):
        self.text_color = color

        # ttk widgets
        self.style.configure("TLabel", foreground=color)
        self.style.configure("TEntry", foreground=color, insertcolor=color)
        self.style.configure("TCombobox", foreground=color, arrowcolor=color)
        self.style.map("TCombobox",
                       fieldbackground=[("readonly", BG_FIELD)],
                       foreground=[("readonly", color)],
                       selectbackground=[("readonly", BG_FIELD)],
                       selectforeground=[("readonly", color)])
        self.style.configure("TButton", foreground=color)
        self.style.map("TButton", foreground=[("active", color)])
        self.root.option_add("*TCombobox*Listbox.foreground", color)
        self.root.option_add("*TCombobox*Listbox.selectForeground", color)

        # Chat area (existing and future messages)
        self.chat_display.configure(fg=color)
        self.chat_display.tag_config("received", foreground=color)
        self.chat_display.tag_config("sent", foreground=color)

        # Swatch
        self.swatch.configure(bg=color)

    def append_message(self, name, text, is_sent):
        self.chat_display.configure(state='normal')

        tag = "sent" if is_sent else "received"

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
