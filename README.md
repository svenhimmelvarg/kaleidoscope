# Kaleidoscope

Kaleidoscope is a project featuring a CLI tool (`op`) that helps manage, index, and serve content (such as ComfyUI outputs) through its integrated services.

## Prerequisites

- Python 3.8 or higher
- Git
- [uv](https://github.com/astral-sh/uv) (An extremely fast Python package and project manager)

## Installation

1. **Clone the repository:**
   ```bash
   git clone git@github.com:svenhimmelvarg/kaleidoscope.git
   cd kaleidoscope
   ```

2. **Create and activate a virtual environment using `uv`:**
   ```bash
   uv venv
   
   # On macOS/Linux:
   source .venv/bin/activate
   
   # On Windows:
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   With the virtual environment activated, install the required packages using `uv pip`:
   ```bash
   uv pip install click python-dotenv requests rich Pillow inotify_simple
   ```

## Configuration

Before running the services, you must initialize and configure the `op` environment.

1. **Initialize the configuration file:**
   This will create a `.env` file in your root directory.
   ```bash
   python -m op init
   ```

2. **Set the required configuration paths:**
   You need to define the paths to your local instances and repositories. Replace `.` with your actual absolute or relative paths as needed:
   ```bash
   python -m op config set COMFYUI_INSTANCE_BASE_PATH .
   python -m op config set COMFYUI_OUTPUT_PATH .
   python -m op config set KALEIDESCOPE_REPO_PATH .
   ```

3. **Verify your configuration:**
   Check your current configuration values:
   ```bash
   python -m op config show
   ```
   Validate that no required variables are missing:
   ```bash
   python -m op config validate
   ```

## Running the Application

Once everything is configured, you can use the `serve` command to run different modules. 

To run the legacy indexer:
```bash
python -m op serve indexer.legacy
```

To run the search module:
```bash
python -m op serve search
```

## CLI Usage

The `op` CLI provides several other commands. You can explore them using the `--help` flag:
```bash
python -m op --help
```

Available commands include:
- `init`: Initialize the environment configuration.
- `config`: Group of commands to view, set, or validate configuration variables.
- `serve`: Run a service module.
- `indexer`: Run indexing jobs.
- `ingest`: Ingest data into the system.
- `start` / `stop`: Manage background services.
- `supervisor`: Run the supervisor process.
