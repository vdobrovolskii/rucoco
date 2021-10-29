import platform
import tkinter as tk
from tkinter import ttk
from typing import *

from coref_markup.application import Application


if __name__ == "__main__":
    root = tk.Tk()
    root.iconphoto(False, tk.PhotoImage(file='icon.png'))
    root.title("Coref Markup")
    app = Application(root)
    ttk.Style().theme_use({"Windows": "winnative", "Darwin": "aqua"}.get(platform.system(), "default"))
    app.mainloop()
