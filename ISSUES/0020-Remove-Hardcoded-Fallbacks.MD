# Remove Hardcoded Fallbacks

## Problem
In `kaleidescope.ui/vite.config.ts` and `indexer.legacy/graph.py`, there are hardcoded fallback values for critical configuration settings.

```typescript
// kaleidescope.ui/vite.config.ts
const apiUrl = process.env.KALEIDESCOPE_API_URL || env.VITE_KALEIDESCOPE_API_URL || env.KALEIDESCOPE_API_URL || 'http://localhost:8000'
const convexUrl = process.env.CONVEX_URL || env.CONVEX_URL || 'http://127.0.0.1:3210'
// ...
'import.meta.env.VITE_RELEASE_FOLDER': JSON.stringify(process.env.RELEASE_FOLDER || env.RELEASE_FOLDER || 'release'),
'import.meta.env.VITE_INDEX_NAME': JSON.stringify(process.env.INDEX_NAME || env.INDEX_NAME || 'comfy_outputs_v110'),
'import.meta.env.VITE_INVOKE_METHOD': JSON.stringify(process.env.INVOKE_METHOD || env.INVOKE_METHOD || 'invoke')
```

```python
# indexer.legacy/graph.py
effective_index_name = args.indexer_name or config.get("INDEX_NAME", "comfy_outputs_v110")
```

Under no circumstances should we hardcode values like this. If configuration is missing, the application should fail fast and explicitly tell the user what is missing rather than silently using an incorrect default, which can cause subtle and confusing bugs.

## Solution

1. Refactor `kaleidescope.ui/vite.config.ts` to require environment variables. If a variable is missing, throw an error.
2. Refactor `indexer.legacy/graph.py` to require `INDEX_NAME` from arguments or configuration. Raise a `ValueError` if missing.
3. Ensure `.env.local.5174` and `.env` have the necessary variables defined so development continues working.

## TODO Checklist

- [x] Update `kaleidescope.ui/vite.config.ts` to use a `requireEnv` helper.
- [x] Remove all fallback strings from `vite.config.ts`.
- [x] Update `indexer.legacy/graph.py` to raise `ValueError` instead of falling back to `"comfy_outputs_v110"`.
- [x] Verify build/run processes to ensure the error messages are clear and legitimate configurations still work.
