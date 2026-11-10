import re
import keyword
import builtins
import customtkinter as ctk
import pywinstyles
import os
import ctypes
from tkinter import filedialog
from bisect import bisect_right
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("meow.editor")
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")  
print(os.path.join(os.path.dirname(ctk.__file__), "assets", "themes"))

SYNTAX_COLORS = {
    "dark": {
        "call":      "#50fa7b",
        "defname":   "#50fa7b",
        "decorator": "#ffb86c",
        "selfcls":   "#ffb86c",
        "keyword":   "#ff79c6",
        "builtin":   "#8be9fd",
        "number":    "#bd93f9",
        "string":    "#f1fa8c",
        "comment":   "#6272a4",
    },
    "light": {
        "call":      "#3aab56",
        "defname":   "#50fa7b",
        "decorator": "#b07f4b",
        "selfcls":   "#cf9659",
        "keyword":   "#a55281",
        "builtin":   "#609eac",
        "number":    "#8467ad",
        "string":    "#b7bb84",
        "comment":   "#4f5c84"
    },
}

BUILTINS = [n for n in dir(builtins) if not n.startswith("_")]

PATTERNS = [
    ("call",      r"\b[A-Za-z_]\w*(?=\()"),
    ("defname",   r"(?<=def )\w+|(?<=class )\w+"),
    ("decorator", r"^[ \t]*@[\w.]+"),
    ("selfcls",   r"\b(?:self|cls)\b"),
    ("keyword",   r"\b(?:" + "|".join(keyword.kwlist) + r")\b"),
    ("builtin",   r"\b(?:" + "|".join(BUILTINS) + r")\b"),
    ("number",    r"\b(?:0[xX][0-9a-fA-F_]+|\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?)\b"),
    ("string",    r"(?P<string>[rRbBfFuU]{0,2}(?:\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\"\n]*\"|'[^'\n]*'))"
                  r"|(?P<comment>#[^\n]*)"),
]
COMPILED = [(tag, re.compile(p, re.MULTILINE)) for tag, p in PATTERNS]


class Editor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("meow")
        self.geometry("900x600")
        self.path = None
        self.mode = "dark"
        self.highlight_job = None
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(toolbar, text="Open", width=80, height= 35, command=self.open_file).pack(side="left", padx=4)
        ctk.CTkButton(toolbar, text="Save", width=80, height= 35, command=self.save_file).pack(side="left", padx=4)
        ctk.CTkOptionMenu(toolbar,width=70, height= 40, values=["dark", "light"],command=self.change_mode).pack(side="right", padx=4)
        self.editor_font = ctk.CTkFont(family="Cascadia Code SemiBold", size=16)
        self.text = ctk.CTkTextbox(self, font=self.editor_font, undo=True, wrap="none")
        self.text.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        tab_width = self.editor_font.measure(" " * 4)
        self.text.configure(tabs=(tab_width,))
        self.text.bind("<Tab>", self.insert_spaces)
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<Control-o>", lambda e: self.open_file())

        self.pairs = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
        for opener in self.pairs:
            self.text.bind(opener, self.auto_pair)
        for closer in (")", "]", "}"):
            self.text.bind(closer, self.skip_closer)
        self.text.bind("<BackSpace>", self.smart_backspace)
        self.apply_syntax_colors("dark")
        self.text.bind("<KeyRelease>", self.schedule_highlight)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "favicon (1).ico")
        self.after(250, lambda: self.iconbitmap(icon_path))
        
        
    def change_mode(self, choice):
        self.mode = choice
        ctk.set_appearance_mode(choice)
        self.apply_syntax_colors(choice)
        self.apply_window_style(choice)

    def apply_window_style(self, mode):
        try:
            if mode == "light":
                pywinstyles.apply_style(self, "acrylic")   
                self.attributes("-alpha", 0.9)
            else:
                pywinstyles.apply_style(self, "normal")
                self.attributes("-alpha", 1)
        except Exception as e:
            print("window style failed:", e)

    def apply_syntax_colors(self, mode):
        for tag, color in SYNTAX_COLORS[mode].items():
            self.text.tag_config(tag, foreground=color)
        self.highlight()

    def schedule_highlight(self, event=None):
        if self.highlight_job:
            self.after_cancel(self.highlight_job)
        self.highlight_job = self.after(150, self.highlight)

    def highlight(self):
        self.highlight_job = None
        content = self.text.get("1.0", "end-1c")
        line_starts = [0]
        for m in re.finditer(r"\n", content):
            line_starts.append(m.end())

        def to_index(offset):
            line = bisect_right(line_starts, offset) - 1
            return f"{line + 1}.{offset - line_starts[line]}"
        for tag in SYNTAX_COLORS["dark"]:
            self.text.tag_remove(tag, "1.0", "end")

        for tag, regex in COMPILED:
            for m in regex.finditer(content):
                name = m.lastgroup or tag
                self.text.tag_add(name, to_index(m.start()), to_index(m.end()))

    def insert_spaces(self, event):
        self.text.insert("insert", " " * 4)
        return "break"

    def auto_pair(self, event):
        char = event.char
        closer = self.pairs[char]
        if char in ("'", '"'):
            prev = self.text.get("insert-1c", "insert")
            if prev.isalnum() and self.text.get("insert") != char:
                return None

        if char == closer and self.text.get("insert") == closer:
            self.text.mark_set("insert", "insert+1c")
            return "break"

        if self.text.tag_ranges("sel"):
            selected = self.text.get("sel.first", "sel.last")
            self.text.delete("sel.first", "sel.last")
            self.text.insert("insert", char + selected + closer)
            return "break"
        self.text.insert("insert", char + closer)
        self.text.mark_set("insert", "insert-1c")
        return "break"

    def skip_closer(self, event):
        if self.text.get("insert") == event.char:
            self.text.mark_set("insert", "insert+1c")
            return "break"

    def smart_backspace(self, event):
        before = self.text.get("insert-1c", "insert")
        after = self.text.get("insert", "insert+1c")
        if before in self.pairs and self.pairs[before] == after:
            self.text.delete("insert-1c", "insert+1c")
            return "break"
        
    def open_file(self):
        path = filedialog.askopenfilename()
        if path:
            with open(path, encoding="utf-8") as f:
                self.text.delete("1.0", "end")
                self.text.insert("1.0", f.read())
            self.path = path
            self.title(f"meow - {path}")
            self.highlight()

    def save_file(self):
        if not self.path:
            self.path = filedialog.asksaveasfilename(defaultextension=".py")
        if self.path:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end-1c"))
            self.title(f"meow - {self.path}")
            self.highlight()


Editor().mainloop()
