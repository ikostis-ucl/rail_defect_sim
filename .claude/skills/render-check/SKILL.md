---
description: Check render output after running the pipeline. Use after any runtime script finishes to verify the output looks correct.
---

## Recent output files
!`ls -lht data/output/ 2>/dev/null | head -20 || echo "data/output/ does not exist or is empty"`

## Instructions

1. Check whether an output file or directory was created.
2. If it's an MP4, flag if the file size is suspiciously small (under ~500 KB usually means a failed or near-empty render).
3. If only PNG frames are present (no MP4), note that ffmpeg may be missing or the codec fallback triggered.
4. Report what was found in 2–3 lines: path, size, and whether it looks healthy or suspect.
