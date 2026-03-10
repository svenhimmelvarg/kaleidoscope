import os
import glob
import logging
from PIL import Image
from PIL.ExifTags import TAGS
import queue
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
import time
from .utils import hash_file, hash_json_data

logger = logging.getLogger(__name__)


def walk(path, limit=None):
    if limit is None:
        limit = -1

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
            except PermissionError:
                logger.warning(f"Permission denied: {path}")
        elif os.path.isfile(path):
            yield path


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


class PngHandler(FileSystemEventHandler):
    def __init__(self, file_queue):
        self.file_queue = file_queue

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".png"):
            self.file_queue.put(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".png"):
            self.file_queue.put(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and event.dest_path.lower().endswith(".png"):
            self.file_queue.put(event.dest_path)


def watch_pngs(watch_path, limit=100, skip_count=-1):
    count = 0
    path = watch_path
    if "*" in path or "?" in path or "[" in path:
        glob_paths = glob.glob(path, recursive=True)
        paths = glob_paths
    else:
        paths = [path]

    file_queue = queue.Queue()
    event_handler = PngHandler(file_queue)

    try:
        observer = Observer()
    except Exception:
        observer = PollingObserver()

    watchers = 0
    for p in paths:
        if os.path.isdir(p):
            observer.schedule(event_handler, path=p, recursive=True)
            watchers += 1
            # logger.info(f" * is folder - adding to watch : {p}")
        else:
            dir_path = os.path.dirname(p)
            if dir_path and os.path.isdir(dir_path):
                observer.schedule(event_handler, path=dir_path, recursive=False)
                watchers += 1
                # logger.info(f" * is file dir - adding to watch : {dir_path}")

    logger.info(f"Watching {watchers} folders")
    observer.start()

    processed_files = set()

    try:
        while True:
            if limit is not None and count >= limit:
                break

            try:
                # We use a non-blocking get to not hang forever if empty,
                # but wait 1s so we don't spin CPU too hard
                f_name = file_queue.get(timeout=1.0)

                if f_name not in processed_files:
                    time.sleep(1)  # Wait for file write to complete
                    try:
                        print(f"DEBUG: Watcher Discovered: {os.path.abspath(f_name)}")
                        yield (read_png_metadata(f_name), f_name)
                        count += 1
                        processed_files.add(f_name)
                    except Exception as e:
                        logger.error(f"Error processing {f_name}: {e}")
            except queue.Empty:
                pass
    finally:
        observer.stop()
        observer.join()


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
