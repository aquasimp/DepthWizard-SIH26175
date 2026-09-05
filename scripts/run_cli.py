"""CLI tool for running DepthWizard inference directly on local imagery."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="DepthWizard CLI Inference")
    parser.add_argument("--input", "-i", required=True, help="Path to input image (PNG, JPG, GeoTIFF)")
    parser.add_argument("--output-dir", "-o", default="outputs", help="Directory to save output files")
    parser.add_argument("--mode", choices=["relative", "metric"], default="metric", help="Inference mode")
    parser.add_argument("--device", default="auto", help="Compute device (cuda, cpu, auto)")
    args = parser.parse_args()

    print(f"Running DepthWizard CLI in {args.mode} mode on {args.input}")


if __name__ == "__main__":
    main()
