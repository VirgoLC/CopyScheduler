import calendar
import ctypes
import math
import os
import queue
import shutil
import threading
import uuid
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


class CopyScheduler:
    def __init__(self, root):
        self.root = root
        self.root.title("CopyScheduler")
        self.root.geometry("860x820")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.last_run_key = None
        self._version_clicks = 0

        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        self.mode = tk.StringVar(value="Every day")
        self.time = tk.StringVar(value="12:00")
        self.selected_date = tk.StringVar(value=date.today().isoformat())
        self.overwrite_existing = tk.BooleanVar(value=False)
        self.progress_percent = tk.StringVar(value="0%")

        self.custom_days = {day: True for day in DAYS}
        self.display_days = {
            day: tk.BooleanVar(value=True) for day in DAYS
        }
        self.day_buttons = {}

        self.events = queue.Queue()
        self.copying = False
        self.schedule_enabled = False
        self.recent_paths = []

        self.browse_directories = {"source": None, "destination": None}

        self._apply_theme()
        self._set_window_icon()
        self._build_ui()
        self._update_mode()
        self._update_clock()

        self.root.after_idle(self._align_repeat_width)
        self.root.after(200, self._process_events)
        self.root.after(1000, self._check_schedule)

    def _on_close(self):
        if self.copying:
            messagebox.showwarning(
                "Copy in progress",
                "Wait for the copy to finish before closing the application.",
                parent=self.root,
            )
            return

        self.root.destroy()

    def _apply_theme(self):
        self.colors = {
            "bg": "#151922",
            "panel": "#202632",
            "field": "#171d27",
            "text": "#f2f5fb",
            "muted": "#bac5d6",
            "border": "#343d4d",
            "accent": "#769cff",
            "accent_active": "#91adff",
            "progress": "#63C7A5",
            "selection": "#405a86",
            "button_hover": "#2c3748",
        }
        c = self.colors
        self.root.configure(bg=c["bg"])

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            ".",
            font=("Segoe UI", 10),
            background=c["bg"],
            foreground=c["text"],
        )
        style.configure("TFrame", background=c["bg"])
        style.configure("Card.TFrame", background=c["panel"])
        style.configure(
            "Card.TLabelframe",
            background=c["panel"],
            bordercolor=c["border"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=c["panel"],
            foreground=c["text"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure("TLabel", background=c["bg"], foreground=c["text"])
        style.configure(
            "Card.TLabel", background=c["panel"], foreground=c["text"]
        )
        style.configure(
            "Section.TLabel",
            background=c["panel"],
            foreground=c["text"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Popup.Section.TLabel",
            background=c["bg"],
            foreground=c["text"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "TEntry",
            fieldbackground=c["field"],
            foreground=c["text"],
            insertcolor=c["text"],
            bordercolor=c["border"],
            padding=7,
        )
        style.configure(
            "TCombobox",
            fieldbackground=c["field"],
            foreground=c["text"],
            arrowcolor=c["text"],
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", c["field"])],
            foreground=[("readonly", c["text"])],
            selectbackground=[("readonly", c["selection"])],
            selectforeground=[("readonly", c["text"])],
        )
        style.configure(
            "TButton",
            background=c["panel"],
            foreground=c["text"],
            bordercolor=c["border"],
            padding=(10, 6),
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("active", c["selection"])],
            foreground=[("active", c["text"])],
        )
        style.configure(
            "Accent.TButton",
            background=c["accent"],
            foreground="#101522",
            padding=(12, 7),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", c["accent_active"])],
            foreground=[("active", "#101522")],
        )
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=c["panel"],
            background=c["progress"],
            bordercolor=c["panel"],
            lightcolor=c["progress"],
            darkcolor=c["progress"],
            borderwidth=0,
            troughrelief="flat",
            pbarrelief="flat",
            thickness=16,
        )
        style.configure(
            "Vertical.TScrollbar",
            background=c["panel"],
            troughcolor=c["field"],
            bordercolor=c["panel"],
            arrowcolor=c["text"],
        )

    def _set_window_icon(self):
        icon_path = Path(__file__).with_name("app.ico")
        if not icon_path.is_file():
            return

        try:
            self.root.iconbitmap(default=str(icon_path))
        except tk.TclError as error:
            print(f"Unable to load window icon: {error}")

    @staticmethod
    def _rounded_rect(
        canvas,
        x1,
        y1,
        x2,
        y2,
        radius,
        fill,
        outline=None,
    ):
        outline = fill if outline is None else outline
        radius = max(1, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))

        points = []
        segments_per_corner = 24
        corners = (
            (x2 - radius, y1 + radius, -90),
            (x2 - radius, y2 - radius, 0),
            (x1 + radius, y2 - radius, 90),
            (x1 + radius, y1 + radius, 180),
        )

        for center_x, center_y, start_angle in corners:
            for step in range(segments_per_corner + 1):
                angle = math.radians(
                    start_angle + 90 * step / segments_per_corner
                )
                points.extend((
                    center_x + radius * math.cos(angle),
                    center_y + radius * math.sin(angle),
                ))

        return canvas.create_polygon(
            points,
            fill=fill,
            outline=outline,
            width=1,
            joinstyle="round",
        )

    def _rounded_button(
        self,
        parent,
        text,
        command,
        width=86,
        height=36,
        fill=None,
        outline=None,
        foreground=None,
        hover_fill=None,
        font=("Segoe UI", 10, "bold"),
    ):
        fill = fill or self.colors["accent"]
        outline = outline or fill
        foreground = foreground or "#101522"
        hover_fill = hover_fill or self.colors["accent_active"]
        radius = min(12, height // 2)

        canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=self.colors["panel"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        canvas.button_text = text

        def draw(button_fill):
            canvas.delete("all")
            self._rounded_rect(
                canvas,
                1.5,
                1.5,
                width - 1.5,
                height - 1.5,
                radius - 1,
                button_fill,
                outline,
            )
            canvas.text_item = canvas.create_text(
                width // 2,
                height // 2,
                text=canvas.button_text,
                fill=foreground,
                font=font,
            )

        canvas.redraw = draw
        draw(fill)
        canvas.bind("<Enter>", lambda _event: draw(hover_fill))
        canvas.bind("<Leave>", lambda _event: draw(fill))
        canvas.bind("<Button-1>", lambda _event: command())
        canvas.bind("<Return>", lambda _event: command())
        canvas.bind("<space>", lambda _event: command())
        return canvas

    @staticmethod
    def _set_button_text(button, text):
        button.button_text = text
        button.itemconfigure(button.text_item, text=text)

    def _outlined_value(self, parent, text, font=("Segoe UI", 11, "bold")):
        outer = tk.Frame(parent, bg=self.colors["border"], padx=1, pady=1)
        label = tk.Label(
            outer,
            text=text,
            bg=self.colors["field"],
            fg=self.colors["text"],
            font=font,
            padx=9,
            pady=5,
        )
        label.pack()
        return outer, label

    def _draw_day_button(self, day):
        canvas = self.day_buttons[day]
        selected = self.display_days[day].get()
        enabled = self.mode.get() == "Selected days"

        if not enabled:
            fill = self.colors["panel"]
            border = self.colors["border"]
            text_color = self.colors["muted"]
        elif selected:
            fill = self.colors["accent"]
            border = self.colors["accent"]
            text_color = "#101522"
        else:
            fill = self.colors["panel"]
            border = self.colors["border"]
            text_color = self.colors["text"]

        canvas.delete("all")
        self._rounded_rect(canvas, 1.5, 1.5, 40.5, 30.5, 6, fill, border)
        canvas.create_text(
            21, 16, text=day, fill=text_color, font=("Segoe UI", 9, "bold")
        )
        canvas.configure(cursor="hand2" if enabled else "arrow")

    def _toggle_day(self, day):
        if self.mode.get() != "Selected days":
            return
        value = not self.display_days[day].get()
        self.display_days[day].set(value)
        self.custom_days[day] = value
        self._draw_day_button(day)

    def _align_repeat_width(self):
        if not self.days_row.winfo_exists():
            return

        self.root.update_idletasks()
        width = self.days_row.winfo_reqwidth()
        height = self.mode_box.winfo_reqheight()
        self.repeat_container.configure(width=width, height=height)
        self.repeat_container.pack_propagate(False)

    def _build_ui(self):
        footer = tk.Frame(self.root, height=26, bg=self.colors["panel"])
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

        tk.Frame(
            footer, height=1, bg=self.colors["border"]
        ).pack(side="top", fill="x")

        footer_content = tk.Frame(footer, bg=self.colors["panel"])
        footer_content.pack(fill="both", expand=True)

        tk.Label(
            footer_content,
            text="CopyScheduler",
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=18)

        self.version_label = tk.Label(
            footer_content,
            text="v0.1b",
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self.version_label.pack(side="right", padx=18)
        self.version_label.bind("<Button-1>", self._version_clicked)

        main = ttk.Frame(self.root, padding=14)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        header = tk.Frame(
            main,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(1, weight=1)

        tk.Frame(
            header, bg=self.colors["accent"], width=5
        ).grid(row=0, column=0, rowspan=2, sticky="ns")

        tk.Label(
            header,
            text="CopyScheduler",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=("Segoe UI", 20, "bold"),
        ).grid(row=0, column=1, sticky="w", padx=14, pady=(9, 0))

        tk.Label(
            header,
            text="Schedule file and folder copies",
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10, "italic"),
        ).grid(row=1, column=1, sticky="w", padx=14, pady=(1, 9))

        self._rounded_button(
            header, "About", self._show_about, width=86, height=38
        ).grid(row=0, column=2, rowspan=2, padx=14, pady=9)

        paths = ttk.LabelFrame(
            main,
            text="  Source and Destination  ",
            style="Card.TLabelframe",
            padding=12,
        )
        paths.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        paths.columnconfigure(1, weight=1)

        ttk.Label(paths, text="Source item:", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=5
        )
        ttk.Entry(
            paths, textvariable=self.source, state="readonly"
        ).grid(row=0, column=1, sticky="ew", padx=10)
        self._rounded_button(
            paths,
            "Browse...",
            lambda: self._open_object_picker("source"),
            width=82,
            height=32,
            fill=self.colors["panel"],
            outline=self.colors["border"],
            foreground=self.colors["text"],
            hover_fill=self.colors["button_hover"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=2)

        ttk.Label(
            paths, text="Destination folder:", style="Section.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(
            paths, textvariable=self.destination, state="readonly"
        ).grid(
            row=1, column=1, sticky="ew", padx=10
        )
        self._rounded_button(
            paths,
            "Browse...",
            lambda: self._open_object_picker("destination"),
            width=82,
            height=32,
            fill=self.colors["panel"],
            outline=self.colors["border"],
            foreground=self.colors["text"],
            hover_fill=self.colors["button_hover"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=1, column=2)

        overwrite_frame = tk.Frame(
            paths, bg=self.colors["border"], padx=1, pady=1
        )
        overwrite_frame.grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        overwrite_inner = tk.Frame(
            overwrite_frame, bg=self.colors["field"], padx=7, pady=3
        )
        overwrite_inner.pack()

        tk.Checkbutton(
            overwrite_inner,
            text="Automatically replace existing files and folders",
            variable=self.overwrite_existing,
            background=self.colors["field"],
            foreground=self.colors["text"],
            activebackground=self.colors["field"],
            activeforeground=self.colors["text"],
            selectcolor=self.colors["field"],
            highlightthickness=0,
            bd=0,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        schedule = ttk.LabelFrame(
            main, text="  Schedule  ", style="Card.TLabelframe", padding=12
        )
        schedule.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        schedule.columnconfigure(1, weight=0)

        ttk.Label(schedule, text="Repeat:", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        self.repeat_container = ttk.Frame(schedule, style="Card.TFrame")
        self.repeat_container.grid(row=0, column=1, sticky="w", padx=10)
        self.mode_box = ttk.Combobox(
            self.repeat_container,
            textvariable=self.mode,
            values=("Every day", "Selected days", "Specific date"),
            state="readonly",
        )
        self.mode_box.pack(fill="x")
        self.mode_box.bind("<<ComboboxSelected>>", self._update_mode)

        ttk.Label(schedule, text="Time:", style="Section.TLabel").grid(
            row=1, column=0, sticky="w", pady=(8, 4)
        )

        time_controls = ttk.Frame(schedule, style="Card.TFrame")
        time_controls.grid(
            row=1, column=1, sticky="w", padx=10, pady=(8, 4)
        )
        time_badge, self.time_label = self._outlined_value(
            time_controls, self.time.get()
        )
        time_badge.pack(side="left", padx=(0, 10))

        self._rounded_button(
            time_controls,
            "Choose time...",
            self._open_time_picker,
            width=126,
            height=32,
            fill=self.colors["panel"],
            outline=self.colors["border"],
            foreground=self.colors["text"],
            hover_fill=self.colors["button_hover"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        self.schedule_detail_label = ttk.Label(
            schedule, text="Days of the week:", style="Section.TLabel"
        )
        self.schedule_detail_label.grid(
            row=2, column=0, sticky="nw", pady=(7, 3)
        )

        self.days_row = ttk.Frame(schedule, style="Card.TFrame")
        self.days_row.grid(
            row=2, column=1, columnspan=2, sticky="w", padx=10, pady=4
        )

        for day in DAYS:
            button = tk.Canvas(
                self.days_row,
                width=42,
                height=32,
                bg=self.colors["panel"],
                highlightthickness=0,
                bd=0,
            )
            button.pack(side="left", padx=3)
            button.bind(
                "<Button-1>",
                lambda _event, name=day: self._toggle_day(name),
            )
            self.day_buttons[day] = button
            self._draw_day_button(day)

        self.date_row = ttk.Frame(schedule, style="Card.TFrame")
        date_badge, self.date_label = self._outlined_value(
            self.date_row,
            self._format_date(),
            font=("Segoe UI", 10, "bold"),
        )
        date_badge.pack(side="left", padx=(0, 10))

        self._rounded_button(
            self.date_row,
            "Choose date...",
            self._open_calendar,
            width=118,
            height=32,
            fill=self.colors["panel"],
            outline=self.colors["border"],
            foreground=self.colors["text"],
            hover_fill=self.colors["button_hover"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        actions = ttk.Frame(schedule, style="Card.TFrame")
        actions.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.copy_button = self._rounded_button(
            actions,
            "Copy now",
            self._start_manual_copy,
            width=100,
            height=36,
            fill=self.colors["panel"],
            outline=self.colors["accent"],
            foreground=self.colors["text"],
            hover_fill=self.colors["button_hover"],
        )
        self.copy_button.pack(side="left", padx=(0, 8))

        self.schedule_button = self._rounded_button(
            actions,
            "Enable schedule",
            self._toggle_schedule,
            width=148,
            height=36,
            fill=self.colors["accent"],
            outline=self.colors["accent"],
            foreground="#101522",
            hover_fill=self.colors["accent_active"],
        )
        self.schedule_button.pack(side="left")

        activity = ttk.LabelFrame(
            main, text="  Activity  ", style="Card.TLabelframe", padding=10
        )
        activity.grid(row=3, column=0, sticky="nsew")
        activity.columnconfigure(0, weight=1)
        activity.rowconfigure(2, weight=1, minsize=150)

        progress_row = ttk.Frame(activity, style="Card.TFrame")
        progress_row.grid(row=0, column=0, sticky="ew")
        progress_row.columnconfigure(0, weight=1)

        progress_border = tk.Frame(
            progress_row, bg=self.colors["border"], padx=1, pady=1
        )
        progress_border.grid(row=0, column=0, sticky="ew")
        progress_border.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(
            progress_border, maximum=100, value=0
        )
        self.progress.grid(row=0, column=0, sticky="ew")

        ttk.Label(
            progress_row,
            textvariable=self.progress_percent,
            style="Section.TLabel",
            width=5,
            anchor="e",
        ).grid(row=0, column=1, padx=(10, 0))

        log_header = ttk.Frame(activity, style="Card.TFrame")
        log_header.grid(row=1, column=0, sticky="ew", pady=(8, 6))
        log_header.columnconfigure(0, weight=1)

        ttk.Label(log_header, text="Log", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        clock_frame, self.clock_label = self._outlined_value(
            log_header, "", font=("Segoe UI", 9, "bold")
        )
        clock_frame.grid(row=0, column=1, sticky="e", padx=(8, 10))

        self._rounded_button(
            log_header,
            "Clear",
            self._clear_log,
            width=76,
            height=32,
            fill=self.colors["panel"],
            outline=self.colors["border"],
            foreground=self.colors["text"],
            hover_fill=self.colors["button_hover"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=2)

        log_frame = ttk.Frame(activity, style="Card.TFrame")
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = tk.Text(
            log_frame,
            wrap="word",
            font=("Consolas", 10),
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=8,
            state="disabled",
            background=self.colors["field"],
            foreground=self.colors["text"],
            insertbackground=self.colors["text"],
            selectbackground=self.colors["selection"],
            selectforeground=self.colors["text"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        self.log.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def _version_clicked(self, _event=None):
        self._version_clicks += 1
        if self._version_clicks >= 7:
            self._version_clicks = 0
            messagebox.showinfo(
                "A little secret",
                "Made with care by VirgoLC.",
                parent=self.root,
            )

    def _open_object_picker(self, target="source"):
        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.title(
            "Select source item"
            if target == "source"
            else "Select destination folder"
        )
        popup.transient(self.root)
        popup.geometry("640x460")
        popup.minsize(500, 360)
        popup.configure(bg=self.colors["bg"])

        frame = ttk.Frame(popup, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        ttk.Label(
            frame,
            text="Choose a file, folder, or drive",
            style="Popup.Section.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        path_var = tk.StringVar()
        path_entry = ttk.Combobox(
            frame,
            textvariable=path_var,
            values=self.recent_paths,
            state="normal",
        )
        path_entry.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        suggestion_window = tk.Toplevel(popup)
        suggestion_window.withdraw()
        suggestion_window.overrideredirect(True)
        suggestion_window.transient(popup)

        suggestion_list = tk.Listbox(
            suggestion_window,
            height=6,
            activestyle="none",
            takefocus=False,
            font=("Segoe UI", 10),
            background=self.colors["field"],
            foreground=self.colors["text"],
            selectbackground=self.colors["selection"],
            selectforeground=self.colors["text"],
            relief="solid",
            borderwidth=1,
        )
        suggestion_list.pack(fill="both", expand=True)

        list_frame = ttk.Frame(frame)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        items = tk.Listbox(
            list_frame,
            activestyle="none",
            selectmode="browse",
            font=("Segoe UI", 10),
            relief="solid",
            borderwidth=1,
            background=self.colors["field"],
            foreground=self.colors["text"],
            selectbackground=self.colors["selection"],
            selectforeground=self.colors["text"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        items.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, command=items.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        items.configure(yscrollcommand=scrollbar.set)

        entries = []
        state = {"current_path": None, "showing_drives": False}

        def remember_path(path):
            value = str(path)
            self.recent_paths = [
                recent for recent in self.recent_paths if recent != value
            ]
            self.recent_paths.insert(0, value)
            self.recent_paths = self.recent_paths[:5]
            path_entry.configure(values=self.recent_paths)

        def select_path(path):
            path = Path(path)

            if target == "destination" and not path.is_dir():
                messagebox.showerror(
                    "Folder required",
                    "Select a folder or drive as the destination.",
                    parent=popup,
                )
                return

            remember_path(path)
            if target == "destination":
                self.destination.set(str(path))
            else:
                self.source.set(str(path))

            self.browse_directories[target] = (
                path if path.is_dir() else path.parent
            )
            popup.destroy()

        def load_drives():
            state["showing_drives"] = True
            state["current_path"] = None
            path_var.set("This PC")
            items.delete(0, "end")
            entries.clear()

            try:
                drive_mask = ctypes.windll.kernel32.GetLogicalDrives()
            except (AttributeError, OSError):
                drive_mask = 0

            for index in range(26):
                if drive_mask & (1 << index):
                    drive = Path(f"{chr(65 + index)}:\\")
                    try:
                        drive_type = ctypes.windll.kernel32.GetDriveTypeW(
                            str(drive)
                        )
                    except (AttributeError, OSError):
                        drive_type = 0

                    label = "Network drive" if drive_type == 4 else "Drive"
                    entries.append(drive)
                    items.insert("end", f"[{label}]  {drive}")

            if not entries:
                items.insert("end", "No drives found")

        def load_folder(folder):
            folder = Path(folder)
            try:
                children = sorted(
                    folder.iterdir(),
                    key=lambda item: (
                        not item.is_dir(),
                        item.name.casefold(),
                    ),
                )
            except OSError as error:
                messagebox.showerror(
                    "Unable to open folder",
                    str(error),
                    parent=popup,
                )
                return

            state["showing_drives"] = False
            state["current_path"] = folder
            self.browse_directories[target] = folder
            path_var.set(str(folder))
            items.delete(0, "end")
            entries.clear()

            for child in children:
                try:
                    is_directory = child.is_dir()
                except OSError:
                    is_directory = False

                label = "[FOLDER] " if is_directory else "[FILE] "
                entries.append(child)
                items.insert("end", f"{label}{child.name}")

        def open_typed_path(_event=None):
            suggestion_window.withdraw()
            raw_path = os.path.expandvars(path_var.get().strip())

            if (
                len(raw_path) >= 2
                and raw_path[0] == raw_path[-1]
                and raw_path[0] in ("'", '"')
            ):
                raw_path = raw_path[1:-1].strip()

            if not raw_path or raw_path.casefold() == "this pc":
                load_drives()
                return "break"

            if (
                len(raw_path) == 2
                and raw_path[1] == ":"
                and raw_path[0].isalpha()
            ):
                raw_path += "\\"

            try:
                path = Path(raw_path).expanduser()

                if path.is_dir():
                    remember_path(path)
                    load_folder(path)
                elif path.is_file() and target == "source":
                    select_path(path)
                elif path.is_file():
                    messagebox.showerror(
                        "Folder required",
                        "Enter a folder path for the destination.",
                        parent=popup,
                    )
                else:
                    messagebox.showerror(
                        "Path not found",
                        f"The path does not exist:\n{path}",
                        parent=popup,
                    )
            except (OSError, RuntimeError, ValueError) as error:
                messagebox.showerror(
                    "Invalid path",
                    str(error),
                    parent=popup,
                )

            return "break"

        def show_suggestions(suggestions):
            suggestion_list.delete(0, "end")

            if not suggestions:
                suggestion_window.withdraw()
                return

            for suggestion in suggestions[:6]:
                suggestion_list.insert("end", suggestion)

            suggestion_list.configure(height=min(len(suggestions), 6))
            suggestion_window.update_idletasks()

            x = path_entry.winfo_rootx()
            y = path_entry.winfo_rooty() + path_entry.winfo_height()
            width = path_entry.winfo_width()
            height = suggestion_list.winfo_reqheight()

            cursor_position = path_entry.index(tk.INSERT)
            suggestion_window.geometry(f"{width}x{height}+{x}+{y}")
            suggestion_window.deiconify()
            suggestion_window.lift()

            def restore_focus():
                try:
                    if popup.winfo_exists() and path_entry.winfo_exists():
                        path_entry.focus_set()
                        path_entry.icursor(cursor_position)
                except tk.TclError:
                    pass

            popup.after_idle(restore_focus)

        def choose_suggestion(event):
            index = suggestion_list.nearest(event.y)
            if index >= 0:
                path_var.set(suggestion_list.get(index))
                path_entry.icursor("end")

            suggestion_window.withdraw()
            path_entry.focus_set()
            return "break"

        suggestion_list.bind("<Button-1>", choose_suggestion)
        def handle_suggestion_key(event):
            if event.keysym in ("Up", "Down"):
                if (
                    not suggestion_window.winfo_viewable()
                    or suggestion_list.size() == 0
                ):
                    return

                selection = suggestion_list.curselection()
                if selection:
                    index = selection[0] + (1 if event.keysym == "Down" else -1)
                else:
                    index = 0 if event.keysym == "Down" else suggestion_list.size() - 1

                index = max(0, min(index, suggestion_list.size() - 1))
                suggestion_list.selection_clear(0, "end")
                suggestion_list.selection_set(index)
                suggestion_list.activate(index)
                suggestion_list.see(index)
                return "break"

            if event.keysym == "Return":
                selection = suggestion_list.curselection()
                if suggestion_window.winfo_viewable() and selection:
                    selected_path = suggestion_list.get(selection[0])
                    path_var.set(selected_path)
                    path_entry.icursor("end")
                    path_entry.focus_set()

                    try:
                        if Path(os.path.expandvars(selected_path)).is_dir():
                            suggest_paths()
                        else:
                            suggestion_window.withdraw()
                    except (OSError, ValueError):
                        suggestion_window.withdraw()

                    return "break"

                return open_typed_path(event)

        def suggest_paths(event=None):
            if event and (
                event.state & 0x4
                or event.keysym in {
                    "Return", "Escape", "Up", "Down", "Tab",
                    "Left", "Right", "Home", "End",
                }
            ):
                return

            raw_path = os.path.expandvars(path_var.get().strip())
            if (
                len(raw_path) >= 2
                and raw_path[0] == raw_path[-1]
                and raw_path[0] in ("'", '"')
            ):
                raw_path = raw_path[1:-1].strip()

            if not raw_path:
                path_entry.configure(values=self.recent_paths)
                suggestion_window.withdraw()
                return

            suggestions = []
            seen = set()

            def add(value):
                if value not in seen:
                    seen.add(value)
                    suggestions.append(value)

            try:
                if raw_path.endswith(("\\", "/")):
                    parent = Path(raw_path).expanduser()
                    prefix = ""
                elif (
                    len(raw_path) == 2
                    and raw_path[1] == ":"
                    and raw_path[0].isalpha()
                ):
                    parent = Path(raw_path + "\\")
                    prefix = ""
                else:
                    typed = Path(raw_path).expanduser()
                    parent = typed.parent
                    prefix = typed.name.casefold()

                for child in parent.iterdir():
                    if not child.name.casefold().startswith(prefix):
                        continue

                    try:
                        is_directory = child.is_dir()
                        is_file = child.is_file()
                    except OSError:
                        continue

                    if is_directory or (target == "source" and is_file):
                        value = str(child)
                        if is_directory:
                            value += os.sep
                        add(value)

            except (OSError, RuntimeError, ValueError):
                pass

            show_suggestions(suggestions)

        def show_recent_paths_on_arrow(event):
            # Стрелка Combobox находится у правого края поля.
            if event.x >= path_entry.winfo_width() - 24:
                path_entry.configure(values=self.recent_paths)

        path_entry.bind("<Button-1>", show_recent_paths_on_arrow)
        path_entry.bind("<KeyRelease>", suggest_paths)
        path_entry.bind("<<ComboboxSelected>>", open_typed_path)
        path_entry.bind("<KeyPress-Up>", handle_suggestion_key)
        path_entry.bind("<KeyPress-Down>", handle_suggestion_key)
        path_entry.bind("<KeyPress-Return>", handle_suggestion_key)

        def go_up():
            current_path = state["current_path"]
            if state["showing_drives"] or current_path is None:
                load_drives()
            elif current_path.parent == current_path:
                load_drives()
            else:
                load_folder(current_path.parent)

        def choose_selected(_event=None):
            selection = items.curselection()
            if not selection or selection[0] >= len(entries):
                return

            selected = entries[selection[0]]
            try:
                if selected.is_dir():
                    load_folder(selected)
                else:
                    select_path(selected)
            except OSError as error:
                messagebox.showerror(
                    "Unable to access item", str(error), parent=popup
                )

        def accept_selection():
            selection = items.curselection()
            if selection and selection[0] < len(entries):
                select_path(entries[selection[0]])
            elif state["current_path"] is not None:
                select_path(state["current_path"])

        toolbar = ttk.Frame(frame)
        toolbar.grid(row=3, column=0, sticky="ew", pady=(9, 0))

        ttk.Button(toolbar, text="↑ Up", command=go_up).pack(side="left")
        ttk.Button(
            toolbar, text="Drives", command=load_drives
        ).pack(side="left", padx=7)
        ttk.Button(
            toolbar,
            text="Select current folder",
            command=lambda: (
                select_path(state["current_path"])
                if state["current_path"] is not None
                else None
            ),
        ).pack(side="right")
        ttk.Button(
            toolbar,
            text="Select",
            style="Accent.TButton",
            command=accept_selection,
        ).pack(side="right", padx=7)

        items.bind("<Double-Button-1>", choose_selected)
        items.bind("<Return>", choose_selected)

        saved_folder = self.browse_directories.get(target)
        if saved_folder is not None and saved_folder.is_dir():
            load_folder(saved_folder)
        else:
            load_drives()

        popup.update_idletasks()
        self._center_window(popup, self.root)
        popup.deiconify()
        popup.lift()
        popup.grab_set()
        path_entry.focus_set()

    def _format_date(self):
        try:
            value = date.fromisoformat(self.selected_date.get())
            return f"{value.day} {MONTHS[value.month - 1]} {value.year}"
        except ValueError:
            return self.selected_date.get()

    def _update_mode(self, _event=None):
        mode = self.mode.get()

        if mode == "Every day":
            for variable in self.display_days.values():
                variable.set(True)
            self.schedule_detail_label.configure(text="Days of the week:")
            self.days_row.grid()
            self.date_row.grid_remove()
        elif mode == "Selected days":
            for day in DAYS:
                self.display_days[day].set(self.custom_days[day])
            self.schedule_detail_label.configure(text="Days of the week:")
            self.days_row.grid()
            self.date_row.grid_remove()
        else:
            self.schedule_detail_label.configure(text="Date:")
            self.days_row.grid_remove()
            self.date_row.grid(
                row=2,
                column=1,
                columnspan=2,
                sticky="w",
                padx=10,
                pady=4,
            )

        for day in DAYS:
            self._draw_day_button(day)

    def _center_window(self, window, relative_to):
        window.update_idletasks()
        width, height = window.winfo_width(), window.winfo_height()
        x = relative_to.winfo_rootx() + (
            relative_to.winfo_width() - width
        ) // 2
        y = relative_to.winfo_rooty() + (
            relative_to.winfo_height() - height
        ) // 2
        x = max(0, min(x, window.winfo_screenwidth() - width))
        y = max(0, min(y, window.winfo_screenheight() - height))
        window.geometry(f"+{x}+{y}")

    def _open_calendar(self):
        try:
            current = date.fromisoformat(self.selected_date.get())
        except ValueError:
            current = date.today()

        popup = tk.Toplevel(self.root)
        popup.title("Choose date")
        popup.transient(self.root)
        popup.resizable(False, False)
        popup.configure(bg=self.colors["bg"])
        popup.grab_set()

        frame = ttk.Frame(popup, padding=16)
        frame.pack()
        year, month = current.year, current.month
        heading = tk.StringVar()
        calendar_area = ttk.Frame(frame)
        calendar_area.pack()

        def choose_day(day_number):
            self.selected_date.set(date(year, month, day_number).isoformat())
            self.date_label.configure(text=self._format_date())
            popup.destroy()

        def draw_month():
            heading.set(f"{MONTHS[month - 1]} {year}")
            for widget in calendar_area.winfo_children():
                widget.destroy()

            for column, day_name in enumerate(DAYS):
                ttk.Label(
                    calendar_area,
                    text=day_name,
                    anchor="center",
                    style="Popup.Section.TLabel",
                ).grid(row=0, column=column, padx=4, pady=(4, 8))

            for row, week in enumerate(
                calendar.monthcalendar(year, month), start=1
            ):
                for column, day_number in enumerate(week):
                    if day_number:
                        ttk.Button(
                            calendar_area,
                            text=str(day_number),
                            width=4,
                            command=lambda number=day_number: choose_day(
                                number
                            ),
                        ).grid(row=row, column=column, padx=3, pady=3)

        def change_month(amount):
            nonlocal year, month
            month += amount
            if month < 1:
                year -= 1
                month = 12
            elif month > 12:
                year += 1
                month = 1
            draw_month()

        header = ttk.Frame(frame)
        header.pack(fill="x", pady=(0, 10))
        ttk.Button(
            header, text="‹", width=3, command=lambda: change_month(-1)
        ).pack(side="left")
        ttk.Label(
            header,
            textvariable=heading,
            style="Popup.Section.TLabel",
            anchor="center",
        ).pack(side="left", fill="x", expand=True, padx=12)
        ttk.Button(
            header, text="›", width=3, command=lambda: change_month(1)
        ).pack(side="right")

        draw_month()
        popup.update_idletasks()
        self._center_window(popup, self.root)
        popup.deiconify()
        popup.grab_set()

    def _open_time_picker(self):
        popup = tk.Toplevel(self.root)
        popup.title("Choose time")
        popup.transient(self.root)
        popup.resizable(False, False)
        popup.configure(bg=self.colors["bg"])
        popup.grab_set()

        frame = ttk.Frame(popup, padding=22)
        frame.pack()
        ttk.Label(
            frame,
            text="Scroll or select a value",
            style="Popup.Section.TLabel",
        ).pack(pady=(0, 14))

        try:
            initial_hour, initial_minute = map(
                int, self.time.get().split(":")
            )
        except ValueError:
            initial_hour, initial_minute = 12, 0

        lists = ttk.Frame(frame)
        lists.pack()
        lists.columnconfigure(0, weight=1)
        lists.columnconfigure(2, weight=1)

        def make_picker(parent, label, values, initial, column_index):
            column = ttk.Frame(parent)
            column.grid(row=0, column=column_index, padx=10)
            ttk.Label(
                column,
                text=label,
                style="Popup.Section.TLabel",
                anchor="center",
            ).pack(fill="x", pady=(0, 6))

            inner = ttk.Frame(column)
            inner.pack()
            box = tk.Listbox(
                inner,
                height=5,
                width=5,
                exportselection=False,
                activestyle="none",
                font=("Segoe UI", 16, "bold"),
                relief="flat",
                borderwidth=0,
                background=self.colors["field"],
                foreground=self.colors["text"],
                selectbackground=self.colors["selection"],
                selectforeground="#ffffff",
                highlightthickness=1,
                highlightbackground=self.colors["border"],
            )
            scroll = ttk.Scrollbar(inner, command=box.yview)
            box.configure(yscrollcommand=scroll.set)
            box.pack(side="left", fill="y")
            scroll.pack(side="right", fill="y")

            for value in values:
                box.insert("end", f"{value:02d}")

            selected = [initial % len(values)]

            def set_value(index):
                index %= len(values)
                selected[0] = index
                box.selection_clear(0, "end")
                box.selection_set(index)
                box.activate(index)
                box.see(index)

            def on_select(_event=None):
                selection = box.curselection()
                if selection:
                    selected[0] = selection[0]

            def on_wheel(event):
                set_value(selected[0] + (-1 if event.delta > 0 else 1))
                return "break"

            box.bind("<<ListboxSelect>>", on_select)
            box.bind("<MouseWheel>", on_wheel)
            set_value(selected[0])
            return lambda: selected[0]

        get_hour = make_picker(lists, "Hours", range(24), initial_hour, 0)
        ttk.Label(
            lists,
            text=":",
            style="Popup.Section.TLabel",
            font=("Segoe UI", 20, "bold"),
        ).grid(row=0, column=1, padx=2, pady=(22, 0))
        get_minute = make_picker(
            lists, "Minutes", range(60), initial_minute, 2
        )

        def apply_time():
            value = f"{get_hour():02d}:{get_minute():02d}"
            self.time.set(value)
            self.time_label.configure(text=value)
            popup.destroy()

        ttk.Button(
            frame, text="Done", style="Accent.TButton", command=apply_time
        ).pack(fill="x", pady=(18, 0))

        popup.update_idletasks()
        self.root.update_idletasks()
        x = self.root.winfo_rootx()
        y = self.root.winfo_rooty() + (
            self.root.winfo_height() - popup.winfo_height()
        ) // 2
        x = max(0, min(x, popup.winfo_screenwidth() - popup.winfo_width()))
        y = max(0, min(y, popup.winfo_screenheight() - popup.winfo_height()))
        popup.geometry(f"+{x}+{y}")

    def _format_datetime(self, value):
        offset = value.strftime("%z")
        offset = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC"
        return (
            f"{value.day} {MONTHS[value.month - 1]}, "
            f"{value.strftime('%H:%M')} {offset}"
        )

    def _update_clock(self):
        self.clock_label.configure(
            text=self._format_datetime(datetime.now().astimezone())
        )
        self.root.after(1000, self._update_clock)

    def _write_log(self, message):
        timestamp = self._format_datetime(datetime.now().astimezone())
        self.log.configure(state="normal")
        self.log.insert("end", f"[{timestamp}]  {message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _show_about(self):
        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.title("About CopyScheduler")
        popup.transient(self.root)
        popup.resizable(False, False)
        popup.configure(bg=self.colors["bg"])

        content = ttk.Frame(popup, padding=20)
        content.pack(fill="both", expand=True)

        icon_path = Path(__file__).with_name("app.png")
        try:
            image = tk.PhotoImage(file=str(icon_path))
            factor = max(
                1,
                (image.width() + 79) // 80,
                (image.height() + 79) // 80,
            )
            if factor > 1:
                image = image.subsample(factor, factor)

            self.about_icon_image = image
            ttk.Label(content, image=image).pack(side="left", padx=(0, 18))
        except (tk.TclError, OSError):
            pass

        ttk.Label(
            content,
            text=(
                "CopyScheduler\n"
                "Version 0.1b\n"
                "by VirgoLC\n\n"
                "Copy files and folders manually or on a schedule.\n\n"
                "The application must remain open for scheduled copies."
            ),
            justify="left",
            wraplength=320,
        ).pack(side="left")

        ttk.Button(
            popup,
            text="Close",
            style="Accent.TButton",
            command=popup.destroy,
        ).pack(pady=(0, 16))

        popup.update_idletasks()
        self._center_window(popup, self.root)
        popup.deiconify()
        popup.lift()
        popup.grab_set()

    def _start_manual_copy(self):
        self._start_copy(scheduled=False)

    def _start_copy(self, scheduled):
        if self.copying:
            if scheduled:
                self._write_log(
                    "Scheduled copy skipped: another copy is already running."
                )
            return

        def reject(reason):
            if scheduled:
                self._write_log(f"Scheduled copy skipped: {reason}")
            else:
                messagebox.showerror("Error", reason, parent=self.root)

        source_text = self.source.get().strip()
        destination_text = self.destination.get().strip()

        if not source_text:
            reject("Select a source item.")
            return
        if not destination_text:
            reject("Select a destination folder.")
            return

        try:
            source = Path(source_text).expanduser()
            destination_folder = Path(destination_text).expanduser()

            if not source.exists() or not (
                source.is_file() or source.is_dir()
            ):
                reject("Select an existing file, folder, or drive.")
                return
            if not destination_folder.is_dir():
                reject("Select an existing destination folder.")
                return

            source = source.resolve()
            destination_folder = destination_folder.resolve()
            source_name = source.name or source.drive.rstrip("\\/:")
            target = destination_folder / source_name

            if source.is_dir() and source.parent == source:
                reject("Selecting an entire drive or filesystem root is disabled.")
                return

            if source.is_dir():
                try:
                    destination_folder.relative_to(source)
                except ValueError:
                    pass
                else:
                    reject(
                        "A folder cannot be copied into itself or "
                        "one of its subfolders."
                    )
                    return

            target_exists = target.exists() or target.is_symlink()

            if target_exists:
                try:
                    if os.path.samefile(source, target):
                        reject("Source and destination are the same.")
                        return
                except OSError:
                    pass

                if not self.overwrite_existing.get():
                    if scheduled:
                        reject(
                            "Destination already exists and automatic "
                            f"replacement is disabled: {target}"
                        )
                        return

                    overwrite = messagebox.askyesno(
                        "Item already exists",
                        f"Replace the existing destination item?\n\n{target}",
                        parent=self.root,
                    )
                    if not overwrite:
                        self._write_log(f"Replacement cancelled: {target}")
                        return

        except (OSError, RuntimeError, ValueError) as error:
            reject(f"Unable to validate copy paths: {error}")
            return

        self.copying = True
        self.copy_button.configure(state="disabled")
        self.progress["value"] = 0
        self.progress_percent.set("0%")
        self._write_log(f"Copy started: {source}")

        try:
            worker = threading.Thread(
                target=self._copy_worker,
                args=(source, target),
                daemon=True,
            )
            worker.start()
        except RuntimeError as error:
            self.copying = False
            self.copy_button.configure(state="normal")
            reject(f"Unable to start copy worker: {error}")

    @staticmethod
    def _remove_path(path):
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    def _copy_worker(self, source, target):
        token = uuid.uuid4().hex
        temp_path = target.with_name(f".{target.name}.{token}.copying")
        backup_path = target.with_name(f".{target.name}.{token}.backup")
        backup_created = False

        try:
            if source.is_file():
                total = source.stat().st_size
            else:
                total = 0
                for root, dirs, files in os.walk(source, followlinks=False):
                    dirs[:] = [
                        name
                        for name in dirs
                        if not (Path(root) / name).is_symlink()
                    ]
                    for name in files:
                        path = Path(root) / name
                        if not path.is_symlink():
                            total += path.stat().st_size

            copied = [0]
            last_percent = [-1]

            def copy_file(src, dst):
                with open(src, "rb") as source_file, open(
                    dst, "wb"
                ) as target_file:
                    while True:
                        chunk = source_file.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        target_file.write(chunk)
                        copied[0] += len(chunk)

                        percent = (
                            100
                            if total == 0
                            else min(100, int(copied[0] * 100 / total))
                        )
                        if percent != last_percent[0]:
                            self.events.put(("progress", percent))
                            last_percent[0] = percent

                shutil.copystat(src, dst)
                return dst

            if source.is_file():
                copy_file(source, temp_path)
            else:
                shutil.copytree(
                    source,
                    temp_path,
                    copy_function=copy_file,
                    symlinks=True,
                )

            self.events.put(("progress", 100))

            if target.exists() or target.is_symlink():
                target.rename(backup_path)
                backup_created = True

            try:
                temp_path.rename(target)
            except Exception:
                if backup_created:
                    backup_path.rename(target)
                    backup_created = False
                raise

            if backup_created:
                try:
                    self._remove_path(backup_path)
                    backup_created = False
                except Exception as cleanup_error:
                    self.events.put((
                        "done",
                        True,
                        f"Copy completed: {target}. "
                        f"Could not remove backup {backup_path}: "
                        f"{cleanup_error}",
                    ))
                    return

            self.events.put(("done", True, f"Copy completed: {target}"))

        except Exception as error:
            try:
                self._remove_path(temp_path)
            except OSError:
                pass

            if backup_created and not (target.exists() or target.is_symlink()):
                try:
                    backup_path.rename(target)
                    backup_created = False
                except OSError as restore_error:
                    error = (
                        f"{error}; failed to restore previous destination: "
                        f"{restore_error}. Backup remains at {backup_path}"
                    )

            self.events.put(("done", False, f"Copy error: {error}"))

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()

                if event[0] == "progress":
                    percent = event[1]
                    self.progress["value"] = percent
                    self.progress_percent.set(f"{percent}%")
                elif event[0] == "done":
                    _, success, message = event
                    self.copying = False
                    self.copy_button.configure(state="normal")
                    if success:
                        self.progress["value"] = 100
                        self.progress_percent.set("100%")
                    self._write_log(message)

        except queue.Empty:
            pass

        self.root.after(200, self._process_events)

    def _toggle_schedule(self):
        if self.schedule_enabled:
            self.schedule_enabled = False
            self._set_button_text(self.schedule_button, "Enable schedule")
            self.schedule_button.redraw(self.colors["accent"])
            self._write_log("Schedule disabled.")
            return

        try:
            datetime.strptime(self.time.get(), "%H:%M")

            if self.mode.get() == "Specific date":
                selected = date.fromisoformat(self.selected_date.get())
                if selected < date.today():
                    raise ValueError("The selected date has already passed.")

            if (
                self.mode.get() == "Selected days"
                and not any(self.custom_days.values())
            ):
                raise ValueError("Select at least one day of the week.")

            if not self.source.get().strip():
                raise ValueError("Select a source item.")
            if not Path(self.source.get()).expanduser().exists():
                raise ValueError("The source item was not found.")
            if not self.destination.get().strip():
                raise ValueError("Select a destination folder.")
            if not Path(self.destination.get()).expanduser().is_dir():
                raise ValueError("The destination folder was not found.")

        except (OSError, RuntimeError, ValueError) as error:
            messagebox.showerror(
                "Check your settings",
                str(error),
                parent=self.root,
            )
            return

        self.schedule_enabled = True
        self._set_button_text(self.schedule_button, "Disable schedule")
        self.schedule_button.redraw(self.colors["accent"])
        self._write_log("Schedule enabled. Keep the application open.")

    def _check_schedule(self):
        if self.schedule_enabled:
            now = datetime.now()
            due = now.strftime("%H:%M") == self.time.get()
            mode = self.mode.get()

            if mode == "Selected days":
                due = due and self.custom_days[DAYS[now.weekday()]]
            elif mode == "Specific date":
                due = (
                    due
                    and now.date().isoformat() == self.selected_date.get()
                )

            run_key = f"{mode}:{now.date()}:{self.time.get()}"
            if due and run_key != self.last_run_key:
                self.last_run_key = run_key
                if self.copying:
                    self._write_log(
                        "Scheduled copy skipped: another copy is already running."
                    )
                else:
                    self._write_log("Scheduled copy is due.")
                    self._start_copy(scheduled=True)

        self.root.after(1000, self._check_schedule)


if __name__ == "__main__":
    window = tk.Tk()
    app = CopyScheduler(window)
    window.mainloop()