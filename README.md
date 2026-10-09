# CopyScheduler

CopyScheduler is a small Windows desktop application for copying files and folders manually or on a schedule.

## About

This is my first project, and I am still learning how to build and improve software. I originally made CopyScheduler for my own use. It may contain bugs or rough edges, so feedback and bug reports are welcome.

## Features

- Copy files and folders with a progress indicator.
- Schedule copies daily, on selected weekdays, or on a specific date.
- Browse for source and destination paths.
- View copy activity and errors in the application log.
- Choose whether existing destination items should be replaced.

The application must remain open for scheduled copies to run.

## Run from source

On Windows, install Python and run:

```powershell
py "python copy_scheduler.py"
```

## Build the executable

Install PyInstaller:

```powershell
py -m pip install pyinstaller
```

From the project folder, build the executable:

```powershell
py -m PyInstaller --noconfirm --clean --onefile --windowed --name CopyScheduler --icon "app.ico" --add-data "app.ico;." --add-data "app.png;." "python copy_scheduler.py"
```

The executable will be created at `dist\CopyScheduler.exe`.

## Project files

- `python copy_scheduler.py` — application source code.
- `app.ico` — application icon.
- `app.png` — image shown in the About window.

## Feedback

Please open an issue if you find a bug or have a suggestion. Since this is my first project, constructive feedback is appreciated.
