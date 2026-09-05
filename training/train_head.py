"""Fine-tune the DPT decoder head on metric nDSM."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Train metric nDSM head")
    parser.add_argument("--config", default="training/configs/dav2s_gamus_smoke.yaml")
    args = parser.parse_args()
    print(f"Training with config: {args.config}")


if __name__ == "__main__":
    main()
