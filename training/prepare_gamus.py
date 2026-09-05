"""Download and preprocess a stratified subset of the GAMUS dataset."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GAMUS dataset subset")
    parser.add_argument("--output-dir", default="data/gamus")
    args = parser.parse_args()
    print(f"Preparing GAMUS dataset into {args.output_dir}")


if __name__ == "__main__":
    main()
