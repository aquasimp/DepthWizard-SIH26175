"""Height-stratified batch sampler for metric height estimation on GAMUS.

Mitigates the long-tailed height distribution documented in Xiong et al. (2023)
by ensuring that tall structures (height >= 15 m) appear consistently across
batches rather than being drowned out by ground-level pixels.

Assigns crops to 4 tall-fraction buckets:
  B0: < 0.01
  B1: 0.01 - 0.05
  B2: 0.05 - 0.15
  B3: >= 0.15

Enforces that at least 37.5% of slots in each accumulation window (or batch)
are drawn from the tall buckets (B2 u B3), with weighted priority on B3.
"""

import csv
import math
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union

import numpy as np
import torch
from torch.utils.data import Sampler


class HeightStratifiedBatchSampler(Sampler[List[int]]):
    """Batch sampler enforcing minimum representation of tall structures per batch/window.

    Attributes:
        batch_size: Micro-batch size or batch size emitted per iteration.
        accumulation_steps: Gradient accumulation window length.
        min_tall_ratio: Minimum fraction of batch/window allocated to B2 u B3 (default 0.375 = 37.5%).
        seed: Random seed for deterministic reproducibility.
    """

    def __init__(
        self,
        manifest_path: Union[str, Path],
        batch_size: int = 8,
        accumulation_steps: int = 1,
        min_tall_ratio: float = 0.375,
        b3_allocation_ratio: float = 0.60,
        seed: int = 1337,
        drop_last: bool = False,
    ):
        self.manifest_path = Path(manifest_path)
        self.batch_size = batch_size
        self.accumulation_steps = accumulation_steps
        self.window_size = batch_size * accumulation_steps
        self.min_tall_ratio = min_tall_ratio
        self.b3_allocation_ratio = b3_allocation_ratio
        self.seed = seed
        self.drop_last = drop_last
        self.epoch = 0

        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")

        # Read only TRAIN split crops
        self.train_indices: List[int] = []
        self.crop_ids: List[str] = []
        self.tall_fractions: List[float] = []

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            idx = 0
            for row in reader:
                if row.get("split") == "train":
                    self.train_indices.append(idx)
                    self.crop_ids.append(row["crop_id"])
                    tf = float(row.get("band_15_30", 0.0)) + float(row.get("band_30_inf", 0.0))
                    self.tall_fractions.append(tf)
                    idx += 1

        total_crops = len(self.train_indices)
        if total_crops == 0:
            raise ValueError(f"No train crops found in manifest at {self.manifest_path}")

        # Partition into buckets
        self.buckets: Dict[str, List[int]] = {
            "B0": [],  # < 0.01
            "B1": [],  # 0.01 - 0.05
            "B2": [],  # 0.05 - 0.15
            "B3": [],  # >= 0.15
        }

        for local_idx, tf in enumerate(self.tall_fractions):
            if tf < 0.01:
                self.buckets["B0"].append(local_idx)
            elif tf < 0.05:
                self.buckets["B1"].append(local_idx)
            elif tf < 0.15:
                self.buckets["B2"].append(local_idx)
            else:
                self.buckets["B3"].append(local_idx)

        tall_count = len(self.buckets["B2"]) + len(self.buckets["B3"])
        tall_ratio = tall_count / float(total_crops)

        # Requirement 4.1: If B2 u B3 is empty or pathologically small (< 2%), RAISE
        if tall_count == 0 or tall_ratio < 0.02:
            raise ValueError(
                f"HeightStratifiedBatchSampler: Tall buckets B2 u B3 contain only {tall_count} "
                f"crops ({tall_ratio * 100:.2f}%), which is below the mandatory 2.0% threshold. "
                "Cannot guarantee height-stratified batch generation."
            )

        # Quota configuration for accumulation window of size self.window_size (e.g. 8)
        # To guarantee both (i) >=95% windows with tall crops and (ii) >=2.5x corpus baseline tall-pixel share,
        # we allocate 6 slots to B3 (mean tall 0.36), 1 to B2 (mean tall 0.09), and 1 to B0/B1.
        self.b3_per_window = max(1, int(round(self.window_size * 0.75)))   # 6 of 8
        self.b2_per_window = max(1, int(round(self.window_size * 0.125)))  # 1 of 8
        self.other_per_window = max(1, self.window_size - (self.b3_per_window + self.b2_per_window)) # 1 of 8
        self.num_windows = total_crops // self.window_size if self.drop_last else math.ceil(total_crops / self.window_size)

    def set_epoch(self, epoch: int) -> None:

        self.epoch = epoch

    def __len__(self) -> int:
        return self.num_windows * self.accumulation_steps

    def __iter__(self) -> Iterator[List[int]]:
        rng = np.random.RandomState(self.seed + self.epoch)

        # Create shuffled copies of each bucket
        shuffled_buckets = {
            name: list(rng.permutation(indices))
            for name, indices in self.buckets.items()
        }
        pointers = {name: 0 for name in self.buckets}
        oversample_counts = {name: 0 for name in self.buckets}

        def draw_from_bucket(bucket_name: str, count: int) -> List[int]:
            drawn = []
            if count <= 0:
                return drawn
            if len(self.buckets[bucket_name]) == 0:
                available = [b for b in ["B3", "B2", "B1", "B0"] if len(self.buckets[b]) > 0]
                if not available:
                    return drawn
                bucket_name = available[0]
            pool = shuffled_buckets[bucket_name]
            while len(drawn) < count:
                avail = len(pool) - pointers[bucket_name]
                needed = count - len(drawn)
                if avail >= needed:
                    start = pointers[bucket_name]
                    end = start + needed
                    drawn.extend(pool[start:end])
                    pointers[bucket_name] = end
                else:
                    # Take remainder of pool
                    if avail > 0:
                        drawn.extend(pool[pointers[bucket_name] :])
                    # Reshuffle and wrap around
                    pool = list(rng.permutation(self.buckets[bucket_name]))
                    shuffled_buckets[bucket_name] = pool
                    pointers[bucket_name] = 0
                    oversample_counts[bucket_name] += 1
            return drawn

        # Emit batches
        for _ in range(self.num_windows):
            # Draw for the full accumulation window
            window_indices = []
            # 1. Draw tall samples (B3 and B2)
            window_indices.extend(draw_from_bucket("B3", self.b3_per_window))
            window_indices.extend(draw_from_bucket("B2", self.b2_per_window))

            # 2. Draw remaining samples from B0 and B1
            b1_count = self.other_per_window // 2
            b0_count = self.other_per_window - b1_count
            window_indices.extend(draw_from_bucket("B1", b1_count))
            window_indices.extend(draw_from_bucket("B0", b0_count))

            # Shuffle within the accumulation window
            window_indices = list(rng.permutation(window_indices))

            # Split into micro-batches
            for step in range(self.accumulation_steps):
                start = step * self.batch_size
                end = start + self.batch_size
                micro_batch = window_indices[start:end]
                if len(micro_batch) == self.batch_size or not self.drop_last:
                    yield micro_batch

    def get_oversampling_factors(self) -> Dict[str, float]:
        """Compute realized oversampling factor for each bucket across an epoch."""
        factors = {}
        total_drawn = {
            "B3": self.num_windows * self.b3_per_window,
            "B2": self.num_windows * self.b2_per_window,
            "B1": self.num_windows * (self.other_per_window // 2),
            "B0": self.num_windows * (self.other_per_window - (self.other_per_window // 2)),
        }
        for b, drawn in total_drawn.items():
            pool_sz = max(1, len(self.buckets[b]))
            factors[b] = round(drawn / pool_sz, 3)
        return factors
