from dataclasses import dataclass
from typing import Any, List
import argparse

from punter import *
import punter


def create_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input json array")
    args = parser.parse_args()
    return args


def fn_hashId(k, ctx):
    return k


def fn_get_workflow(data, ctx):
    return data["node"]


def fn_get_prompt(data, ctx):
    return data["textbox"]


def fn_get_image_url(data, ctx):
    return f"http://localhost:4777/{data}"


def fn_write_kvs(data, ctx):
    fnames = []
    for k, v in data.items():
        f_name = f"{cache_folder(ctx['_id'])}/{k}"
        open(f_name, "w").write(str(v))
    return []


def fn_write(data, ctx):

    fnames = []
    f_name = f"{cache_folder(ctx['_id'])}/{ctx['cache.output_key']}"
    open(f_name, "w").write(str(data))
    return {"file": f_name, "content": str(data)}
    return {"file": f_name, "content_type": "json", "content": json.loads(str(data))}


def fn_write_json(data, ctx):
    # print(">>>>",data.keys(), ctx["cache.entries"])
    f_name = f"{cache_folder(ctx['_id'])}/{ctx['cache.output_key']}"
    open(f_name, "w").write(json.dumps(json.loads(str(data))))
    return []


def fn_hash(data, ctx):
    """Generate SHA-256 hash of the given data"""
    import hashlib

    # Convert data to string and encode to bytes
    data_str = str(data)
    data_bytes = data_str.encode("utf-8")
    # Generate SHA-256 hash
    hash_object = hashlib.sha256(data_bytes)
    # Return hex digest
    print(data)
    return hash_object.hexdigest()


def fn_default_zero(data, ctx):
    return 0


args = create_arguments()
count = 0

transforms = [
    ("_id", (fn_hashId, "id")),
    ("_id", (fn_default_zero, "score")),
    ("_id", (fn_default_zero, "vote")),
    ("_id", (fn_get_image_url, "image_url")),
    ("_id", (fn_write, "_id")),
    ("data.png_workflow", (fn_write, "png_workflow.json")),
    ("data.png_prompt", (fn_write, "png_prompt.json")),
    ("data.info_prompt", (fn_write, "info_prompt.json")),
    ("data.info_workflow", (fn_write, "info_workflow.json")),
]
punter.set_transforms(transforms)

