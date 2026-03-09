import os
import shutil
import subprocess
import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GitRepo:
    url: str
    branch: str
    path: str


def run_git_command(
    command: List[str], cwd: str, check: bool = True
) -> subprocess.CompletedProcess:
    logger.debug(f"Running git command: {' '.join(command)} in {cwd}")
    try:
        result = subprocess.run(command, cwd=cwd, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e.stderr}")
        raise


def prepare(repo_url: str, branch: str = "main", base_dir: str = "/tmp") -> GitRepo:
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    temp_dir = os.path.join(base_dir, f"{repo_name}_{branch}_{os.getpid()}")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    return GitRepo(url=repo_url, branch=branch, path=temp_dir)


def clone(repo: GitRepo) -> None:
    logger.info(f"Cloning {repo.url} (branch: {repo.branch}) into {repo.path}")
    run_git_command(
        ["git", "clone", "--branch", repo.branch, "--depth", "1", repo.url, "."], cwd=repo.path
    )


def commit(repo: GitRepo, message: str) -> None:
    logger.info(f"Committing changes in {repo.path}")
    run_git_command(["git", "add", "-A"], cwd=repo.path)

    status = run_git_command(["git", "status", "--porcelain"], cwd=repo.path)
    if not status.stdout.strip():
        logger.info("No changes to commit")
        return

    run_git_command(["git", "commit", "-m", message], cwd=repo.path)


def publish(repo: GitRepo) -> None:
    logger.info(f"Pushing changes to origin/{repo.branch}")
    run_git_command(["git", "push", "origin", repo.branch], cwd=repo.path)


def gc(repo: GitRepo) -> None:
    if os.path.exists(repo.path):
        logger.info(f"Cleaning up {repo.path}")
        shutil.rmtree(repo.path)
