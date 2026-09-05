"""Evaluate fine-tuned checkpoint against frozen baseline."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate checkpoint")
    parser.add_argument("--checkpoint", default="models/dav2s_gamus_ft_v1.pth")
    args = parser.parse_args()
    print(f"Evaluating checkpoint: {args.checkpoint}")


if __name__ == "__main__":
    main()
