#!/usr/bin/env python3
"""
analyze_fitness_landscape.py

Comprehensive tool for Assignment 6 - Task 1: Fitness Landscape Exploration across representations (f0, f1, f4, fH).

Pipeline:
1. Ingests evolutionary runs from pickled logbooks (*.logbook.pkl) created by FramsticksEvolutionScheduled.py.
2. Extracts candidate parent solutions from logbook.hof_history across all runs for each representation.
3. Selects a uniform distribution of parent solutions across the fitness spectrum [0, F_max] (default: >= 200).
4. Probes the local landscape by generating and evaluating N mutants-neighbors per parent (default: 20) in parallel.
5. Filters infeasible individuals and tracks mutation lethality/retries.
6. Generates scatter plots (Parent Fitness vs. Mutant Fitness) with:
   - Diagonal y = x reference line.
   - Unified fixed axes [0, global_F_max] across all representations.
   - Fraction of beneficial mutants (% improved).
7. Outputs detailed CSV data and summary statistics.

Usage:
  python scripts/analyze_fitness_landscape.py \
      --stats-dir stats/2026-10-24_06 \
      --frams-path Framsticks55 \
      --formats 0 1 4 H \
      --num-samples 200 \
      --num-mutants 20 \
      --workers 20 \
      --out-dir "assignments/Assignment 6 - Fitness Landscape Exploration/task1/results"
"""

import os
import sys
import glob
import re
import json
import pickle
import argparse
import random
from typing import List, Dict, Any, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
import matplotlib
if os.environ.get('MPLBACKEND') == 'Agg' or '--headless' in sys.argv:
    matplotlib.use('Agg')
else:
    try:
        matplotlib.use("TkAgg")
    except Exception:
        matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure framspy-download is accessible
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRAMSPY_DIR = os.path.join(REPO_ROOT, "framspy-download")
if FRAMSPY_DIR not in sys.path:
    sys.path.insert(0, FRAMSPY_DIR)

FITNESS_VALUE_INFEASIBLE_SOLUTION = -999999.0

REPRESENTATION_COLORS = {
    '0': '#2ca02c',  # Green
    '1': '#1f77b4',  # Blue
    '4': '#ff7f0e',  # Orange
    'H': '#9467bd',  # Purple
}


# ==============================================================================
# 1. Loading and Extracting Candidates from Logbooks
# ==============================================================================

def find_logbooks_for_format(stats_dir: str, genformat: str) -> List[str]:
    """Finds all *.logbook.pkl files belonging to a specific genome format in stats_dir."""
    pattern = os.path.join(stats_dir, "**", f"*f{genformat}-*.logbook.pkl")
    files = glob.glob(pattern, recursive=True)
    if not files:
        # Fallback to general pattern
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
                # Unique signature: (round(fit, 8), geno)
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

    # Sort ascending by fitness
    candidates.sort(key=lambda x: x['fitness'])
    return candidates


def identify_outlier_runs(
    stats_dir: str = None,
    formats: List[str] = ['0', '1', '4', 'H'],
    logbooks_by_format: Dict[str, List[str]] = None
) -> Tuple[Dict[str, set], Dict[str, Dict[str, Any]]]:
    """
    Identifies evolutionary runs whose final best fitness exceeds the standard
    Tukey boxplot upper fence: Q3 + 1.5 * IQR (matching Figure 2 boxplot outlier definition).
    Uses high-efficiency pure Python dictionary buckets + compiled NumPy percentile (Option C).

    Returns:
      outlier_runs: Dict mapping format -> set of outlier run names (e.g. {'HoF-f4-37.logbook', ...})
      outlier_stats: Dict mapping format -> summary statistics (q25, q75, iqr, upper_fence, n_runs, outliers)
    """
    # 1. Discover all logbook files in a single pass
    if logbooks_by_format:
        files = [p for flist in logbooks_by_format.values() for p in flist]
    elif stats_dir and os.path.exists(stats_dir):
        files = glob.glob(os.path.join(stats_dir, "**", "*.logbook.pkl"), recursive=True)
    else:
        files = []

    # 2. Ingest last HoF individual per run into format-keyed dictionary buckets
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

    # 3. High-efficiency NumPy percentile & Tukey fence calculation per format
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

        print(f"[OUTLIERS] f{fmt}: {len(outliers_dict)}/{len(items)} runs classified as outliers (Upper Fence > {upper_fence:.6f}):")
        for r_name, r_fit in sorted(outliers_dict.items(), key=lambda x: x[1], reverse=True):
            print(f"   -> {r_name}: max fitness = {r_fit:.6f}")

    return outlier_runs, outlier_stats


# ==============================================================================
# 2. Uniform Fitness Sampling
# ==============================================================================

def sample_uniform_fitness(candidates: List[Dict[str, Any]], num_samples: int = 200) -> List[Dict[str, Any]]:
    """
    Selects num_samples individuals whose fitnesses are as uniformly distributed
    as possible between min_fitness and max_fitness without large gaps.
    """
    if len(candidates) <= num_samples:
        print(f"[INFO] Candidate count ({len(candidates)}) <= requested samples ({num_samples}). Keeping all candidates.")
        return candidates

    fits = np.array([c['fitness'] for c in candidates])
    f_min, f_max = fits[0], fits[-1]

    if f_max == f_min:
        # Trivial case: all have same fitness
        return random.sample(candidates, num_samples)

    # Construct ideal target grid
    target_grid = np.linspace(f_min, f_max, num_samples)

    selected_indices = []
    available_indices = list(range(len(candidates)))

    for target in target_grid:
        # Find available candidate closest to target
        best_idx = min(available_indices, key=lambda idx: abs(candidates[idx]['fitness'] - target))
        selected_indices.append(best_idx)
        available_indices.remove(best_idx)

    selected_indices.sort()
    selected_samples = [candidates[i] for i in selected_indices]
    return selected_samples


# ==============================================================================
# 3. Parallel Mutant Generation & Neighborhood Evaluation Worker
# ==============================================================================

def _worker_probe_parents(
    worker_id: int,
    parents_batch: List[Dict[str, Any]],
    frams_path: str,
    sim_settings: str,
    optimization_target: str,
    num_mutants: int,
    max_retries: int
) -> List[Dict[str, Any]]:
    """
    Worker process: initializes an isolated FramsticksLib instance and probes
    each parent by generating num_mutants valid neighbors.
    """
    from FramsticksLib import FramsticksLib
    frams_lib = FramsticksLib(frams_path, None, sim_settings)

    results = []

    for p in parents_batch:
        p_fit = p['fitness']
        p_geno = p['genotype']
        p_gen = p.get('gen', 0)
        p_run = p.get('run', '')

        valid_mutants_found = 0
        attempts = 0

        while valid_mutants_found < num_mutants and attempts < (num_mutants * max_retries):
            attempts += 1
            try:
                # 1. Mutate
                mutant_geno = frams_lib.mutate([p_geno])[0]
                if mutant_geno == p_geno or mutant_geno == frams_lib.GENOTYPE_INVALID:
                    continue

                # 2. Evaluate
                data = frams_lib.evaluate([mutant_geno])
                eval_dict = data[0].get("evaluations", {}).get("", {})
                if optimization_target not in eval_dict:
                    continue

                mut_fit = float(eval_dict[optimization_target])
                if mut_fit <= FITNESS_VALUE_INFEASIBLE_SOLUTION or np.isnan(mut_fit):
                    continue

                # Successfully evaluated valid mutant
                valid_mutants_found += 1
                is_improved = bool(mut_fit > p_fit)

                results.append({
                    "parent_run": p_run,
                    "parent_gen": p_gen,
                    "parent_fitness": p_fit,
                    "parent_genotype": p_geno,
                    "mutant_index": valid_mutants_found,
                    "mutant_fitness": mut_fit,
                    "mutant_genotype": mutant_geno,
                    "is_improved": is_improved,
                    "fitness_delta": mut_fit - p_fit,
                    "total_attempts": attempts
                })

            except Exception:
                continue

    return results


def probe_landscape_parallel(
    parents: List[Dict[str, Any]],
    frams_path: str,
    sim_settings: str,
    optimization_target: str,
    num_mutants: int = 20,
    max_retries: int = 20,
    workers: int = 8
) -> List[Dict[str, Any]]:
    """
    Distributes parent probing across multiple worker processes.
    """
    if not parents:
        return []

    # Chunk parents across workers
    chunk_size = max(1, len(parents) // workers)
    batches = [parents[i:i + chunk_size] for i in range(0, len(parents), chunk_size)]

    all_results = []
    print(f"Probing {len(parents)} parents across {len(batches)} worker batches ({num_mutants} mutants each)...")

    with ProcessPoolExecutor(max_workers=min(workers, len(batches))) as executor:
        futures = {
            executor.submit(
                _worker_probe_parents,
                idx,
                batch,
                frams_path,
                sim_settings,
                optimization_target,
                num_mutants,
                max_retries
            ): idx for idx, batch in enumerate(batches)
        }

        completed = 0
        for fut in as_completed(futures):
            batch_res = fut.result()
            all_results.extend(batch_res)
            completed += 1
            print(f"  [Progress] Worker batch {completed}/{len(batches)} complete ({len(batch_res)} mutant evaluations).")

    return all_results


# ==============================================================================
# 4. Auxiliary Plotting: Climbers Distribution & Uniform Parents (Figure 0)
# ==============================================================================

def plot_climbers_distribution(
    climbers_data: Dict[str, np.ndarray],
    parents_data: Dict[str, np.ndarray],
    out_dir: str,
    align_axes: bool = True,
    target_metric_label: str = "Net rectilinear displacement speed"
):
    """
    Plots a 2x2 grid of compound distribution panels (one for each representation).
    Each panel contains:
      - Top: Frequency histogram of unique climbers + KDE curve (left axis)
             and uniform selected parents step distribution (right axis).
      - Bottom: Marginal horizontal quartile diagram (boxplot without dots, comparing Climbers vs. Parents).

    Parameters:
      align_axes (bool): If True (default), aligns the x-axis and both y-axes across all 4 representations,
                         suppresses inner tick labels, and minimizes whitespace between subplots.
                         If False, each panel uses its own local fitness range and count limits.
    """
    os.makedirs(out_dir, exist_ok=True)
    formats = ['0', '1', '4', 'H']

    # 1. Compute global ranges if align_axes is True
    global_x_max = 0.0
    global_climber_max_count = 0
    global_parent_max_count = 0

    n_bins = 35
    binned_data = {}

    for fmt in formats:
        #
        cfits = climbers_data.get(fmt, np.array([]))
        pfits = parents_data.get(fmt, np.array([]))
        n_c = len(cfits)
        f_max = cfits[-1] if n_c > 0 else (pfits[-1] if len(pfits) > 0 else 0.01)

        if f_max > global_x_max:
            global_x_max = f_max

        bins = np.linspace(0, f_max, n_bins + 1)
        c_counts, _ = np.histogram(cfits, bins=bins) if len(cfits) > 0 else (np.array([]), bins)
        p_counts, _ = np.histogram(pfits, bins=bins) if len(pfits) > 0 else (np.array([]), bins)

        if len(c_counts) > 0 and max(c_counts) > global_climber_max_count:
            global_climber_max_count = max(c_counts)
        if len(p_counts) > 0 and max(p_counts) > global_parent_max_count:
            global_parent_max_count = max(p_counts)

        binned_data[fmt] = {
            "cfits": cfits,
            "pfits": pfits,
            "f_max": f_max,
            "bins": bins,
            "bin_width": bins[1] - bins[0] if len(bins) > 1 else 0.001,
            "c_counts": c_counts,
            "p_counts": p_counts
        }

    # If align_axes is True, recompute bins across unified range [0, global_x_max]
    if align_axes:
        unified_bins = np.linspace(0, global_x_max, n_bins + 1)
        unified_bin_width = unified_bins[1] - unified_bins[0]
        global_climber_max_count = 0
        global_parent_max_count = 0

        for fmt in formats:
            cfits = binned_data[fmt]["cfits"]
            pfits = binned_data[fmt]["pfits"]
            c_counts, _ = np.histogram(cfits, bins=unified_bins) if len(cfits) > 0 else (np.zeros(n_bins), unified_bins)
            p_counts, _ = np.histogram(pfits, bins=unified_bins) if len(pfits) > 0 else (np.zeros(n_bins), unified_bins)

            if len(c_counts) > 0 and max(c_counts) > global_climber_max_count:
                global_climber_max_count = max(c_counts)
            if len(p_counts) > 0 and max(p_counts) > global_parent_max_count:
                global_parent_max_count = max(p_counts)

            binned_data[fmt]["bins"] = unified_bins
            binned_data[fmt]["bin_width"] = unified_bin_width
            binned_data[fmt]["c_counts"] = c_counts
            binned_data[fmt]["p_counts"] = p_counts

    # 2. Build Figure with 2x2 compound GridSpec
    fig = plt.figure(figsize=(15, 11), dpi=300)

    # Configure grid layout and spacing based on alignment
    if align_axes:
        outer_grid = fig.add_gridspec(2, 2, left=0.07, right=0.93, top=0.90, bottom=0.07, wspace=0.07, hspace=0.18)
    else:
        outer_grid = fig.add_gridspec(2, 2, left=0.08, right=0.92, top=0.90, bottom=0.07, wspace=0.28, hspace=0.32)

    for idx, fmt in enumerate(formats):
        row = idx // 2
        col = idx % 2

        subgrid = outer_grid[idx].subgridspec(2, 1, height_ratios=[4.2, 1], hspace=0.05)
        ax_main = fig.add_subplot(subgrid[0])
        ax_bottom = fig.add_subplot(subgrid[1], sharex=ax_main)

        cfits = binned_data[fmt]["cfits"]
        pfits = binned_data[fmt]["pfits"]
        bins = binned_data[fmt]["bins"]
        bin_width = binned_data[fmt]["bin_width"]
        p_counts = binned_data[fmt]["p_counts"]
        f_max = binned_data[fmt]["f_max"]
        color = REPRESENTATION_COLORS.get(fmt, '#1f77b4')

        n_climbers = len(cfits)
        n_parents = len(pfits)

        # -------------------------------------------------------------
        # TOP AXIS: Main Distribution Histogram & Parents Step Curve
        # -------------------------------------------------------------
        ax_main.set_title(
            f"f{fmt} (Pool: {n_climbers:,} Unique Climbers | {n_parents} Selected Parents)",
            fontsize=12,
            fontweight='bold',
            pad=8
        )

        counts, bin_edges, _ = ax_main.hist(
            cfits,
            bins=bins,
            color=color,
            alpha=0.45,
            edgecolor=color,
            linewidth=1.2,
            label=f'Unique Climbers Pool (N={n_climbers:,})'
        )

        # KDE line
        if n_climbers > 1:
            kde = gaussian_kde(cfits, bw_method='scott')
            x_max_eval = global_x_max if align_axes else f_max
            x_eval = np.linspace(0, x_max_eval, 300)
            y_eval = kde(x_eval) * n_climbers * bin_width
            ax_main.plot(x_eval, y_eval, color=color, linewidth=2.2, label='Climber Density (KDE)')

        # Secondary y-axis for Selected Parents
        ax2 = ax_main.twinx()
        if len(p_counts) > 0 and len(bin_edges) > 1:
            ax2.step(
                bin_edges[:-1],
                p_counts,
                where='post',
                color='#d62728',
                linewidth=1.8,
                linestyle='--',
                label=f'Selected Parents (n={n_parents}, Uniform)'
            )
            # Close step at the end
            ax2.plot([bin_edges[-2], bin_edges[-1]], [p_counts[-1], p_counts[-1]], color='#d62728', linewidth=1.8, linestyle='--')

        # -------------------------------------------------------------
        # BOTTOM AXIS: Marginal Quartile Boxplot Diagram (IQR & Median)
        # -------------------------------------------------------------
        box_data = [cfits if len(cfits) > 0 else [0], pfits if len(pfits) > 0 else [0]]
        bplot = ax_bottom.boxplot(
            box_data,
            vert=False,
            widths=0.6,
            patch_artist=True,
            showfliers=False,  # strictly omit plotting individual dots
            medianprops=dict(color='black', linewidth=1.8),
            boxprops=dict(linewidth=1.2),
            whiskerprops=dict(linewidth=1.2),
            capprops=dict(linewidth=1.2)
        )
        bplot['boxes'][0].set_facecolor(color)
        bplot['boxes'][0].set_alpha(0.65)
        bplot['boxes'][1].set_facecolor('#d62728')
        bplot['boxes'][1].set_alpha(0.65)

        ax_bottom.set_yticks([1, 2])
        if (not align_axes) or (col == 0):
            ax_bottom.set_yticklabels(['Climbers', 'Parents'], fontsize=8.5, fontweight='bold')
            ax_bottom.tick_params(axis='y', length=3)
        else:
            ax_bottom.tick_params(axis='y', labelleft=False, length=0)
            ax_bottom.set_yticklabels([])

        ax_bottom.grid(True, linestyle=':', alpha=0.45)
        ax_main.tick_params(axis='x', labelbottom=False, length=0)

        # X-axis labels and ticks on ax_bottom
        if (not align_axes) or (row == 1):
            ax_bottom.set_xlabel("Fitness", fontsize=10, fontweight='bold')
            ax_bottom.tick_params(axis='x', labelbottom=True)
        else:
            ax_bottom.tick_params(axis='x', labelbottom=False, length=0)
            ax_bottom.set_xlabel("")

        # -------------------------------------------------------------
        # Conditional Y-Axis Labeling & Limits
        # -------------------------------------------------------------
        if align_axes:
            x_lim = (0, global_x_max * 1.05)
            y_lim_main = (0, global_climber_max_count * 1.08 if global_climber_max_count > 0 else 10)
            y_lim_parent = (0, global_parent_max_count * 1.15 if global_parent_max_count > 0 else 10)
        else:
            x_lim = (0, f_max * 1.04)
            y_lim_main = (0, max(counts) * 1.08 if len(counts) > 0 else 10)
            y_lim_parent = (0, max(p_counts) * 1.25 if len(p_counts) > 0 else 10)

        ax_main.set_xlim(x_lim)
        ax_bottom.set_xlim(x_lim)
        ax_main.set_ylim(y_lim_main)
        ax2.set_ylim(y_lim_parent)

        if (not align_axes) or (col == 0):
            ax_main.set_ylabel("Unique Climbers Count", color='black', fontsize=10, fontweight='bold')
            ax_main.tick_params(axis='y', labelcolor='black')
        else:
            ax_main.tick_params(axis='y', labelleft=False)
            ax_main.set_ylabel("")

        if (not align_axes) or (col == 1):
            ax2.set_ylabel("Selected Parents Count (per bin)", color='#d62728', fontsize=10, fontweight='bold')
            ax2.tick_params(axis='y', labelcolor='#d62728')
        else:
            ax2.tick_params(axis='y', labelright=False)
            ax2.set_ylabel("")

        ax_main.grid(True, linestyle=':', alpha=0.55)

        # Legend
        lines_1, labels_1 = ax_main.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax_main.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right', fontsize=8.5, framealpha=0.92)

    alignment_str = "Aligned Axes" if align_axes else "Independent Axes"
    plt.suptitle(
        f"Distribution of Unique Evolutionary Climbers ({target_metric_label})\n"
        f"across different genetic representations (f0, f1, f4 and fH) [{alignment_str}]",
        fontsize=14,
        fontweight='bold',
        y=0.965
    )

    out_path = os.path.join(out_dir, "climbers_distribution_2x2.png")
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Saved climbers distribution plot ({alignment_str}) to: {out_path}")


# ==============================================================================
# 5. Primary Plotting: Landscape Neighborhood Probing
# ==============================================================================

def plot_fitness_landscape(
    format_data: Dict[str, pd.DataFrame],
    out_dir: str,
    optimization_target: str = "velocity",
    desaturate_outliers: bool = True,
    outlier_runs: Dict[str, set] = None
):
    """
    Generates individual and unified scatter plots comparing Parent Fitness (x)
    vs. Mutant Fitness (y) with a fixed scale [0, max_F] and y=x line.
    Calculates Pearson correlation coefficient and mutation fragility/lethality metrics.

    Parameters:
      desaturate_outliers (bool): If True (default), mutants whose parents originate from
                                  outlier evolutionary runs (exceeding Q3 + 1.5*IQR in Figure 2)
                                  are colored in neutral gray (#8c8c8c). Standard mutants retain
                                  their representation color.
      outlier_runs (Dict[str, set]): Mapping of format string to set of outlier run names.
    """
    os.makedirs(out_dir, exist_ok=True)
    if outlier_runs is None:
        outlier_runs = {}

    # 1. Determine global max fitness across all representations for fixed scale
    global_max = 0.0
    for fmt, df in format_data.items():
        if not df.empty:
            m_max = max(df['parent_fitness'].max(), df['mutant_fitness'].max())
            if m_max > global_max:
                global_max = m_max

    plot_max = global_max * 1.05 if global_max > 0 else 0.05
    print(f"Global maximum fitness across all formats: {global_max:.6f}. Axis limit set to [0, {plot_max:.6f}].")

    summary_rows = []
    summary_map = {}

    # 2. Precompute metrics and generate individual plots per genetic representation
    for fmt, df in format_data.items():
        if df.empty:
            continue

        n_mutants = len(df)
        n_improved = int(df['is_improved'].sum())
        pct_improved = (n_improved / n_mutants * 100.0) if n_mutants > 0 else 0.0

        n_neutral = int((np.abs(df['fitness_delta']) < 1e-6).sum())
        pct_neutral = (n_neutral / n_mutants * 100.0) if n_mutants > 0 else 0.0

        n_worse = int((df['fitness_delta'] < -1e-6).sum())
        pct_worse = (n_worse / n_mutants * 100.0) if n_mutants > 0 else 0.0

        # Pearson correlation coefficient (Item C)
        if n_mutants > 1 and df['parent_fitness'].std() > 0 and df['mutant_fitness'].std() > 0:
            r_val = float(df['parent_fitness'].corr(df['mutant_fitness']))
            r_str = f"r = {r_val:.3f}"
        else:
            r_val = np.nan
            r_str = "r = N/A"

        # Mutation fragility & lethality calculation (Item B)
        if 'total_attempts' in df.columns:
            parent_group = df.groupby(['parent_run', 'parent_fitness', 'parent_genotype'])['total_attempts'].max()
            tot_att = int(parent_group.sum())
            infeasible = max(0, tot_att - n_mutants)
            lethality_rate = (infeasible / tot_att * 100.0) if tot_att > 0 else 0.0
        else:
            tot_att = n_mutants
            infeasible = 0
            lethality_rate = 0.0

        # Outlier identification matching Figure 2 boxplot
        out_set = outlier_runs.get(fmt, set())
        normalized_out_set = set()
        for o in out_set:
            normalized_out_set.add(str(o).strip())
            normalized_out_set.add(str(o).replace('.logbook', '').strip())
            normalized_out_set.add(f"{str(o).strip()}.logbook")

        if 'parent_run' in df.columns and normalized_out_set:
            is_outlier = df['parent_run'].astype(str).isin(normalized_out_set)
        else:
            is_outlier = pd.Series(False, index=df.index)

        n_outliers = int(is_outlier.sum())
        n_std = n_mutants - n_outliers
        n_parents_std = int(df.loc[~is_outlier, 'parent_fitness'].nunique()) if n_std > 0 else 0
        n_parents_out = int(df.loc[is_outlier, 'parent_fitness'].nunique()) if n_outliers > 0 else 0

        metrics = {
            "Representation": f"f{fmt}",
            "Parents Sampled": df['parent_fitness'].nunique(),
            "Total Mutants": n_mutants,
            "Standard Mutants": n_std,
            "Outlier Mutants": n_outliers,
            "Better Mutants (y > x)": n_improved,
            "% Better": f"{pct_improved:.2f}%",
            "Neutral Mutants (y ~ x)": n_neutral,
            "% Neutral": f"{pct_neutral:.2f}%",
            "Worse Mutants (y < x)": n_worse,
            "% Worse": f"{pct_worse:.2f}%",
            "Pearson r": f"{r_val:.4f}" if not np.isnan(r_val) else "N/A",
            "Total Attempts": tot_att,
            "Infeasible Mutations": infeasible,
            "Lethality Rate (%)": f"{lethality_rate:.2f}%",
            "Max Parent Fitness": df['parent_fitness'].max(),
            "Max Mutant Fitness": df['mutant_fitness'].max(),
            "_n_mutants": n_mutants,
            "_n_std": n_std,
            "_n_outliers": n_outliers,
            "_n_parents_std": n_parents_std,
            "_n_parents_out": n_parents_out,
            "_is_outlier": is_outlier,
            "_n_improved": n_improved,
            "_pct_improved": pct_improved,
            "_r_val": r_val,
            "_r_str": r_str,
            "_tot_attempts": tot_att,
            "_infeasible": infeasible,
            "_lethality_rate": lethality_rate
        }
        summary_rows.append(metrics)
        summary_map[fmt] = metrics

        fig, ax = plt.subplots(figsize=(8, 7), dpi=300)

        # Plot y = x diagonal reference line
        ax.plot([0, plot_max], [0, plot_max], color='#d62728', linestyle='--', linewidth=1.5, label='y = x (Neutral)')

        # Scatter plot of mutant points (with outlier desaturation if enabled)
        if desaturate_outliers and n_outliers > 0:
            ax.scatter(
                df.loc[~is_outlier, 'parent_fitness'],
                df.loc[~is_outlier, 'mutant_fitness'],
                color=REPRESENTATION_COLORS.get(fmt, '#1f77b4'),
                alpha=0.35,
                edgecolors='none',
                s=22,
                label=f'Standard Mutants (N={n_std:,})'
            )
            ax.scatter(
                df.loc[is_outlier, 'parent_fitness'],
                df.loc[is_outlier, 'mutant_fitness'],
                color='#8c8c8c',
                alpha=0.35,
                edgecolors='none',
                s=22,
                label=f'Outlier Run Mutants (N={n_outliers:,})'
            )
        else:
            ax.scatter(
                df['parent_fitness'],
                df['mutant_fitness'],
                color=REPRESENTATION_COLORS.get(fmt, '#1f77b4'),
                alpha=0.35,
                edgecolors='none',
                s=22,
                label=f'Mutants (N={n_mutants:,})'
            )

        target_display = "Net rectilinear displacement speed" if optimization_target == "velocity" else optimization_target
        ax.set_xlim(0, plot_max)
        ax.set_ylim(0, plot_max)
        ax.set_xlabel(f"Parent Fitness ({target_display})", fontsize=12, fontweight='bold')
        ax.set_ylabel(f"Mutant Fitness ({target_display})", fontsize=12, fontweight='bold')
        ax.set_title(
            f"Fitness Landscape Neighborhood: f{fmt}\n"
            f"Better Mutants: {n_improved}/{n_mutants} ({pct_improved:.2f}%) | Pearson {r_str}",
            fontsize=13,
            pad=12
        )
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(loc='upper left', frameon=True)

        plt.tight_layout()
        single_plot_path = os.path.join(out_dir, f"landscape_scatter_f{fmt}.png")
        fig.savefig(single_plot_path)
        plt.close(fig)
        print(f"Saved landscape plot: {single_plot_path}")

    # 3. Combined 2x2 multi-panel plot with Clutter Reduction & Pearson r in Subplot Titles (Items A & C)
    fig, axes = plt.subplots(2, 2, figsize=(14, 12), dpi=300)
    axes = axes.flatten()

    all_formats = ['0', '1', '4', 'H']
    for idx, fmt in enumerate(all_formats):
        ax = axes[idx]
        row = idx // 2
        col = idx % 2
        df = format_data.get(fmt, pd.DataFrame())

        ax.plot([0, plot_max], [0, plot_max], color='#d62728', linestyle='--', linewidth=1.5, label='y = x')

        if not df.empty and fmt in summary_map:
            sm = summary_map[fmt]
            is_out = sm.get('_is_outlier', pd.Series(False, index=df.index))
            n_out = sm.get('_n_outliers', 0)
            n_st = sm.get('_n_std', len(df))

            if desaturate_outliers and n_out > 0:
                ax.scatter(
                    df.loc[~is_out, 'parent_fitness'],
                    df.loc[~is_out, 'mutant_fitness'],
                    color=REPRESENTATION_COLORS.get(fmt, '#1f77b4'),
                    alpha=0.35,
                    edgecolors='none',
                    s=18,
                    label=f'Standard (N={n_st:,})'
                )
                ax.scatter(
                    df.loc[is_out, 'parent_fitness'],
                    df.loc[is_out, 'mutant_fitness'],
                    color='#8c8c8c',
                    alpha=0.35,
                    edgecolors='none',
                    s=18,
                    label=f'Outlier runs (N={n_out:,})'
                )
            else:
                ax.scatter(
                    df['parent_fitness'],
                    df['mutant_fitness'],
                    color=REPRESENTATION_COLORS.get(fmt, '#1f77b4'),
                    alpha=0.35,
                    edgecolors='none',
                    s=18,
                    label=f'Mutants (N={sm["_n_mutants"]:,})'
                )
            ax.set_title(f"f{fmt} (% Improved: {sm['_pct_improved']:.2f}% | {sm['_r_str']})", fontsize=12, fontweight='bold')
        else:
            ax.set_title(f"f{fmt} (No Data)", fontsize=12)

        ax.set_xlim(0, plot_max)
        ax.set_ylim(0, plot_max)

        # Clutter Reduction (Item A): outer axis labels & ticks only
        if col == 0:
            ax.set_ylabel("Mutant Fitness (Net rectilinear displacement speed)", fontsize=10, fontweight='bold')
            ax.tick_params(axis='y', labelleft=True)
        else:
            ax.set_ylabel("")
            ax.tick_params(axis='y', labelleft=False)

        if row == 1:
            ax.set_xlabel("Parent Fitness (Net rectilinear displacement speed)", fontsize=10, fontweight='bold')
            ax.tick_params(axis='x', labelbottom=True)
        else:
            ax.set_xlabel("")
            ax.tick_params(axis='x', labelbottom=False)

        ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(loc='upper left', fontsize=8.5, framealpha=0.85)

    subtitle_extra = " | Outlier runs desaturated in gray" if desaturate_outliers else ""
    plt.suptitle(
        "Comparative Fitness Landscape Neighborhoods (Net rectilinear displacement speed)\n"
        "across different genetic representations (f0, f1, f4 and fH)\n"
        f"Fixed Scale: [0, {plot_max:.4f}], Diagonal y=x reference{subtitle_extra}",
        fontsize=13.5,
        fontweight='bold',
        y=0.985
    )
    fig.subplots_adjust(left=0.08, right=0.96, top=0.91, bottom=0.08, wspace=0.06, hspace=0.14)
    combined_plot_path = os.path.join(out_dir, "landscape_scatter_comparison_2x2.png")
    fig.savefig(combined_plot_path)
    plt.close(fig)
    print(f"Saved 2x2 comparison plot: {combined_plot_path}")

    # 4. Save Quantitative Summary CSV
    if summary_rows:
        sum_df = pd.DataFrame(summary_rows)
        # Drop internal helper columns before saving
        clean_sum_df = sum_df.drop(
            columns=[col for col in sum_df.columns if col.startswith('_')],
            errors='ignore'
        )
        csv_path = os.path.join(out_dir, "landscape_metrics_summary.csv")
        clean_sum_df.to_csv(csv_path, index=False)
        print(f"\n=== Landscape Metrics Summary ===")
        print(clean_sum_df.to_string(index=False))
        print(f"\nSaved metrics summary table to: {csv_path}")

        # 5. Export Markdown Summary Table (Item E)
        export_markdown_summary(summary_rows, out_dir)


# ==============================================================================
# 6. Auxiliary Plotting: Mutation Fragility & Lethality Analysis (Item B)
# ==============================================================================

def plot_mutation_fragility(
    format_data: Dict[str, pd.DataFrame],
    out_dir: str
):
    """
    Analyzes and visualizes mutation fragility / lethality rates and attempt
    distributions across representations (f0, f1, f4, fH).
    """
    os.makedirs(out_dir, exist_ok=True)
    formats = ['0', '1', '4', 'H']

    lethality_stats = []
    parent_breakdowns = []

    for fmt in formats:
        df = format_data.get(fmt, pd.DataFrame())
        if df.empty:
            continue

        n_valid = len(df)
        if 'total_attempts' in df.columns:
            parent_group = df.groupby(['parent_run', 'parent_fitness', 'parent_genotype'])['total_attempts'].max()
            tot_attempts = int(parent_group.sum())
            infeasible = max(0, tot_attempts - n_valid)
            lethality_rate = (infeasible / tot_attempts * 100.0) if tot_attempts > 0 else 0.0

            # Retries per parent beyond baseline 20
            retries = parent_group - (n_valid // len(parent_group) if len(parent_group) > 0 else 20)
            retries = retries.clip(lower=0)

            c_0 = int((retries == 0).sum())
            c_1_2 = int(((retries >= 1) & (retries <= 2)).sum())
            c_3_plus = int((retries >= 3).sum())
            n_parents = len(parent_group)
        else:
            tot_attempts = n_valid
            infeasible = 0
            lethality_rate = 0.0
            c_0 = df['parent_fitness'].nunique()
            c_1_2 = 0
            c_3_plus = 0
            n_parents = c_0

        lethality_stats.append({
            "fmt": fmt,
            "label": f"f{fmt}",
            "color": REPRESENTATION_COLORS.get(fmt, '#1f77b4'),
            "n_valid": n_valid,
            "tot_attempts": tot_attempts,
            "infeasible": infeasible,
            "lethality_rate": lethality_rate
        })

        parent_breakdowns.append({
            "fmt": fmt,
            "label": f"f{fmt}",
            "n_parents": n_parents,
            "c_0": c_0,
            "c_1_2": c_1_2,
            "c_3_plus": c_3_plus,
            "pct_fragile": ((c_1_2 + c_3_plus) / n_parents * 100.0) if n_parents > 0 else 0.0
        })

    if not lethality_stats:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    # -------------------------------------------------------------
    # Panel 1: Mutation Lethality / Infeasibility Rate (%)
    # -------------------------------------------------------------
    labels = [s["label"] for s in lethality_stats]
    rates = [s["lethality_rate"] for s in lethality_stats]
    colors = [s["color"] for s in lethality_stats]

    bars1 = ax1.bar(labels, rates, color=colors, alpha=0.85, edgecolor='black', linewidth=1.2, width=0.55)
    ax1.set_ylabel("Mutation Lethality Rate (%)", fontsize=11, fontweight='bold')
    ax1.set_title("Mutation Infeasibility & Lethality Rate\n(% of mutation attempts rejected as broken/infeasible)", fontsize=12, fontweight='bold', pad=10)
    ax1.grid(axis='y', linestyle=':', alpha=0.6)
    max_rate = max(rates) if rates else 1.0
    ax1.set_ylim(0, max(3.0, max_rate * 1.35))

    for bar, s in zip(bars1, lethality_stats):
        h = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            h + 0.07,
            f"{s['lethality_rate']:.2f}%\n({s['infeasible']:,} / {s['tot_attempts']:,})",
            ha='center',
            va='bottom',
            fontsize=9.5,
            fontweight='bold'
        )

    # -------------------------------------------------------------
    # Panel 2: Parent Fragility Breakdown (Stacked Bar Chart)
    # -------------------------------------------------------------
    p_labels = [b["label"] for b in parent_breakdowns]
    p_0 = np.array([b["c_0"] for b in parent_breakdowns])
    p_1_2 = np.array([b["c_1_2"] for b in parent_breakdowns])
    p_3_plus = np.array([b["c_3_plus"] for b in parent_breakdowns])

    w = 0.55
    ax2.bar(p_labels, p_0, width=w, label='Robust Parents (0 retries, 100% viable)', color='#2ca02c', alpha=0.8, edgecolor='black', linewidth=1.1)
    ax2.bar(p_labels, p_1_2, width=w, bottom=p_0, label='Moderate Fragility (1-2 retries)', color='#ff7f0e', alpha=0.85, edgecolor='black', linewidth=1.1)
    ax2.bar(p_labels, p_3_plus, width=w, bottom=p_0 + p_1_2, label='High Fragility (≥3 retries)', color='#d62728', alpha=0.85, edgecolor='black', linewidth=1.1)

    ax2.set_ylabel("Number of Parents (out of 200)", fontsize=11, fontweight='bold')
    ax2.set_title("Parent Genotype Fragility Breakdown\n(Number of retries required to find 20 viable mutants)", fontsize=12, fontweight='bold', pad=10)
    ax2.set_ylim(0, 265)
    ax2.grid(axis='y', linestyle=':', alpha=0.6)
    ax2.legend(loc='upper right', fontsize=9, framealpha=0.95)

    for i, b in enumerate(parent_breakdowns):
        total = b["n_parents"]
        fragile = b["c_1_2"] + b["c_3_plus"]
        pct = b["pct_fragile"]
        ax2.text(
            i,
            total + 4,
            f"{pct:.1f}% Fragile\n({fragile}/{total})",
            ha='center',
            va='bottom',
            fontsize=9.5,
            fontweight='bold'
        )

    plt.suptitle(
        "Mutational Fragility and Infeasibility Analysis across Representations (f0, f1, f4 and fH)",
        fontsize=13,
        fontweight='bold',
        y=0.98
    )
    plt.tight_layout(rect=[0, 0.03, 1, 0.94])
    out_path = os.path.join(out_dir, "landscape_fragility_comparison.png")
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Saved mutation fragility plot: {out_path}")


# ==============================================================================
# 7. Auxiliary Function: Markdown Summary Export (Item E)
# ==============================================================================

def export_markdown_summary(summary_rows: List[Dict[str, Any]], out_dir: str) -> str:
    """
    Exports quantitative landscape metrics directly into a publication-ready
    GitHub-flavored Markdown table, complete with bold formatting for peak metrics.
    """
    os.makedirs(out_dir, exist_ok=True)
    if not summary_rows:
        return ""

    # Determine maxima for bold highlighting
    max_imp = max((r.get('_pct_improved', 0.0) for r in summary_rows), default=0.0)
    max_neu = max((float(r.get('% Neutral', '0').replace('%', '')) for r in summary_rows), default=0.0)
    max_wor = max((float(r.get('% Worse', '0').replace('%', '')) for r in summary_rows), default=0.0)
    max_r = max((r.get('_r_val', -1.0) for r in summary_rows if not np.isnan(r.get('_r_val', np.nan))), default=-1.0)
    max_let = max((r.get('_lethality_rate', 0.0) for r in summary_rows), default=0.0)
    max_fit = max((r.get('Max Mutant Fitness', 0.0) for r in summary_rows), default=0.0)

    lines = [
        "| Representation | Parents Sampled (Std / Outlier) | Total Mutants (Std / Outlier) | Better Mutants ($y > x$) | **% Improved** | Neutral Mutants ($y \\approx x$) | **% Neutral** | Worse Mutants ($y < x$) | **% Worse** | Pearson $r$ | **Lethality Rate** | Max Parent Fitness | Max Mutant Fitness |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for r in summary_rows:
        rep = r['Representation']
        n_p = r['Parents Sampled']
        p_std = r.get('_n_parents_std', n_p)
        p_out = r.get('_n_parents_out', 0)
        p_str = f"{n_p} ({p_std} / {p_out})" if p_out > 0 else f"{n_p}"

        n_m = r['Total Mutants']
        m_std = r.get('_n_std', n_m)
        m_out = r.get('_n_outliers', 0)
        m_str = f"{n_m:,} ({m_std:,} / {m_out:,})" if m_out > 0 else f"{n_m:,}"

        n_b = r['Better Mutants (y > x)']
        pct_imp = r.get('_pct_improved', 0.0)
        pct_imp_str = f"**{r['% Better']}**" if abs(pct_imp - max_imp) < 1e-4 else r['% Better']

        n_neu = r['Neutral Mutants (y ~ x)']
        pct_neu = float(r.get('% Neutral', '0').replace('%', ''))
        pct_neu_str = f"**{r['% Neutral']}**" if abs(pct_neu - max_neu) < 1e-4 else r['% Neutral']

        n_wor = r['Worse Mutants (y < x)']
        pct_wor = float(r.get('% Worse', '0').replace('%', ''))
        pct_wor_str = f"**{r['% Worse']}**" if abs(pct_wor - max_wor) < 1e-4 else r['% Worse']

        r_v = r.get('_r_val', np.nan)
        r_str = f"**{r.get('Pearson r', 'N/A')}**" if (not np.isnan(r_v) and abs(r_v - max_r) < 1e-4) else r.get('Pearson r', 'N/A')

        let_v = r.get('_lethality_rate', 0.0)
        let_str = f"**{r.get('Lethality Rate (%)', '0.00%')}**" if abs(let_v - max_let) < 1e-4 else r.get('Lethality Rate (%)', '0.00%')

        mp_fit = f"{r['Max Parent Fitness']:.6f}"
        mm_fit = f"**{r['Max Mutant Fitness']:.6f}**" if abs(r['Max Mutant Fitness'] - max_fit) < 1e-6 else f"{r['Max Mutant Fitness']:.6f}"

        row_str = f"| **{rep}** | {p_str} | {m_str} | {n_b} | {pct_imp_str} | {n_neu} | {pct_neu_str} | {n_wor} | {pct_wor_str} | {r_str} | {let_str} | {mp_fit} | {mm_fit} |"
        lines.append(row_str)

    md_content = "\n".join(lines) + "\n"
    out_path = os.path.join(out_dir, "landscape_metrics_summary.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n=== Landscape Metrics Summary (Markdown) ===\n")
    print(md_content)
    print(f"Saved Markdown summary table to: {out_path}")
    return md_content


# ==============================================================================
# 8. Main CLI Entry Point
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Analyze fitness landscape and mutational neighborhoods across representations.")
    parser.add_argument('--stats-dir', default="stats", help="Directory containing .logbook.pkl files (default: stats)")
    parser.add_argument('--frams-path', default="Framsticks55", help="Path to Framsticks library folder (default: Framsticks55)")
    parser.add_argument('--sim', default="eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim", help="Sim file settings")
    parser.add_argument('--opt', default="velocity", help="Optimization criterion (default: velocity)")
    parser.add_argument('--formats', nargs='+', default=['0', '1', '4', 'H'], help="Representations to analyze (default: 0 1 4 H)")
    parser.add_argument('--num-samples', type=int, default=200, help="Number of diversified parent samples per format (default: 200)")
    parser.add_argument('--num-mutants', type=int, default=20, help="Number of mutants evaluated per parent (default: 20)")
    parser.add_argument('--max-retries', type=int, default=20, help="Max retry attempts for infeasible mutants (default: 20)")
    parser.add_argument('--workers', type=int, default=os.cpu_count(), help="Parallel worker processes (default: CPU count)")
    parser.add_argument('--out-dir', default="results/landscape", help="Output directory for data and plots")
    parser.add_argument('--plot-only', action='store_true', help="Skip mutant probing and re-generate plots from existing CSVs in out-dir")
    parser.add_argument('--align-axes', dest='align_axes', action='store_true', help="Align axes across representations in distribution plot (default: True)")
    parser.add_argument('--no-align-axes', dest='align_axes', action='store_false', help="Use local independent axes per representation")
    parser.add_argument('--desaturate-outliers', dest='desaturate_outliers', action='store_true', help="Color mutants from outlier runs in gray on Figure 3 (default: True)")
    parser.add_argument('--no-desaturate-outliers', dest='desaturate_outliers', action='store_false', help="Color all mutants in representation theme color on Figure 3")
    parser.add_argument('--force-rescan', action='store_true', help="Bypass climber pool cache and re-extract from raw logbook files")
    parser.set_defaults(align_axes=True, desaturate_outliers=True)

    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    format_data: Dict[str, pd.DataFrame] = {}

    # --------------------------------------------------------------------------
    # Climber Pool & Outlier Run Caching Mechanism (Item D):
    # Parsing and unpickling 192 multi-megabyte logbook files across 48 runs x 4
    # representations takes ~15-20 seconds. To allow instantaneous subsequent runs
    # and plot re-generations (--plot-only), extracted climber pools and identified
    # outlier runs are cached to 'climbers_cache.pkl' in the output directory.
    # --------------------------------------------------------------------------
    cache_path = os.path.join(args.out_dir, "climbers_cache.pkl")

    if args.plot_only:
        print("[INFO] --plot-only mode: Loading existing CSV data from:", args.out_dir)
        climbers_data = {}
        parents_data = {}
        outlier_runs = {}

        for fmt in args.formats:
            csv_path = os.path.join(args.out_dir, f"landscape_data_f{fmt}.csv")
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                format_data[fmt] = df
                parents_data[fmt] = np.sort(df['parent_fitness'].unique())
                print(f"  Loaded {len(df)} mutant records ({len(parents_data[fmt])} parents) for f{fmt}")
            else:
                print(f"  [WARN] No data file found for f{fmt} at {csv_path}")
                parents_data[fmt] = np.array([])

        # Check climber and outlier cache first before unpickling logbooks
        loaded_from_cache = False
        if not args.force_rescan and os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    cached_dict = pickle.load(f)
                if isinstance(cached_dict, dict) and 'climbers' in cached_dict:
                    climbers_data = cached_dict['climbers']
                    outlier_runs = cached_dict.get('outliers', {})
                    loaded_from_cache = True
                    print(f"[CACHE] Successfully loaded climber pools and outlier runs from cache: {cache_path}")
                elif isinstance(cached_dict, dict) and all(fmt in cached_dict for fmt in args.formats):
                    climbers_data = cached_dict
                    loaded_from_cache = True
                    print(f"[CACHE] Successfully loaded climber pools from cache (legacy format): {cache_path}")
            except Exception as e:
                print(f"[WARN] Failed to read climber cache ({e}). Falling back to logbook ingestion.")

        if not loaded_from_cache:
            print("[INFO] Ingesting logbooks from stats directory...")
            for fmt in args.formats:
                if args.stats_dir and os.path.exists(args.stats_dir):
                    logbooks = find_logbooks_for_format(args.stats_dir, fmt)
                    if logbooks:
                        candidates = extract_climbing_candidates(logbooks)
                        climbers_data[fmt] = np.array([c['fitness'] for c in candidates])
                        print(f"  Loaded {len(candidates)} unique climbers for f{fmt} from stats.")
                    else:
                        climbers_data[fmt] = np.array([])
                else:
                    climbers_data[fmt] = np.array([])

        # Identify outlier runs if enabled and not already loaded from cache
        if args.desaturate_outliers and not outlier_runs and args.stats_dir and os.path.exists(args.stats_dir):
            outlier_runs, _ = identify_outlier_runs(stats_dir=args.stats_dir, formats=args.formats)

        # Save climber and outlier cache for instant future runs
        if not loaded_from_cache or (args.desaturate_outliers and outlier_runs):
            try:
                cache_dict = {'climbers': climbers_data, 'outliers': outlier_runs}
                with open(cache_path, "wb") as f:
                    pickle.dump(cache_dict, f)
                print(f"[CACHE] Saved unique climber pools and outlier run mappings to: {cache_path}")
            except Exception as e:
                print(f"[WARN] Could not save climber cache: {e}")

        if any(len(v) > 0 for v in climbers_data.values()):
            print("\n--- Generating Auxiliary Climbers Distribution Plot (Figure 0) ---")
            plot_climbers_distribution(
                climbers_data=climbers_data,
                parents_data=parents_data,
                out_dir=args.out_dir,
                align_axes=args.align_axes,
                target_metric_label="Net rectilinear displacement speed"
            )

        print("\n--- Generating Landscape Scatter Plots & Summary (Figure 3) ---")
        plot_fitness_landscape(
            format_data=format_data,
            out_dir=args.out_dir,
            optimization_target=args.opt,
            desaturate_outliers=args.desaturate_outliers,
            outlier_runs=outlier_runs
        )

        print("\n--- Generating Auxiliary Mutation Fragility & Lethality Analysis (Item B) ---")
        plot_mutation_fragility(format_data, args.out_dir)
        return

    # Full Pipeline Execution
    print(f"=== Starting Fitness Landscape Analysis ===")
    print(f"Stats Directory: {args.stats_dir}")
    print(f"Formats: {args.formats}")
    print(f"Parents per format: {args.num_samples}, Mutants per parent: {args.num_mutants}")
    print(f"Parallel Workers: {args.workers}")
    print(f"Output Directory: {args.out_dir}\n")

    climbers_data = {}
    parents_data = {}

    for fmt in args.formats:
        print(f"\n--- Processing Representation f{fmt} ---")
        logbooks = find_logbooks_for_format(args.stats_dir, fmt)
        print(f"Found {len(logbooks)} logbooks for f{fmt}.")
        if not logbooks:
            print(f"[WARN] No logbooks found for f{fmt} in {args.stats_dir}. Skipping.")
            continue

        # 1. Extract climbing candidates
        candidates = extract_climbing_candidates(logbooks)
        print(f"Extracted {len(candidates)} unique climbing candidates from history.")
        if not candidates:
            print(f"[WARN] No climbing candidates extracted for f{fmt}. Skipping.")
            continue
        climbers_data[fmt] = np.array([c['fitness'] for c in candidates])

        # 2. Select uniform fitness distribution
        parents = sample_uniform_fitness(candidates, num_samples=args.num_samples)
        p_fits = [p['fitness'] for p in parents]
        parents_data[fmt] = np.sort(np.array(p_fits))
        print(f"Selected {len(parents)} parents spanning fitness [{min(p_fits):.6f}, {max(p_fits):.6f}].")

        # 3. Probe landscape in parallel
        probed_records = probe_landscape_parallel(
            parents=parents,
            frams_path=args.frams_path,
            sim_settings=args.sim,
            optimization_target=args.opt,
            num_mutants=args.num_mutants,
            max_retries=args.max_retries,
            workers=args.workers
        )

        df = pd.DataFrame(probed_records)
        format_data[fmt] = df

        # Save format CSV
        csv_path = os.path.join(args.out_dir, f"landscape_data_f{fmt}.csv")
        df.to_csv(csv_path, index=False)
        print(f"Saved {len(df)} neighborhood probing records to: {csv_path}")

    # Identify outlier runs across representations
    outlier_runs = {}
    if args.desaturate_outliers and args.stats_dir and os.path.exists(args.stats_dir):
        outlier_runs, _ = identify_outlier_runs(stats_dir=args.stats_dir, formats=args.formats)

    # Save climber and outlier cache for fast future analysis
    try:
        cache_dict = {'climbers': climbers_data, 'outliers': outlier_runs}
        with open(cache_path, "wb") as f:
            pickle.dump(cache_dict, f)
        print(f"[CACHE] Cached unique climber pools and outliers to: {cache_path}")
    except Exception as e:
        print(f"[WARN] Could not cache climber pools: {e}")

    # 4. Generate auxiliary climbers distribution plot (Figure 0)
    print("\n--- Generating Auxiliary Climbers Distribution Plot (Figure 0) ---")
    plot_climbers_distribution(
        climbers_data=climbers_data,
        parents_data=parents_data,
        out_dir=args.out_dir,
        align_axes=args.align_axes,
        target_metric_label="Net rectilinear displacement speed"
    )

    # 5. Generate landscape scatter plots and summary (Figure 3)
    print("\n--- Generating Landscape Scatter Plots & Summary (Figure 3) ---")
    plot_fitness_landscape(
        format_data=format_data,
        out_dir=args.out_dir,
        optimization_target=args.opt,
        desaturate_outliers=args.desaturate_outliers,
        outlier_runs=outlier_runs
    )

    # 6. Generate auxiliary mutation fragility plot
    print("\n--- Generating Auxiliary Mutation Fragility & Lethality Analysis (Item B) ---")
    plot_mutation_fragility(format_data, args.out_dir)

    print("\n=== All Landscape Analysis Tasks Complete ===")


if __name__ == "__main__":
    main()
