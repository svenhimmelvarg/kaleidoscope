# Kaleidoscope

Kaleidoscope is a project featuring a CLI tool (`op`) that helps manage, index, and serve content (such as ComfyUI outputs) through its integrated services.

## Prerequisites

- Python 3.10 or higher
- Git
- [uv](https://github.com/astral-sh/uv) (An extremely fast Python package and project manager)

## Installation

```bash
git clone git@github.com:svenhimmelvarg/kaleidoscope.git
cd kaleidoscope
./install.sh
```

*Note: The installation script will automatically set up your virtual environment, install dependencies, initialize the configuration, and prompt you for the path to your ComfyUI instance.*

## Running the Application

Once installation is complete, you must activate the virtual environment before starting the stack:

```bash
source .venv/bin/activate
op start
```
