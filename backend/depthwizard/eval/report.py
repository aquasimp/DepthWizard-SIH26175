"""Evaluation report and figure generator."""

from pathlib import Path
from typing import Dict, Union


def generate_evaluation_report(
    results_by_terrain: Dict[str, Dict[str, float]],
    out_markdown_path: Union[str, Path],
    assets_dir: Union[str, Path],
) -> None:
    """Generate docs/06-evaluation-report.md with tables and figures."""
    pass
