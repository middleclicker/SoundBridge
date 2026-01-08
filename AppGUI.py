import customtkinter as ctk
import sounddevice as sd
import numpy as np
import threading
import sys

# --- Configuration ---
BLOCKSIZE = 4096
BUFFER_TIME = 7 
THEME_COLOR = "dark-blue" 
MAX_DELAY_MS = 500 

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme(THEME_COLOR)

class AudioRouterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Audio Router & Delay Manager")
        self.geometry("950x600")
        
        # Handle the "X" button gracefully
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Audio State
        self.running = False
        self.streams = []
        self.sample_rate = 44100
        self.channels = 2
        self.ring_buffer = None
        self.write_ptr = 0
        self.buffer_sample_size = 0
        
        self.speakers_config = {} 

        self._init_ui()
        self._scan_devices()

    def _init_ui(self):
        # 1. Top Bar
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(fill="x", padx=20, pady=20)

        self.lbl_input = ctk.CTkLabel(self.top_frame, text="Input Source:", font=("Roboto", 14, "bold"))
        self.lbl_input.pack(side="left", padx=10)

        self.input_dropdown = ctk.CTkOptionMenu(self.top_frame, values=[], width=250)
        self.input_dropdown.pack(side="left", padx=10)

        self.btn_refresh = ctk.CTkButton(self.top_frame, text="↻ Refresh", width=100, command=self._scan_devices)
        self.btn_refresh.pack(side="left", padx=10)

        self.btn_start = ctk.CTkButton(self.top_frame, text="START ENGINE", fg_color="green", width=120, command=self.toggle_engine)
        self.btn_start.pack(side="right", padx=10)

        # 2. Main List Area
        self.lbl_outputs = ctk.CTkLabel(self, text="Output Targets", font=("Roboto", 16, "bold"))
        self.lbl_outputs.pack(pady=(10, 5), padx=20, anchor="w")

        # Header row
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=40)
        ctk.CTkLabel(header_frame, text="Device Name", width=200, anchor="w").pack(side="left")
        ctk.CTkLabel(header_frame, text="Volume", width=150).pack(side="left", padx=30)
        ctk.CTkLabel(header_frame, text=f"Delay (0-{MAX_DELAY_MS}ms)", width=250).pack(side="right", padx=60)

        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Detected Outputs")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 3. Footer
        self.status_bar = ctk.CTkLabel(self, text="Status: Ready", text_color="gray")
        self.status_bar.pack(side="bottom", pady=5)

    def _scan_devices(self):
        if self.running:
            self.stop_engine()

        self.speakers_config = {}
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        devices = sd.query_devices()
        input_options = []
        virtual_drivers = ['blackhole', 'soundflower', 'loopback', 'zoom', 'microsoft teams', 'vb-cable']
        default_input_selection = None

        for i, device in enumerate(devices):
            name = device['name']
            lower_name = name.lower()
            max_out = device['max_output_channels']
            max_in = device['max_input_channels']

            if max_in > 0:
                input_options.append(f"{i}: {name}")
                if not default_input_selection and any(v in lower_name for v in virtual_drivers):
                    default_input_selection = f"{i}: {name}"

            if max_out > 0:
                is_virtual = any(v in lower_name for v in virtual_drivers)
                if not is_virtual:
                    self._add_speaker_row(i, name)

        self.input_dropdown.configure(values=input_options)
        if default_input_selection:
            self.input_dropdown.set(default_input_selection)
        elif input_options:
            self.input_dropdown.set(input_options[0])

        self.status_bar.configure(text=f"Scan Complete. Found {len(self.speakers_config)} output targets.")

    def _add_speaker_row(self, device_id, name):
        row = ctk.CTkFrame(self.scroll_frame)
        row.pack(fill="x", pady=5, padx=5)

        is_enabled = ctk.BooleanVar(value=True) 
        chk = ctk.CTkCheckBox(row, text=name, variable=is_enabled, width=200)
        chk.pack(side="left", padx=10, pady=10)

        vol_frame = ctk.CTkFrame(row, fg_color="transparent")
        vol_frame.pack(side="left", fill="x", expand=True, padx=10)
        
        slider_vol = ctk.CTkSlider(vol_frame, from_=0, to=100, number_of_steps=100, width=120)
        slider_vol.set(100)
        slider_vol.pack(side="left")

        # Delay Controls
        delay_frame = ctk.CTkFrame(row, fg_color="transparent")
        delay_frame.pack(side="right", padx=10)

        lbl_delay_val = ctk.CTkLabel(delay_frame, text="100ms", width=50, font=("Monospace", 12))
        
        slider_delay = ctk.CTkSlider(
            delay_frame, 
            from_=0, 
            to=MAX_DELAY_MS, 
            number_of_steps=MAX_DELAY_MS, 
            width=200,
            command=lambda v: lbl_delay_val.configure(text=f"{int(v)}ms")
        )
        slider_delay.set(100)
        
        def nudge(amount):
            current = slider_delay.get()
            new_val = current + amount
            if 0 <= new_val <= MAX_DELAY_MS:
                slider_delay.set(new_val)
                lbl_delay_val.configure(text=f"{int(new_val)}ms")

        btn_minus = ctk.CTkButton(delay_frame, text="-", width=30, height=20, fg_color="gray", command=lambda: nudge(-1))
        btn_plus = ctk.CTkButton(delay_frame, text="+", width=30, height=20, fg_color="gray", command=lambda: nudge(1))

        btn_minus.pack(side="left", padx=2)
        slider_delay.pack(side="left", padx=5)
        btn_plus.pack(side="left", padx=2)
        lbl_delay_val.pack(side="left", padx=5)

        self.speakers_config[device_id] = {
            "enabled_var": is_enabled,
            "vol_slider": slider_vol,
            "delay_slider": slider_delay,
            "name": name
        }

    # --- Audio Engine ---

    def _get_input_device_id(self):
        val = self.input_dropdown.get()
        if not val: return None
        return int(val.split(":")[0])

    def input_callback(self, indata, frames, time_info, status):
        end_ptr = self.write_ptr + frames
        if end_ptr < self.buffer_sample_size:
            self.ring_buffer[self.write_ptr:end_ptr] = indata
        else:
            remaining = self.buffer_sample_size - self.write_ptr
            self.ring_buffer[self.write_ptr:] = indata[:remaining]
            self.ring_buffer[:frames - remaining] = indata[remaining:]
        self.write_ptr = (self.write_ptr + frames) % self.buffer_sample_size

    def output_callback(self, device_id, outdata, frames, time_info, status):
        conf = self.speakers_config[device_id]
        
        if not conf["enabled_var"].get():
            outdata.fill(0)
            return

        delay_ms = conf["delay_slider"].get()
        delay_samples = int((delay_ms / 1000.0) * self.sample_rate)
        volume = conf["vol_slider"].get() / 100.0

        read_ptr = (self.write_ptr - delay_samples - frames) % self.buffer_sample_size
        end_ptr = read_ptr + frames

        if end_ptr < self.buffer_sample_size:
            outdata[:] = self.ring_buffer[read_ptr:end_ptr]
        else:
            remaining = self.buffer_sample_size - read_ptr
            outdata[:remaining] = self.ring_buffer[read_ptr:]
            outdata[remaining:] = self.ring_buffer[:frames - remaining]
        
        outdata[:] = outdata * volume

    def toggle_engine(self):
        if self.running:
            self.stop_engine()
        else:
            self.start_engine()

    def start_engine(self):
        dev_id = self._get_input_device_id()
        if dev_id is None:
            self.status_bar.configure(text="Error: No Input Selected", text_color="red")
            return

        try:
            dev_info = sd.query_devices(dev_id, 'input')
            self.sample_rate = int(dev_info['default_samplerate'])
            self.buffer_sample_size = BUFFER_TIME * self.sample_rate
            self.ring_buffer = np.zeros((self.buffer_sample_size, self.channels))
            self.write_ptr = 0

            in_stream = sd.InputStream(
                device=dev_id, 
                channels=self.channels, 
                samplerate=self.sample_rate, 
                callback=self.input_callback, 
                blocksize=BLOCKSIZE
            )
            in_stream.start()
            self.streams.append(in_stream)

            count = 0
            for dev_id, conf in self.speakers_config.items():
                if conf["enabled_var"].get():
                    def callback_wrapper(outdata, frames, time, status, did=dev_id):
                        self.output_callback(did, outdata, frames, time, status)

                    out_stream = sd.OutputStream(
                        device=dev_id,
                        channels=self.channels,
                        samplerate=self.sample_rate,
                        callback=callback_wrapper,
                        blocksize=BLOCKSIZE
                    )
                    out_stream.start()
                    self.streams.append(out_stream)
                    count += 1

            self.running = True
            self.btn_start.configure(text="STOP ENGINE", fg_color="red")
            self.status_bar.configure(text=f"Running: {count} active outputs.", text_color="green")
            self.input_dropdown.configure(state="disabled")
            self.btn_refresh.configure(state="disabled")

        except Exception as e:
            self.stop_engine()
            self.status_bar.configure(text=f"Error: {str(e)}", text_color="red")
            print(e)

    # ---------------------------------------------------------
    # NON-BLOCKING STOP LOGIC
    # ---------------------------------------------------------
    def stop_engine(self):
        """Initiates the stop process in a separate thread to prevent UI freezing."""
        if not self.running:
            return

        # 1. Disable controls immediately so user sees reaction
        self.btn_start.configure(state="disabled", text="STOPPING...")
        self.status_bar.configure(text="Stopping streams... (this may take a moment)", text_color="orange")
        
        # 2. Start background thread
        threading.Thread(target=self._stop_engine_worker, daemon=True).start()

    def _stop_engine_worker(self):
        """Closes streams in the background."""
        for s in self.streams:
            try:
                s.stop()
                s.close()
            except Exception as e:
                print(f"Error closing stream: {e}")
        
        self.streams = []
        self.running = False
        
        # 3. Schedule UI update on main thread
        self.after(0, self._on_stop_complete)

    def _on_stop_complete(self):
        """Called back on the main thread when audio is fully closed."""
        self.btn_start.configure(state="normal", text="START ENGINE", fg_color="green")
        self.status_bar.configure(text="Stopped.", text_color="gray")
        self.input_dropdown.configure(state="normal")
        self.btn_refresh.configure(state="normal")

    def on_close(self):
        """Handle window close button."""
        if self.running:
            # If running, stop first (blocking is okay here as app is dying)
            self.status_bar.configure(text="Closing...", text_color="red")
            self.update_idletasks() # Force UI update
            for s in self.streams:
                s.stop()
                s.close()
        self.destroy()

if __name__ == "__main__":
    app = AudioRouterApp()
    app.mainloop()
