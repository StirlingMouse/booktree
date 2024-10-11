#!/usr/bin/env python3
import configparser
import copy
import json
import os
import re
import subprocess
import sys
import tkinter as tk
from contextlib import redirect_stdout
from tkinter import filedialog, messagebox, ttk
from types import SimpleNamespace

import booktree
import myx_args


def from_metadata(value):
    if value == "mam":
        return "MAM"
    elif value == "log":
        return "Log"
    return "MAM + Audible"


def to_metadata(value):
    if value == "MAM":
        return "mam"
    elif value == "Log":
        return "log"
    return "mam-audible"


def test_ffprobe():
    try:
        cmnd = ["ffprobe", "-version"]
        p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate()
        return True
    except:
        return False


class BooktreeApp:
    def __init__(self, root, cgf):
        self.root = root
        self.root.title("Booktree")
        self.root.geometry("700x500")
        self.root.resizable(True, True)

        self.config = cfg

        # Create GUI elements
        self.create_widgets()

        if not test_ffprobe():
            messagebox.showwarning(
                "ffprobe is missing",
                "Could not run ffprobe, booktree will still work but matchrates will be much worse. Please install ffmpeg which provides ffprobe.",
            )

    def create_widgets(self):
        # Style configuration
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10))
        style.configure("TEntry", font=("Arial", 10))

        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(10, weight=1)

        # Source Directory
        sourcedir_label = ttk.Label(main_frame, text="Source Directory:")
        sourcedir_label.grid(row=0, column=0, sticky="e", pady=5)
        sourcedir_label_ttp = CreateToolTip(
            sourcedir_label, "Choose where your audio or ebooks are stored"
        )

        self.sourcedir_entry = ttk.Entry(main_frame, width=50)
        self.sourcedir_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.sourcedir_entry.insert(
            0,
            self.config.get("Config/paths/0/source_path", os.path.expanduser("~")),
        )

        # Browse Button for Source Directory
        self.sourcedir_browse_button = ttk.Button(
            main_frame, text="Browse", command=self.browse_sourcedir
        )
        self.sourcedir_browse_button.grid(row=0, column=2, padx=5, pady=5)

        # Media Directory
        mediadir_label = ttk.Label(main_frame, text="Media Directory:")
        mediadir_label.grid(row=1, column=0, sticky="e", pady=5)
        mediadir_label_ttp = CreateToolTip(
            sourcedir_label, "Choose where your audio or ebooks will be sorted into"
        )

        self.mediadir_entry = ttk.Entry(main_frame, width=50)
        self.mediadir_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.mediadir_entry.insert(
            0,
            self.config.get("Config/paths/0/media_path", os.path.expanduser("~")),
        )

        # Browse Button for Media Directory
        self.mediadir_browse_button = ttk.Button(
            main_frame, text="Browse", command=self.browse_mediadir
        )
        self.mediadir_browse_button.grid(row=1, column=2, padx=5, pady=5)

        # Media Type
        media_type_label = ttk.Label(main_frame, text="Media Type:")
        media_type_label.grid(row=2, column=0, sticky="e", pady=5)
        # media_type_label_ttp = CreateToolTip(ip_method_label, "Choose how the script should obtain your IP address.")

        self.media_type_var = tk.StringVar(
            value=(
                "Ebooks"
                if bool(self.config.get("Config/flags/ebooks", 0))
                else "Audiobooks"
            )
        )
        self.media_type_menu = ttk.OptionMenu(
            main_frame,
            self.media_type_var,
            self.media_type_var.get(),
            "Audiobooks",
            "Ebooks",
            command=self.update_media_type_fields,
        )
        self.media_type_menu.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Metadata source
        metadata_source_label = ttk.Label(main_frame, text="Metadata Source:")
        metadata_source_label.grid(row=3, column=0, sticky="e", pady=5)
        # metadata_source_label_ttp = CreateToolTip(ip_method_label, "Choose how the script should obtain your IP address.")

        self.metadata_source_var = tk.StringVar(
            value=from_metadata(self.config.get("Config/metadata", "mam-audible"))
        )
        self.metadata_source_menu = ttk.OptionMenu(
            main_frame,
            self.metadata_source_var,
            self.metadata_source_var.get(),
            "MAM + Audible",
            "MAM",
            "Log",
            command=self.update_metadata_source_fields,
        )
        self.metadata_source_menu.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Metadata source Options Frames
        self.mam_frame = ttk.Frame(main_frame)
        self.log_mode_frame = ttk.Frame(main_frame)

        # MAM Session Cookie
        mam_cookie_label = ttk.Label(self.mam_frame, text="MAM Session Cookie:")
        mam_cookie_label.grid(row=0, column=0, sticky="e", pady=5)
        mam_cookie_label_ttp = CreateToolTip(
            mam_cookie_label,
            "Your IP or ASN locked session cookie from the MyAnonamouse website.\nThis is different from your browser session.\nSee the Help section for instructions on how to obtain it.",
        )

        self.mam_cookie_entry = ttk.Entry(self.mam_frame, width=50)
        self.mam_cookie_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.mam_cookie_entry.insert(0, self.config.get("Config/session", ""))

        cookie_help_button = ttk.Button(
            self.mam_frame, text="Help", command=self.show_cookie_help
        )
        cookie_help_button.grid(row=0, column=2, padx=5, pady=5)

        # Log file
        logfile_label = ttk.Label(self.log_mode_frame, text="Log File:")
        logfile_label.grid(row=0, column=0, sticky="e", pady=5)
        logfile_label_ttp = CreateToolTip(
            logfile_label, "Select the log file to read metadata from"
        )

        files = self.config.get("Config/paths/0/files", "")
        self.logfile_entry = ttk.Entry(self.log_mode_frame, width=50)
        self.logfile_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.logfile_entry.insert(0, files if isinstance(files, str) else "")

        logfile_help_button = ttk.Button(
            self.log_mode_frame, text="Help", command=self.show_logfile_help
        )
        logfile_help_button.grid(row=0, column=3, padx=5, pady=5)

        # Browse Button for Log File
        self.logfile_browse_button = ttk.Button(
            self.log_mode_frame, text="Browse", command=self.browse_logfile
        )
        self.logfile_browse_button.grid(row=0, column=2, padx=5, pady=5)

        # Multibook
        self.multibook_var = tk.IntVar()
        self.multibook_var.set(
            1 if bool(self.config.get("Config/flags/multibook", 0)) else 0
        )
        self.multibook_check = ttk.Checkbutton(
            main_frame,
            text="Source has collections",
            variable=self.multibook_var,
            command=self.toggle_multibook,
        )
        self.multibook_check.grid(row=7, column=1, padx=5, pady=5, sticky="w")
        multibook_ttp = CreateToolTip(
            self.multibook_check,
            "Check this box if the source directory contains collections (multiple books in the same folder)",
        )

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, columnspan=3, pady=10)

        self.save_button = ttk.Button(
            button_frame, text="Save Config", command=self.save_config
        )
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.run_button = ttk.Button(
            button_frame, text="Organize Books", command=self.run
        )
        self.run_button.pack(side=tk.LEFT, padx=5)

        self.dry_run_button = ttk.Button(
            button_frame, text="Dry Run", command=self.dry_run
        )
        self.dry_run_button.pack(side=tk.LEFT, padx=5)

        # Output Box
        output_label = ttk.Label(main_frame, text="Output Messages:")
        output_label.grid(row=9, column=0, sticky="nw", pady=5)
        self.output_text = tk.Text(
            main_frame, wrap=tk.WORD, height=20, width=70, state="disabled"
        )
        self.output_text.grid(
            row=10, column=0, columnspan=3, padx=5, pady=5, sticky="nsew"
        )
        output_scrollbar = ttk.Scrollbar(
            main_frame, orient=tk.VERTICAL, command=self.output_text.yview
        )
        output_scrollbar.grid(row=10, column=3, sticky="ns", pady=5)
        self.output_text.configure(yscrollcommand=output_scrollbar.set)

        # Initialize fields based on Metadata source
        self.update_metadata_source_fields(self.metadata_source_var.get())

    def show_cookie_help(self):
        help_text = """
How to Obtain the Correct MAM Session Cookie:

1. Log into your MAM account:
   - Go to https://www.myanonamouse.net and log in.

2. Navigate to Security Settings:
   - Click on your username at the top of the page.
   - Select "Preferences" or "Edit Profile"
   - Go to the "Security" tab.

3. Create a New Session:
   - Choose to create a new session.
   - Go to https://www.myanonamouse.net/myip.php and copy your IP address
   - Enter your IP address into the "Create session" box
   - Click on "Submit changes!"

4. Copy the Session Cookie (`mam_id`):
   - Copy the long string that is displayed
   - Paste it into the "MAM Session Cookie" field in the application
"""
        messagebox.showinfo("Help", help_text)

    def show_logfile_help(self):
        help_text = """
Log mode lets you correct matches or metadata from an earlier run.

1. Run booktree (normally or in dry run)
2. Open the .csv file that got created in the logs directory with Excel or similar
3. TODO, describe editing the CSV
4. Select the log file here
"""
        messagebox.showinfo("Help", help_text)

    def update_media_type_fields(self, method):
        pass

    def update_metadata_source_fields(self, metadata_source):
        self.mam_frame.grid_forget()
        self.log_mode_frame.grid_forget()

        if metadata_source == "MAM + Audible":
            self.mam_frame.grid(row=4, column=0, columnspan=3, pady=5, sticky="ew")
            self.mam_frame.columnconfigure(1, weight=1)
        elif metadata_source == "MAM":
            self.mam_frame.grid(row=4, column=0, columnspan=3, pady=5, sticky="ew")
            self.mam_frame.columnconfigure(1, weight=1)
        elif metadata_source == "Log":
            self.log_mode_frame.grid(row=5, column=0, columnspan=3, pady=5, sticky="ew")
            self.log_mode_frame.columnconfigure(1, weight=1)
        pass

    def browse_sourcedir(self):
        directory = filedialog.askdirectory(mustexist = True)
        if directory:
            self.sourcedir_entry.delete(0, tk.END)
            self.sourcedir_entry.insert(0, directory)

    def browse_mediadir(self):
        directory = filedialog.askdirectory(mustexist = True)
        if directory:
            self.mediadir_entry.delete(0, tk.END)
            self.mediadir_entry.insert(0, directory)

    def browse_logfile(self):
        logfile = filedialog.askopenfilename(filetypes=[("log file", "*.csv")])
        if logfile:
            self.logfile_entry.delete(0, tk.END)
            self.logfile_entry.insert(0, directory)

    def save_config(self):
        self.config._data["Config"]["metadata"] = to_metadata(
            self.metadata_source_var.get()
        )
        self.config._data["Config"]["session"] = self.mam_cookie_entry.get()
        self.config._data["Config"]["paths"][0]["files"] = (
            self.logfile_entry.get()
            if self.metadata_source_var.get() == "Log"
            else (
                ["**/*.m4b", "**/*.mp3", "**/*.m4a"]
                if self.media_type_var.get() == "Audiobooks"
                else ["**/*.epub", "**/*.pdf"]
            )
        )
        self.config._data["Config"]["paths"][0][
            "media_path"
        ] = self.mediadir_entry.get()
        self.config._data["Config"]["paths"][0][
            "source_path"
        ] = self.sourcedir_entry.get()
        self.config._data["Config"]["flags"]["multibook"] = (
            1 if self.multibook_var.get() else 0
        )
        self.config._data["Config"]["flags"]["ebooks"] = (
            1 if self.media_type_var.get() == "Ebooks" else 0
        )

        with open(self.config.config_file, "w") as configfile:
            configfile.write(json.dumps(self.config._data))
        self.append_output("Config Saved\n")

    def toggle_multibook(self):
        pass

    def run(self):
        self.run_with_config(self.config)

    def dry_run(self):
        config = copy.deepcopy(self.config)
        config._data["Config"]["flags"]["dry_run"] = True
        self.run_with_config(config)

    def run_with_config(self, config):
        that = self

        class OutputText:
            def write(self, line):
                that.append_output(line)
                that.root.update()

        with redirect_stdout(OutputText()):
            booktree.main(config)

    def append_output(self, text):
        self.output_text.configure(state="normal")
        self.output_text.insert(tk.END, text)
        self.output_text.configure(state="disabled")
        self.output_text.see(tk.END)


class CreateToolTip(object):
    """
    Create a tooltip for a given widget.
    """

    def __init__(self, widget, text="Widget info"):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, _event):
        x = self.widget.winfo_rootx() + 50
        y = self.widget.winfo_rooty() + 20
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Removes the window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(
            tw,
            text=self.text,
            background="lightyellow",
            relief="solid",
            borderwidth=1,
            wraplength=300,
        )
        label.pack(ipadx=1)

    def hide_tooltip(self, _event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


if __name__ == "__main__":
    config_file = "./config.json"
    # check if config files are present
    if not os.path.exists(config_file):
        file = open(config_file, "w")
        file.write(
            r"""
{
    "Config": {
        "metadata": "mam-audible",
        "matchrate": 70,
        "fuzzy_match": "token_sort",
        "log_path": "./logs",    
        "session": "",
        "paths": [{
            "files": ["**/*.m4b", "**/*.mp3", "**/*.m4a"],
            "source_path": "",
            "media_path": ""
        }],
        "flags": {
            "dry_run": 0,
            "verbose": 1,
            "multibook": 0,
            "ebooks": 0,
            "no_opf": 0,
            "no_cache": 0,
            "fixid3": 0,
            "add_narrators": 0 
        },
        "target_path": {
            "in_series": "{author}/{series}/{series} #{part} - {title}",
            "no_series": "{author}/{title}",
            "disc_folder": "{title} {disc}"
        },
        "tokens":{
            "skip_series": 0,
            "kw_ignore": [".", ":", "_", "[", "]", "{", "}", ",", ";", "(", ")"],
            "kw_ignore_words": ["the","and","m4b","mp3","series","audiobook","audiobooks", "book", "part", "track", "novel", "disc"],
            "title_patterns": ["-end", "\bpart\b", "\btrack\b", "\bof\b",  "\bbook\b", "m4b", "\\(", "\\)", "_", "\\[", "\\]", "\\.", "\\s?-\\s?"]
        }  
    }
}
"""
        )
        file.close()

    try:
        cfg = myx_args.Config(
            SimpleNamespace(
                config_file=config_file,
                dry_run=None,
                verbose=None,
                multibook=None,
                ebooks=None,
                no_opf=None,
                no_cache=None,
                fixid3=None,
                add_narrators=None,
            )
        )

    except Exception as e:
        raise Exception(
            f"\nThere was a problem reading your config file {config_file}: {e}\n"
        )

    root = tk.Tk()
    app = BooktreeApp(root, cfg)
    root.mainloop()
