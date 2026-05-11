
import os
import datetime
import json
import requests
import subprocess
import base64
import hashlib
from math import gcd
from functools import lru_cache, reduce
from typing import Callable, Dict, Any, List
from PIL import Image

from graph import parse_graph, topological_order
#from punter import deref2
#from punter.data import _t, tupler
from punter.data import _t, tupler, deref2
from punter.models import Workflow
from config import get_indexer_legacy_config

_model = None
_nlp = None

def log(prefix, msg):
    print(f"{prefix} {msg}")

def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"Failed to load spacy model: {e}")
            _nlp = False
    return _nlp if _nlp is not False else None

def hyponym_count_capped(synset, cap=50):
    count = 0
    queue = synset.hyponyms()
    while queue and count < cap:
        count += 1
        current = queue.pop(0)
        queue.extend(current.hyponyms())
    return count

def extract_hypernym_lineages(text):
    nlp = get_nlp()
    if not nlp:
        return []
    
    app_config = get_indexer_legacy_config()
    hyponym_cap = app_config.get("hyponym_count_cap", 50)
    
    from nltk.corpus import wordnet as wn
    
    doc = nlp(text)
    categories = []
    
    allowed_deps = {"nsubj", "nsubjpass", "dobj", "pobj", "compound", "conj"}
    
    for token in doc:
        if token.pos_ == "NOUN" and token.dep_ in allowed_deps:
            noun = token.text.lower()
            if noun not in categories:
                categories.append(noun)
            
            synsets = wn.synsets(noun, pos=wn.NOUN)
            if not synsets:
                continue
                
            # Take the first synset (most common meaning)
            synset = synsets[0]
            
            # Go back up traversing hypernyms
            current_synsets = [synset]
            noun_lineage = []
            while current_synsets:
                next_synsets = []
                for s in current_synsets:
                    hypernyms = s.hypernyms()
                    for h in hypernyms:
                        # Check descendants to avoid extremely general nodes
                        if hyponym_count_capped(h, cap=hyponym_cap) >= hyponym_cap:
                            continue # Skip this hypernym and its ancestors
                            
                        # Extract the base word from the synset name (e.g., 'dog.n.01' -> 'dog')
                        name = h.name().split('.')[0].replace('_', ' ')
                        if name not in categories:
                            categories.append(name)
                        if name not in noun_lineage:
                            noun_lineage.append(name)
                        next_synsets.append(h)
                current_synsets = next_synsets
            
            if noun_lineage:
                print(f"{noun} : {' '.join(noun_lineage)}")
                
    return list(set(categories))

def get_caption_from_smolvlm(image_path):
    import time
    start_time = time.time()
    
    app_config = get_indexer_legacy_config()
    vlm_config = app_config.get("vlm", {})
    model_name = vlm_config.get("model_name", "smolvlm")
    system_prompt = vlm_config.get("system_prompt", "")
    user_prompt = vlm_config.get("prompt", "describe this image in great detail focusing on the concrete subjects, objects, and setting.")
    
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        data_uri = f"data:image/jpeg;base64,{encoded_string}"
        
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": data_uri}}
            ]
        })
        
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 500
        }
        
        response = requests.post("http://localhost:10000/v1/chat/completions", json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        elapsed_time = time.time() - start_time
        print(f"caption_elapsed_time: {elapsed_time:.2f}s")
        return result['choices'][0]['message']['content']
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"Error getting caption from SmolVLM: {e}")
        print(f"caption_elapsed_time: {elapsed_time:.2f}s")
        return ""

def get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
            os.makedirs(model_dir, exist_ok=True)
            _model = SentenceTransformer('clip-ViT-B-32', cache_folder=model_dir)
        except Exception as e:
            print(f"Failed to load sentence-transformer model: {e}")
            _model = False # Set to false to avoid repeated attempts
    return _model if _model is not False else None

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

def extract_mp4_metadata(source_path: str) -> dict:
    """Extract metadata tags from an MP4 file using ffprobe."""
    if not source_path or not os.path.exists(source_path):
        return {}

    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            source_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Tags are usually under format.tags
        return data.get("format", {}).get("tags", {})
    except Exception as e:
        log("extract_mp4_metadata", f"Error extracting metadata from {source_path}: {e}")
        return {}

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
    if not source_path:
        log("fn_get_elapsed_ms", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_elapsed_ms", f"File not found: {source_path}")
        return None

    if source_path.lower().endswith(".mp4"):
        tags = extract_mp4_metadata(source_path)
        if "elapsed_ms" in tags:
            try:
                return int(float(tags["elapsed_ms"]))
            except ValueError:
                return None
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
    if not source_path:
        log("fn_get_wait_time_ms", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_wait_time_ms", f"File not found: {source_path}")
        return None

    if source_path.lower().endswith(".mp4"):
        tags = extract_mp4_metadata(source_path)
        if "wait_time_ms" in tags:
            try:
                return int(float(tags["wait_time_ms"]))
            except ValueError:
                return None
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
    if not source_path:
        log("fn_get_parent_id", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_parent_id", f"File not found: {source_path}")
        return None

    if source_path.lower().endswith(".mp4"):
        tags = extract_mp4_metadata(source_path)
        if "parent_id" in tags:
            return str(tags["parent_id"])
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
    if not source_path:
        log("fn_get_traced_elapsed_ms", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_traced_elapsed_ms", f"File not found: {source_path}")
        return None

    if source_path.lower().endswith(".mp4"):
        tags = extract_mp4_metadata(source_path)
        if "traced_elapsed_ms" in tags:
            try:
                return int(float(tags["traced_elapsed_ms"]))
            except ValueError:
                return None
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
    if not source_path:
        log("fn_get_trace", f"No source_path in ctx keys: {list(ctx.keys())}")
        return None
    if not os.path.exists(source_path):
        log("fn_get_trace", f"File not found: {source_path}")
        return None

    if source_path.lower().endswith(".mp4"):
        tags = extract_mp4_metadata(source_path)
        if "trace" in tags:
            try:
                return json.loads(tags["trace"])
            except Exception as e:
                log("fn_get_trace", f"Error parsing JSON from trace in MP4: {e}")
                return None
        return None

    try:
        with Image.open(source_path) as img:
            if hasattr(img, "text") and "trace" in img.text:
                trace_str = img.text["trace"]
                log("fn_get_trace", "Found trace")
                return json.loads(trace_str)
            else:
                log(
                    "fn_get_trace",
                    f"No trace in text keys: {list(img.text.keys()) if hasattr(img, 'text') else 'no text attr'}",
                )
    except Exception as e:
        log("fn_get_trace", f"Error: {e}")
    return None

def __(**kwargs):
    return kwargs



def with_base_identity(doc: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **doc, 
        "id": artifact["id"],
        "workflow_id": artifact.get("workflow_id"),
        "source": artifact.get("source_path", "").split("/")[0] if "source_path" in artifact else "N/A"
    }

def with_file_metadata(doc: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    source_path = artifact.get("source_path")
    if not source_path:
        return doc
        
    file_stat = os.stat(source_path)
    creation_time = datetime.datetime.fromtimestamp(file_stat.st_ctime)
    
    is_video = source_path.lower().endswith(".mp4")
    
    return {
        **doc,
        "created": int(file_stat.st_ctime),
        "type": "video" if is_video else "image",
        "content_type": "video/mp4" if is_video else "image/png",
        "dd": creation_time.day,
        "mm": creation_time.month,
        "yy": creation_time.year,
        "dayOfWeek": creation_time.strftime("%A"),
        "week": f"{str(creation_time.year)[-2:]}{creation_time.isocalendar()[1]:02d}",
        "weekday": f"{str(creation_time.year)[-2:]}{creation_time.isocalendar()[1]:02d}{creation_time.isocalendar()[2]}"
    }

def with_comfy_graph(doc: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    data1 = artifact.get("png_prompt.json", {}).get("content", {})
    graph_doc = fn_create_meilisearch_doc(data1, ctx={"cache._id": artifact["id"]})
    
    source_path = artifact.get("source_path")
    elapsed_ms = fn_get_elapsed_ms(data1, {"source_path": source_path})
    wait_time_ms = fn_get_wait_time_ms(data1, {"source_path": source_path})
    
    time_bucket = None
    if elapsed_ms is not None:
        elapsed_seconds = elapsed_ms / 1000
        if elapsed_seconds <= 20:
            time_bucket = "fast"
        elif elapsed_seconds <= 30:
            time_bucket = "short"
        elif elapsed_seconds <= 45:
            time_bucket = "medium"
        elif elapsed_seconds <= 60:
            time_bucket = "medium_long"
        else:
            time_bucket = "long"
            
    res_content = artifact.get("resolution", {}).get("content", {})
    
    extended_doc = {
        **doc, 
        **graph_doc,
        "image_url": source_path,
        "resolution": f"{res_content.get('width', 0)}x{res_content.get('height', 0)}",
        "orientation": res_content.get("orientation"),
        "width": res_content.get("width"),
        "height": res_content.get("height"),
        "elapsed_ms": elapsed_ms,
        "wait_time_ms": wait_time_ms,
        "time_bucket": time_bucket,
        "parent_id": fn_get_parent_id(data1, {"source_path": source_path}),
        "trace": fn_get_trace(data1, {"source_path": source_path}),
        "traced_elapsed_ms": fn_get_traced_elapsed_ms(data1, {"source_path": source_path}),
        "score": 0,
        "vote": 0
    }
    
    # Hash ids
    extended_doc["wf_hash_id"] = new_hash(extended_doc)
    extended_doc["inputs_hash_id"] = new_hash_inputs(extended_doc)
    
    return extended_doc

def with_caption(doc: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    source_path = artifact.get("source_path")
    if not source_path or doc.get("type") != "image":
        return doc
        
    caption = get_caption_from_smolvlm(source_path)
    if caption:
        return {
            **doc,
            "caption": caption
        }
    return doc

def with_categories(doc: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    caption = doc.get("caption")
    if not caption:
        return doc
        
    categories = extract_hypernym_lineages(caption)
    if categories:
        return {
            **doc,
            "categories": categories
        }
    return doc

def with_vectors(doc: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    source_path = artifact.get("source_path")
    if not source_path or doc.get("type") != "image":
        return doc
        
    model = get_model()
    if model:
        try:
            image = Image.open(source_path)
            vector = model.encode(image).tolist()
            return {
                **doc,
                "_vectors": {"default": vector},
                "vector_embedding": vector
            }
        except Exception as e:
            print(f"Failed to generate vector for {artifact.get('id')}: {e}")
            
    return doc

def build_enriched_document(artifact: Dict[str, Any], steps: List[Callable]) -> Workflow:
    import time
    current_doc = {}
    for step_fn in steps:
        start_time = time.time()
        current_doc = step_fn(current_doc, artifact)
        elapsed_ms = (time.time() - start_time) * 1000.0
        print(f"pipeline_step: {step_fn.__name__} [{elapsed_ms:.2f} ms]")
    return Workflow.model_validate(current_doc)

