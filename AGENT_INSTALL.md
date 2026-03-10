# Kaleidoscope

Kaleidoscope is a project featuring a CLI tool (`op`) that helps manage, index, and serve content (such as ComfyUI outputs) through its integrated services.

Before starting this installation ask the user 

  * The path to their comfyui installation 
  * After the installation inform the user that 
    * a virtual env has been created 
    * the virtual env needs to be activated before `op start` is executed 

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

Once everything is configured, you can start the entire stack using `honcho` and the `Procfile`:

```bash
op start
```



