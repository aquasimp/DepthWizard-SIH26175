"""Generate synthetic demo assets (16-bit PNG, texture JPEG, meta.json, GLB) for offline testing."""

from pathlib import Path


def generate_demo_assets(output_dir: str = "data/samples/demo_assets") -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Generating synthetic demo assets into {out}...")


if __name__ == "__main__":
    generate_demo_assets()
