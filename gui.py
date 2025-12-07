# So... this file got a bit large over time.
# I’ve tried to keep things tidy, but I know there are some rough edges.
# (Note to self: maybe break this into modules one day.)

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
import time
from PIL import Image, ImageTk
from ctypes import windll
import platform
import sys

# I like having this around for PyInstaller stuff.
# Might refactor later depending on how many assets we start shipping.
def grab_resource(p):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, p)
    return os.path.join(os.path.abspath("."), p)

# DPI fix for Windows — never really investigated all cases,
# but it seems good enough for now.
try:
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


# Constants I probably should put in one place, but meh
UMODEL_BIN = "umodel/umodel.exe"
LOG_FNAME = "umodel_export_log.txt"

# I sometimes forget which extensions are which, so I keep them here
TEX_EXTS = "utx upk uasset"
MESH_EXTS = "usx unr upk uasset"

# Asset files
APP_LOGO = grab_resource("logo.png")
APP_ICON = grab_resource("icon.ico")


# Clearing logs — maybe in the future I may want to archive instead of delete?
def nuke_log():
    try:
        if os.path.exists(LOG_FNAME):
            os.remove(LOG_FNAME)
    except:
        # Don't really care if deletion borks
        pass


# Basic timestamped logger — nothing fancy.
def write_log(msg):
    ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{ts} {msg}"
    with open(LOG_FNAME, "a") as lf:
        lf.write(line + "\n")


# Wrapper for calling UModel itself
def call_umodel(src_dir, out_dir, pkg_name, fmt_flag):
    # I could build this command with f-strings, but I'm weirdly attached
    # to list-building like this.
    args = [
        UMODEL_BIN,
        "-export",
        fmt_flag,
        f"-path={src_dir}",
        f"-out={out_dir}",
        pkg_name
    ]

    # Try hiding the console window on Windows (looks a bit cleaner)
    launch_stuff = None
    if platform.system() == "Windows":
        launch_stuff = subprocess.STARTUPINFO()
        launch_stuff.dwFlags |= subprocess.SW_HIDE

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            startupinfo=launch_stuff
        )

        write_log(f"Running: {' '.join(args)}")
        if result.stdout:
            write_log("UMODEL SAYS:\n" + result.stdout.strip())
        if result.stderr:
            write_log("UMODEL ERRORS:\n" + result.stderr.strip())

        # Return True if return code was 0. No rocket science here.
        return (result.returncode == 0)

    except FileNotFoundError:
        messagebox.showerror("Execution Error",
                             f"UModel executable missing! Expected at: {UMODEL_BIN}")
        write_log("FATAL: UModel executable missing!")
        return False

    except Exception as exc:
        messagebox.showerror("Execution Error", f"Unexpected error: {exc}")
        write_log(f"EXCEPTION during UModel call: {exc}")
        return False


class UModelMassGUI:
    def __init__(self, master):
        self.master = master
        master.title("UModel Mass Exporter")
        master.resizable(False, False)

        # App icon (if available)
        if os.path.exists(APP_ICON):
            master.iconbitmap(APP_ICON)

        # Widget variables
        self.src_path_var = tk.StringVar()
        self.out_path_var = tk.StringVar()
        self.export_kind = tk.StringVar(value="textures")  # default

        # Some mildly inconsistent style definitions
        sty = ttk.Style()
        sty.configure("TFrame", background="#ffffff")
        sty.configure("TLabel", background="#ffffff", font=("Helvetica", 10))
        sty.configure("TButton", font=("Helvetica", 10))
        # I keep forgetting I set this, but it seems okay
        sty.configure("TRadiobutton", background="#ffffff")
        sty.configure("TEntry", font=("Helvetica", 10))

        # Menubar
        self._init_menu()

        # Layout root frame
        root_frame = ttk.Frame(master, padding="15")
        root_frame.grid(row=0, column=0, sticky="nsew")

        # Starting row tracker (I tweak this by hand… could be cleaner)
        row_i = 0

        # Try to load the logo
        if os.path.exists(APP_LOGO):
            try:
                img = Image.open(APP_LOGO)
                self._logo_tk = ImageTk.PhotoImage(img)
                ttk.Label(root_frame, image=self._logo_tk).grid(
                    row=row_i, column=0, columnspan=3, pady=(0, 15)
                )
                row_i += 1
            except Exception as err:
                write_log(f"Logo load failed: {err}")
                ttk.Label(root_frame, text="[Logo Missing]").grid(
                    row=row_i, column=0, columnspan=3
                )
                row_i += 1
        else:
            # Fallback title
            ttk.Label(
                root_frame,
                text="Universal UModel Asset Exporter",
                font=("Helvetica", 14)
            ).grid(row=row_i, column=0, columnspan=3, pady=(0, 15))
            row_i += 1

        # Asset selection header
        ttk.Label(root_frame, text="1. Choose Type of Assets:").grid(
            row=row_i, column=0, columnspan=3, sticky="w", pady=(0, 5)
        )
        row_i += 1

        # Radio buttons
        rb_frame = ttk.Frame(root_frame)
        rb_frame.grid(row=row_i, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(
            rb_frame,
            text="Textures (*.utx, *.upk) — PNG Output",
            variable=self.export_kind,
            value="textures"
        ).pack(anchor="w")
        ttk.Radiobutton(
            rb_frame,
            text="Meshes/Maps (*.usx, *.unr) — OBJ Output",
            variable=self.export_kind,
            value="meshes"
        ).pack(anchor="w")
        row_i += 1

        # Source folder
        ttk.Label(root_frame, text="2. Pick Source Folder:").grid(
            row=row_i, column=0, columnspan=3, sticky="w", pady=(10, 5)
        )
        row_i += 1

        ttk.Entry(root_frame, textvariable=self.src_path_var,
                  width=50).grid(row=row_i, column=0, columnspan=2, sticky="ew")
        ttk.Button(root_frame, text="Browse",
                   command=self._choose_source).grid(row=row_i, column=2, sticky="e")
        row_i += 1

        # Output folder
        ttk.Label(root_frame, text="3. Pick Output Folder:").grid(
            row=row_i, column=0, columnspan=3, sticky="w", pady=(10, 5)
        )
        row_i += 1

        ttk.Entry(root_frame, textvariable=self.out_path_var,
                  width=50).grid(row=row_i, column=0, columnspan=2, sticky="ew")
        ttk.Button(root_frame, text="Browse",
                   command=self._choose_output).grid(row=row_i, column=2, sticky="e")
        row_i += 1

        # Start export button — arguably too big, but I like the spacious design.
        ttk.Button(
            root_frame, text="Start Export!", padding="10",
            command=self._begin_export
        ).grid(row=row_i, column=0, columnspan=3, pady=(20, 0), sticky="ew")

    # Menus (I don't touch this often)
    def _init_menu(self):
        m = tk.Menu(self.master)
        self.master.config(menu=m)
        help_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="Help", menu=help_m)
        help_m.add_command(label="About / Credits", command=self._show_about)

    # Quick popup with credits
    def _show_about(self):
        win = tk.Toplevel(self.master)
        win.title("About UModel Exporter")
        win.resizable(False, False)

        if os.path.exists(APP_ICON):
            win.iconbitmap(APP_ICON)

        frame = ttk.Frame(win, padding="20")
        frame.pack(fill="both", expand=True)

        r = 0

        # Logo (again)
        if os.path.exists(APP_LOGO):
            try:
                img = Image.open(APP_LOGO)
                win._credits_logo = ImageTk.PhotoImage(img)
                ttk.Label(frame, image=win._credits_logo).grid(
                    row=r, column=0, pady=(0, 15)
                )
                r += 1
            except:
                pass

        ttk.Label(frame, text="Version 1.0.0").grid(row=r, column=0, sticky="w")
        r += 1

        ttk.Label(frame, text="Backend: UModel by Gildor").grid(
            row=r, column=0, sticky="w", pady=(10, 0)
        )
        r += 1

        lnk1 = ttk.Label(frame, text="gildor.org/en/projects/umodel",
                         foreground="blue", cursor="hand2")
        lnk1.grid(row=r, column=0, sticky="w")
        lnk1.bind("<Button-1>",
                  lambda e: os.startfile("http://www.gildor.org/en/projects/umodel"))
        r += 1

        ttk.Button(frame, text="Close", command=win.destroy).grid(
            row=r, column=0, pady=(20, 0)
        )

        # Slightly obsessive modal behavior
        win.transient(self.master)
        win.grab_set()
        self.master.wait_window(win)

    # Directory choosers
    def _choose_source(self):
        chosen = filedialog.askdirectory(title="Pick folder with game packages")
        if chosen:
            self.src_path_var.set(chosen)

    def _choose_output(self):
        outdir = filedialog.askdirectory(title="Pick export destination")
        if outdir:
            self.out_path_var.set(outdir)

    def _begin_export(self):
        src = self.src_path_var.get()
        out = self.out_path_var.get()
        kind = self.export_kind.get()

        if not src or not out:
            messagebox.showwarning("Missing info",
                                   "Please choose both source and output directories.")
            return

        expected_umodel_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), UMODEL_BIN
        )

        if not os.path.exists(expected_umodel_path):
            messagebox.showerror(
                "Missing Executable",
                f"Could not find UModel executable.\nExpected: {UMODEL_BIN}"
            )
            return

        if not os.path.exists(src):
            messagebox.showwarning("Invalid Path", "Source folder doesn’t exist.")
            return

        # Eh, safe enough
        os.makedirs(out, exist_ok=True)

        if kind == "textures":
            exts = TEX_EXTS.split()
            fmt = "-png"
            title = "Texture Export"
        else:
            exts = MESH_EXTS.split()
            fmt = "-obj"
            title = "Mesh/Map Export"

        # Confirmation prompt  
        if not messagebox.askyesno(
            "Ready?",
            f"Begin {title}?\nSource: {src}\nOutput: {out}\n(This will clear the log first.)"
        ):
            return

        self._do_export(src, out, exts, fmt, title)

    def _do_export(self, src, out, ext_list, fmt_flag, label):
        nuke_log()
        write_log(f"=== {label} START ===")
        write_log(f"SOURCE: {src}")
        write_log(f"OUTPUT: {out}")

        processed = 0

        # Note to self: Maybe walk recursively later?
        for fileext in ext_list:
            write_log(f"Looking for .{fileext} files...")
            for fname in os.listdir(src):
                # Classic human thing: lower() + endswith instead of fancy patterns
                if fname.lower().endswith("." + fileext):
                    ok = call_umodel(src, out, fname, fmt_flag)
                    if ok:
                        processed += 1

        # A slightly over-detailed completion popup.
        messagebox.showinfo(
            "Done!",
            f"Finished exporting.\nFiles processed: {processed}\n"
            f"Check output folder and {LOG_FNAME} for details."
        )

        write_log(f"=== EXPORT COMPLETE ({processed} files) ===")


# Main entry — nothing fancy except the AppUserModelID thing for Windows taskbar icons.
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    root = tk.Tk()

    # Windows-specific app ID for taskbar
    if platform.system() == "Windows" and os.path.exists(APP_ICON):
        try:
            myappid = "umodel.mass.exporter.v1"
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = UModelMassGUI(root)
    root.mainloop()