# TSV Twin - Railway Video Generator

This project generates a procedural top-down railway flyover video in Blender.

## Installation

### 1. Blender

Download and install **Blender 5.1+** from [blender.org/download](https://www.blender.org/download/).

**Linux — system package (requires root):**
```bash
sudo apt install blender          # Ubuntu / Debian
sudo dnf install blender          # Fedora
sudo pacman -S blender            # Arch
```

**Linux — portable install (no root):**
```bash
# Download the official tarball from blender.org, then:
tar -xf blender-5.1.0-linux-x64.tar.xz -C ~/apps/
echo 'export PATH="$HOME/apps/blender-5.1.0-linux-x64:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**macOS:**
```bash
brew install --cask blender
```

**Windows:**
Download the installer from [blender.org/download](https://www.blender.org/download/) and make sure the install directory is on your `PATH`.

Verify:
```bash
blender --version
```

### 2. ffmpeg

ffmpeg is required for assembling the final `.mp4` when Blender cannot write video directly.

**Linux — system package (requires root):**
```bash
sudo apt install ffmpeg            # Ubuntu / Debian
sudo dnf install ffmpeg            # Fedora
sudo pacman -S ffmpeg              # Arch
```

**Linux — portable install (no root):**
```bash
# Download a static build from https://johnvansickle.com/ffmpeg/
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg-release-amd64-static.tar.xz
mkdir -p ~/bin
cp ffmpeg-*-static/ffmpeg ~/bin/
# Make sure ~/bin is on your PATH (add to ~/.bashrc if not already):
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org/download](https://ffmpeg.org/download.html) and add the `bin/` folder to your `PATH`.

Verify:
```bash
ffmpeg -version
```

### 3. Clone the repository

```bash
git clone <repo-url> tsv_twin
cd tsv_twin
```

### 4. Install Python dependencies with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install the project:

```bash
uv sync
```

This installs all dependencies (including `bpy` and `configargparse`) defined in `pyproject.toml`.

---

## Structure

- `run_video_gen.py`: canonical driver script (Blender CLI entrypoint)
- `app/config/`: runtime settings and mode presets
- `app/core/`: orchestration pipeline
- `app/scene/`: scene cleanup, world setup, and lighting
- `app/render/`: render output and engine settings
- `app/materials/`: procedural materials
- `app/geometry/`: track and environment geometry builders
- `app/camera/`: camera setup and movement animation


## Run

```bash
blender --background --python run_video_gen.py
```

By default, renders are written to `data/output/rail_render_<timestamp>/rail_render_<timestamp>.mp4`.

If your Blender build cannot write `FFMPEG` output directly, the pipeline renders a temporary PNG sequence and then auto-assembles a single `.mp4` using system `ffmpeg`.

## Configuration Overrides

Use Blender argument passthrough (`--`) to pass script flags:

```bash
blender --background --python run_video_gen.py -- --fps 12 --duration-seconds 10
blender --background --python run_video_gen.py -- --fps 24 --resolution-x 1920 --resolution-y 1080
```

## Preset Run Scripts

Preset bash scripts are available under `runtime/` with full commands included:

- `runtime/draft_quick.sh`
- `runtime/draft_preview.sh`
- `runtime/final_fullhd.sh`
- `runtime/final_4k.sh`

Run any preset directly:

```bash
./runtime/draft_quick.sh
./runtime/final_fullhd.sh
```

You can still pass extra overrides to any preset script:

```bash
./runtime/draft_quick.sh --duration-seconds 12
./runtime/final_fullhd.sh --output-filename client_take_2.mp4
```

## Common Overrides

```bash
blender --background --python run_video_gen.py -- --duration-seconds 5
blender --background --python run_video_gen.py -- --output-filename out.mp4
```
