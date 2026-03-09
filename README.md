# Kaleidoscope

Kaleidoscope is a project featuring a CLI tool (`op`) that helps manage, index, and serve content (such as ComfyUI outputs) through its integrated services.

## Prerequisites

- Python 3.10 or higher
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

3. **Install the package and dependencies:**
   With the virtual environment activated, install the project in editable mode:
   ```bash
   uv pip install -e .
   ```
   *(This will automatically install required dependencies and make the `op` command available globally in your environment).*

## Configuration

Before running the services, you must initialize and configure the `op` environment.

1. **Initialize the configuration file:**
   This will create a `.env` file in your root directory.
   ```bash
   op init
   ```

2. **Set the required configuration paths:**
   You need to define the paths to your local instances and repositories. Replace `.` with your actual absolute or relative paths as needed:
   ```bash
   op config set COMFYUI_INSTANCE_BASE_PATH .
   op config set COMFYUI_OUTPUT_PATH .
   op config set KALEIDESCOPE_REPO_PATH .
   ```

3. **Verify your configuration:**
   Check your current configuration values:
   ```bash
   op config show
   ```
   Validate that no required variables are missing:
   ```bash
   op config validate
   ```

## Running the Application

Once everything is configured, you can use the `serve` command to run different modules. 

To run the legacy indexer:
```bash
op serve indexer.legacy
```

To run the search module:
```bash
op serve search
```

## CLI Usage

The `op` CLI provides several other commands. You can explore them using the `--help` flag:
```bash
op --help
```

Available commands include:
- `init`: Initialize the environment configuration.
- `config`: Group of commands to view, set, or validate configuration variables.
- `serve`: Run a service module.
- `indexer`: Run indexing jobs.
- `ingest`: Ingest data into the system.
- `start` / `stop`: Manage background services.
- `supervisor`: Run the supervisor process.