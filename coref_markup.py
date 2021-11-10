import argparse
import platform
import tkinter as tk
from tkinter import ttk
from typing import *

from coref_markup.application import Application


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("filename", default=None, nargs="?")
    args = argparser.parse_args()

    root = tk.Tk()
    root.iconphoto(False, tk.PhotoImage(file="resources/icon.png"))
    root.title("Coref Markup")

    ttk.Style().theme_use({"Windows": "winnative", "Darwin": "aqua"}.get(platform.system(), "default"))
    dark_mode = False
    if platform.system() == "Darwin":
        try:
            dark_mode = bool(root.tk.call("::tk::unsupported::MacWindowStyle", "isdark", root))
        except tk.TclError:
            pass

    app = Application(root, dark_mode=dark_mode)
    if args.filename is not None:
        app.open_file(args.filename)

    app.mainloop()
