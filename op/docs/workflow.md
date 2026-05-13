# Workflow Commands

The `op workflow:*` commands inspect and invoke Kaleidescope/ComfyUI workflows.

Use the same environment file you use for serving or starting OP:

```bash
OP_ENV_FILE=.env.datavelt.tailscale op workflow:get <doc.id>
```

## `workflow:get`

Returns the invokable fields exposed on a document from Meilisearch.

```bash
OP_ENV_FILE=.env.datavelt.tailscale op workflow:get <doc.id>
```

The output includes the document id plus the `text` and `inputs` arrays. These are the fields used to build override payloads for `workflow:invoke`.

Example shape:

```json
{
  "id": "506d0c5ccd0a93c7c84b5c15c790eb034033649df657bd92cc90afba4d2ca526",
  "inputs": [
    {
      "_id": "78",
      "value": "input/datavelt/example.png",
      "key": "image",
      "type": "image "
    }
  ],
  "text": [
    {
      "_id": "57:27",
      "value": "A prompt...",
      "key": "text",
      "type": "text "
    }
  ]
}
```

## `workflow:get-prompt`

Returns the raw ComfyUI API prompt JSON stored for a document.

```bash
OP_ENV_FILE=.env.datavelt.tailscale op workflow:get-prompt <doc.id>
```

This command calls the Kaleidescope API endpoint `GET /workflow/{doc.id}` and prints the stored `png_prompt.json`.

## `workflow:invoke`

Invokes a stored workflow/document with an override JSON file.

```bash
OP_ENV_FILE=.env.datavelt.tailscale op workflow:invoke <doc.id> input.json
```

Example text override:

```json
[
  {
    "id": "57:27",
    "text": "subject: cinematic action hero..."
  }
]
```

Example image override:

```json
[
  {
    "id": "78",
    "image": "./input-image.png"
  }
]
```

Local image paths are uploaded to Convex and replaced with `virtual://...` URIs before invocation.

The command respects `INVOKE_METHOD`, so `INVOKE_METHOD=invoke2` posts to `/workflow/{doc.id}/invoke2`.

## `workflow:invoke-prompt`

Invokes a local ComfyUI API prompt JSON directly.

```bash
OP_ENV_FILE=.env.datavelt.tailscale op workflow:invoke-prompt /path/to/prompt.json
```

Before queueing the prompt, the command finds all nodes whose `class_type` contains `SaveImage` and sets:

```text
inputs.filename_prefix = $RELEASE_FOLDER/$D-$M/img
```

For example, on May 13 with `RELEASE_FOLDER=datavelt`, the prefix becomes:

```text
datavelt/13-5/img
```

The command queues the prompt directly to ComfyUI at `http://127.0.0.1:8188/prompt`, polls `http://127.0.0.1:8188/history/{prompt_id}`, and prints generated output paths and UI URLs.

Example output:

```json
[
  {
    "file_path": "/mnt/sdc1/apps/comfyui.bleedingedge/output/datavelt/13-5/img_00001_.png",
    "url": "http://100.78.193.123:5173/images/comfyui.bleedingedge/output/datavelt/13-5/img_00001_.png"
  }
]
```

## `workflow:lineage`

Returns ancestor documents by following image input references.

```bash
OP_ENV_FILE=.env.datavelt.tailscale op workflow:lineage <doc.id>
```
