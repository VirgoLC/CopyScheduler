# CopyScheduler

A lightweight Windows desktop app for copying files and folders manually or on a schedule.

## About

I created CopyScheduler for my own use. This is my first programming project, and I’m still learning. I used AI extensively during development, and much of the code was generated or adapted with AI assistance, I don’t claim to have written every line myself.

The app may contain bugs or rough edges. Feedback and bug reports are welcome.

## Features

- Copy individual files or folders.
- Schedule copies every day, on selected weekdays, or on a specific date.
- Browse for source and destination paths.
- Track copy progress and view activity in the log.
- Choose whether existing destination items should be replaced.

> **Note:** CopyScheduler must remain open for scheduled copies to run.

## Download

Download the latest `CopyScheduler.exe` from the [Releases](https://github.com/VirgoLC/CopyScheduler/releases) page.

## Run from source

Requires Windows and Python 3.

```powershell
py "copy_scheduler.py"
```

The app uses Python’s standard library, including Tkinter.

## Build the executable

Install PyInstaller:

```powershell
py -m pip install pyinstaller
```

From the project folder, run:

```powershell
py -m PyInstaller --noconfirm --clean --onefile --windowed --name CopyScheduler --icon "app.ico" --add-data "app.ico;." --add-data "app.png;." "copy_scheduler.py"
```

The executable will be created at `dist\CopyScheduler.exe`.

## License

This project is licensed under the GNU Affero General Public License v3.0. See [`LICENSE`](LICENSE) for details.