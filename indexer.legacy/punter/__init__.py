def deref(data, k):
    parts = k.split(".")
    current = data
    for el in parts:
        if el not in current:
            return None
        current = current[el]
    return current


import re


def deref2(data, k):
    def regex_match_keys(pattern, snippet):
        for k in snippet.keys():
            # print(k,pattern, re.match(pattern, k, re.IGNORECASE) is not None)
            m = re.search(pattern, k, re.IGNORECASE)
            if m is not None:
                return k
        return None

    parts = k.split(".")
    current = data
    for el in parts:
        # if el not in current:
        m = regex_match_keys(el, current)
        if m is None:
            return None

        el = m
        current = current[el]
    return current


def apply_transform(key, spec, data, ignore_errors=[]):
    (fn, output_key) = spec

    datum = deref2(data, key)

    if datum is None and key in ignore_errors:
        datum = {"message": "Not Available"}
        # fn = lambda d,ctx :  {"message": "Not Available"}

        print(
            f"Skipping {data['_id']} because {key} returns no value ",
            data["data"].keys(),
        )
        print(
            f"{key}: Falling back to  { {output_key: _(datum=datum, ctx=data)} }, {data['data']['filename']} "
        )

    elif datum is None:
        print(
            f"Skipping {data['_id']} because {key} returns no value ",
            data["data"].keys(),
        )
        raise Exception(f"key: {key} - {cache_context(data['_id'])}")

    entries = cache_context(data["_id"])
    data["cache._id"] = data["_id"]
    data["cache.entries"] = entries
    data["cache.key"] = key
    data["cache.output_key"] = output_key
    return {output_key: fn(datum, ctx=data)}


__PIPELINE_CONTEXT__ = {"transforms": []}
__PIPELINE_CACHE_NAME__ = "default"
__DATA_DIR__ = None  # Will be initialized from config or set via set_data_dir()


def set_data_dir(data_dir):
    global __DATA_DIR__
    __DATA_DIR__ = data_dir


def get_data_dir():
    global __DATA_DIR__
    if __DATA_DIR__ is None:
        # Lazy initialization from config if not explicitly set
        config = dotenv_values(".env")
        __DATA_DIR__ = config.get("DATA_DIR", "./data")
    return __DATA_DIR__


def set_transforms(transforms):
    __PIPELINE_CONTEXT__["transforms"] = transforms


def set_cache_name(name):
    global __PIPELINE_CACHE_NAME__
    __PIPELINE_CACHE_NAME__ = name


def get_cache_name():
    return __PIPELINE_CACHE_NAME__


def transform(doc, ignore_errors=[]):
    output = {}
    transforms = __PIPELINE_CONTEXT__["transforms"]
    for t in transforms:
        (source_key, spec) = t
        output.update(apply_transform(source_key, spec, doc, ignore_errors))
    return output


import os
from dotenv import dotenv_values

config = dotenv_values(".env")


def cache_folder(unique_id):
    folder = f"{get_data_dir()}/output/{get_cache_name()}/{unique_id}"
    os.makedirs(folder, exist_ok=True)
    return folder


def cache_exists(unique_id, key):
    folder = cache_folder(unique_id)
    f_name = f"{folder}/{key}"
    if os.path.exists(f_name):
        return True
    return False


def cache_context(unique_id):
    context = {"_id": unique_id}
    # print(cache_folder(unique_id))
    context["entries"] = list(os.listdir(cache_folder(unique_id)))
    return context


def cache_write(unique_id, key, data, file_type=None):
    if type(data) == dict and (file_type is None or file_type == "json"):
        file_type = "json"
        ret_data = json.dumps(data)
        data = ret_data

    folder = cache_folder(unique_id)
    f_name = f"{folder}/{key}"
    open(f_name, "w").write(data)
    return f_name


def cache_get(unique_id, key, file_type=None):
    folder = cache_folder(unique_id)
    f_name = f"{folder}/{key}"
    data = open(f_name).read()

    if file_type is None or file_type == "json":
        file_type = "json"
        # print(" * cache_get:",f_name)
        ret_data = json.loads(data)
        data = ret_data
        return data

    return data


import glob


def walk(path, limit=None):
    if limit is None:
        limit = -1
    files = []

    # Check if path contains glob patterns
    if "*" in path or "?" in path or "[" in path:
        # Handle glob pattern
        glob_paths = glob.glob(path, recursive=True)
        print("Walking:")
        for p in glob_paths:
            print(f"  * {p}")
        paths = glob_paths
    else:
        # Handle single path as before
        paths = [path]
        print("Walking:")
        print(f"  * {path}")

    while len(paths) > 0:
        path = paths.pop()
        if os.path.isdir(path):
            for f in os.listdir(path):
                f = f"{path}/{f}"
                if os.path.isdir(f):
                    paths.append(f)
                if os.path.isfile(f):
                    yield f
        elif os.path.isfile(path):
            yield path


import os
import datetime
import time
import queue
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler


def _(**kwargs):
    return kwargs


class MediaHandler(FileSystemEventHandler):
    def __init__(self, file_queue):
        self.file_queue = file_queue

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith((".png", ".mp4")):
            self.file_queue.put(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.lower().endswith((".png", ".mp4")):
            self.file_queue.put(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and event.dest_path.lower().endswith((".png", ".mp4")):
            self.file_queue.put(event.dest_path)


def watch_media(watch_path, limit=100, skip_count=-1):
    count = 0
    path = watch_path
    if "*" in path or "?" in path or "[" in path:
        glob_paths = glob.glob(path, recursive=True)
        print("Walking:")
        for p in glob_paths:
            print(f"  * {p}")
        paths = glob_paths
    else:
        paths = [path]
        print("Walking:")
        print(f"  * {path}")

    file_queue = queue.Queue()
    event_handler = MediaHandler(file_queue)

    try:
        observer = Observer()
    except Exception:
        observer = PollingObserver()

    for p in paths:
        if os.path.isdir(p):
            observer.schedule(event_handler, path=p, recursive=True)
            print(f" * is folder - adding to watch : {p}")
        else:
            dir_path = os.path.dirname(p)
            if dir_path and os.path.isdir(dir_path):
                observer.schedule(event_handler, path=dir_path, recursive=False)
                print(f" * is file dir - adding to watch : {dir_path}")

    observer.start()
    print("Watch List started.")

    pending_files = {}  # path -> first_seen_time
    processed_files = set()

    try:
        while count < limit:
            # 1. Process anything in the queue
            try:
                # We use a non-blocking get to not hang forever if empty,
                # but wait 0.5s so we don't spin CPU too hard
                f_name = file_queue.get(timeout=0.5)

                if f_name not in processed_files:
                    if f_name not in pending_files:
                        pending_files[f_name] = time.time()
                        print(f"[DEBUG] '{f_name}' added to pending_files (first seen).")

                    try:
                        metadata_result = read_media_metadata(f_name)
                        data = metadata_result.get("data", {})

                        # Fast path: Check if metadata injected by kaleidoscope exists
                        has_meta = (
                            "png_parent_id" in data
                            or "png_elapsed_ms" in data
                            or "info_parent_id" in data
                            or "info_elapsed_ms" in data
                        )

                        if has_meta:
                            print(
                                f"[DEBUG] '{f_name}' hit fast-path! Metadata found. Yielding immediately."
                            )
                            yield (metadata_result, f_name)
                            count += 1
                            processed_files.add(f_name)
                            if f_name in pending_files:
                                del pending_files[f_name]
                    except Exception as e:
                        print(f"Error reading metadata for {f_name} on fast-path: {e}")
            except queue.Empty:
                pass

            # 2. Flush pending files older than 10 seconds
            current_time = time.time()
            to_flush = []
            for f_name, first_seen in pending_files.items():
                if current_time - first_seen >= 10.0:
                    to_flush.append(f_name)
                    print(f"[DEBUG] '{f_name}' reached 10s timeout. Adding to flush queue.")

            for f_name in to_flush:
                if f_name not in processed_files:
                    try:
                        metadata_result = read_media_metadata(f_name)
                        data = metadata_result.get("data", {})
                        has_meta = (
                            "png_parent_id" in data
                            or "png_elapsed_ms" in data
                            or "info_parent_id" in data
                            or "info_elapsed_ms" in data
                        )

                        meta_status = (
                            "WITH kaleidoscope metadata"
                            if has_meta
                            else "WITHOUT kaleidoscope metadata"
                        )
                        print(
                            f"[DEBUG] '{f_name}' being processed by slow-path flush. Yielding {meta_status}."
                        )

                        yield (metadata_result, f_name)
                        count += 1
                        processed_files.add(f_name)
                    except Exception as e:
                        print(f"Error processing {f_name} on slow-path flush: {e}")
                del pending_files[f_name]

    finally:
        observer.stop()
        observer.join()


def get_media(start_path, limit=None, skip_count=-1, watch=False):
    if watch:
        return watch_media(start_path, limit=limit, skip_count=skip_count)
    return get_all_media(start_path, limit=limit, skip_count=-1, watch=True)


def get_all_media(start_path, limit=None, skip_count=-1, watch=True):
    count = 0
    if skip_count is None:
        skip_count = -1
    for f in walk(start_path, limit):
        if skip_count >= 0:
            skip_count = skip_count - 1
            continue
        if not f.lower().endswith((".png", ".mp4")):
            continue
        try:
            yield (read_media_metadata(f), f)
            count = count + 1
        except Exception as e:
            print(f"{e} : {f} : {limit}")
        limit = limit - 1
        if limit == 0:
            break

    print(skip_count, limit)


import json


def hash_file(f_name):
    import io, hashlib, hmac

    digest = None
    with open(f_name, "rb") as f:
        h = hashlib.new("sha256")
        h.update(f.read())
        digest = h.hexdigest()
    return digest


def hash_binary_data(data):
    import io, hashlib, hmac

    h = hashlib.new("sha256")
    h.update(data)
    digest = h.hexdigest()
    return digest


def hash_json_data(data):
    import io, hashlib, hmac

    h = hashlib.new("sha256")
    h.update(json.dumps(data).encode("utf-8"))
    digest = h.hexdigest()
    return digest


def read_jsonl(f_name, limit=None):
    results = []
    if limit is None:
        limit = -1
    _id = hash_file(f_name)
    with open(f_name) as f:
        for line in f:
            datum = json.loads(line)
            datum_id = hash_json_data(datum)
            datum.update({"_id": f"{_id}_{datum_id}"})
            results.append(datum)
            limit = limit - 1
            if limit == 0:
                break

    return {"_id": _id, "data": results}


def read_json_folder(folder):
    results = []
    for f in os.listdir(folder):
        results.append(
            json.loads(
                open(
                    f"{folder}/{f}",
                ).read()
            )
        )
    return results


def read_mp4_metadata(file_path):
    import os
    import subprocess
    import json

    file_id = hash_file(file_path)
    metadata = {
        "filename": os.path.basename(file_path),
        "format": "mp4",
    }

    try:
        # Use ffprobe to extract format tags
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(result.stdout)

        tags = probe_data.get("format", {}).get("tags", {})

        # Add tags mapping them similarly to PNG text chunks
        for key, value in tags.items():
            metadata[f"png_{key.lower()}"] = value

        # Add basic info
        if "streams" in probe_data:
            for stream in probe_data["streams"]:
                if stream.get("codec_type") == "video":
                    metadata["size"] = (stream.get("width", 0), stream.get("height", 0))
                    break

    except Exception as e:
        metadata["error"] = str(e)

    metadata_id = hash_json_data(metadata)
    metadata["_id"] = f"{file_id}_{metadata_id}"

    return {
        "_id": file_id,
        "data": metadata,
    }


def read_media_metadata(file_path):
    """
    Read media metadata from a file (PNG or MP4) and return it in a structured format.
    """
    if str(file_path).lower().endswith(".mp4"):
        return read_mp4_metadata(file_path)

    from PIL import Image
    from PIL.ExifTags import TAGS
    import os

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")

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
