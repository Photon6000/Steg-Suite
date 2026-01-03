# Steg-Suite Console 🕵️‍♂️🔓

**Steg-Suite Console** is a unified, cross-platform GUI designed to make complex command-line steganography tools accessible and easy to chain together.

Instead of memorizing dozens of flags for `zsteg`, `binwalk`, or `steghide`, this tool lets you fast through your CTF challenges. Drag, drop, check the boxes, and let the suite handle the syntax.

![Steg-Suite Screenshot](assets/screenshot.png)

---

## 🤖 About "Vibe Coding"
This project was **"Vibe Coded"** with the assistance of AI (Gemini). The goal was to take powerful but fragmented CLI tools and wrap them in a simplified, modern interface without over-engineering the solution. It focuses on flow, speed, and utility.

---

## ✨ Key Features

* **🛠️ All-in-One Toolbox:** Wraps `Binwalk`, `Zsteg`, `Steghide`, `Stegseek`, `ExifTool`, `Pngcheck`, `Jsteg`, `Stegsnow`, `Hashcat`, and `Hexdump`.
* **⛓️ Chain Attacks:** Select multiple tools and run them sequentially.
* **🖱️ Drag & Drop:** Load files instantly without typing paths.
* **🖥️ Cross-Platform:**
    * **Linux:** Full support.
    * **Windows:** (Experimental) Includes path configuration for `.exe` tools and a pure-Python fallback for `hexdump`.
* **⚙️ Smart Configuration:** Define custom paths for your tools via `config_application.txt`.
* **🧠 Intelligent Output:** Filters noise (like empty Zsteg lines) so you only see the flag/data.
* **🛑 Control:** Stop hanging processes instantly and save your logs.

---

## ⚠️ Disclaimer: Windows Support
Support for **Windows is currently experimental**. While the code handles `.exe` paths and platform-specific commands, steganography tools are natively designed for Linux. You may encounter bugs or setup hurdles on Windows.

---

## 🚀 Getting Started

### 1. Prerequisites
You need **Python 3.8+**.
Crucially, this app is a **GUI Wrapper**—it runs tools already installed on your system. You must install the underlying tools:

* **Linux (Kali/Debian):**
    ```bash
    sudo apt install binwalk zsteg steghide stegseek exiftool pngcheck jsteg stegsnow hashcat
    ```
* **Windows:**
    Download the executables for the tools you need (e.g., ExifTool, Steghide) and note their install paths.

### 2. Installation
```bash
# Clone the repo
git clone [https://github.com/YOUR_USERNAME/Steg-Suite-Console.git](https://github.com/Photon6000/Steg-Suite-Console.git)
cd Steg-Suite-Console

# Install Python GUI libraries
pip install customtkinter tkinterdnd2
