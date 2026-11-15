#!/usr/bin/env python3
"""
landscape_utils.py

Shared constants, utilities, logbook parsers, and sampling algorithms
for Assignment 6: Fitness Landscape Exploration across representations (f0, f1, f4, fH).
"""

import os
import glob
import re
import pickle
import random
import math
from typing import List, Dict, Any, Tuple, Optional, Union, Sequence

import numpy as np

FITNESS_VALUE_INFEASIBLE_SOLUTION = -999999.0

REPRESENTATION_COLORS = {
    '0': '#2ca02c',  # Green
    '1': '#1f77b4',  # Blue
    '4': '#ff7f0e',  # Orange
    'H': '#9467bd',  # Purple
}

FORMAT_NAMES = {
    '0': '$f_0$ (Direct)',
    '1': '$f_1$ (Recurrent Tree)',
    '4': '$f_4$ (Developmental Grammar)',
    'H': '$f_H$ (Handle-based)'
}


# ==============================================================================
# 1. Loading and Extracting Candidates from Logbooks
# ==============================================================================

def find_logbooks_for_format(stats_dir: str, genformat: str) -> List[str]:
    """Finds all *.logbook.pkl files belonging to a specific genome format in stats_dir."""
    pattern = os.path.join(stats_dir, "**", f"*f{genformat}-*.logbook.pkl")
    files = glob.glob(pattern, recursive=True)
    if not files:
        pattern2 = os.path.join(stats_dir, "**", f"*{genformat}*.logbook.pkl")
        files = glob.glob(pattern2, recursive=True)
    return sorted(files)


def extract_climbing_candidates(logbook_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Extracts all (gen, fitness, genotype) records from logbook.hof_history
    across the provided logbook files. Drops exact duplicates.
    """
    candidates = []
    seen = set()

    for p in logbook_paths:
        try:
            with open(p, 'rb') as f:
                log = pickle.load(f)
            history = getattr(log, 'hof_history', [])
            run_name = os.path.splitext(os.path.basename(p))[0]
            for r in history:
                fit = float(r.get('fitness', 0.0))
                geno = r.get('genotype', '').strip()
                if not geno or fit <= FITNESS_VALUE_INFEASIBLE_SOLUTION:
                    continue
                sig = (round(fit, 8), geno)
                if sig not in seen:
                    seen.add(sig)
                    candidates.append({
                        "run": run_name,
                        "gen": r.get('gen', 0),
                        "fitness": fit,
                        "genotype": geno
                    })
        except Exception as e:
            print(f"[WARN] Failed to parse logbook '{p}': {e}")

    candidates.sort(key=lambda x: x['fitness'])
    return candidates


def identify_outlier_runs(
    stats_dir: Optional[str] = None,
    formats: List[str] = ['0', '1', '4', 'H'],
    logbooks_by_format: Optional[Dict[str, List[str]]] = None
) -> Tuple[Dict[str, set], Dict[str, Dict[str, Any]]]:
    """
    Identifies evolutionary runs whose final best fitness exceeds the standard
    Tukey boxplot upper fence: Q3 + 1.5 * IQR (matching Figure 2 boxplot outlier definition).
    """
    if logbooks_by_format:
        files = [p for flist in logbooks_by_format.values() for p in flist]
    elif stats_dir and os.path.exists(stats_dir):
        files = glob.glob(os.path.join(stats_dir, "**", "*.logbook.pkl"), recursive=True)
    else:
        files = []

    fmt_runs: Dict[str, List[Tuple[str, float]]] = {fmt: [] for fmt in formats}
    for p in files:
        m = re.search(r'[-_]f([^-.]+)[-_.]', os.path.basename(p))
        try:
            with open(p, 'rb') as f:
                log = pickle.load(f)
            hist = getattr(log, 'hof_history', [])
            if hist:
                last_hof = hist[-1]
                fmt = m.group(1) if m else last_hof.get('genotype', '').split('\n')[0].replace('//', '').strip()
                if fmt in fmt_runs:
                    run_name = os.path.splitext(os.path.basename(p))[0]
                    fit = float(last_hof.get('fitness', 0.0))
                    fmt_runs[fmt].append((run_name, fit))
        except Exception as e:
            print(f"[WARN] Error reading logbook '{p}': {e}")

    outlier_runs: Dict[str, set] = {fmt: set() for fmt in formats}
    outlier_stats: Dict[str, Dict[str, Any]] = {}

    for fmt in formats:
        items = fmt_runs.get(fmt, [])
        if len(items) < 4:
            continue

        vals = np.array([fit for _, fit in items], dtype=np.float64)
        q25, q75 = np.percentile(vals, [25, 75])
        iqr = q75 - q25
        upper_fence = q75 + 1.5 * iqr

        outliers_dict = {run_name: fit for run_name, fit in items if fit > upper_fence}
        outlier_runs[fmt] = set(outliers_dict.keys())
        outlier_stats[fmt] = {
            "n_runs": len(items),
            "q25": float(q25),
            "q75": float(q75),
            "iqr": float(iqr),
            "upper_fence": float(upper_fence),
            "outliers": outliers_dict
        }

    return outlier_runs, outlier_stats


# ==============================================================================
# 2. Uniform & Stratified Fitness Sampling
# ==============================================================================

def binning(data: Union[int, Sequence, np.ndarray, Dict], k: float = 1.0) -> int:
    """Computes default bin count using the square root choice of data size: int(sqrt(N))."""
    if isinstance(data, (int, np.integer)):
        n = int(data)
    elif isinstance(data, dict):
        n = max((len(v) for v in data.values()), default=0)
    else:
        n = len(data)
    return max(1, int(np.sqrt(k * n)))


def sample_stratified_binned_fitness(
    candidates: List[Dict[str, Any]],
    num_samples: int = 200,
    n_bins: Optional[int] = None,
    exact_num: bool = True,
    seed: Optional[int] = 42
) -> List[Dict[str, Any]]:
    """
    Selects parent solutions across the fitness domain using Stratified Random Binning.
    Partitions [F_min, F_max] into n_bins equal-width intervals, sampling k_per_bin per bin.
    """
    if not candidates:
        return []
    if len(candidates) <= num_samples:
        return candidates

    rng = random.Random(seed) if seed is not None else random

    fits = np.array([c['fitness'] for c in candidates])
    f_min, f_max = float(fits[0]), float(fits[-1])

    if f_max <= f_min:
        return rng.sample(candidates, num_samples)

    if n_bins is None:
        n_bins = binning(num_samples)
    k_per_bin = int(math.ceil(num_samples / n_bins))
    span = f_max - f_min

    bin_indices: List[List[int]] = [[] for _ in range(n_bins)]
    for idx, c in enumerate(candidates):
        f = float(c['fitness'])
        b = min(int((f - f_min) / span * n_bins), n_bins - 1)
        bin_indices[b].append(idx)

    for b in range(n_bins):
        rng.shuffle(bin_indices[b])

    selected_indices: List[int] = []
    unselected_per_bin: Dict[int, List[int]] = {}

    for b in range(n_bins):
        b_idxs = bin_indices[b]
        k = min(k_per_bin, len(b_idxs))
        selected_indices.extend(b_idxs[:k])
        unselected_per_bin[b] = b_idxs[k:]

    if exact_num:
        if len(selected_indices) > num_samples:
            excess = len(selected_indices) - num_samples
            to_drop = set(rng.sample(range(len(selected_indices)), excess))
            selected_indices = [idx for i, idx in enumerate(selected_indices) if i not in to_drop]
        elif len(selected_indices) < num_samples:
            deficit = num_samples - len(selected_indices)
            active_bins = [b for b in range(n_bins) if len(unselected_per_bin[b]) > 0]
            active_bins.sort(key=lambda b: len(unselected_per_bin[b]))

            while deficit > 0 and active_bins:
                next_active = []
                for b in active_bins:
                    if deficit == 0:
                        break
                    selected_indices.append(unselected_per_bin[b].pop(0))
                    deficit -= 1
                    if len(unselected_per_bin[b]) > 0:
                        next_active.append(b)
                active_bins = next_active

    selected_indices.sort()
    return [candidates[i] for i in selected_indices]


def sample_uniform_fitness(candidates: List[Dict[str, Any]], num_samples: int = 200) -> List[Dict[str, Any]]:
    """
    [DEPRECATED: Use sample_stratified_binned_fitness() instead]
    Selects num_samples individuals by matching an equidistant target grid spanning
    [F_min, F_max] to the closest unique solution without replacement.
    """
    if len(candidates) <= num_samples:
        return candidates

    fits = np.array([c['fitness'] for c in candidates])
    f_min, f_max = fits[0], fits[-1]

    if f_max == f_min:
        return random.sample(candidates, num_samples)

    target_grid = np.linspace(f_min, f_max, num_samples)
    selected_indices = []
    available_indices = list(range(len(candidates)))

    for target in target_grid:
        best_idx = min(available_indices, key=lambda idx: abs(candidates[idx]['fitness'] - target))
        selected_indices.append(best_idx)
        available_indices.remove(best_idx)

    selected_indices.sort()
    return [candidates[i] for i in selected_indices]

