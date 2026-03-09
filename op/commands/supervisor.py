import asyncio
import logging
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

import click

logger = logging.getLogger(__name__)

BASE_DIR = Path(".kaleidoscope")
LOGS_DIR = BASE_DIR / "logs"
PIDS_DIR = BASE_DIR / "pids"


@dataclass
class Component:
    name: str
    slot: int
    command: str
    optional: bool


COMPONENTS = [
    Component(name="search", slot=0, command="op serve search", optional=False),
    Component(name="indexer.legacy", slot=1, command="op serve indexer.legacy", optional=False),
    Component(name="kaleidoscope", slot=1, command="op serve kaleidoscope", optional=False),
    Component(name="kaleidoscope.ui", slot=2, command="op serve kaleidoscope.ui", optional=True),
]


def get_components_by_slot(slot: int):
    return [c for c in COMPONENTS if c.slot == slot]


def ensure_dirs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    PIDS_DIR.mkdir(parents=True, exist_ok=True)


def get_pid_path(component_name: str) -> Path:
    return PIDS_DIR / f"{component_name}.pid"


def get_log_path(component_name: str) -> Path:
    return LOGS_DIR / f"{component_name}.log"


def read_pid(pid_path: Path) -> int | None:
    if not pid_path.exists():
        return None
    try:
        return int(pid_path.read_text().strip())
    except (ValueError, IOError):
        return None


def write_pid(pid_path: Path, pid: int):
    pid_path.write_text(str(pid))


def delete_pid(pid_path: Path):
    if pid_path.exists():
        pid_path.unlink()


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


async def spawn_process(component: Component) -> asyncio.subprocess.Process | None:
    log_path = get_log_path(component.name)
    pid_path = get_pid_path(component.name)

    log_file = open(log_path, "w")

    try:
        proc = await asyncio.create_subprocess_shell(
            component.command,
            stdout=log_file,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.getcwd(),
        )
        write_pid(pid_path, proc.pid)
        logger.info(f"Started {component.name} with pid {proc.pid}")
        return proc
    except Exception as e:
        logger.error(f"Failed to start {component.name}: {e}")
        log_file.close()
        return None


async def monitor_process(
    component: Component, proc: asyncio.subprocess.Process, failure_event: asyncio.Event
):
    await proc.wait()

    if proc.returncode != 0:
        if component.optional:
            logger.warning(
                f"{component.name} died (exit code {proc.returncode}) - optional, continuing"
            )
        else:
            logger.error(f"{component.name} died (exit code {proc.returncode})")
            failure_event.set()


async def start_components():
    ensure_dirs()

    for comp in COMPONENTS:
        pid_path = get_pid_path(comp.name)
        existing_pid = read_pid(pid_path)
        if existing_pid and is_process_alive(existing_pid):
            logger.warning(f"{comp.name} already running with pid {existing_pid}, skipping")
        elif existing_pid:
            logger.info(f"Removing stale pid file for {comp.name}")
            delete_pid(pid_path)

    max_slot = max(c.slot for c in COMPONENTS)
    processes: dict[str, asyncio.subprocess.Process] = {}
    monitors: list[asyncio.Task] = []
    failure_event = asyncio.Event()

    for slot in range(max_slot + 1):
        components_in_slot = get_components_by_slot(slot)
        logger.info(f"Starting slot {slot}: {[c.name for c in components_in_slot]}")

        slot_procs = await asyncio.gather(*[spawn_process(c) for c in components_in_slot])

        for comp, proc in zip(components_in_slot, slot_procs):
            if proc:
                processes[comp.name] = proc
                monitor = asyncio.create_task(monitor_process(comp, proc, failure_event))
                monitors.append(monitor)

        await asyncio.sleep(1)

        if failure_event.is_set():
            logger.error(f"Failure detected in slot {slot}, shutting down")
            await shutdown_all(processes, monitors)
            sys.exit(1)

    click.echo("All components running — ctrl+c to stop", err=True)

    try:
        await asyncio.wait_for(failure_event.wait(), timeout=None)
    except asyncio.CancelledError:
        pass

    if failure_event.is_set():
        logger.error("A non-optional component died, shutting down")
        await shutdown_all(processes, monitors)
        sys.exit(1)


async def shutdown_all(
    processes: dict[str, asyncio.subprocess.Process], monitors: list[asyncio.Task]
):
    for monitor in monitors:
        monitor.cancel()

    if monitors:
        await asyncio.gather(*monitors, return_exceptions=True)

    for name, proc in processes.items():
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            click.echo(f"Stopped {name}", err=True)
        except Exception as e:
            logger.error(f"Error stopping {name}: {e}")

    for comp in COMPONENTS:
        delete_pid(get_pid_path(comp.name))


@click.group()
def supervisor():
    pass


@supervisor.command()
def start():
    asyncio.run(start_components())


@supervisor.command()
def stop():
    ensure_dirs()

    killed_any = False
    for comp in COMPONENTS:
        pid_path = get_pid_path(comp.name)
        pid = read_pid(pid_path)
        if pid is None:
            continue

        if is_process_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                click.echo(f"Sent SIGTERM to {comp.name} (pid {pid})")
                killed_any = True
            except ProcessLookupError:
                click.echo(f"Already stopped: {comp.name}")
        else:
            click.echo(f"Process not running: {comp.name}")

        delete_pid(pid_path)

    if not killed_any:
        click.echo("Nothing running", err=True)


@supervisor.command()
def status():
    ensure_dirs()

    found_any = False
    for comp in COMPONENTS:
        pid_path = get_pid_path(comp.name)
        pid = read_pid(pid_path)
        if pid is None:
            continue

        found_any = True
        if is_process_alive(pid):
            click.echo(f"● running  {comp.name} (pid {pid})", err=True)
        else:
            click.echo(f"● stopped  {comp.name} (stale pid file)", err=True)

    if not found_any:
        click.echo("Nothing running", err=True)


@supervisor.command()
@click.argument("component")
def logs(component):
    valid_names = [c.name for c in COMPONENTS]
    if component not in valid_names:
        click.echo(f"Unknown component: {component}", err=True)
        click.echo(f"Available: {', '.join(valid_names)}", err=True)
        raise SystemExit(1)

    log_path = get_log_path(component)
    if not log_path.exists():
        click.echo(f"Log file not found: {log_path}", err=True)
        available = [p.name for p in LOGS_DIR.glob("*.log")] if LOGS_DIR.exists() else []
        if available:
            click.echo(f"Available logs: {', '.join(available)}", err=True)
        raise SystemExit(1)

    click.echo(f"tail -f {log_path}", err=True)
