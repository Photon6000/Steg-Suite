import customtkinter as ctk
from tkinter import messagebox, simpledialog, filedialog
import subprocess
import os
import time
import shutil
import shlex
import threading
import platform
import mimetypes

# Try to import Drag and Drop library, fallback gracefully if missing
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
    class DnDWrapper(TkinterDnD.DnDWrapper): pass
except ImportError:
    HAS_DND = False
    class DnDWrapper(object): pass

# --- ToolTip Class ---
class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.waittime = 500
        self.wraplength = 180
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        self.tw = ctk.CTkToplevel(self.widget)
        self.tw.wm_overrideredirect(True) 
        self.tw.geometry("+%d+%d" % (x, y))
        
        label = ctk.CTkLabel(self.tw, text=self.text, justify='left',
                           fg_color="#333333", text_color="#ffffff",
                           corner_radius=6, width=200, wraplength=self.wraplength)
        label.pack(ipadx=5, ipady=5)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

# --- Main Application ---
BaseClass = ctk.CTk
if HAS_DND:
    class StegoBase(ctk.CTk, DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
    BaseClass = StegoBase

class StegoApp(BaseClass):
    def __init__(self):
        super().__init__()
        
        # 1. LOAD EXTERNAL CONFIGURATION
        self.app_config = self.load_config_from_file()
        self.tool_paths = self.load_tool_paths_from_file()
        self.tool_descriptions = self.load_tooltips_from_file()
        self.is_windows = platform.system() == "Windows"

        # Apply Configuration
        ctk.set_appearance_mode(self.app_config.get("theme", "dark"))
        ctk.set_default_color_theme(self.app_config.get("color_theme", "blue"))
        
        self.title("Steg-Suite Console")
        self.geometry("1100x850")

        # Data Structures
        self.tool_display_map = {
            "binwalk": "Binwalk", "zsteg": "Zsteg", "pngcheck": "Pngcheck",
            "steghide": "Steghide", "stegseek": "Stegseek", "jsteg": "Jsteg",
            "stegsnow": "Stegsnow", "hexdump": "Hexdump", "hashcat": "Hashcat"
        }

        self.tool_compatibility = {
            "png": ["binwalk", "zsteg", "pngcheck", "steghide", "stegseek", "hexdump", "exiftool"],
            "jpeg": ["binwalk", "steghide", "stegseek", "jsteg", "hexdump", "hashcat","exiftool"],
            "jpg": ["binwalk", "steghide", "stegseek", "jsteg", "hexdump", "hashcat","exiftool"],
            "txt": ["stegsnow", "hexdump", "hashcat","exiftool"],
            "zip": ["binwalk", "hexdump", "gunzip","exiftool"],
            "hash": ["hashcat", "hexdump","exiftool"]
        }

        self.selected_file = ""
        self.tool_widgets = {}
        self._last_resize_time = 0
        self.stop_flag = threading.Event() 

        # Resize Throttling Variables
        self._target_sidebar_width = 220
        self._resize_scheduled = False

        # Initialization
        self._setup_layout()
        self._setup_sidebar()
        self._setup_main_area()
        self._setup_keybindings()
        
        if HAS_DND:
            self._setup_drag_drop()
        
        # Run system check after UI loads
        self.after(500, self.check_system_dependencies)

    # --- Cross-Platform Helper ---
    def quote_path(self, path):
        """
        Windows requires double quotes for paths in cmd.
        Linux/Posix uses shlex.quote (usually single quotes).
        """
        if self.is_windows:
            return f'"{path}"'
        return shlex.quote(path)

    # --- Configuration Loaders ---
    def load_config_from_file(self):
        config = {
            "theme": "dark", 
            "color_theme": "blue",
            "default_dir": os.path.expanduser("~"),
            "font_size": "13"
        }
        try:
            if os.path.exists("config.txt"):
                with open("config.txt", "r") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            key, value = line.strip().split("=", 1)
                            config[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error loading config: {e}")
        return config

    def load_tool_paths_from_file(self):
        paths = {}
        try:
            if os.path.exists("config_application.txt"):
                with open("config_application.txt", "r") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            key, value = line.strip().split("=", 1)
                            paths[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error loading tool paths: {e}")
        return paths

    def get_tool_cmd(self, tool_name):
        return self.tool_paths.get(tool_name, tool_name)

    def load_tooltips_from_file(self):
        tooltips = {}
        try:
            if os.path.exists("tooltips.txt"):
                with open("tooltips.txt", "r") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            key, value = line.strip().split("=", 1)
                            tooltips[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error loading tooltips: {e}")
        return tooltips

    # --- UI Setup Helpers ---
    def _setup_layout(self):
        self.grid_columnconfigure(0, weight=1, minsize=200) 
        self.grid_columnconfigure(1, weight=0) 
        self.grid_columnconfigure(2, weight=4) 
        self.grid_rowconfigure(0, weight=1)

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, corner_radius=1, fg_color="#1a1a1a")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) 
        
        ctk.CTkLabel(self.sidebar, text="TOOLBOX", 
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)
        
        self.scrollable_tools = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scrollable_tools.pack(fill="both", expand=True, padx=5)

        for internal_name, display_name in self.tool_display_map.items():
            v = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(self.scrollable_tools, text=display_name, variable=v, font=("Consolas", 14))
            cb.pack(pady=8, padx=10, anchor="w")
            self.tool_widgets[internal_name] = {"var": v, "widget": cb}
            
            if internal_name in self.tool_descriptions:
                ToolTip(cb, self.tool_descriptions[internal_name])

        self.btn_select_all = ctk.CTkButton(
            self.sidebar, text="Select All", 
            command=lambda: self.toggle_all_tools(True),
            height=30, fg_color="#444444", hover_color="#555555"
        )
        self.btn_select_all.pack(pady=(10, 5), padx=25, fill="x")

        self.btn_deselect_all = ctk.CTkButton(
            self.sidebar, text="Deselect All",
            command=lambda: self.toggle_all_tools(False),
            height=30, fg_color="#444444", hover_color="#555555"
        )
        self.btn_deselect_all.pack(pady=(0, 20), padx=25, fill="x")

        self.drag_handle = ctk.CTkFrame(self, width=6, corner_radius=0, fg_color="#333333", cursor="sb_h_double_arrow")
        self.drag_handle.grid(row=0, column=1, sticky="ns")
        self.drag_handle.bind("<B1-Motion>", self.resize_sidebar)
        self.drag_handle.bind("<Enter>", lambda e: self.drag_handle.configure(fg_color="#555555"))
        self.drag_handle.bind("<Leave>", lambda e: self.drag_handle.configure(fg_color="#333333"))

    def _setup_main_area(self):
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=0, column=2, sticky="nsew", padx=20, pady=20)

        self.header = ctk.CTkFrame(self.main_panel, fg_color="#2b2b2b", height=100)
        self.header.pack(fill="x", pady=(0, 20))
        
        self.btn_browse = ctk.CTkButton(self.header, text="LOAD TARGET", font=("Arial", 14, "bold"), 
                                        command=self.browse_file_native)
        self.btn_browse.place(relx=0.05, rely=0.5, anchor="w")

        self.lbl_path = ctk.CTkLabel(self.header, text="No file loaded... (Drag & Drop available)", 
                                     font=("Consolas", 12), text_color="#aaaaaa")
        self.lbl_path.place(relx=0.25, rely=0.5, anchor="w")

        self.button_container = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.button_container.pack(fill="x", pady=5)

        self.btn_run = ctk.CTkButton(self.button_container, text="RUN TOOLS", height=45, 
                                     fg_color="#00c853", hover_color="#00e676", text_color="black",
                                     font=("Arial", 16, "bold"), command=self.start_processing_thread)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_stop = ctk.CTkButton(self.button_container, text="🛑 STOP", height=45, width=100,
                                      fg_color="#CC0000", hover_color="#990000", 
                                      text_color="white", font=("Arial", 16, "bold"),
                                      state="disabled", command=self.stop_execution)
        self.btn_stop.pack(side="left", padx=(0, 10))

        self.btn_export = ctk.CTkButton(self.button_container, text="💾 SAVE", height=45, width=100,
                                        fg_color="#2196F3", hover_color="#1976D2",
                                        command=self.export_output)
        self.btn_export.pack(side="left", padx=(0, 10))

        self.btn_clear = ctk.CTkButton(self.button_container, text="CLEAR", height=45, width=100,
                                       fg_color="#cf6679", hover_color="#b00020",
                                       command=self.clear_console)
        self.btn_clear.pack(side="right")

        font_size = int(self.app_config.get("font_size", 13))
        self.output_box = ctk.CTkTextbox(self.main_panel, font=("Consolas", font_size), 
                                         border_width=2, border_color="#333333")
        self.output_box.configure(state="disabled")
        self.output_box.pack(fill="both", expand=True, pady=10)

    def _setup_keybindings(self):
        self.bind("<Control-o>", lambda e: self.browse_file_native())
        self.bind("<Control-r>", lambda e: self.start_processing_thread())
        self.bind("<Control-l>", lambda e: self.clear_console())
        self.bind("<Control-s>", lambda e: self.export_output())
        self.bind("<Escape>", lambda e: self.stop_execution())
        self.after(1000, lambda: self.log("Shortcuts: Ctrl+O (Load) | Ctrl+R (Run) | Ctrl+S (Save) | ESC (Stop)\n"))

    def _setup_drag_drop(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        file_path = event.data.strip()
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        
        if os.path.isfile(file_path):
            self.selected_file = file_path
            self.lbl_path.configure(text=f"PATH: {os.path.basename(file_path)}", text_color="#00e676")
            self.pre_scan()
        else:
            self.log(f"[!] Invalid Drop: {file_path} is not a file.\n", "error")

    # --- Resize Logic ---
    def resize_sidebar(self, event):
        current_time = time.time()
        if current_time - self._last_resize_time < 0.01: return
        self._last_resize_time = current_time
        new_width = event.x_root - self.winfo_rootx()
        if new_width < 180: new_width = 180
        if new_width > 600: new_width = 600
        self._target_sidebar_width = new_width
        if not self._resize_scheduled:
            self._resize_scheduled = True
            self.after(10, self._apply_resize)

    def _apply_resize(self):
        new_width = self._target_sidebar_width
        current_width = self.sidebar.winfo_width()
        if abs(new_width - current_width) > 1:
            self.sidebar.configure(width=new_width)
        self._resize_scheduled = False

    # --- Console Helpers (Colored) ---
    def log(self, message, msg_type="normal"):
        colors = {
            "success": "#00ff00", "error": "#ff5555",
            "warning": "#ffaa00", "info": "#00aaff", "normal": "#ffffff"
        }
        if msg_type == "normal":
            if message.startswith("[+]"): msg_type = "success"
            elif message.startswith("[-]") or "Error" in message: msg_type = "error"
            elif message.startswith("[!]"): msg_type = "warning"
            elif message.startswith("[~]") or "Running" in message: msg_type = "info"

        def _write():
            self.output_box.configure(state="normal")
            start_pos = self.output_box.index("end-1c")
            self.output_box.insert("end", message)
            end_pos = self.output_box.index("end-1c")
            
            tag_name = f"color_{msg_type}"
            self.output_box.tag_add(tag_name, start_pos, end_pos)
            self.output_box.tag_config(tag_name, foreground=colors.get(msg_type, "#ffffff"))
            
            self.output_box.see("end")
            self.output_box.configure(state="disabled")
        self.after(0, _write)

    def clear_console(self):
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.configure(state="disabled")

    def export_output(self):
        content = self.output_box.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Export", "Log is empty!", parent=self)
            return
        
        path = filedialog.asksaveasfilename(
            initialdir=self.app_config.get("default_dir", os.path.expanduser("~")),
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            parent=self
        )
        if path:
            try:
                with open(path, "w") as f:
                    f.write(content)
                self.log(f"\n[+] Log saved to {path}\n", "success")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}", parent=self)

    def toggle_all_tools(self, select_state):
        for data in self.tool_widgets.values():
            if data["widget"].cget("state") != "disabled":
                data["var"].set(select_state)

    # --- Core Logic ---
    def check_system_dependencies(self):
        self.log(">>> [SYSTEM CHECK] Verifying tools...\n")
        for tool in self.tool_display_map.keys():
            cmd = self.get_tool_cmd(tool)
            # Cross-platform check
            if shutil.which(cmd) is not None or os.path.exists(cmd):
                self.log(f"[+] Found: {tool}\n", "success")
            else:
                self.tool_widgets[tool]["widget"].configure(text_color="#ff5555", state="disabled")
                self.log(f"[-] Missing: {tool} (Command: {cmd})\n", "error")
        self.log("-" * 40 + "\n")

    def browse_file_native(self):
        file_path = ""
        initial_dir = self.app_config.get("default_dir", os.path.expanduser("~"))
        
        # On Linux, try zenity. On Windows, skip straight to filedialog.
        if not self.is_windows:
            try:
                file_path = subprocess.check_output(
                    ["zenity", "--file-selection", "--title=Select Target File", f"--filename={initial_dir}/"],
                    stderr=subprocess.DEVNULL, timeout=60
                ).decode("utf-8").strip()
            except Exception:
                pass # Fall through to filedialog

        if not file_path:
            file_path = filedialog.askopenfilename(initialdir=initial_dir, parent=self)

        if file_path:
            if not os.path.exists(file_path):
                messagebox.showerror("Error", "File does not exist!", parent=self)
                return
            self.selected_file = file_path
            self.lbl_path.configure(text=f"PATH: {os.path.basename(file_path)}", text_color="#00e676")
            self.pre_scan()

    def pre_scan(self):
        self.log(f"\n[!] Identifying target file type...\n")
        
        # 1. Type Identification
        try:
            # Linux 'file' command is best, but not default on Windows
            if shutil.which("file"):
                res = subprocess.check_output(["file", self.selected_file], stderr=subprocess.STDOUT, timeout=10).decode()
                self.log(f"{res}\n")
            else:
                # Windows Fallback: Use standard python lib
                mime, _ = mimetypes.guess_type(self.selected_file)
                self.log(f"Detected (MIME): {mime or 'Unknown'}\n")
        except Exception as e:
            self.log(f"Type check error: {e}\n", "error")

        # 2. ExifTool (Cross-platform)
        try:
            exif_cmd = self.get_tool_cmd("exiftool")
            if shutil.which(exif_cmd) or os.path.exists(exif_cmd):
                self.log("-" * 15 + " EXIF METADATA " + "-" * 15 + "\n", "info")
                exif_out = subprocess.check_output(
                    [exif_cmd, self.selected_file], 
                    stderr=subprocess.STDOUT, 
                    timeout=15
                ).decode()
                self.log(exif_out + "\n")
            else:
                self.log("[*] ExifTool not installed. Skipping metadata.\n", "warning")
        except Exception as e:
            self.log(f"[!] ExifTool error: {e}\n", "error")

        self.log("-" * 50 + "\n")
        
        # 3. Highlight Tools
        for t_name in self.tool_display_map.keys():
            widget = self.tool_widgets[t_name]["widget"]
            if widget.cget("state") != "disabled":
                widget.configure(text_color="white")
                self.tool_widgets[t_name]["var"].set(False)
        
        ext = self.selected_file.split('.')[-1].lower()
        if ext in self.tool_compatibility:
            for suggested in self.tool_compatibility[ext]:
                if suggested in self.tool_widgets:
                    w = self.tool_widgets[suggested]["widget"]
                    if w.cget("state") != "disabled":
                        w.configure(text_color="#00c853")

    # --- Tool Specialized Handlers ---
    def get_tool_command(self, tool_name):
        handlers = {
            "binwalk": self._prompt_binwalk, "zsteg": self._prompt_zsteg,
            "pngcheck": self._prompt_pngcheck, "jsteg": self._prompt_jsteg,
            "stegseek": self._prompt_stegseek, "hashcat": self._prompt_hashcat,
            "stegsnow": self._prompt_stegsnow, "hexdump": self._prompt_hexdump,
            "steghide": lambda: [self.get_tool_cmd("steghide"), "info", self.selected_file]
        }
        return handlers[tool_name]() if tool_name in handlers else [self.get_tool_cmd(tool_name), self.selected_file]

    # --- PROMPTS ---
    def _prompt_binwalk(self):
        binwalk_cmd = self.get_tool_cmd("binwalk")
        mode = messagebox.askquestion("Binwalk", "Do you want to EXTRACT files? (No for Analyze)", type='yesnocancel', parent=self)
        if mode == 'yes':
            rec = messagebox.askyesno("Binwalk", "Use Matryoshka (Recursive) extraction?", parent=self)
            cmd = [binwalk_cmd, "-e", "-M"] if rec else [binwalk_cmd, "-e"]
            cmd.append(self.selected_file)
            return cmd
        return [binwalk_cmd, self.selected_file] if mode == 'no' else None

    def _prompt_zsteg(self):
        zsteg_cmd = self.get_tool_cmd("zsteg")
        mode = messagebox.askyesnocancel("Zsteg", 
                                       "Run 'All Methods' brute-force scan (-a)?\n\nYes = Brute-force (-a)\nNo = Specific Extraction or Standard Scan\nCancel = Abort", 
                                       parent=self)
        if mode is None: return None
        if mode: return [zsteg_cmd, "-a", self.selected_file]
        
        want_extract = messagebox.askyesno("Zsteg", "Do you want to EXTRACT a payload (-E)?", parent=self)
        if want_extract:
            payload = simpledialog.askstring("Zsteg Extract", "Enter payload config (e.g., '1b,rgb,lsb'):\nCheck previous scan results.", parent=self)
            if not payload: return None

            save_path = filedialog.asksaveasfilename(title="Save Extracted File", initialdir=self.app_config.get("default_dir", os.path.expanduser("~")), parent=self)
            if save_path:
                safe_payload = self.quote_path(payload)
                safe_input = self.quote_path(self.selected_file)
                safe_output = self.quote_path(save_path)
                return f"{zsteg_cmd} -E {safe_payload} {safe_input} > {safe_output}"
            return None

        no_limit = messagebox.askyesno("Zsteg Config", "Disable output limit? (--limit 0)", parent=self)
        cmd = [zsteg_cmd]
        if no_limit: cmd.extend(["--limit", "0"])
        cmd.append(self.selected_file)
        return cmd

    def _prompt_pngcheck(self):
        pngcheck_cmd = self.get_tool_cmd("pngcheck")
        v = messagebox.askyesno("Pngcheck", "Verbose mode? (-v)", parent=self)
        x = messagebox.askyesno("Pngcheck", "Extract embedded PNGs? (-x)", parent=self)
        cmd = [pngcheck_cmd]
        if v: cmd.append("-v")
        if x: cmd.append("-x")
        cmd.append(self.selected_file)
        return cmd

    def _prompt_jsteg(self):
        jsteg_cmd = self.get_tool_cmd("jsteg")
        mode = messagebox.askquestion("Jsteg", "REVEAL data? (No to HIDE)", type='yesnocancel', parent=self)
        if mode == 'yes': return [jsteg_cmd, "reveal", self.selected_file]
        elif mode == 'no':
            secret = filedialog.askopenfilename(title="Select data to hide", parent=self)
            output = filedialog.asksaveasfilename(title="Save output JPEG", defaultextension=".jpg", parent=self)
            if secret and output: return [jsteg_cmd, "hide", self.selected_file, secret, output]
        return None

    def _prompt_stegseek(self):
        stegseek_cmd = self.get_tool_cmd("stegseek")
        mode = messagebox.askquestion("StegSeek", "CRACK mode? (No for SEED)", type='yesnocancel', parent=self)
        if mode == 'yes':
            wl = filedialog.askopenfilename(title="Select Wordlist", parent=self)
            return [stegseek_cmd, self.selected_file, wl] if wl else None
        return [stegseek_cmd, "--seed", self.selected_file] if mode == 'no' else None

    def _prompt_hashcat(self):
        hashcat_cmd = self.get_tool_cmd("hashcat")
        act = messagebox.askquestion("Hashcat", "IDENTIFY hash? (No to CRACK)", type='yesnocancel', parent=self)
        if act == 'yes': return [hashcat_cmd, self.selected_file]
        elif act == 'no':
            mt = simpledialog.askinteger("Hashcat", "Hash-type Num:", initialvalue=0, parent=self)
            wl = filedialog.askopenfilename(title="Select Wordlist", parent=self)
            if mt is not None and wl: 
                return [hashcat_cmd, "-a", "0", "-m", str(mt), self.selected_file, wl, "--show"]
        return None

    def _prompt_stegsnow(self):
        stegsnow_cmd = self.get_tool_cmd("stegsnow")
        mode = messagebox.askquestion("Stegsnow", "Reveal hidden data? (No to HIDE)", type='yesnocancel', parent=self)
        if mode == 'yes':
            pwd = simpledialog.askstring("Passphrase", "Enter password:", show='*', parent=self)
            cmd = [stegsnow_cmd, "-C"]
            if pwd: cmd.extend(["-p", pwd])
            cmd.append(self.selected_file)
            return cmd
        elif mode == 'no':
            msg = simpledialog.askstring("Message", "Enter message to hide:", parent=self)
            path = filedialog.asksaveasfilename(title="Save as", defaultextension=".txt", parent=self)
            if msg and path: return [stegsnow_cmd, "-C", "-m", msg, self.selected_file, path]
        return None

    def _prompt_hexdump(self):
        # On Windows, system 'hexdump' likely doesn't exist.
        # We rely on internal Python fallback unless it's External Mode.
        mode = messagebox.askquestion("Hexdump", "Use 'less' mode (External Window)?", type='yesnocancel', parent=self)
        
        if mode == 'yes':
            # External Window: requires system commands
            safe_file = self.quote_path(self.selected_file)
            if self.is_windows:
                # Windows external window
                cmd = f'start cmd /k "hexdump -C {safe_file} | more"'
                subprocess.Popen(cmd, shell=True)
                return "EXTERNAL"
            else:
                # Linux external window
                cmd = f"x-terminal-emulator -e \"sh -c 'hexdump -C {safe_file} | less'\""
                subprocess.Popen(cmd, shell=True)
                return "EXTERNAL"

        elif mode == 'no':
            # INTERNAL MODE: We return a special dictionary to handle logic in Python
            # This makes it 100% cross-platform without needing grep/head installed.
            pat = simpledialog.askstring("Hexdump", "Enter pattern to grep (Cancel/Empty for head):", parent=self)
            lines = 100
            if not pat:
                lines = simpledialog.askinteger("Hexdump", "How many lines to see?", parent=self, minvalue=1, initialvalue=100) or 100
                
            return {"type": "INTERNAL_HEXDUMP", "pattern": pat, "lines": lines}

        return None

    # --- Pure Python Hexdump Implementation ---
    def do_internal_hexdump(self, filepath, pattern=None, max_lines=100):
        """Cross-platform hexdump generator"""
        try:
            output_lines = []
            with open(filepath, 'rb') as f:
                offset = 0
                count = 0
                while True:
                    if self.stop_flag.is_set(): break
                    chunk = f.read(16)
                    if not chunk: break

                    # Format: 00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
                    hex_str = ' '.join(f'{b:02x}' for b in chunk)
                    # Add extra space after 8 bytes
                    if len(chunk) > 8:
                        hex_str = hex_str[:23] + " " + hex_str[23:]
                    
                    # Pad hex string if chunk is short
                    hex_str = hex_str.ljust(48)
                    
                    ascii_str = ''.join((chr(b) if 32 <= b < 127 else '.') for b in chunk)
                    line = f"{offset:08x}  {hex_str}  |{ascii_str}|"
                    
                    # Filter logic
                    if pattern:
                        if pattern.lower() in line.lower():
                            output_lines.append(line)
                            count += 1
                    else:
                        output_lines.append(line)
                        count += 1
                        if count >= max_lines: break
                    
                    offset += 16
            
            return "\n".join(output_lines) + "\n"
        except Exception as e:
            return f"Error reading file: {e}"

    # --- Execution Logic ---
    def stop_execution(self):
        self.stop_flag.set()
        self.log("\n[!] STOP REQUESTED... Terminating processes.\n", "error")
        self.btn_stop.configure(state="disabled")

    def start_processing_thread(self):
        if not self.selected_file:
            messagebox.showwarning("File Error", "Please load a target file first!", parent=self)
            return
        
        selected_tools = [t for t, data in self.tool_widgets.items() if data["var"].get() is True]
        commands_to_run = []
        
        for tool in selected_tools:
            try:
                cmd = self.get_tool_command(tool)
                if cmd:
                    commands_to_run.append((tool, cmd))
            except Exception as e:
                self.log(f"[!] Error preparing {tool}: {e}\n", "error")

        if not commands_to_run:
            self.log("[!] No actions selected or cancelled by user.\n", "warning")
            return

        self.stop_flag.clear()
        self.btn_run.configure(state="disabled", text="RUNNING...")
        self.btn_stop.configure(state="normal")
        threading.Thread(target=self.run_logic_worker, args=(commands_to_run,), daemon=True).start()

    def run_logic_worker(self, commands_to_run):
        for idx, (tool_name, cmd) in enumerate(commands_to_run, 1):
            if self.stop_flag.is_set(): break
            if cmd == "EXTERNAL": continue
            
            self.log(f"\n[~] Running: {self.tool_display_map[tool_name]}...\n", "info")
            
            # Special handling for internal Python Hexdump
            if isinstance(cmd, dict) and cmd.get("type") == "INTERNAL_HEXDUMP":
                result = self.do_internal_hexdump(self.selected_file, cmd["pattern"], cmd["lines"])
                self.log(result)
                self.log("-" * 40 + "\n")
                continue

            # Regular Process execution
            try:
                # Windows needs shell=True for complex commands (redirection >)
                # Linux needs shell=True for pipes or >
                use_shell = isinstance(cmd, str)
                
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=use_shell
                )
                
                stdout = ""
                stderr = ""

                while True:
                    try:
                        stdout, stderr = process.communicate(timeout=0.1)
                        break 
                    except subprocess.TimeoutExpired:
                        if self.stop_flag.is_set():
                            process.terminate()
                            self.log("[!] Process killed by user.\n", "error")
                            return 

                if process.returncode == 0:
                    output = stdout if stdout else "[+] Done (No Output).\n"
                    
                    if tool_name == "zsteg":
                        lines = output.splitlines()
                        filtered_lines = [line for line in lines if not line.strip().endswith("..")]
                        if filtered_lines:
                            output = "\n".join(filtered_lines) + "\n"
                        else:
                            output = "[*] Zsteg completed. No hidden data detected.\n"

                    self.log(output)
                else:
                    self.log(f"[-] Error Code {process.returncode}:\n", "error")
                    self.log(stderr, "error")
                    if tool_name == "hashcat": self.log(stdout)
                    self.log("[!] CHAIN STOPPED DUE TO ERROR.\n", "error")
                    break 
                    
            except Exception as e:
                self.log(f"[!] Execution Error: {e}\n", "error")
                break
            
            self.log("-" * 40 + "\n")

        self.after(0, lambda: self.btn_run.configure(state="normal", text="RUN TOOLS"))
        self.after(0, lambda: self.btn_stop.configure(state="disabled"))

if __name__ == "__main__":
    app = StegoApp()
    app.mainloop()

