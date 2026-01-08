# SoundBridge

**Bridge the gap between your input and multiple outputs.**

**SoundBridge** is a modern, lightweight audio routing utility built with Python. It allows you to take a single audio input (like a microphone or a virtual cable) and broadcast it to multiple output devices simultaneously.

What sets SoundBridge apart is the ability to set **independent delay compensation** (millisecond precision) and volume levels for every speaker. This is perfect for multi-room setups, connecting Bluetooth and wired speakers simultaneously, or fixing sync issues in complex audio environments.

<img width="1062" height="740" alt="DemoScreenshot1" src="https://github.com/user-attachments/assets/2687b6af-b753-45ab-87b3-94889e6c68c9" />

## 🚀 Features

* **Multi-Output Routing:** Send one audio source to as many devices as your computer can handle.
* **Precision Sync:** Independent, real-time delay sliders (0-500ms) with fine-tune (+/- 1ms) buttons.
* **Modern UI:** Built with `CustomTkinter` for a sleek, dark-mode native look.
* **Volume Mixing:** Individual volume controls for every output device.
* **Smart Detection:** Automatically filters virtual drivers and prioritizes physical outputs.
* **Non-Blocking:** Multi-threaded audio engine ensures the UI never freezes, even when starting/stopping complex streams.

## 🛠️ Prerequisites

You need **Python 3.7+** installed on your system.

## 📦 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/soundbridge.git
cd soundbridge

```


2. **Install the dependencies:**
```bash
pip install customtkinter sounddevice numpy

```


*Note for Linux users: You may need to install PortAudio development headers (e.g., `sudo apt-get install libportaudio2`).*

## 🎛️ Usage

1. **Run the application:**
```bash
python main.py

```


2. **Select Input:**
* Choose your source from the "Input Source" dropdown (e.g., a microphone, or a virtual cable like BlackHole/VB-Cable to route system audio).


3. **Configure Outputs:**
* **Check** the boxes for the speakers you want to use.
* **Slide** the Volume to mix levels.
* **Adjust Delay** if one speaker is physically further away or has Bluetooth lag. Use the `+` / `-` buttons for perfect sync.


4. **Start Engine:**
* Click **START ENGINE** to begin routing.



## 💡 How it Works

SoundBridge uses a **Ring Buffer** architecture. It captures audio into a circular memory buffer and allows multiple "reader" pointers (the output devices) to read from that buffer at different offsets.

* **Zero Delay:** The reader is right behind the writer.
* **500ms Delay:** The reader waits until the writer has moved 500ms ahead in the buffer before reading.

This ensures all devices play the exact same sample data, just at different times, correcting for physical distance or hardware latency.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
