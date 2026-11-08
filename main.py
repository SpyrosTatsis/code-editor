import customtkinter as ctk
from tkinter import filedialog
import re
import keyword
import builtins

SYNTAX_COLORS = {
    "dark": {
        "keyword":  "#ff79c6",
        "builtin":  "#8be9fd",
        "function": "#50fa7b",
        "number":   "#bd93f9",
        "string":   "#f1fa8c",
        "comment":  "#6272a4",
    },
    "light": {
        "keyword":  "#d6007a",
        "builtin":  "#0077aa",
        "function": "#008a2e",
        "number":   "#6a3fc0",
        "string":   "#9a6700",
        "comment":  "#6a737d",
    },
}
PATTERNS = [
    ("keyword",  r"\b(?:" + "|".join(keyword.kwlist) + r")\b"),
    ("builtin",  r"\b(?:" + "|".join(n for n in dir(builtins) if not n.startswith("_")) + r")\b"),
    ("number",   r"\b\d+(?:\.\d+)?\b"),
    ("function", r"(?<=def )\w+|(?<=class )\w+"),
    ("string",   r"(?P<string>\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\"\n]*\"|'[^'\n]*')"
                 r"|(?P<comment>#[^\n]*)"),
]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")  


class Editor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("meow")
        self.geometry("900x600")
        self.path = None

        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(toolbar, text="Open", width=70, command=self.open_file).pack(side="left", padx=4)
        ctk.CTkButton(toolbar, text="Save", width=70, command=self.save_file).pack(side="left", padx=4)
        ctk.CTkOptionMenu(toolbar, values=["dark", "light"],
                  command=self.change_mode).pack(side="right", padx=4)

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

        self.highlight_job = None
        self.apply_syntax_colors("dark")
        self.text.bind("<KeyRelease>", self.schedule_highlight)

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

    def save_file(self):
        if not self.path:
            self.path = filedialog.asksaveasfilename(defaultextension=".txt")
        if self.path:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end-1c"))
            self.title(f"meow - {self.path}")
    def change_mode(self, choice):
        ctk.set_appearance_mode(choice)
        self.attributes("-alpha", 0.85 if choice == "light" else 1.0)

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

        for tag in SYNTAX_COLORS["dark"]:
            self.text.tag_remove(tag, "1.0", "end")

        for tag, pattern in PATTERNS:
            for m in re.finditer(pattern, content):
                name = m.lastgroup or tag      
                self.text.tag_add(name, f"1.0+{m.start()}c", f"1.0+{m.end()}c")


Editor().mainloop()