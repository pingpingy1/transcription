import tkinter as tk
from tkinter import filedialog as fd
from tkinter import messagebox as mb
from tkinter import ttk
from audio_ctrl import AudioController


# --------------
# Macro Manager
# --------------
class MacroManager:
    def __init__(self, root, text_widget):
        self.root = root
        self.text = text_widget
        self.macros = {
            chr(c): ""
            for c in range(ord("A"), ord("Z") + 1)
        }

        for key in self.macros:
            self.root.bind_all(
                f"<Alt-{key.lower()}>",
                lambda e, k=key: self.insert_macro(k),
            )

    def insert_macro(self, key):
        content = self.macros.get(key, "")
        if content:
            self.text.insert("insert", content)

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Macro Settings")

        entries = {}

        for i, key in enumerate(self.macros):
            tk.Label(win, text=f"Alt+{key}").grid(row=i, column=0, sticky="e")
            e = tk.Entry(win, width=40)
            e.insert(0, self.macros[key])
            e.grid(row=i, column=1, padx=5, pady=2)
            entries[key] = e

        def save():
            for k, e in entries.items():
                self.macros[k] = e.get()
            win.destroy()

        tk.Button(win, text="Save", command=save).grid(
            row=len(self.macros), column=0, columnspan=2, pady=10
        )


# ------------------
# Speed Controller
# ------------------
class SpeedControl(ttk.Frame):
    def __init__(self, master, on_change):
        super().__init__(master)
        self.on_change = on_change
        self.var = tk.IntVar(value=0)

        self.label = ttk.Label(self, text="Speed: 0% (1.00x)")
        self.label.pack()
        self.scale = ttk.Scale(
            self,
            from_=-99,
            to=100,
            orient="horizontal",
            command=self._changed,
            length=400,
        )
        self.scale.set(0)
        self.scale.pack(fill="x", padx=10)

        self.scale.bind("<Button-1>", self.jump_on_click)
        self.scale.bind("<Double-Button-1>", self.reset)

    def _changed(self, value):
        percent = int(float(value))
        speed = 1.0 + percent / 100.0
        self.label.config(
            text=f"Speed: {percent}% ({speed:.2f}x)",
        )
        self.on_change(speed)

    def reset(self, event=None):
        self.scale.set(0)
        self._changed(0)

    def jump_on_click(self, e):
        element = self.scale.identify(e.x, e.y)
        if element not in ("trough", "track"):
            return

        minv = float(self.scale.cget("from"))
        maxv = float(self.scale.cget("to"))

        trough_start, _ = self.scale.coords(minv)
        trough_end, _ = self.scale.coords(maxv)
        ratio = (e.x - trough_start) / (trough_end - trough_start)

        self.scale.set(minv + ratio * (maxv - minv))
        return "break"


# ---------
# Main App
# ---------
class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transcription practice")
        self.geometry("900x600")

        self.audio = AudioController()

        self.rewind_short = 1.0
        self.rewind_long = 3.0

        self.create_menu()
        self.create_toolbar()
        self.create_widgets()
        self.bind_keys()

    # ----- UI -----
    def create_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Open", accelerator="Ctrl+O", command=self.open_file,
        )
        file_menu.add_command(
            label="Save", accelerator="Ctrl+Shift+M", command=self.save_text,
        )
        menubar.add_cascade(label="File", menu=file_menu)

        macro_menu = tk.Menu(menubar, tearoff=0)
        macro_menu.add_command(
            label="Config macros", command=self.open_macro_settings,
        )
        macro_menu.add_command(
            label="Preferences", command=self.open_seek_settings,
        )
        menubar.add_cascade(label="Macro", menu=macro_menu)

        self.config(menu=menubar)

    def create_toolbar(self):
        bar = tk.Frame(self)
        bar.pack(side="top", fill="x")

        tk.Button(
            bar, text="📂", command=self.open_file
        ).pack(side="left")
        tk.Button(
            bar, text="▶️/⏸", command=self.audio.play_pause
        ).pack(side="left")
        tk.Button(
            bar, text="⚙️ Macro", command=self.open_macro_settings
        ).pack(side="left")

    def create_widgets(self):
        self.text = tk.Text(self, wrap="word")
        self.text.pack(fill="both", expand=True)

        self.macro_manager = MacroManager(self, self.text)

        self.wave_canvas = tk.Canvas(self, height=120, bg="#f0f0f0")
        self.wave_canvas.pack(fill="x")
        self.draw_dummy_wave()

        slider = ttk.Frame(self)
        slider.pack(side="top", fill="x")
        self.speed_control = SpeedControl(
            slider,
            on_change=self.audio.set_speed,
        )
        self.speed_control.pack(side="right", fill="x", padx=10)

    # ----- Actions -----
    def open_file(self):
        path = fd.askopenfilename(
            filetypes=[("Audio files", "*.wav *.mp3"), ("All files", "*.*")]
        )
        if path:
            self.audio.load(path)
            self.draw_dummy_wave()
            self.text.focus_set()

    def save_text(self):
        path = fd.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end-1c"))

    def open_seek_settings(self):
        win = tk.Toplevel(self)
        win.title("Preferences")
        
        fields = [
            ("Short time skip", "rewind_short"),
            ("Long time skip", "rewind_long"),
        ]
        entries = {}
        for i, (label, attr) in enumerate(fields):
            tk.Label(win, text=label).grid(
                row=i, column=0, sticky="e", padx=5, pady=4,
            )
            e = tk.Entry(win, width=10)
            e.insert(0, str(getattr(self, attr)))
            e.grid(row=i, column=1, padx=5)
            tk.Label(win, text="secs").grid(row=i, column=2, sticky="w")
            entries[attr] = e

        def save():
            try:
                for attr, e in entries.items():
                    setattr(self, attr, float(e.get()))
                win.destroy()
            except ValueError:
                mb.showerror("Error", "Please enter a number.")

        tk.Button(win, text="Save", command=save).grid(
            row=len(fields), column=0, columnspan=3, pady=10,
        )

    def open_macro_settings(self):
        self.macro_manager.open_settings()

    # ----- Waveform (dummy) -----
    def draw_dummy_wave(self):
        self.wave_canvas.delete("all")
        w = self.wave_canvas.winfo_width() or 800
        h = self.wave_canvas.winfo_height()
        for x in range(0, w, 4):
            y = h // 2
            self.wave_canvas.create_line(x, y - 20, x, y + 20, fill="#999")

    # ----- Key Bindings -----
    def bind_keys(self):
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-Shift-M>", lambda e: self.save_text())

        # Maintain cursor position upon playing/pausing
        def play_pause_restore_cursor(e):
            index = self.text.index(tk.INSERT)
            self.audio.play_pause()
            self.text.mark_set(tk.INSERT, index)
            return "break"
        self.text.bind("<Control-p>", play_pause_restore_cursor)

        # Bind <Ctrl-a> to select all text
        def select_all_text(e):
            self.text.tag_add(tk.SEL, "1.0", "end-1c")
            self.text.mark_set(tk.INSERT, "1.0")
            self.text.see("insert")
            return "break"
        self.text.bind("<Control-a>", select_all_text)

        self.bind("<F8>", lambda e: self.audio.seek(-self.rewind_long))
        self.bind("<F9>", lambda e: self.audio.seek(-self.rewind_long))
        self.bind("<F11>", lambda e: self.audio.seek(self.rewind_short))
        self.bind("<F12>", lambda e: self.audio.seek(self.rewind_long))

        # Override default F10 behavior
        def on_f10(e):
            self.audio.seek(-self.rewind_short)
            return "break"
        self.bind_all("<F10>", on_f10)

        # Bind <Ctrl-0> to reset playback speed
        def reset_speed(e):
            self.speed_control.reset()
            return "break"
        self.bind("<Control-0>", reset_speed)


if __name__ == "__main__":
    MainApp().mainloop()

