import os
import glob
import json
import logging
from PIL import Image
from PIL.ExifTags import TAGS
from inotify_simple import INotify, flags
import datetime
import time
from .utils import hash_file, hash_json_data

logger = logging.getLogger(__name__)


def walk(path, limit=None):
    if limit is None:
        limit = -1
    files = []

    # Check if path contains glob patterns
    if "*" in path or "?" in path or "[" in path:
        # Handle glob pattern
        glob_paths = glob.glob(path, recursive=True)
        # print("Walking:")
        # for p in glob_paths:
        #     print(f"  * {p}")
        paths = glob_paths
    else:
        # Handle single path as before
        paths = [path]
        # print("Walking:")
        # print(f"  * {path}")

    while len(paths) > 0:
        path = paths.pop()
        if os.path.isdir(path):
            try:
                for f in os.listdir(path):
                    f = f"{path}/{f}"
                    if os.path.isdir(f):
                        paths.append(f)
                    if os.path.isfile(f):
                        yield f
            except PermissionError as e:
                logger.warning(f"Permission denied: {path}")
        elif os.path.isfile(path):
            yield path


def get_folders_updated_last_week(path):
    """Get folders that have been updated in the last 7 days."""
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    folders = []
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                creation_time = datetime.date.fromtimestamp(os.path.getctime(item_path))
                if creation_time >= week_ago:
                    folders.append(item_path)
    except OSError:
        pass
    return folders


def get_all_child_folders(path):
    paths = []
    if "*" in path or "?" in path or "[" in path:
        # Handle glob pattern
        glob_paths = glob.glob(path, recursive=True)
        paths = glob_paths
    else:
        # Handle single path as before
        paths = [path]
    folders = []
    folders.extend(paths)

    for p in paths:
        try:
            if os.path.isdir(p):
                for item in os.listdir(p):
                    item_path = os.path.join(p, item)
                    if os.path.isdir(item_path):
                        folders.append(item_path)
        except OSError:
            pass
    return folders


def read_png_metadata(file_path):
    """
    Read PNG metadata from a file and return it in a structured format.

    Args:
        file_path (str): Path to the PNG file

    Returns:
        dict: Dictionary with "_id" (file hash) and "data" (metadata entries)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PNG file not found: {file_path}")

    # Get file hash as ID
    file_id = hash_file(file_path)

    # Open the image and extract metadata
    try:
        with Image.open(file_path) as img:
            # Get basic image info
            metadata = {
                "filename": os.path.basename(file_path),
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
            }

            # Extract EXIF data if available
            if hasattr(img, "_getexif") and img._getexif() is not None:
                exif_data = img._getexif()
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    metadata[f"exif_{tag}"] = value

            # Extract PNG text chunks (metadata specific to PNG format)
            if hasattr(img, "text") and img.text:
                for key, value in img.text.items():
                    metadata[f"png_{key.lower()}"] = value

            # Extract PNG info dictionary
            if hasattr(img, "info") and img.info:
                for key, value in img.info.items():
                    if key not in metadata:  # Avoid duplicates
                        metadata[f"info_{key.lower()}"] = value

    except Exception as e:
        # If we can't process the image, at least return basic file info
        metadata = {"filename": os.path.basename(file_path), "error": str(e)}

    # Create a unique ID for this metadata entry
    metadata_id = hash_json_data(metadata)
    metadata["_id"] = f"{file_id}_{metadata_id}"

    # Return in the same format as other read functions
    return {
        "_id": file_id,
        "data": metadata,  # Wrap in a list to match the expected format
    }


def watch_pngs(watch_path, limit=100, skip_count=-1):
    count = 0
    inotify = INotify()
    watchers = {}

    if "*" in watch_path or "?" in watch_path or "[" in watch_path:
        # Handle glob pattern
        glob_paths = glob.glob(watch_path, recursive=True)
        paths = glob_paths
    else:
        # Handle single path
        paths = [watch_path]

    folders_to_add = []

    for path in paths:
        try:
            wd = inotify.add_watch(path, flags.CREATE | flags.MOVED_TO)
            watchers[wd] = path
            folders_to_add.extend(get_all_child_folders(path))
        except OSError as e:
            logger.error(f"Failed to watch {path}: {e}")

    while len(folders_to_add) > 0:
        path = folders_to_add.pop()
        try:
            wd = inotify.add_watch(path, flags.CREATE | flags.MOVED_TO)
            watchers[wd] = path
            # logger.info(f" * is folder - adding to watch : {path}")
            folders_to_add.extend(get_folders_updated_last_week(path))
        except OSError:
            pass  # Ignore permission errors etc

    logger.info(f"Watching {len(watchers)} folders")

    while True:
        if limit is not None and count >= limit:
            break

        events = inotify.read()
        files = []

        for e in events:
            if e.wd not in watchers:
                continue

            watch_path = watchers[e.wd]
            f_name = os.path.join(watch_path, e.name)

            if os.path.isdir(f_name):
                # logger.info(f" * is folder - adding to watch : {f_name}")
                try:
                    wd = inotify.add_watch(f_name, flags.CREATE | flags.MOVED_TO)
                    watchers[wd] = f_name
                except OSError:
                    pass
                continue

            if e.name.lower().endswith(".png"):
                files.append(f_name)

        if files:
            # logger.info(f"Yields {len(files)} new files")
            time.sleep(1)  # Wait for file write to complete

            for f in files:
                try:
                    print(f"DEBUG: Watcher Discovered: {os.path.abspath(f)}")
                    yield (read_png_metadata(f), f)
                    count += 1
                except Exception as e:
                    logger.error(f"Error processing {f}: {e}")


def get_all_pngs(start_path, limit=None, skip_count=-1, watch=False):
    count = 0
    if skip_count is None:
        skip_count = -1

    for f in walk(start_path, limit):
        if not f.lower().endswith(".png"):
            continue

        if skip_count >= 0:
            skip_count = skip_count - 1
            continue
        try:
            yield (read_png_metadata(f), f)
            count = count + 1
        except Exception as e:
            logger.error(f"{e} : {f}")

        if limit is not None:
            limit = limit - 1
            if limit == 0:
                break


def get_pngs(start_path, limit=None, skip_count=-1, watch=False):
    if watch:
        return watch_pngs(start_path, limit=limit, skip_count=skip_count)
    return get_all_pngs(start_path, limit=limit, skip_count=skip_count, watch=False)
