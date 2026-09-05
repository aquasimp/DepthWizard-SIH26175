"""Benchmark script evaluating model performance across urban, sparse, hilly, forested terrains."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="DepthWizard Terrain Benchmark")
    parser.add_argument("--test-dir", default="data/gamus/test")
    parser.add_argument("--tags-csv", default="data/reference/terrain_tags.csv")
    args = parser.parse_args()
    print(f"Running terrain benchmarks on {args.test_dir} with {args.tags_csv}...")


if __name__ == "__main__":
    main()
