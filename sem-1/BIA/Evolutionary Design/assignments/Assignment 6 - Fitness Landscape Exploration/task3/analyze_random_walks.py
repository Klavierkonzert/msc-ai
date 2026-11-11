#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
analyze_random_walks.py: Streamlined pipeline for Assignment 6 - Task 3:
Fitness Landscape Exploration via Random Walks ("Solution as Memory").

1. Samples 20 stratified parents across [0, F_max] per representation from Task 1 logbooks.
2. Generates Figure 0: Climber pool boxplots vs. selected parent uniformity (continuous KS test).
3. Executes 30-step sequential chained random walks (S_0 -> S_1 -> ... -> S_30) in parallel.
4. Generates Figure 1 (2x2 comparative grid) and standalone trajectory plots.
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
if os.environ.get('MPLBACKEND') == 'Agg' or '--headless' in sys.argv:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import multiprocessing as mp

# Paths & shared utilities
TASK3_DIR = os.path.dirname(os.path.abspath(__file__))
ASSIGNMENT_DIR = os.path.abspath(os.path.join(TASK3_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(ASSIGNMENT_DIR, "..", ".."))

for p in [ASSIGNMENT_DIR, os.path.join(REPO_ROOT, "framspy-download"), os.path.join(REPO_ROOT, "scripts")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from landscape_utils import (
    extract_climbing_candidates, sample_stratified_binned_fitness,
    REPRESENTATION_COLORS, FORMAT_NAMES, FITNESS_VALUE_INFEASIBLE_SOLUTION
)

TIER_COLORS = ['#d62728', '#ff7f0e', '#2a86c6', '#3ecb58']  # Worst to Best: Red, Orange, Light Blue, Light Green
TIER_LABELS = ['Worst 5 (Red)', 'Low-Mid 5 (Orange)', 'High-Mid 5 (Blue)', 'Best 5 (Green)']


# ==============================================================================
# 1. Parent Selection & Continuous Uniformity
# ==============================================================================

def select_parents(formats, stats_dir, num_parents=20, seed=42):
    """Samples stratified parents across [0, F_max] and computes continuous KS test."""
    parents_by_fmt, climbers_by_fmt, stats_by_fmt = {}, {}, {}

    for fmt in formats:
        files = [os.path.join(stats_dir, f) for f in os.listdir(stats_dir) if f.startswith(f"HoF-f{fmt}-") and f.endswith(".logbook.pkl")]
        cands = extract_climbing_candidates(files)
        climbers_by_fmt[fmt] = np.sort([c['fitness'] for c in cands])

        parents = sample_stratified_binned_fitness(cands, num_samples=num_parents, exact_num=True, seed=seed)
        parents.sort(key=lambda x: x['fitness'])
        for idx, p in enumerate(parents):
            p.update({'seed_id': idx, 'tier': min(idx // 5, 3), 'format': fmt})

        fits = np.array([p['fitness'] for p in parents])
        ks = stats.kstest(fits, 'uniform', args=(0.0, fits.max()))
        parents_by_fmt[fmt] = parents
        stats_by_fmt[fmt] = {'ks_stat': float(ks.statistic), 'ks_p': float(ks.pvalue), 'f_max': float(fits.max())}
        print(f"[SELECT] f{fmt}: Sampled {len(parents)} parents. KS: D={ks.statistic:.3f} (p={ks.pvalue:.4f})")

    return parents_by_fmt, climbers_by_fmt, stats_by_fmt


# ==============================================================================
# 2. Figure 0: Climber Pool vs. Selected Parent Uniformity
# ==============================================================================

def plot_figure_0(climbers_by_fmt, parents_by_fmt, stats_by_fmt, out_path):
    """Figure 0: Climber fitness boxplots overlaid with 20 stratified parent points and KS metrics."""
    formats = list(parents_by_fmt.keys())
    fig, ax = plt.subplots(figsize=(11.0, 6.8))
    rng = np.random.RandomState(42)

    for i, fmt in enumerate(formats):
        cfits = climbers_by_fmt[fmt]
        fits = np.array([p['fitness'] for p in parents_by_fmt[fmt]])
        c = REPRESENTATION_COLORS[fmt]

        # Candidate pool boxplot (transparent, matching-color median)
        ax.boxplot(cfits, positions=[i], widths=0.48, patch_artist=True, showfliers=False,
                   boxprops=dict(facecolor=c, alpha=0.22, edgecolor=c, linewidth=1.6),
                   whiskerprops=dict(color=c, alpha=0.55, linewidth=1.3),
                   capprops=dict(color=c, alpha=0.55, linewidth=1.3),
                   medianprops=dict(color=c, alpha=0.9, linewidth=2.4))

        # 20 selected parent points colored by tier
        for t in range(4):
            t_fits = fits[t*5 : (t+1)*5]
            ax.scatter(i + rng.uniform(-0.13, 0.13, len(t_fits)), t_fits, c=TIER_COLORS[t],
                       s=54, edgecolors='black', linewidths=0.5, zorder=5, alpha=0.92)

    # Legends
    stat_handles = [Patch(facecolor=REPRESENTATION_COLORS[fmt], edgecolor=REPRESENTATION_COLORS[fmt], alpha=0.45,
                          label=rf"$f_{{{fmt}}} \rightarrow \mathrm{{KS}}\ D={stats_by_fmt[fmt]['ks_stat']:.3f}$ ($p={stats_by_fmt[fmt]['ks_p']:.3f}$)")
                    for fmt in formats]
    tier_handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=TIER_COLORS[3-i], markeredgecolor='black',
                           markersize=8.5, label=TIER_LABELS[3-i]) for i in range(4)]

    leg1 = ax.legend(handles=stat_handles, loc='upper left', fontsize=9.2, framealpha=0.92,
                     title="Original distribution boxplots vs.\nuniformity metrics of selected samples")
    leg2 = ax.legend(handles=tier_handles, loc='upper right', fontsize=9.5, framealpha=0.92,
                     title="Selected Parent Tiers")
    ax.add_artist(leg1)

    ax.set_xticks(range(len(formats)))
    ax.set_xticklabels([FORMAT_NAMES[fmt] for fmt in formats], fontsize=11)
    ax.set_ylabel(r"Fitness (Net Rectilinear Displacement Speed)", fontsize=11.5, fontweight='bold')
    ax.set_title("Figure 0: Distribution of Fitness Values across Evolutionary Climbers\nvs. Uniformity of Selected Parents ($N=20$)",
                 fontsize=12.0, fontweight='bold', pad=12)
    ax.grid(True, linestyle=':', alpha=0.6, axis='y')
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[PLOT] Saved Figure 0 to: {out_path}")


# ==============================================================================
# 3. Chained Random Walk Simulation
# ==============================================================================

def _worker_walk(batch, frams_path, sim_settings, walk_steps, max_retries):
    """Evaluates 30-step random walk trajectories for a batch of parents."""
    from FramsticksLib import FramsticksLib
    flib = FramsticksLib(frams_path, None, sim_settings)
    flib.PRINT_FRAMSTICKS_OUTPUT = False
    flib.GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL = False

    records = []
    for parent in batch:
        fmt, seed_id, tier = parent['format'], parent['seed_id'], parent['tier']
        cur_geno, cur_fit = parent['genotype'], float(parent['fitness'])
        records.append({'format': fmt, 'seed_id': seed_id, 'tier': tier, 'step': 0, 'fitness': cur_fit, 'genotype': cur_geno})

        for step in range(1, walk_steps + 1):
            valid, attempts = False, 0
            while not valid and attempts < max_retries:
                attempts += 1
                try:
                    m_geno = flib.mutate([cur_geno])[0]
                    if not m_geno or m_geno == cur_geno or m_geno == flib.GENOTYPE_INVALID:
                        continue
                    data = flib.evaluate([m_geno])
                    m_fit = float(data[0].get("evaluations", {}).get("", {}).get('velocity', FITNESS_VALUE_INFEASIBLE_SOLUTION))
                    if m_fit > FITNESS_VALUE_INFEASIBLE_SOLUTION and not np.isnan(m_fit) and m_fit >= 0:
                        valid = True
                        cur_geno, cur_fit = m_geno, m_fit
                except Exception:
                    continue

            if not valid:
                cur_fit = 0.0
            records.append({'format': fmt, 'seed_id': seed_id, 'tier': tier, 'step': step, 'fitness': cur_fit, 'genotype': cur_geno})
    return records


def run_random_walks(parents_by_fmt, frams_path, sim_settings, walk_steps=30, max_retries=50, workers=8):
    """Executes random walks in parallel across workers."""
    all_parents = [p for plist in parents_by_fmt.values() for p in plist]
    chunk_size = max(1, len(all_parents) // workers)
    batches = [all_parents[i:i + chunk_size] for i in range(0, len(all_parents), chunk_size)]

    with mp.Pool(processes=min(workers, len(batches))) as pool:
        results = pool.starmap(_worker_walk, [(b, frams_path, sim_settings, walk_steps, max_retries) for b in batches])

    df = pd.DataFrame([rec for b in results for rec in b])
    return {fmt: df[df['format'] == fmt].sort_values(['seed_id', 'step']) for fmt in parents_by_fmt}


# ==============================================================================
# 4. Trajectory Plotting
# ==============================================================================

def plot_trajectories(dfs_by_fmt, out_dir, walk_steps=30, plot_individual=False):
    """Generates 2x2 comparative grid and optional individual trajectory plots."""
    formats = list(dfs_by_fmt.keys())
    global_max = max(df['fitness'].max() for df in dfs_by_fmt.values())
    y_lim = [-global_max * 0.02, global_max * 1.05]

    # Figure 1: 2x2 Grid
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), sharex=True, sharey=True)
    tier_legend = [Line2D([0], [0], color=TIER_COLORS[3-i], lw=2.2, marker='o', markersize=5, label=TIER_LABELS[3-i]) for i in range(4)]

    for idx, fmt in enumerate(formats):
        ax = axes.flatten()[idx]
        df = dfs_by_fmt[fmt]
        for sid in sorted(df['seed_id'].unique(), reverse=True):
            sdf = df[df['seed_id'] == sid].sort_values('step')
            ax.plot(sdf['step'], sdf['fitness'], color=TIER_COLORS[sdf['tier'].iloc[0]], lw=1.5, alpha=0.52,
                    marker='o', markersize=3.6, markeredgecolor='black', markeredgewidth=0.2)

        ax.set_title(FORMAT_NAMES[fmt], fontsize=12.5, fontweight='bold', pad=8)
        ax.set_xlim(-0.5, walk_steps + 0.5)
        ax.set_ylim(y_lim)
        ax.grid(True, linestyle=':', alpha=0.6)
        if idx in [2, 3]: ax.set_xlabel(r"Mutation Step in Sequence ($k = 0 \dots 30$)", fontsize=11, fontweight='bold')
        if idx in [0, 2]: ax.set_ylabel(r"Fitness (Locomotion Velocity $v$)", fontsize=11, fontweight='bold')

    fig.legend(handles=tier_legend, loc='lower center', ncol=4, fontsize=10.5, framealpha=0.92, edgecolor='gray', bbox_to_anchor=(0.5, 0.015))
    plt.suptitle("Figure 1: Sequential Random Walk Fitness Trajectories across Genetic Encodings\n"
                 r"Chained Mutations Initiated at 4 Distinct Fitness Tiers",
                 fontsize=13.5, fontweight='bold', y=0.985)
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    fig1_path = os.path.join(out_dir, "random_walk_trajectories_2x2.png")
    plt.savefig(fig1_path, dpi=300)
    plt.close()
    print(f"[PLOT] Saved Figure 1 to: {fig1_path}")

    # Standalone individual representation plots (optional, False by default)
    if plot_individual:
        for fmt, df in dfs_by_fmt.items():
            fig, ax = plt.subplots(figsize=(9, 6.2))
            for sid in sorted(df['seed_id'].unique(), reverse=True):
                sdf = df[df['seed_id'] == sid].sort_values('step')
                ax.plot(sdf['step'], sdf['fitness'], color=TIER_COLORS[sdf['tier'].iloc[0]], lw=1.6, alpha=0.52,
                        marker='o', markersize=4.0, markeredgecolor='black', markeredgewidth=0.25)
            f_max = df['fitness'].max()
            ax.set_xlim(-0.5, walk_steps + 0.5)
            ax.set_ylim(-f_max * 0.02, f_max * 1.05)
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.set_xlabel(r"Mutation Step in Sequence ($k = 0 \dots 30$)", fontsize=11)
            ax.set_ylabel(r"Fitness (Net Rectilinear Displacement Speed)", fontsize=11, fontweight='bold')
            ax.set_title(f"Random Walk Trajectories: {FORMAT_NAMES[fmt]} (20 Lines)", fontsize=12.5, pad=10)
            ax.legend(handles=tier_legend, loc='upper right', fontsize=9.5, framealpha=0.92)
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, f"random_walk_trajectories_f{fmt}.png"), dpi=300)
            plt.close()


# ==============================================================================
# 5. Main Entry Point
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Task 3: Random Walk Fitness Landscape Exploration.")
    parser.add_argument('--formats', nargs='+', default=['0', '1', '4', 'H'])
    parser.add_argument('--stats-dir', default=os.path.join(ASSIGNMENT_DIR, "task1", "stats", "2026-10-24_19"))
    parser.add_argument('--frams-path', default=os.path.join(REPO_ROOT, "Framsticks55"))
    parser.add_argument('--sim-settings', default="eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim")
    parser.add_argument('--out-dir', default=os.path.join(TASK3_DIR, "results", "random_walks"))
    parser.add_argument('--num-parents', type=int, default=20)
    parser.add_argument('--walk-steps', type=int, default=30)
    parser.add_argument('--max-retries', type=int, default=50)
    parser.add_argument('--workers', type=int, default=min(os.cpu_count() or 1, 24))
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--plot-individual', action='store_true', help="Also generate individual 1x1 trajectory plots per representation (default: False)")
    parser.add_argument('--plot-only', action='store_true')
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Sample 20 Stratified Parents and Extract Climber Pool
    parents_by_fmt, climbers_by_fmt, stats_by_fmt = select_parents(
        formats=args.formats,
        stats_dir=args.stats_dir,
        num_parents=args.num_parents,
        seed=args.seed
    )

    plot_figure_0(climbers_by_fmt, parents_by_fmt, stats_by_fmt, os.path.join(args.out_dir, "random_walk_parents_distribution.png"))

    dfs_by_fmt = {}
    need_sim = False
    for fmt in args.formats:
        csv_path = os.path.join(args.out_dir, f"random_walk_data_f{fmt}.csv")
        if args.plot_only and os.path.exists(csv_path):
            dfs_by_fmt[fmt] = pd.read_csv(csv_path)
        else:
            need_sim = True

    if need_sim:
        dfs_by_fmt = run_random_walks(parents_by_fmt, args.frams_path, args.sim_settings, args.walk_steps, args.max_retries, args.workers)
        for fmt, df in dfs_by_fmt.items():
            df.to_csv(os.path.join(args.out_dir, f"random_walk_data_f{fmt}.csv"), index=False)

    plot_trajectories(dfs_by_fmt, args.out_dir, args.walk_steps, plot_individual=args.plot_individual)
    print("\n[DONE] Task 3 random walk pipeline completed successfully.")


if __name__ == "__main__":
    main()
