# Project landing page

This folder is the source for the TSV Twin landing page, served via **GitHub Pages**.

- `index.html` — the single, self-contained page (inline CSS/JS, no build step).
- `media/` — rendered clips and stills the page embeds (see `media/README.md`).
- `.nojekyll` — tells GitHub Pages to serve the files as-is (no Jekyll processing).

## Enabling GitHub Pages (one time)

1. Push this `docs/` folder to the default branch (`main`).
2. On GitHub: **Settings → Pages**.
3. Under **Build and deployment → Source**, choose **Deploy from a branch**.
4. Set **Branch** to `main` and **Folder** to `/docs`, then **Save**.
5. After a minute the site is live at:

   ```
   https://ikostis-ucl.github.io/rail_defect_sim/
   ```

   (If the repo later moves to a UCLouvain organization, the URL becomes
   `https://<org>.github.io/rail_defect_sim/` — all paths in the page are relative, so nothing needs changing.)

## Local preview

It's just a static file — open it directly, or serve the folder:

```bash
python3 -m http.server -d docs 8000   # then visit http://localhost:8000
```

## Custom domain (optional)

Add a `CNAME` file here containing your domain (e.g. `tsvtwin.example.org`) and configure the DNS
record as described in GitHub's Pages documentation.
