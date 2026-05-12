#!/usr/bin/env python3
"""Copy media files and spread their mtimes across a date range."""

from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path


MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".mp4"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy media files to an output folder with mtimes spread across N days."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Input file or directory containing media files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="Destination folder for copied media files.",
    )
    parser.add_argument(
        "--age",
        "-a",
        required=True,
        type=int,
        help="Number of days across which copied files should be distributed.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of files to copy. Defaults to 10.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively collect files when input is a directory.",
    )
    return parser.parse_args()


def collect_media_files(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in MEDIA_EXTENSIONS else []

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    iterator = input_path.rglob("*") if recursive else input_path.iterdir()
    files = [path for path in iterator if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS]
    return sorted(files, key=lambda path: path.name)


def timestamp_for_index(index: int, count: int, age_days: int, now: datetime) -> float:
    if count <= 1:
        target = now - timedelta(days=age_days)
    else:
        span_seconds = age_days * 24 * 60 * 60
        offset_seconds = span_seconds * (index / (count - 1))
        target = now - timedelta(seconds=span_seconds - offset_seconds)

    return target.timestamp()


def main() -> int:
    args = parse_args()

    if args.age < 0:
        raise ValueError("--age must be zero or greater")
    if args.limit < 1:
        raise ValueError("--limit must be one or greater")

    input_path = args.input.expanduser().resolve()
    output_dir = args.output.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_files = collect_media_files(input_path, args.recursive)[: args.limit]
    if not source_files:
        print(f"No media files found in {input_path}")
        return 1

    now = datetime.now()
    copied_files: list[tuple[Path, datetime]] = []

    for index, source in enumerate(source_files):
        destination = output_dir / source.name
        shutil.copy2(source, destination)

        timestamp = timestamp_for_index(index, len(source_files), args.age, now)
        # Update both atime and mtime. Linux ctime changes automatically and cannot be set.
        os.utime(destination, (timestamp, timestamp))
        copied_files.append((destination, datetime.fromtimestamp(timestamp)))

    print(f"Copied {len(copied_files)} file(s) to {output_dir}")
    for destination, timestamp in copied_files:
        print(f"{timestamp.isoformat(timespec='seconds')}  {destination}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
