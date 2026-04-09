from __future__ import annotations
from graph import *
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import argparse
import json
import requests
import os
import datetime
from math import gcd
from PIL import Image
from dotenv import dotenv_values
import os

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
    parser.add_argument("--watch", help="watch folder")
    parser.add_argument("--limit", help="watch folder", default=1)
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


def fn_hash(data, ctx):
    """Generate SHA-256 hash of the given data"""
    import hashlib

    # Convert data to string and encode to bytes
    data_str = str(data).strip()

    data_bytes = data_str.encode("utf-8")
    # Generate SHA-256 hash
    hash_object = hashlib.sha256(data_bytes)
    # Return hex digest
    # print(hash_object.hexdigest(), len(data))
    return hash_object.hexdigest()


def fn_hash_workflow_json(data, ctx):
    """Generate SHA-256 hash of the given data"""
    import hashlib

    # Convert data to string and encode to bytes
    data = json.loads(data)
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


def __(**kwargs):
    return kwargs


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


def fn_create_meilisearch_doc(data, ctx):
    ## #####################################
    ## consts
    ## #####################################

    aspect_ratios = [
        "1:1 (Perfect Square)",
        "2:3 (Classic Portrait)",
        "3:4 (Golden Ratio)",
        "3:5 (Elegant Vertical)",
        "4:5 (Artistic Frame)",
        "5:7 (Balanced Portrait)",
        "5:8 (Tall Portrait)",
        "7:9 (Modern Portrait)",
        "9:16 (Slim Vertical)",
        "9:19 (Tall Slim)",
        "9:21 (Ultra Tall)",
        "9:32 (Skyline)",
        "3:2 (Golden Landscape)",
        "4:3 (Classic Landscape)",
        "5:3 (Wide Horizon)",
        "5:4 (Balanced Frame)",
        "7:5 (Elegant Landscape)",
        "8:5 (Cinematic View)",
        "9:7 (Artful Horizon)",
        "16:9 (Panorama)",
        "19:9 (Cinematic Ultrawide)",
        "21:9 (Epic Ultrawide)",
        "32:9 (Extreme Ultrawide)",
    ]

    ## #####################################

    g = parse_graph(data)  #
    order = topological_order(g)
    matcher = {
        "class_type": ["CLIPTextEncode"],
        "input": ["text"],
        "type": List,
        "output_field": "text",
        "output_fn": None,
    }

    def fn_save_node(params):
        def do(value, ctx):
            for k, v in ctx[1]["inputs"].items():
                break
            if "values" in params._fields:
                return __(
                    _id=ctx.id,
                    value=value,
                    key=k,
                    type=params.type,
                    _values=params.values,
                )
            return __(_id=ctx.id, value=value, key=k, type=params.type)

        return do

    def fn_extract_power_loras(value, ctx):
        loras = []
        if isinstance(value, dict):
            for k, v in value.items():
                if k.startswith("lora_") and isinstance(v, dict):
                    if "lora" in v and isinstance(v["lora"], str) and v["lora"]:
                        if v.get("on", True):
                            loras.append(v["lora"])
        return loras

    # textbox_pattern = "(\w*|\|)Text\w*.inputs.(text|value)"
    # textbox_pattern = r'[A-Za-z|0-9]+.inputs.(text|value)'
    # textbox_pattern = r'[A-Za-z|0-9]*Text[A-Za-z|0-9]*.inputs.(text|value)'
    textbox_pattern = r"[A-Za-z|0-9]*Text[A-Za-z|0-9]*.inputs.(text|value|\w*prompt\w*)"
    matchers = [
        {
            "ref": r"Power_Lora_Loader.*\.inputs",
            "type": list,
            "output_field": "loras",
            "output_fn": fn_extract_power_loras,
        },
        {
            "ref": "TextBox1.inputs.text1",
            "type": list,
            "output_field": "text",
            "output_fn": fn_save_node(_t(type="text ")),
        },
        {
            "ref": textbox_pattern,
            "type": list,
            "output_field": "text",
            "output_fn": fn_save_node(_t(type="text ")),
        },
        {
            "ref": "LoadImage.inputs.image",
            "type": list,
            "output_field": "inputs",
            "output_fn": fn_save_node(_t(type="image ")),
        },
        {
            "ref": "NunchakuFluxLoraLoader.inputs.lora_name",
            "type": list,
            "output_field": "loras",
            "output_fn": None,
        },
        {
            "ref": "LoraLoaderModelOnly.inputs.lora_name",
            "type": list,
            "output_field": "loras",
            "output_fn": None,
        },
        {
            "ref": r"\w*Lora\w*.inputs.\w*lora\w*",
            "type": list,
            "output_field": "loras",
            "output_fn": None,
        },
        {
            "ref": "KSampler.inputs.scheduler",
            "type": list,
            "output_field": "schedulers",
            "output_fn": None,
        },
        {
            "ref": "KSampler.inputs.sampler_name",
            "type": list,
            "output_field": "samplers",
            "output_fn": None,
        },
        {
            "ref": "FluxResolutionNode.inputs.aspect_ratio",
            "type": list,
            "output_field": "inputs",
            "output_fn": fn_save_node(_t(type="res.aspectratio", values=aspect_ratios)),
        },
        # {
        #     "ref":"FluxResolutionNode.inputs.megapixel",
        #     "type": list,
        #     "output_field": "inputs",
        #     "output_fn": fn_save_node ( _t( type = "res.megapixel"  ))
        # },
        {
            "ref": r"\w*DiTLoader\w*.inputs.\w*model\w*",
            "type": list,
            "output_field": "models",
            "output_fn": None,
        },
        {
            "ref": "WanVideoModelLoader.inputs.model",
            "type": list,
            "output_field": "models",
            "output_fn": None,
        },
        {
            "ref": r"UnetLoader\w*.inputs.\w*(model|unet)\w*",
            "type": list,
            "output_field": "models",
            "output_fn": None,
        },
        {
            "ref": "CheckpointLoaderSimple.inputs.ckpt_name",
            "type": list,
            "output_field": "models",
            "output_fn": None,
        },
        {
            "ref": "WanVideoModelLoader.inputs.model",
            "type": list,
            "output_field": "models",
            "output_fn": None,
        },
        {
            "ref": "ClownsharKSampler_Beta.inputs.sampler_name",
            "type": list,
            "output_field": "samplers",
            "output_fn": None,
        },
    ]

    def match(node_data, matchers):
        for m in matchers:
            try:
                d = deref2(node_data, m["ref"])
            except Exception as e:
                print(m, f"{e} \n =============\n")
                # import sys;sys.exit(1)
                return None
            value = d.v
            if type(value) is list:
                continue
            if value is not None:
                return (d, m)
        return None

    def stich(d, v, m):
        field = m["output_field"]

        if field not in d:
            if m["type"] == list:
                if isinstance(v, list):
                    d[field] = v.copy()
                else:
                    d[field] = [v]
            else:
                d[field] = v
        else:
            if m["type"] == list:
                items_to_add = v if isinstance(v, list) else [v]
                for item in items_to_add:
                    if type(item) is dict:
                        d[field].append(item)
                    elif isinstance(item, str) and item.strip() != "" and item not in d[field]:
                        d[field].append(item)
            else:
                d[field] = ",".join([str(d[field]), str(v)])

        return d

    search_doc = {"id": ctx["cache._id"]}

    for idx, n in enumerate(order):
        node = data[n]
        # print(node)
        doc = {node["class_type"].replace(" ", "_"): {"inputs": node["inputs"]}}
        ret = match(doc, matchers)
        if ret is None:
            continue

        (d, m) = ret
        value = d.v

        if value is None:
            continue

        with tupler("Context") as _:
            fn = m["output_fn"]
            value = fn(value, _(id=n, node=node)) if fn is not None else value
            # print("fn:",fn , m , value )

        # print("progress:", doc,value, stich(search_doc,value,m))
        search_doc = stich(search_doc, value, m)

    # print(order)
    workflow_id0 = "".join([f"{o}.{data[o]['class_type']}" for o in order])
    workflow_id1 = "".join([f"{data[o]['class_type']}" for o in order])
    # print(fn_hash("we",{}))
    search_doc["workflow_structure_id"] = fn_hash(workflow_id1, {})
    search_doc["workflow_structure_signature_id"] = fn_hash(workflow_id0, {})

    return search_doc


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


def new_hash(d):
    enc = lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()[:8]
    wf_struct_id = d["workflow_structure_id"][:4]
    hashy = wf_struct_id
    inputs = d["inputs"] if "inputs" in d else []
    text = d["text"] if "text" in d else []
    for i in inputs:
        hashy = f"{hashy}_{enc(i['value'])}"

    for i in text:
        hashy = f"{hashy}_{enc(i['value'])}"

    return hashy


def new_hash_inputs(d):
    enc = lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()[:8]
    wf_struct_id = ""
    hashy = wf_struct_id
    inputs = d["inputs"] if "inputs" in d else []
    text = d["text"] if "text" in d else []

    for i in sorted([t["value"] for t in text]):
        hashy = f"{hashy}_{enc(i)}"

    return hashy


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
    # print(json.dumps(output))
    # Meilisearch configuration
    raw_url = args.indexer_host or config.get("VITE_MEILISEARCH_HOST") or "127.0.0.1:7700"
    url = raw_url if raw_url.startswith(("http://", "https://")) else "http://" + raw_url

    meillisearch_initalise(url, effective_index_name)
    meillisearch_filter_fields(
        url,
        effective_index_name,
        [
            "loras",
            "models",
            "schedulers",
            "samplers",
            "dd",
            "mm",
            "yy",
            "week",
            "weekday",
            "dayOfWeek",
            "workflow_id",
            "resolution",
            "orientation",
            "width",
            "",
            "height",
            "source",
            "workflow_structure_id",
            "workflow_structure_signature_id",
            "inputs",
            "wf_hash_id",
            "inputs_hash_id",
            "aspect_ratio",
            "megapixels",
            "elapsed_ms",
            "traced_elapsed_ms",
            "time_bucket",
            "vote",
            "score",
            "parent_id",
            "created",
            "type",
            "content_type",
        ],
    )
    print(" * Write to search index")
    sink_count = 0
    dead_count = 0
    for doc in outputs:
        # if cache_exists(doc["id"],"milliesearch_write") and args.overwrite != "true":
        #     print(f"Skipping  - milli doc - '{doc['id']}'")
        #     continue

        data1 = doc["png_prompt.json"]["content"]

        source_path = doc["source_path"]
        file_stat = os.stat(source_path)
        creation_time = datetime.datetime.fromtimestamp(file_stat.st_ctime)
        unix_timestamp = int(file_stat.st_ctime)  # Convert to Unix timestamp

        day = creation_time.day
        dow = creation_time.strftime("%A")
        month = creation_time.month
        year = creation_time.year
        iso_cal = creation_time.isocalendar()
        week_num = iso_cal[1]
        day_num = iso_cal[2]
        week = f"{str(year)[-2:]}{week_num:02d}"
        weekday = f"{str(year)[-2:]}{week_num:02d}{day_num}"
        d1 = fn_create_meilisearch_doc(data1, ctx={"cache._id": doc["id"]})
        d1["image_url"] = f"{doc['source_path']}"
        d1["source"] = d1["image_url"].split("/")[0]
        d1["dd"] = day
        d1["dayOfWeek"] = dow
        d1["mm"] = month
        d1["yy"] = year
        d1["week"] = week
        d1["weekday"] = weekday
        d1["workflow_id"] = doc["workflow_id"]
        d1["resolution"] = (
            f"{doc['resolution']['content']['width']}x{doc['resolution']['content']['height']}"
        )
        d1["orientation"] = doc["resolution"]["content"]["orientation"]
        d1["width"] = doc["resolution"]["content"]["width"]
        d1["height"] = doc["resolution"]["content"]["height"]
        d1["type"] = "video" if doc["source_path"].lower().endswith(".mp4") else "image"
        d1["content_type"] = (
            "video/mp4" if doc["source_path"].lower().endswith(".mp4") else "image/png"
        )

        d1["created"] = unix_timestamp
        d1["elapsed_ms"] = fn_get_elapsed_ms(data1, {"source_path": source_path})
        d1["wait_time_ms"] = fn_get_wait_time_ms(data1, {"source_path": source_path})
        log(
            "sink",
            f"elapsed_ms for {doc['id']}: {d1['elapsed_ms']} wait_time_ms: {d1.get('wait_time_ms')}",
        )
        d1["wf_hash_id"] = new_hash(d1)
        d1["inputs_hash_id"] = new_hash_inputs(d1)
        d1["parent_id"] = fn_get_parent_id(data1, {"source_path": source_path})
        d1["trace"] = fn_get_trace(data1, {"source_path": source_path})
        d1["traced_elapsed_ms"] = fn_get_traced_elapsed_ms(data1, {"source_path": source_path})
        d1["score"] = 0
        d1["vote"] = 0

        # Derive time_bucket from elapsed_ms
        elapsed_ms = d1.get("elapsed_ms")
        if elapsed_ms is not None:
            elapsed_seconds = elapsed_ms / 1000  # Convert ms to seconds
            if elapsed_seconds <= 20:
                d1["time_bucket"] = "fast"
            elif elapsed_seconds <= 30:
                d1["time_bucket"] = "short"
            elif elapsed_seconds <= 45:
                d1["time_bucket"] = "medium"
            elif elapsed_seconds <= 60:
                d1["time_bucket"] = "medium_long"
            else:
                d1["time_bucket"] = "long"

        meillisearch_write(url, effective_index_name, d1)

        # Generate thumbnail proactively
        try:
            source_path = doc["source_path"]
            ensure_thumbnail(doc["id"], source_path)
        except Exception as e:
            print(f"[THUMBNAIL] Failed to generate thumbnail for {doc['id']}: {e}")

        try:
            ret = Workflow.model_validate(d1)
            # print(ret)
        except Exception as e:
            with tupler("DeadLetterConfig") as _:
                dead_letter_config = _(
                    folder=f"{effective_data_dir}/dead.letters/{effective_index_name}/{d1['id']}",
                )

            os.makedirs(dead_letter_config.folder, exist_ok=True)
            open(f"{dead_letter_config.folder}/errors.json", "w").write(json.dumps(e.errors()))
            # print(d1['id'],"    ", json.dumps(e.errors()))

            dead_count = dead_count + 1
            continue
        cache_write(doc["id"], "milliesearch_write", d1, file_type=None)
        sink_count = sink_count + 1

    print(f"processed:  {sink_count}")
    print(f"dead count:  {dead_count}")
    if sink_count > 0:
        print(json.dumps(d1, indent=2))


def fn_write_keys(data, ctx):
    return str(data)


def fn_get_res(data, ctx):
    x, y = data
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


def fn_get_elapsed_ms(data, ctx):
    """Extract elapsed_ms from PNG metadata.

    Reads the 'elapsed_ms' field from PNG text chunks and returns it as an integer.
    This field is written by datavelt.backend when a workflow completes successfully.

    Args:
        data: Unused (PNG text chunks would come here if passed via transform)
        ctx: Context dict containing 'source_path' key with the PNG file path

    Returns:
        int or None: elapsed time in milliseconds, or None if not found
    """
    from PIL import Image

    source_path = ctx.get("source_path")
    if source_path and source_path.lower().endswith(".mp4"):
        return None
    if not source_path:
        log("fn_get_elapsed_ms", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_elapsed_ms", f"File not found: {source_path}")
        return None

    try:
        with Image.open(source_path) as img:
            if hasattr(img, "text") and "elapsed_ms" in img.text:
                raw_value = img.text["elapsed_ms"]
                log(
                    "fn_get_elapsed_ms",
                    f"Found raw_value: {raw_value} (type: {type(raw_value)})",
                )
                if isinstance(raw_value, str):
                    numeric_value = float(raw_value)
                else:
                    numeric_value = float(raw_value)
                return int(numeric_value)
            else:
                log(
                    "fn_get_elapsed_ms",
                    f"No elapsed_ms in text keys: {list(img.text.keys()) if hasattr(img, 'text') else 'no text attr'}",
                )
    except Exception as e:
        log("fn_get_elapsed_ms", f"Error: {e}")
    return None


def fn_get_wait_time_ms(data, ctx):
    """Extract wait_time_ms from PNG metadata.

    Reads the 'wait_time_ms' field from PNG text chunks and returns it as an integer.

    Args:
        data: Unused
        ctx: Context dict containing 'source_path' key with the PNG file path

    Returns:
        int or None: wait time in milliseconds, or None if not found
    """
    from PIL import Image

    source_path = ctx.get("source_path")
    if source_path and source_path.lower().endswith(".mp4"):
        return None
    if not source_path:
        log("fn_get_wait_time_ms", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_wait_time_ms", f"File not found: {source_path}")
        return None

    try:
        with Image.open(source_path) as img:
            if hasattr(img, "text") and "wait_time_ms" in img.text:
                raw_value = img.text["wait_time_ms"]
                log(
                    "fn_get_wait_time_ms",
                    f"Found raw_value: {raw_value} (type: {type(raw_value)})",
                )
                if isinstance(raw_value, str):
                    numeric_value = float(raw_value)
                else:
                    numeric_value = float(raw_value)
                return int(numeric_value)
            else:
                log(
                    "fn_get_wait_time_ms",
                    f"No wait_time_ms in text keys: {list(img.text.keys()) if hasattr(img, 'text') else 'no text attr'}",
                )
    except Exception as e:
        log("fn_get_wait_time_ms", f"Error: {e}")
    return None


def fn_get_parent_id(data, ctx):
    """Extract parent_id from PNG metadata.

    Reads the 'parent_id' field from PNG text chunks and returns it.
    This field is written by datavelt.backend when a workflow is invoked
    with a parent workflow hash.

    Args:
        data: Unused (PNG text chunks would come here if passed via transform)
        ctx: Context dict containing 'source_path' key with the PNG file path

    Returns:
        str or None: parent workflow id/hash, or None if not found
    """
    from PIL import Image

    source_path = ctx.get("source_path")
    if source_path and source_path.lower().endswith(".mp4"):
        return None
    if not source_path:
        log("fn_get_parent_id", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_parent_id", f"File not found: {source_path}")
        return None

    try:
        with Image.open(source_path) as img:
            if hasattr(img, "text") and "parent_id" in img.text:
                parent_id = img.text["parent_id"]
                log("fn_get_parent_id", f"Found parent_id: {parent_id}")
                return str(parent_id)
            else:
                log(
                    "fn_get_parent_id",
                    f"No parent_id in text keys: {list(img.text.keys()) if hasattr(img, 'text') else 'no text attr'}",
                )
    except Exception as e:
        log("fn_get_parent_id", f"Error: {e}")
    return None


def fn_get_traced_elapsed_ms(data, ctx):
    """Extract traced_elapsed_ms from PNG metadata.

    Reads the 'traced_elapsed_ms' field from PNG text chunks and returns it.

    Args:
        data: Unused
        ctx: Context dict containing 'source_path' key with the PNG file path

    Returns:
        int or None: elapsed time in milliseconds, or None if not found
    """
    from PIL import Image

    source_path = ctx.get("source_path")
    if source_path and source_path.lower().endswith(".mp4"):
        return None
    if not source_path:
        log("fn_get_traced_elapsed_ms", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_traced_elapsed_ms", f"File not found: {source_path}")
        return None

    try:
        with Image.open(source_path) as img:
            if hasattr(img, "text") and "traced_elapsed_ms" in img.text:
                raw_value = img.text["traced_elapsed_ms"]
                log("fn_get_traced_elapsed_ms", f"Found traced_elapsed_ms: {raw_value}")
                if isinstance(raw_value, str):
                    numeric_value = float(raw_value)
                else:
                    numeric_value = float(raw_value)
                return int(numeric_value)
            else:
                log(
                    "fn_get_traced_elapsed_ms",
                    f"No traced_elapsed_ms in text keys: {list(img.text.keys()) if hasattr(img, 'text') else 'no text attr'}",
                )
    except Exception as e:
        log("fn_get_traced_elapsed_ms", f"Error: {e}")
    return None


def fn_get_trace(data, ctx):
    """Extract trace from PNG metadata.

    Reads the 'trace' field from PNG text chunks and returns it.

    Args:
        data: Unused
        ctx: Context dict containing 'source_path' key with the PNG file path

    Returns:
        list or dict or None: trace json, or None if not found
    """
    from PIL import Image
    import json

    source_path = ctx.get("source_path")
    if source_path and source_path.lower().endswith(".mp4"):
        return None
    if not source_path:
        log("fn_get_trace", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_trace", f"File not found: {source_path}")
        return None

    try:
        with Image.open(source_path) as img:
            if hasattr(img, "text") and "trace" in img.text:
                trace_str = img.text["trace"]
                log("fn_get_trace", f"Found trace")
                return json.loads(trace_str)
            else:
                log(
                    "fn_get_trace",
                    f"No trace in text keys: {list(img.text.keys()) if hasattr(img, 'text') else 'no text attr'}",
                )
    except Exception as e:
        log("fn_get_trace", f"Error: {e}")
    return None


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
# hard_limit = 100000
hard_limit = 100000  # args.limit
count = 0
should_watch = True if args.watch == "true" else False
for r, file_path in get_media(
    os.path.abspath(args.input), limit=hard_limit, watch=should_watch
):  # records:
    if args.skip_cache_hits == "true":
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
            import traceback

            if "id" in r:
                print(f" {r['id']} - {e} - Current Count: {count}")
            else:
                print(f"error - {e}")
            print("Traceback:")
            traceback.print_exc()
            continue
    output["source_path"] = file_path
    output["id"] = r["_id"]
    #     print(output.keys())
    # #        output["inputs"]))
    #     import sys;sys.exit(0)
    outputs.append(output)
    count = count + 1
    if count > hard_limit:
        break
    if args.watch == "true":
        sink([output])

print(f"Processed {count} records")

if args.watch != "true":
    print("Sinking")
    sink(outputs)


## start -  jump prompt  ; ./meilisearch--master-keypassword
