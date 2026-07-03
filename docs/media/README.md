# Landing-page media

Drop rendered clips and stills here; the landing page (`docs/index.html`) references them by relative path.

## Current files

The Output gallery in `index.html` shows one card per camera rig. Each `<source>` points at:

| File | Camera rig | Notes |
|---|---|---|
| `demo_birds_eye.mp4` | top-down bird's-eye | the longest clip; the flyover the hero animation mirrors |
| `demo_drone_three_quarter.mp4` | angled drone (¾ view) | visibly shows a gauge-widening defect |
| `demo_low_inspection.mp4` | low, near-railhead inspection | dramatic vanishing-point perspective |
| `demo_windshield.mp4` | driver's-eye / cab windshield | track receding to the horizon |

These are short draft renders acting as placeholders. To replace one, drop a new file at the
same path (or edit the `<source src="…">` in `index.html`). All clips are 16:9; the gallery
crops with `object-fit: cover`. GIFs or stills work too.

## Producing web-friendly media

Render a clip, then transcode it small and fast-starting so it streams well on the page:

```bash
# render a preview clip
./runtime/draft_preview.sh

# transcode to a lean, web-optimized mp4 (~1280px wide)
ffmpeg -i data/output/<run_name>/<file>.mp4 \
  -vf "scale=1280:-2" -c:v libx264 -crf 24 -preset slow \
  -movflags +faststart -an docs/media/flyover.mp4

# grab a poster frame
ffmpeg -i docs/media/flyover.mp4 -vframes 1 docs/media/flyover-poster.jpg

# (optional) a looping GIF instead
ffmpeg -i docs/media/flyover.mp4 -vf "fps=12,scale=800:-1" docs/media/flyover.gif
```

## Wiring it into the page

In `docs/index.html`, find the `media-slot` blocks in the **Output** section and replace the
`<div class="placeholder">…</div>` with the commented-out `<video>` example already shown there:

```html
<video autoplay muted loop playsinline poster="media/flyover-poster.jpg">
  <source src="media/flyover.mp4" type="video/mp4" />
</video>
```

Keep videos `muted` + `playsinline` so they autoplay on mobile browsers.
