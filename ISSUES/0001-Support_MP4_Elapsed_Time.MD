# Issue 0001: Support MP4 Metadata Extraction for Elapsed Time

## Goal
Make `indexer.legacy/graph.py` extract metadata like `elapsed_ms` and other metadata embedded in `.mp4` video files (currently only PNGs are fully supported). The extracted fields will be pushed to the Meilisearch index.

## Details
`kaleidescope/services/image.py` correctly uses `ffmpeg` to embed these metadata fields into `.mp4` files (via `update_mp4_metadata`), but `indexer.legacy/graph.py` is hardcoded to skip `.mp4` files when attempting to extract metadata like `elapsed_ms`, `wait_time_ms`, `parent_id`, `trace`, and `traced_elapsed_ms`.

## Implementation Steps
1. Add an `ffprobe` helper inside `indexer.legacy/graph.py` to extract `.mp4` metadata using `subprocess.run` (cached per file to avoid redundant calls).
2. Update extraction functions:
    * `fn_get_elapsed_ms`
    * `fn_get_wait_time_ms`
    * `fn_get_parent_id`
    * `fn_get_traced_elapsed_ms`
    * `fn_get_trace`
3. Update `sink` loops if needed to ensure no other `.mp4` checks accidentally block the extraction.

## TODO
- [x] Add `extract_mp4_metadata` function using `ffprobe`
- [x] Update `fn_get_elapsed_ms` to support MP4s
- [x] Update `fn_get_wait_time_ms` to support MP4s
- [x] Update `fn_get_parent_id` to support MP4s
- [x] Update `fn_get_traced_elapsed_ms` to support MP4s
- [x] Update `fn_get_trace` to support MP4s
- [x] Write test cases / assets to `./ISSUES/0001/tests`
- [x] Run test/verification steps against an existing MP4 file