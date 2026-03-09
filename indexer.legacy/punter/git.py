from pathlib import Path
import re
import shutil
from datetime import datetime
import subprocess
import os
from dotenv import load_dotenv
from .data import _t


def gc(repo) -> None:
    workspace_path = Path(repo.path)
    if not workspace_path.exists():
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    trash_base = Path("trash") / repo.host / repo.repository
    trash_path = trash_base / f"{repo.branch}.{timestamp}"

    trash_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(workspace_path), str(trash_path))

    print(f"punter.git.gc - moved to {trash_path}")


def prepare(repository: str, branch: str = "main", host: str = None) -> tuple:
    repository = repository.strip()
    repo_path = _parse_repository_url(repository, host)

    workspace_path = Path("workspace") / repo_path.host / repo_path.repository / branch

    if workspace_path.exists():
        repo = _t(
            host=repo_path.host,
            repository=repo_path.repository,
            branch=branch,
            path=str(workspace_path),
            remote=repo_path.remote,
        )
        gc(repo)

    workspace_path.mkdir(parents=True, exist_ok=True)

    return _t(
        host=repo_path.host,
        repository=repo_path.repository,
        branch=branch,
        path=str(workspace_path),
        remote=repo_path.remote,
    )


def _parse_repository_url(repository: str, host: str = None) -> tuple:
    ssh_match = re.match(r"git@([^:]+):(.+)\.git$", repository)
    if ssh_match:
        extracted_host = ssh_match.group(1)
        extracted_repo = ssh_match.group(2).replace(".git", "")
        if extracted_host == "localhost":
            extracted_host = "local"
        return _t(host=extracted_host, repository=extracted_repo, remote=repository)

    https_match = re.match(r"https?://([^/]+)/(.+)\.git$", repository)
    if https_match:
        extracted_host = https_match.group(1)
        extracted_repo = https_match.group(2).replace(".git", "")
        return _t(host=extracted_host, repository=extracted_repo, remote=repository)

    local_path = Path(repository)
    if local_path.is_absolute():
        safe_name = local_path.name.replace(".git", "")
        return _t(host="local", repository=safe_name, remote=str(local_path))

    if str(local_path).startswith("."):
        safe_name = local_path.resolve().name.replace(".git", "")
        return _t(host="local", repository=safe_name, remote=str(local_path.resolve()))

    return _t(host=host or "local", repository=str(repository), remote=repository)


def clone(repo) -> None:
    subprocess.run(
        ["git", "clone", repo.remote, "."],
        cwd=repo.path,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "checkout", repo.branch], cwd=repo.path, capture_output=True, text=True
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "checkout", "-b", repo.branch],
            cwd=repo.path,
            check=True,
            capture_output=True,
        )


def commit(repo, file_list: list[str], comment: str, git_subfolder: str = None) -> None:
    # Check for uncommitted changes (excluding untracked files)
    status_result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo.path,
        capture_output=True,
        text=True,
    )
    print(
        "git status --porcelain --untracked-files=all -->", status_result.stdout.strip()
    )
    # Filter out untracked files (?? prefix) - only fail on modified/staged/tracked changes
    clean_status = "\n".join(
        line
        for line in status_result.stdout.strip().split("\n")
        if line and not line.startswith("?? ")
    )
    print("commit::", status_result, clean_status)
    if clean_status.strip():
        raise ValueError(
            f"Uncommitted changes exist in workspace. Commit or discard them first. --- {clean_status.strip()}"
        )

    # First copy files to workspace
    files_to_add = []
    for file_path in file_list:
        src = Path(file_path)
        if git_subfolder:
            rel_path = Path(git_subfolder) / src.name
            dst = Path(repo.path) / rel_path
            os.makedirs(Path(repo.path) / git_subfolder, exist_ok=True)
        else:
            rel_path = src.name
            dst = Path(repo.path) / src.name
        if src.is_dir():
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        else:
            shutil.copy2(str(src), str(dst))
        files_to_add.append(rel_path)

    print(f" * {files_to_add}")

    result = subprocess.run(
        ["git", "status"],
        cwd=repo.path,
        capture_output=True,
        text=True,
    )   
    print(f"status::getting ready for loop ({files_to_add})", result.stdout ) 
    for file_to_add in files_to_add:
        
        result = subprocess.run(
            ["git", "add", str(file_to_add)],
            cwd=repo.path,
            capture_output=True,
            text=True,
        )
        print(f"status:: ({file_to_add})", result.stdout ) 
        print(f" * Adding  {str(file_to_add)} - returncode: {result.returncode}")
        if result.returncode != 0:
            print(f"git add stderr: {result.stderr}")
        result = subprocess.run(
            ["git", "commit", "-m", comment],
            cwd=repo.path,
            capture_output=True,
            text=True,
        )
        print(f" * Committing  {str(file_to_add)} - returncode: {result.returncode} ,{result.stdout}")
        # if result.returncode != 0:
        #     print(f"git commit stderr: {result.stderr}")
        #     raise ValueError(
        #         f"Git commit failed with code {result.returncode}: {result.stderr}"
        #     )


def publish(repo) -> None:
    load_dotenv()

    github_user = os.getenv("GITHUB_USER")
    github_token = os.getenv("GITHUB_API_KEY")

    if not github_user or not github_token:
        raise ValueError(
            "Missing credentials in .env. Required: GITHUB_USER and GITHUB_API_KEY. "
            "Note: SSH authentication will not require these fields."
        )

    remote = f"https://{github_user}:{github_token}@{repo.host}/{repo.repository}.git"

    subprocess.run(
        ["git", "remote", "set-url", "origin", remote],
        cwd=repo.path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", repo.branch],
        cwd=repo.path,
        check=True,
        capture_output=True,
    )


def _build_remote_url(host: str, repository: str) -> str:
    if host == "local":
        if (
            repository.startswith("/")
            or repository.startswith("./")
            or repository.startswith("../")
        ):
            return f"file://{repository}"
        return f"git@localhost:{repository}.git"
    return f"git@{host}:{repository}.git"
