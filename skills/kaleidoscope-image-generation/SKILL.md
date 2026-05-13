---
name: kaleidoscope-image-generation
description: Generate images through the local Kaleidoscope/OP CLI using `op workflow:*` commands. Use this skill whenever the user asks to generate, invoke, render, or make an image from a prompt using Kaleidoscope, a workflow/doc id, ComfyUI, `op workflow:invoke`, or asks what promptable parameters a Kaleidoscope workflow supports. This skill should also trigger when the user asks for markdown image links, elapsed generation time, workflow parameter reports, or wants to reuse a Kaleidoscope asset/doc id as an image-generation workflow.
---

# Kaleidoscope Image Generation

Use the local `op` command to inspect Kaleidoscope workflows and generate images from user prompts. The user expects real invocation, not a hypothetical prompt, when they provide enough information and ask to generate/render/invoke.

## Core Principles

- Use `op workflow:get <doc.id>` to inspect promptable fields before invoking unless the user has already supplied the exact node id and field.
- Treat `text` and `inputs` from `workflow:get` as the exposed promptable fields.
- Save temporary files only under the current working directory in `./.kaleidoscope-temp/`.
- Report generated images as Markdown image links.
- Include the exact prompt used in a fenced code block beneath the result.
- Report elapsed generation time.
- If a required value is missing or ambiguous, ask one concise question instead of guessing.

## Environment

Prefer the existing `OP_ENV_FILE` environment variable when present.

If `OP_ENV_FILE` is not present and `./.env.datavelt.tailscale` exists, use:

```bash
OP_ENV_FILE=.env.datavelt.tailscale
```

If neither is available, ask the user which OP env file to use. Do not run `op init` automatically.

## Inspecting A Workflow

When the user asks what a workflow can prompt, or before generating from a doc id, run:

```bash
OP_ENV_FILE=<env-file> op workflow:get <doc.id>
```

Summarize the result in plain language:

- Text fields: show `_id`, `key`, and a short current-value preview.
- Image/input fields: show `_id`, `key`, `type`, and a short current-value preview.
- If there is exactly one text field, use it by default for prompt generation.
- If there are multiple text fields and the user did not identify one, ask which field to use.

For raw ComfyUI prompt JSON, use:

```bash
OP_ENV_FILE=<env-file> op workflow:get-prompt <doc.id>
```

## Generating An Image From A Prompt

Use this flow when the user asks to generate/render/invoke an image from a prompt.

1. Identify the workflow/doc id.
2. Inspect promptable parameters with `op workflow:get <doc.id>` unless already known.
3. Choose the prompt field:
   - Use the single available text field automatically.
   - Otherwise ask the user which text field to target.
4. Build an override JSON array using `_id` as `id` and `key` as the field name.
5. Save the JSON file under `./.kaleidoscope-temp/`.
6. Invoke with `op workflow:invoke <doc.id> <payload.json>`.
7. Parse the returned JSON for `file_path` and/or `url`.
8. Return a Markdown image link, elapsed time, and prompt used.

Payload shape:

```json
[
  {
    "id": "57:27",
    "text": "the prompt text"
  }
]
```

Use shell timing around the command:

```bash
SECONDS=0; OP_ENV_FILE=<env-file> op workflow:invoke <doc.id> ./.kaleidoscope-temp/<name>.json; status=$?; printf '\nelapsed_seconds=%s\n' "$SECONDS"; exit $status
```

## Temporary Files

Create the temp directory in the current working directory:

```bash
mkdir -p ./.kaleidoscope-temp
```

Use clear filenames, for example:

```text
./.kaleidoscope-temp/invoke-YYYYMMDD-HHMMSS.json
```

Never use `/tmp`, home-directory scratch folders, or other external paths for skill-created temporary files.

## Markdown Image URL Construction

If the invocation output includes a `file_path`, prefer the Kaleidoscope file-serving URL because it is robust for local absolute paths:

```text
<ui-base>/images/file?path=<urlencoded absolute file_path>
```

Derive `<ui-base>` from the returned `url` when possible. For example, if `url` is:

```text
http://100.78.193.123:5173/images/comfyui.bleedingedge/output/datavelt/13-5/img_00001_.png
```

then `<ui-base>` is:

```text
http://100.78.193.123:5173
```

If you cannot safely derive a file-serving URL, use the returned `url` directly.

## Final Response Format

For successful generation, respond in this shape:

````markdown
Generated in `<elapsed>s`.

![Generated image](<markdown-image-url>)

Local path:

```text
<file_path>
```

Prompt used:

```text
<prompt>
```
````

If multiple images are returned, include all images and local paths, then include one prompt block.

## Workflow Report Format

For workflow inspection requests, respond in this shape:

````markdown
Promptable fields for `<doc.id>`:

Text fields:
- `<_id>` via key `<key>`: <short preview>

Image/input fields:
- `<_id>` via key `<key>` (`<type>`): <short preview>

Override payload example:

```json
[
  {
    "id": "<_id>",
    "<key>": "your prompt or input value"
  }
]
```
````

## Prompt Handling

Use the user's prompt as the source of truth. If they ask to expand or structure it, do so before invocation and show the final prompt used.

When helpful for image models, a structured prompt can use:

```text
subject: ...
foreground: ...
background: ...
scene: ...
```

Do not silently change the user's core subject or intent.

## Error Handling

- If `op workflow:get` fails because the workflow is missing, report the doc id and the command failure.
- If no text fields exist, report the available `inputs` and ask what field to target.
- If invocation fails, include the command-level error and do not invent an image URL.
- If output JSON cannot be parsed, show the raw command output briefly and ask whether to retry.

## Examples

User: `generate an action scene using doc 506d... with a latina action hero in a harbor`

Assistant should inspect the workflow, create `./.kaleidoscope-temp/invoke-*.json`, invoke, and respond with the generated Markdown image plus elapsed time and prompt block.

User: `what can I prompt on this workflow 506d...?`

Assistant should run `op workflow:get`, summarize text and image/input fields, and show the override payload shape.
