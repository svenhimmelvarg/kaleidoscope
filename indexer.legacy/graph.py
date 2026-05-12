from __future__ import annotations
from graph import *
from typing import List
import argparse
import json
import requests
import os
import datetime
from math import gcd
from PIL import Image
from dotenv import dotenv_values
import subprocess
from functools import lru_cache
import base64

_model = None
_nlp = None





def is_experimental_indexing_enabled():
    try:
        release_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "release.json")
        with open(release_path, "r") as f:
            data = json.load(f)
            return data.get("experimental.indexing", {}).get("defaultValue", False)
    except Exception:
        return False

env_file = os.environ.get("OP_ENV_FILE", ".env")
config = dotenv_values(env_file)


def print_config_banner(args=None):
    convex_url = config.get("VITE_CONVEX_URL", "not set")
    index_name = config.get("INDEX_NAME", "not set")
    data_dir = config.get("DATA_DIR", "not set")
    meilisearch_url = config.get("VITE_MEILISEARCH_HOST", "not set")

    # Show effective values (CLI overrides take precedence)
    if args:
        effective_index_name = args.indexer_name or index_name
        effective_meilisearch_url = args.indexer_host or meilisearch_url
        effective_data_dir = args.data_dir or data_dir

        # Mark overridden values with (override)
        index_display = f"{effective_index_name}"
        if args.indexer_name:
            index_display = f"{effective_index_name} (override)"

        meili_display = f"{effective_meilisearch_url}"
        if args.indexer_host:
            meili_display = f"{effective_meilisearch_url} (override)"

        data_display = f"{effective_data_dir}"
        if args.data_dir:
            data_display = f"{effective_data_dir} (override)"
    else:
        index_display = index_name
        meili_display = meilisearch_url
        data_display = data_dir

    banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║                     graph.py Configuration                       ║
╠══════════════════════════════════════════════════════════════════╣
║  VITE_CONVEX_URL:    {convex_url:<42}║
║  INDEX_NAME:         {index_display:<42}║
║  DATA_DIR:           {data_display:<42}║
║  VITE_MEILISEARCH_HOST: {meili_display:<39}║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


from punter import *
from punter.data import *
import punter


def create_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input json array")
    parser.add_argument("--overwrite", help="overwrites existing files")
    parser.add_argument("--skip-cache-hits", help="overwrites existing files")
    parser.add_argument("--skip-transforms", action="store_true", help="skips transforms and sink for already indexed files")
    parser.add_argument("--refresh-index", action="store_true", help="reads from cache instead of filesystem, ordered newest to oldest")
    parser.add_argument("--watch", help="watch folder")
    parser.add_argument("--limit", help="limit number of records to process", default=None)
    parser.add_argument(
        "--indexer.host",
        dest="indexer_host",
        help="Meilisearch host override (e.g., localhost:7700)",
        default=None,
    )
    parser.add_argument(
        "--indexer.name",
        dest="indexer_name",
        help="Meilisearch index name override",
        default=None,
    )
    parser.add_argument(
        "--data_dir",
        dest="data_dir",
        help="Data directory override",
        default=None,
    )
    args = parser.parse_args()
    return args


args = create_arguments()

# Calculate effective configuration values
effective_data_dir = args.data_dir or config.get("DATA_DIR", "./data")

index_name_from_config = config.get("INDEX_NAME")
effective_index_name = args.indexer_name or index_name_from_config
if is_experimental_indexing_enabled():
    effective_index_name = f"{effective_index_name}_ENHANCED"

if not effective_index_name:
    raise ValueError(
        "INDEX_NAME is required. Please provide it via --indexer.name or in your .env file."
    )


# Set up data directory in punter and create directory structure
punter.set_data_dir(effective_data_dir)
os.makedirs(f"{effective_data_dir}/{effective_index_name}", exist_ok=True)

print_config_banner(args)


def log(prefix, msg):
    print(f"{prefix} {msg}")


def fn_write_workflow_json(data, ctx):
    # Get the file path where we'll write the workflow JSON
    f_name = f"{cache_folder(ctx['_id'])}/{ctx['cache.output_key']}"
    try:
        data = json.loads(data)
    except Exception as e:
        return {"fn_write_workflow": {"error": str(e)}}
    # Handle different data types properly
    if isinstance(data, dict):
        # Parse the graph and get topological order
        g = parse_graph(data)

        order = topological_order(g)

        # Create a copy of the data to modify
        ordered_data = data.copy()

        # If the data has a "nodes" field, order it according to the topological order
        if "nodes" in ordered_data and isinstance(ordered_data["nodes"], list):
            # Create a mapping of node id to node object for quick lookup
            node_map = {node["id"]: node for node in ordered_data["nodes"]}

            # Reorder the nodes array based on the topological order
            ordered_nodes = []
            for node_id_str in order:
                node_id = int(node_id_str)  # Convert string id to int
                if node_id in node_map:
                    ordered_nodes.append(node_map[node_id])
            # Update the nodes field with the ordered list
            ordered_data["nodes"] = ordered_nodes

        json_data = ordered_data
        data_str = json.dumps(ordered_data, indent=2)  # Pretty print JSON for better readability
    else:
        data_str = str(data)
        try:
            json_data = json.loads(data_str)
            # Re-serialize with proper formatting
            data_str = json.dumps(json_data, indent=2)
        except json.JSONDecodeError:
            # If it's not valid JSON, just store the string
            json_data = data_str

    # Write the JSON data to file
    open(f_name, "w").write(data_str)

    return {"file": f_name, "content": json_data}


def fn_write(data, ctx):
    fnames = []
    f_name = f"{cache_folder(ctx['_id'])}/{ctx['cache.output_key']}"

    # Handle different data types properly
    if isinstance(data, dict):
        json_data = data
        data_str = json.dumps(data)
    else:
        data_str = str(data)
        try:
            json_data = json.loads(data_str)
        except json.JSONDecodeError:
            # If it's not valid JSON, just store the string
            json_data = data_str

    open(f_name, "w").write(data_str)
    # log("f_write:f_name",f_name)
    return {"file": f_name, "content": json_data}
    # return {"file":f_name , "content_type":"json" ,  "content": json_data }


# def fn_hash(data, ctx):
#     """Generate SHA-256 hash of the given data"""
#     import hashlib

#     # Convert data to string and encode to bytes
#     data_str = str(data).strip()

#     data_bytes = data_str.encode("utf-8")
#     # Generate SHA-256 hash
#     hash_object = hashlib.sha256(data_bytes)
#     # Return hex digest
#     # print(hash_object.hexdigest(), len(data))
#     return hash_object.hexdigest()


def fn_hash_workflow_json(data, ctx):
    """Generate SHA-256 hash of the given data"""
    import hashlib

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            pass

    if not isinstance(data, dict):
        return hashlib.sha256(str(data).encode("utf-8")).hexdigest()

    hashable_doc = {}
    for k, v in data.items():
        if "is_changed" in v:
            del v["is_changed"]
        hashable_doc[k] = v
        for k1, v1 in v["inputs"].items():
            if type(v1) == str:
                v1 = ""
            hashable_doc[k]["inputs"][k1] = v1

    #  print(json.dumps(data,indent=2))

    data_str = str(hashable_doc).strip()

    data_bytes = data_str.encode("utf-8")
    # Generate SHA-256 hash
    hash_object = hashlib.sha256(data_bytes)
    # Return hex digest
    # print(hash_object.hexdigest(), len(data))
    return hash_object.hexdigest()




# def dict_to_namedtuple(name, d):
#     NT = namedtuple(name, d.keys())
#     return NT(**d)

# from collections import namedtuple
# from contextlib import contextmanager
# @contextmanager
# def tupler(name):
#     def fn0(**kwargs):
#         d = kwargs
#         NT = namedtuple(name, d.keys())
#         return NT(**d)
#     yield fn0




def meillisearch_initalise(base_url, index_name):
    """Initialize Meilisearch index"""
    try:
        # Create/update index primary key
        response = requests.patch(
            f"{base_url}/indexes/{index_name}",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer password",
            },
            json={"primaryKey": "id"},
        )
        response.raise_for_status()
        log("meillisearch_initalise", f"Index {index_name} initialized successfully")
        return response.json()
    except requests.exceptions.RequestException as e:
        log("meillisearch_initalise", f"Error initializing index: {e}")


def meillisearch_filter_fields(base_url, index_name, filterable_fields):
    """Configure filterable attributes for the index"""
    try:
        response = requests.put(
            f"{base_url}/indexes/{index_name}/settings/filterable-attributes",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer password",
            },
            json=filterable_fields,
        )
        response.raise_for_status()
        log(
            "meillisearch_filter_fields",
            f"Filterable fields configured: {filterable_fields}",
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        log("meillisearch_filter_fields", f"Error configuring filterable fields: {e}")
        return None


def meillisearch_configure_embedders(base_url, index_name):
    """Configure embedders for vector search"""
    try:
        response = requests.patch(
            f"{base_url}/indexes/{index_name}/settings/embedders",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer password",
            },
            json={
                "default": {
                    "source": "userProvided",
                    "dimensions": 512
                }
            },
        )
        response.raise_for_status()
        log("meillisearch_configure_embedders", "Embedders configured successfully")
    except requests.exceptions.RequestException as e:
        log("meillisearch_configure_embedders", f"Error configuring embedders: {e}")

def meillisearch_write(base_url, index_name, doc):
    """Write a single document to Meilisearch index"""
    try:
        response = requests.put(
            f"{base_url}/indexes/{index_name}/documents",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer password",
            },
            json=[doc],  # Wrap single doc in array
        )
        response.raise_for_status()
        log(
            "meillisearch_write",
            f"Document written successfully: {doc.get('id', 'unknown')}",
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        log("meillisearch_write", f"Error writing document: {e}")
        return None


def meillisearch_multi_search(base_url, index_name, q, facets=[]):
    """Perform multi-search query with facets"""
    try:
        query_data = {
            "queries": [
                {
                    "indexUid": index_name,
                    "q": q,
                    "facets": facets,
                    "attributesToHighlight": ["*"],
                    "highlightPreTag": "<ais-highlight-0000000000>",
                    "highlightPostTag": "</ais-highlight-0000000000>",
                    "limit": 21,
                    "offset": 0,
                }
            ]
        }

        response = requests.post(
            f"{base_url}/multi-search",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer password",
                "Accept": "*/*",
                "User-Agent": "Meilisearch Python Client",
            },
            json=query_data,
        )
        response.raise_for_status()
        log(
            "meillisearch_multi_search",
            f"Multi-search completed for query: '{q}' with facets: {facets}",
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        log("meillisearch_multi_search", f"Error performing multi-search: {e}")
        return None


import hashlib






from punter.data import _t
from punter.models import Workflow


# Thumbnail cache configuration
THUMBNAIL_DIR = "./public/images/thumbnails"
THUMBNAIL_MAX_WIDTH = 300
THUMBNAIL_QUALITY = 85
THUMBNAIL_FORMAT = "JPEG"
THUMBNAIL_EXTENSION = ".jpg"


def get_thumbnail_path(doc_id: str) -> str:
    """Get the filesystem path for a thumbnail."""
    return os.path.join(THUMBNAIL_DIR, f"{doc_id}{THUMBNAIL_EXTENSION}")


def get_thumbnail_url(doc_id: str) -> str:
    """Get the URL path for a thumbnail."""
    return f"/images/thumbnails/{doc_id}{THUMBNAIL_EXTENSION}"


def generate_thumbnail(source_path: str, thumbnail_path: str) -> bool:
    """
    Generate a thumbnail from a source image.

    Args:
        source_path: Path to the source image
        thumbnail_path: Path where thumbnail should be saved

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure thumbnail directory exists
        os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)

        if str(source_path).lower().endswith(".mp4"):
            import subprocess

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                source_path,
                "-vframes",
                "1",
                "-vf",
                f"scale={THUMBNAIL_MAX_WIDTH}:-1",
                "-q:v",
                "2",
                thumbnail_path,
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print(f"[THUMBNAIL] Generated video thumbnail: {thumbnail_path}")
            return True

        # Open and process the image
        with Image.open(source_path) as img:
            # Convert to RGB if necessary (JPG doesn't support transparency)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            # Calculate new dimensions maintaining aspect ratio
            width, height = img.size
            if width > THUMBNAIL_MAX_WIDTH:
                ratio = THUMBNAIL_MAX_WIDTH / width
                new_width = THUMBNAIL_MAX_WIDTH
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save as JPEG
            img.save(thumbnail_path, format=THUMBNAIL_FORMAT, quality=THUMBNAIL_QUALITY)

        print(f"[THUMBNAIL] Generated: {thumbnail_path}")
        return True

    except Exception as e:
        print(f"[THUMBNAIL] Error generating thumbnail: {e}")
        return False


def ensure_thumbnail(doc_id: str, source_image_path: str) -> str:
    """
    Ensure a thumbnail exists for the given document ID.
    If it doesn't exist, generate it from the source image.

    Args:
        doc_id: The document ID
        source_image_path: Path to source image

    Returns:
        str: Path to the thumbnail file, or None if failed
    """
    thumbnail_path = get_thumbnail_path(doc_id)

    # If thumbnail already exists, return it
    if os.path.exists(thumbnail_path):
        return thumbnail_path

    if not source_image_path or not os.path.exists(source_image_path):
        print(f"[THUMBNAIL] Source image not found: {source_image_path}")
        return None

    # Generate the thumbnail
    if generate_thumbnail(source_image_path, thumbnail_path):
        return thumbnail_path

    return None


# Initialize thumbnail directory on module load
os.makedirs(THUMBNAIL_DIR, exist_ok=True)
print(f"[THUMBNAIL] Thumbnail cache directory ready: {os.path.abspath(THUMBNAIL_DIR)}")


def sink(outputs):
    raw_url = args.indexer_host or config.get("VITE_MEILISEARCH_HOST") or "127.0.0.1:7700"
    url = raw_url if raw_url.startswith(("http://", "https://")) else "http://" + raw_url

    meillisearch_initalise(url, effective_index_name)
    meillisearch_filter_fields(
        url,
        effective_index_name,
        [
            "categories", "caption", "loras", "models", "schedulers", "samplers",
            "dd", "mm", "yy", "ym", "week", "weekday", "dayOfWeek", "workflow_id",
            "resolution", "orientation", "width", "height", "source",
            "workflow_structure_id", "workflow_structure_signature_id", "inputs",
            "wf_hash_id", "inputs_hash_id", "aspect_ratio", "megapixels",
            "elapsed_ms", "traced_elapsed_ms", "time_bucket", "vote", "score",
            "parent_id", "created", "type", "content_type",
        ],
    )
    if is_experimental_indexing_enabled():
        meillisearch_configure_embedders(url, effective_index_name)

    print(" * Write to search index")
    sink_count = 0
    dead_count = 0
    d1 = None

    from pydantic import ValidationError
    from pipeline import (
        with_base_identity,
        with_file_metadata,
        with_comfy_graph,
        with_caption,
        with_categories,
        with_vectors,
        build_enriched_document
    )

    pipeline_steps = [
        with_base_identity,
        with_file_metadata,
        with_comfy_graph,
    ]
    if is_experimental_indexing_enabled():
        pipeline_steps.extend([
            with_caption,
            with_categories,
            with_vectors
        ])

    for doc in outputs:
        try:
            validated_doc = build_enriched_document(doc, pipeline_steps)
            doc_payload = validated_doc.model_dump()
            
            meillisearch_write(url, effective_index_name, doc_payload)
            
            ensure_thumbnail(doc["id"], doc["source_path"])
            cache_write(doc["id"], "milliesearch_write", doc_payload, file_type=None)
            
            sink_count += 1
            d1 = doc_payload
            
        except ValidationError as e:
            from punter.data import _t, tupler
            def _(**kwargs): return kwargs
            with tupler("DeadLetterConfig") as _:
                dead_letter_config = _(
                    folder=f"{effective_data_dir}/dead.letters/{effective_index_name}/{doc['id']}",
                )

            os.makedirs(dead_letter_config.folder, exist_ok=True)
            with open(f"{dead_letter_config.folder}/errors.json", "w") as f:
                f.write(e.json())
            
            dead_count += 1
            continue

    print(f"processed:  {sink_count}")
    print(f"dead count:  {dead_count}")
    if sink_count > 0 and d1:
        print(json.dumps(d1, indent=2)[:200])

def fn_write_keys(data, ctx):
    return str(data)


def fn_get_res(data, ctx):
    if isinstance(data, dict) and "message" in data:
        return {"error": data["message"]}
    
    try:
        x, y = data
    except (ValueError, TypeError):
        return {"error": "Invalid size data"}

    res = {}

    # Calculate megapixels
    megapixels = (x * y) / 1000000
    res["megapixels"] = round(megapixels, 2)

    # Determine orientation
    if x > y:
        res["orientation"] = "landscape"
        # Calculate aspect ratio for landscape
        gcd_value = gcd(x, y)
        res["aspect_ratio"] = f"{x // gcd_value}:{y // gcd_value}"
    elif x == y:
        res["orientation"] = "square"
        res["aspect_ratio"] = "1:1"
    else:  # x < y
        res["orientation"] = "portrait"
        # Calculate aspect ratio for portrait
        gcd_value = gcd(x, y)
        res["aspect_ratio"] = f"{x // gcd_value}:{y // gcd_value}"

    res["width"] = x
    res["height"] = y

    return res


pipe = lambda data, ctx: fn_write(fn_get_res(data, ctx), ctx)

count = 0
transforms = [
    ("data.size", (pipe, "resolution")),
    ("data.prompt", (fn_write, "png_prompt.json")),
    ("data.workflow", (fn_write, "png_workflow.json")),
    ("data.prompt", (fn_hash_workflow_json, "workflow_id")),
]
# effective_index_name is calculated earlier after args parsing
# index_name  = "workflowtests"
punter.set_cache_name(effective_index_name)
print("Cache Name:", punter.get_cache_name())
punter.set_transforms(transforms)

outputs = []


print(args)
# Try to parse limit from args, default to large number
try:
    hard_limit = int(args.limit)
except (ValueError, TypeError):
    hard_limit = 100000

count = 0
should_watch = True if args.watch == "true" else False

if args.refresh_index:
    print("Mode B: Refreshing index from cache...")
    base_cache_dir = f"{effective_data_dir}/output/{effective_index_name}"
    
    if os.path.exists(base_cache_dir):
        # Get all subdirectories (doc_ids) with their mtime
        dirs_with_mtime = []
        for d in os.listdir(base_cache_dir):
            dir_path = os.path.join(base_cache_dir, d)
            if os.path.isdir(dir_path):
                dirs_with_mtime.append((os.path.getmtime(dir_path), d))
        
        # Sort by mtime descending (newest first)
        dirs_with_mtime.sort(key=lambda x: x[0], reverse=True)
        
        for _, doc_id in dirs_with_mtime:
            if not should_watch and count >= hard_limit:
                break
                
            if not cache_exists(doc_id, "milliesearch_write") or not cache_exists(doc_id, "output.json"):
                continue
                
            try:
                ms_write = cache_get(doc_id, "milliesearch_write")
                source_path = ms_write.get("image_url")
                
                if not source_path or not os.path.exists(source_path):
                    # print(f"Skipping {doc_id}: source file not found at {source_path}")
                    continue
                    
                output = cache_get(doc_id, "output.json")
                output["source_path"] = source_path
                output["id"] = doc_id
                outputs.append(output)
                count += 1
                
                if args.watch == "true":
                    sink([output])
            except Exception as e:
                print(f"Error processing cached doc {doc_id}: {e}")
                continue
    else:
        print(f"Cache directory not found: {base_cache_dir}")
else:
    print("Mode A: Scanning filesystem...")
    for r, file_path in get_media(
        os.path.abspath(args.input), limit=hard_limit, watch=should_watch
    ):  # records:
        if args.skip_cache_hits == "true":
            continue
            
        if args.skip_transforms and cache_exists(r["_id"], "milliesearch_write"):
            # Skip doc entirely if it has already been processed to sink
            continue
            
        if cache_exists(r["_id"], "output.json") and args.overwrite != "true":
            # print(f" * Key exists {r['_id']}")
            output = cache_get(r["_id"], "output.json")
        else:
            try:
                output = transform(r, ignore_errors=["data.workflow", "data.prompt", "data.size"])
                # output = transform(r)
                f_name = cache_write(r["_id"], "output.json", output)
                print(f_name)
            except Exception as e:
                file_identifier = r.get('id', 'unknown id')
                print(f"Skipping problematic image: {file_identifier} - Error: {e}")
                continue
        output["source_path"] = file_path
        output["id"] = r["_id"]
        #     print(output.keys())
        # #        output["inputs"]))
        #     import sys;sys.exit(0)
        outputs.append(output)
        count = count + 1
        if not should_watch and count >= hard_limit:
            break
        if args.watch == "true":
            sink([output])

print(f"Processed {count} records")

if args.watch != "true":
    print("Sinking")
    sink(outputs)


## start -  jump prompt  ; ./meilisearch--master-keypassword
