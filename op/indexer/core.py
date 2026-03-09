import os
import json
import logging
import requests
import datetime
from math import gcd
from typing import List, Dict, Any, Optional
from PIL import Image

from .utils import tupler, deref2, _t, _, hash_file, hash_json_data
from .graph import parse_graph, topological_order
from .reader import get_pngs

logger = logging.getLogger(__name__)

# Constants
ASPECT_RATIOS = [
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

THUMBNAIL_MAX_WIDTH = 300
THUMBNAIL_QUALITY = 85
THUMBNAIL_FORMAT = "JPEG"
THUMBNAIL_EXTENSION = ".jpg"


def ensure_thumbnail(doc_id: str, source_image_path: str, thumbnail_dir: str) -> Optional[str]:
    """Ensure a thumbnail exists for the given document ID."""
    os.makedirs(thumbnail_dir, exist_ok=True)
    thumbnail_path = os.path.join(thumbnail_dir, f"{doc_id}{THUMBNAIL_EXTENSION}")

    if os.path.exists(thumbnail_path):
        return thumbnail_path

    if not source_image_path or not os.path.exists(source_image_path):
        logger.warning(f"[THUMBNAIL] Source image not found: {source_image_path}")
        return None

    try:
        with Image.open(source_image_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            width, height = img.size
            if width > THUMBNAIL_MAX_WIDTH:
                ratio = THUMBNAIL_MAX_WIDTH / width
                new_width = THUMBNAIL_MAX_WIDTH
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            img.save(thumbnail_path, format=THUMBNAIL_FORMAT, quality=THUMBNAIL_QUALITY)

        logger.info(f"[THUMBNAIL] Generated: {thumbnail_path}")
        return thumbnail_path
    except Exception as e:
        logger.error(f"[THUMBNAIL] Error generating thumbnail: {e}")
        return None


def fn_save_node(params):
    def do(value, ctx):
        k = None
        # Try to find the key in inputs
        if "inputs" in ctx.node:
            for k_in in ctx.node["inputs"]:
                k = k_in
                break

        # Original code logic for key finding was a bit specific to their graph structure
        # using ctx[1] which implies ctx is a tuple.
        # In our port, ctx is passed as _(id=n, node=node)

        if hasattr(ctx, "node") and isinstance(ctx.node, dict) and "inputs" in ctx.node:
            for k_in in ctx.node["inputs"]:
                k = k_in
                break

        if hasattr(params, "_values") and params._values:
            return _(
                _id=ctx.id,
                value=value,
                key=k,
                type=params.type,
                _values=params._values,
            )
        return _(_id=ctx.id, value=value, key=k, type=params.type)

    return do


# Matcher definitions
TEXTBOX_PATTERN = r"[A-Za-z|0-9]*Text[A-Za-z|0-9]*.inputs.(text|value|\w*prompt\w*)"
MATCHERS = [
    {
        "ref": "TextBox1.inputs.text1",
        "type": list,
        "output_field": "text",
        "output_fn": fn_save_node(_t(type="text ")),
    },
    {
        "ref": TEXTBOX_PATTERN,
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
        "output_fn": fn_save_node(_t(type="res.aspectratio", _values=ASPECT_RATIOS)),
    },
    {
        "ref": "NunchakuFluxDiTLoader.inputs.model_path",
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
        "ref": "ClownsharKSampler_Beta.inputs.sampler_name",
        "type": list,
        "output_field": "samplers",
        "output_fn": None,
    },
    {
        "ref": "class_type",
        "match_value": ["CLIPTextEncode"],
        "input": ["text"],
        "type": list,
        "output_field": "text",
        "output_fn": None,
    },
]


def match(node_data, matchers):
    for m in matchers:
        if "ref" in m:
            d = deref2(node_data, m["ref"])
            if d is None or d.v is None:
                continue

            value = d.v
            if isinstance(value, list):
                continue
            return (d, m)
    return None


def stitch(d, v, m):
    field = m["output_field"]

    if field not in d:
        if m["type"] == list:
            d[field] = [v]
        else:
            d[field] = v
    else:
        if m["type"] == list:
            if isinstance(v, dict):
                d[field].append(v)
            elif isinstance(v, str) and v.strip() != "" and v not in d[field]:
                d[field].append(v)
            elif not isinstance(v, (dict, str)) and v not in d[field]:
                d[field].append(v)
        else:
            # Join scalar values? Or overwrite?
            # Original code: d[field] = ",".join(d[field], v) -> This looks like it might fail if d[field] is not list
            # Assuming comma separated string for scalars
            d[field] = f"{d[field]},{v}"

    return d


def fn_hash(data, ctx):
    """Generate SHA-256 hash of the given data"""
    data_str = str(data).strip()
    data_bytes = data_str.encode("utf-8")
    hash_object = hashlib.sha256(data_bytes)
    return hash_object.hexdigest()


import hashlib


def fn_hash_workflow_json(data, ctx):
    """Generate SHA-256 hash of the given data"""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass

    if not isinstance(data, dict):
        return fn_hash(data, ctx)

    hashable_doc = {}
    for k, v in data.items():
        if "is_changed" in v:
            del v["is_changed"]
        hashable_doc[k] = v
        if "inputs" in v and isinstance(v["inputs"], dict):
            for k1, v1 in v["inputs"].items():
                if isinstance(v1, str):
                    v1 = ""
                hashable_doc[k]["inputs"][k1] = v1

    data_str = str(hashable_doc).strip()
    data_bytes = data_str.encode("utf-8")
    hash_object = hashlib.sha256(data_bytes)
    return hash_object.hexdigest()


def create_search_doc(data, ctx_id):
    g = parse_graph(data)
    order = topological_order(g)

    search_doc = {"id": ctx_id}

    for idx, n in enumerate(order):
        node = data[n]
        # Construct a doc fragment to match against
        # Original code used: {node["class_type"].replace(" ", "_"): {"inputs": node["inputs"]}}
        # But deref2 expects keys.
        # Let's clean the class type
        class_type = node.get("class_type", "Unknown").replace(" ", "_")
        doc_frag = {class_type: {"inputs": node.get("inputs", {})}}

        ret = match(doc_frag, MATCHERS)
        if ret is None:
            continue

        (d, m) = ret
        value = d.v

        if value is None:
            continue

        with tupler("Context") as _:
            fn = m["output_fn"]
            # Pass context as named tuple
            if fn is not None:
                value = fn(value, _(id=n, node=node))

        search_doc = stitch(search_doc, value, m)

    workflow_id0 = "".join([f"{o}.{data[o]['class_type']}" for o in order])
    workflow_id1 = "".join([f"{data[o]['class_type']}" for o in order])

    search_doc["workflow_structure_id"] = fn_hash(workflow_id1, {})
    search_doc["workflow_structure_signature_id"] = fn_hash(workflow_id0, {})

    return search_doc


def new_hash(d):
    enc = lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()[:8]
    wf_struct_id = d.get("workflow_structure_id", "")[:4]
    hashy = wf_struct_id
    inputs = d.get("inputs", [])
    text = d.get("text", [])

    # Check if inputs/text are list of objects or strings
    # The original code accessed ['value'] so they expected dicts
    for i in inputs:
        if isinstance(i, dict) and "value" in i:
            hashy = f"{hashy}_{enc(str(i['value']))}"
        elif isinstance(i, str):
            hashy = f"{hashy}_{enc(i)}"

    for i in text:
        if isinstance(i, dict) and "value" in i:
            hashy = f"{hashy}_{enc(str(i['value']))}"
        elif isinstance(i, str):
            hashy = f"{hashy}_{enc(i)}"

    return hashy


def new_hash_inputs(d):
    enc = lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()[:8]
    wf_struct_id = ""
    hashy = wf_struct_id
    text = d.get("text", [])

    values = []
    for t in text:
        if isinstance(t, dict) and "value" in t:
            values.append(str(t["value"]))
        elif isinstance(t, str):
            values.append(t)

    for i in sorted(values):
        hashy = f"{hashy}_{enc(i)}"

    return hashy


def fn_get_res(data, ctx):
    x, y = data
    res = {}

    megapixels = (x * y) / 1000000
    res["megapixels"] = round(megapixels, 2)

    if x > y:
        res["orientation"] = "landscape"
        gcd_value = gcd(x, y)
        res["aspect_ratio"] = f"{x // gcd_value}:{y // gcd_value}"
    elif x == y:
        res["orientation"] = "square"
        res["aspect_ratio"] = "1:1"
    else:  # x < y
        res["orientation"] = "portrait"
        gcd_value = gcd(x, y)
        res["aspect_ratio"] = f"{x // gcd_value}:{y // gcd_value}"

    res["width"] = x
    res["height"] = y

    return res


def meillisearch_write(base_url, index_name, doc, api_key=None):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.put(
            f"{base_url}/indexes/{index_name}/documents?primaryKey=id",
            headers=headers,
            json=[doc],
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error writing to Meilisearch: {e}")
        return None


def meillisearch_settings(base_url, index_name, filterable_fields, api_key=None):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.put(
            f"{base_url}/indexes/{index_name}/settings/filterable-attributes",
            headers=headers,
            json=filterable_fields,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error configuring Meilisearch settings: {e}")
        return None


def run_indexer(
    watch_path,
    index_name,
    meilisearch_url,
    root_path=None,
    limit=100000,
    watch=False,
    overwrite=False,
):
    logger.info(f"Starting indexer on {watch_path}")

    # Configure Meilisearch
    if not meilisearch_url.startswith("http"):
        meilisearch_url = f"http://{meilisearch_url}"

    if root_path:
        thumbnail_dir = os.path.join(root_path, "thumbnails")
    else:
        thumbnail_dir = os.path.join(os.path.dirname(watch_path), "thumbnails")

    logger.info(f"Thumbnails will be stored in: {thumbnail_dir}")

    filterable_fields = [
        "loras",
        "models",
        "schedulers",
        "samplers",
        "dd",
        "mm",
        "yy",
        "dayOfWeek",
        "workflow_id",
        "resolution",
        "orientation",
        "width",
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
        "time_bucket",
        "vote",
        "score",
        "parent_id",
        "created",
    ]

    meillisearch_settings(meilisearch_url, index_name, filterable_fields, "password")

    count = 0
    for metadata, file_path in get_pngs(watch_path, limit=limit, watch=watch):
        print(metadata, file_path)
        try:
            doc_id = metadata["_id"]
            data = metadata["data"]

            # Check for required data
            if "png_prompt" not in data or "png_workflow" not in data:
                print(
                    f"WARN: Skipping {os.path.abspath(file_path)} - missing metadata. Found keys: {list(data.keys())}"
                )
                continue

            try:
                prompt_json = json.loads(data["png_prompt"])
                workflow_json = json.loads(data["png_workflow"])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON for {file_path}")
                continue

            # Create base search doc from workflow structure
            d1 = create_search_doc(prompt_json, doc_id)

            # Add file info
            file_stat = os.stat(file_path)
            creation_time = datetime.datetime.fromtimestamp(file_stat.st_ctime)

            d1["id"] = doc_id
            d1["image_url"] = (
                f"/images/thumbnails/{doc_id}{THUMBNAIL_EXTENSION}"  # Point to thumbnail
            )
            d1["source_path"] = file_path  # Internal use
            d1["dd"] = creation_time.day
            d1["dayOfWeek"] = creation_time.strftime("%A")
            d1["mm"] = creation_time.month
            d1["yy"] = creation_time.year
            d1["created"] = int(file_stat.st_ctime)

            # Calculate hashes
            d1["workflow_id"] = fn_hash_workflow_json(prompt_json, {})
            d1["wf_hash_id"] = new_hash(d1)
            d1["inputs_hash_id"] = new_hash_inputs(d1)

            # Resolution
            if "size" in data:
                w, h = data["size"]
                res = fn_get_res((w, h), {})
                d1.update(res)
                d1["resolution"] = f"{w}x{h}"

            # Extra fields from PNG info/text
            if "png_elapsed_ms" in data:
                try:
                    elapsed_ms = int(float(data["png_elapsed_ms"]))
                    d1["elapsed_ms"] = elapsed_ms

                    elapsed_seconds = elapsed_ms / 1000
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
                except:
                    pass

            if "png_parent_id" in data:
                d1["parent_id"] = data["png_parent_id"]

            # Write to Meilisearch
            meillisearch_write(meilisearch_url, index_name, d1, "password")
            print(f"OK: write to meilisearch {index_name} {d1['id']}")
            print(f" * ingested file - {os.path.abspath(file_path)}")

            # Generate thumbnail
            # thumbnail_dir is calculated at the start of run_indexer

            t = ensure_thumbnail(doc_id, file_path, thumbnail_dir)
            if t:
                print(f" * generated thumbnail - {os.path.abspath(t)}")

            count += 1
            if count % 10 == 0:
                logger.info(f"Indexed {count} files...")

        except Exception as e:
            print(e)
            logger.error(f"Error processing {file_path}: {e}")
            import traceback

            traceback.print_exc()

    logger.info(f"Finished indexing {count} files.")
