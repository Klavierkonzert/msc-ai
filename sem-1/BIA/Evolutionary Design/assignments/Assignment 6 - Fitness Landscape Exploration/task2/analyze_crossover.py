#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
analyze_crossover.py: Lean, end-to-end pipeline for Assignment 6 - Task 2:
Fitness Landscape Exploration under Crossover Recombination.

1. Reuses the 200 uniform parents per representation from Task 1 (landscape_data_f*.csv).
2. Generates 500 parent pairs across 5 shuffle rounds (100 pairs/round).
3. Evaluates 8 offspring per pair (4 in each reciprocal direction: P1 x P2 and P2 x P1),
   yielding 4,000 evaluations per format (16,000 total across f0, f1, f4, fH).
4. Rejects invalid/infeasible offspring (retry up to 20x), tracking crossover lethality.
5. Computes quantitative metrics: Positive Heterosis Index (H+), Heritability (h^2), etc.
6. Generates 2D mid-parent scatter plots (Figure 1) and interactive 3D Plotly HTML files.
"""

import os
import sys
import argparse
import time
import pickle
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
import plotly.graph_objects as go
import multiprocessing as mp
import statsmodels.api as sm

# Setup paths to import from shared scripts and framspy
TASK2_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(TASK2_DIR, "..", "..", ".."))
for p in [os.path.join(REPO_ROOT, "scripts"), os.path.join(REPO_ROOT, "framspy-download")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from analyze_fitness_landscape import REPRESENTATION_COLORS, FITNESS_VALUE_INFEASIBLE_SOLUTION

FORMAT_NAMES = {'0': '$f_0$ (Direct)', '1': '$f_1$ (Recurrent Tree)', '4': '$f_4$ (Developmental Grammar)', 'H': '$f_H$ (Handle-based)'}


# ==============================================================================
# 1. Pairing & Multiprocessing Worker
# ==============================================================================

def generate_shuffled_pairs(parents: List[Dict[str, Any]], rounds: int = 5, seed: int = 42) -> List[Tuple]:
    """Generates ordered pairs (p_low, p_high, round_id, pair_id) across shuffle rounds."""
    pairs = []
    for r in range(rounds):
        perm = np.random.RandomState(seed + r * 1000).permutation(len(parents))
        for i in range(0, len(parents) - 1, 2):
            p1, p2 = parents[perm[i]], parents[perm[i+1]]
            p_low, p_high = (p1, p2) if p1['parent_fitness'] <= p2['parent_fitness'] else (p2, p1)
            pairs.append((p_low, p_high, r + 1, len(pairs)))
    return pairs


def _worker_crossover(batch, frams_path, sim_settings, reps, max_retries):
    """Worker process evaluating crossover offspring for a chunk of parent pairs."""
    from FramsticksLib import FramsticksLib
    flib = FramsticksLib(frams_path, None, sim_settings)
    flib.PRINT_FRAMSTICKS_OUTPUT = False
    flib.GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL = False

    records, eps = [], 1e-6
    for p_low, p_high, s_round, pair_id in batch:
        p_low_f, p_high_f = float(p_low['parent_fitness']), float(p_high['parent_fitness'])
        p_mid_f = 0.5 * (p_low_f + p_high_f)

        for dir_name, g_base, g_donor in [("low_x_high", p_low['parent_genotype'], p_high['parent_genotype']),
                                          ("high_x_low", p_high['parent_genotype'], p_low['parent_genotype'])]:
            for _ in range(reps):
                attempts, valid = 0, False
                while not valid and attempts < max_retries:
                    attempts += 1
                    try:
                        off_geno = flib.crossOver(g_base, g_donor)
                        if not off_geno or off_geno == flib.GENOTYPE_INVALID:
                            continue
                        data = flib.evaluate([off_geno])
                        eval_dict = data[0].get("evaluations", {}).get("", {})
                        off_fit = float(eval_dict.get('velocity', FITNESS_VALUE_INFEASIBLE_SOLUTION))
                        if off_fit <= FITNESS_VALUE_INFEASIBLE_SOLUTION or np.isnan(off_fit):
                            continue

                        valid = True
                        records.append({
                            "pair_id": pair_id, "shuffle_round": s_round, "direction": dir_name,
                            "p_low_fitness": p_low_f, "p_high_fitness": p_high_f, "p_mid_fitness": p_mid_f,
                            "offspring_fitness": off_fit, "delta_high": off_fit - p_high_f,
                            "is_better_high": bool(off_fit > p_high_f + eps),
                            "is_worse_low": bool(off_fit < p_low_f - eps),
                            "is_intermediate": bool(p_low_f - eps <= off_fit <= p_high_f + eps),
                            "attempts": attempts,
                            "p_low_run": p_low.get('parent_run', ''), "p_high_run": p_high.get('parent_run', '')
                        })
                    except Exception:
                        continue
    return records


# ==============================================================================
# 2. Vectorized Metrics & Table
# ==============================================================================

def compute_metrics(df: pd.DataFrame, label: str) -> Dict[str, Any]:
    """Calculates summary crossover statistics including Heritability and Multiple Correlation."""
    if df.empty:
        return {}
    n = len(df)
    y = df['offspring_fitness'].values
    var_mid = float(np.var(df['p_mid_fitness']))
    h2 = float(np.cov(y, df['p_mid_fitness'])[0, 1] / var_mid) if var_mid > 1e-12 else 0.0

    # Multiple linear regression via statsmodels OLS: F(O) ~ beta_0 + beta_low * P_low + beta_high * P_high
    X = sm.add_constant(df[['p_low_fitness', 'p_high_fitness']])
    ols_res = sm.OLS(y, X).fit()
    beta_low, beta_high = ols_res.params['p_low_fitness'], ols_res.params['p_high_fitness']
    R_mult = float(np.sqrt(max(0.0, ols_res.rsquared)))

    tot_att = df['attempts'].sum()
    lethality = float((tot_att - n) / tot_att * 100.0) if tot_att > 0 else 0.0

    return {
        "Representation": label,
        "Heterosis $H^+$ ($O > P_{high}$)": f"{df['is_better_high'].sum()} ({df['is_better_high'].mean()*100:.2f}%)",
        "Intermediate ($P_{low} \\le O \\le P_{high}$)": f"{df['is_intermediate'].sum()} ({df['is_intermediate'].mean()*100:.2f}%)",
        "Destructive ($O < P_{low}$)": f"{df['is_worse_low'].sum()} ({df['is_worse_low'].mean()*100:.2f}%)",
        "Heritability $h^2_{cross}$": f"{h2:.4f}",
        "Multiple $R$": f"{R_mult:.4f}",
        "Weights $(\\beta_{low}, \\beta_{high})$": f"({beta_low:.3f}, {beta_high:.3f})",
        "Lethality Rate": f"{lethality:.2f}%",
        "Max Parent": f"{df['p_high_fitness'].max():.6f}",
        "Max Offspring": f"{df['offspring_fitness'].max():.6f}"
    }


def export_tables(dfs: Dict[str, pd.DataFrame], out_dir: str):
    """Builds and saves the metrics summary table in Markdown and CSV without outlier splitting."""
    rows = []
    for fmt in ['0', '1', '4', 'H']:
        df = dfs.get(fmt, pd.DataFrame())
        if not df.empty:
            rows.append(compute_metrics(df, f"**f{fmt}**"))

    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(os.path.join(out_dir, "crossover_metrics_summary.csv"), index=False)
    with open(os.path.join(out_dir, "crossover_metrics_summary.md"), "w", encoding="utf-8") as f:
        f.write(summary_df.to_markdown(index=False))
    print("\n" + summary_df.to_markdown(index=False) + "\n")


# ==============================================================================
# 3. Visualizations (2D Publication Scatter & 3D Interactive Plotly)
# ==============================================================================

def plot_2d_scatter(dfs: Dict[str, pd.DataFrame], out_dir: str, global_max: float):
    """Figure 1: 2x2 grid of Offspring Fitness vs. Mid-Parent Fitness on fixed shared axes."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12), sharex=True, sharey=True)
    margin = global_max * 0.05
    axis_lim = [0.0 - margin * 0.2, global_max + margin]

    for idx, fmt in enumerate(['0', '1', '4', 'H']):
        ax = axes.flatten()[idx]
        df = dfs.get(fmt, pd.DataFrame())
        if df.empty:
            continue

        x, y = df['p_mid_fitness'], df['offspring_fitness']
        b_mask, w_mask = df['is_better_high'], df['is_worse_low']
        i_mask = ~(b_mask | w_mask)

        ax.scatter(x[w_mask], y[w_mask], c='#d62728', alpha=0.30, s=16, label=r'Destructive ($O < P_{low}$)')
        ax.scatter(x[i_mask], y[i_mask], c='#1f77b4', alpha=0.35, s=16, label=r'Intermediate ($P_{low} \leq O \leq P_{high}$)')
        ax.scatter(x[b_mask], y[b_mask], c='#2ca02c', alpha=0.85, s=28, edgecolors='black', lw=0.5, label=r'Positive Heterosis ($O > P_{high}$)')

        ax.plot(axis_lim, axis_lim, 'r--', lw=1.5, label=r'Mid-Parent Neutrality ($y = \bar{F}(P)$)')

        # Metrics for annotation box via statsmodels
        var_mid = float(np.var(x))
        h2 = float(np.cov(y, x)[0, 1] / var_mid) if var_mid > 1e-12 else 0.0
        X_mat = sm.add_constant(df[['p_low_fitness', 'p_high_fitness']])
        ols_res = sm.OLS(y, X_mat).fit()
        R_mult = float(np.sqrt(max(0.0, ols_res.rsquared)))

        ax.text(0.04, 0.84, f"$H^+ = {b_mask.mean()*100:.2f}\\%$\n$h^2 = {h2:.4f}$\nMult $R = {R_mult:.4f}$",
                transform=ax.transAxes, fontsize=9.5, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.88, edgecolor='gray'))

        ax.set_title(FORMAT_NAMES[fmt], fontsize=12, fontweight='bold', pad=8)
        ax.set_xlim(axis_lim); ax.set_ylim(axis_lim); ax.set_aspect('equal'); ax.grid(True, linestyle=':', alpha=0.6)
        if idx == 0:
            ax.legend(loc='lower right', fontsize=8.5, framealpha=0.9)
        if idx in [2, 3]:
            ax.set_xlabel(r'Mid-Parent Fitness $\bar{F}(P) = \frac{F(P_1) + F(P_2)}{2}$', fontsize=11, fontweight='bold')
        if idx in [0, 2]:
            ax.set_ylabel('Offspring Fitness $F(O)$', fontsize=11, fontweight='bold')

    plt.suptitle("Offspring Fitness vs. Mid-Parent Fitness across Genetic Encodings (f0, f1, f4, fH)\n"
                 r"Fixed Globally Unified Scale $[0, F_{max}^{global}]$ with Mid-Parent Reference Diagonal $y = x$",
                 fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(os.path.join(out_dir, "crossover_scatter_midparent_2x2.png"), dpi=300)
    plt.close()


def plot_3d_interactive(dfs: Dict[str, pd.DataFrame], out_dir: str, global_max: float):
    """Generates interactive 3D HTML scatter plots with reference surfaces."""
    grid_vals = np.linspace(0, global_max, 25)
    X_grid, Y_grid = np.meshgrid(grid_vals, grid_vals)

    for fmt in ['0', '1', '4', 'H']:
        df = dfs.get(fmt, pd.DataFrame())
        if df.empty:
            continue
        sample_df = df.sample(min(len(df), 2000), random_state=42) if len(df) > 2000 else df
        fig = go.Figure()
        fig.add_trace(go.Scatter3d(
            x=sample_df['p_low_fitness'], y=sample_df['p_high_fitness'], z=sample_df['offspring_fitness'],
            mode='markers', marker=dict(size=3.5, color=sample_df['delta_high'], colorscale='Viridis', colorbar=dict(title=r'$\Delta F_{high}$'), opacity=0.75),
            text=[f"P_low: {r['p_low_fitness']:.5f}<br>P_high: {r['p_high_fitness']:.5f}<br>Offspring: {r['offspring_fitness']:.5f}" for _, r in sample_df.iterrows()],
            hoverinfo='text', name='Offspring'
        ))
        fig.add_trace(go.Surface(x=X_grid, y=Y_grid, z=np.maximum(X_grid, Y_grid), colorscale=[[0, 'rgba(255,0,0,0.15)'], [1, 'rgba(255,0,0,0.15)']], showscale=False, name='Best-Parent Ceiling'))
        fig.add_trace(go.Surface(x=X_grid, y=Y_grid, z=0.5*(X_grid+Y_grid), colorscale=[[0, 'rgba(0,0,255,0.1)'], [1, 'rgba(0,0,255,0.1)']], showscale=False, name='Mid-Parent Plane'))
        fig.update_layout(
            title=f"3D Crossover Fitness Landscape - {FORMAT_NAMES[fmt]}",
            scene=dict(xaxis=dict(title='F(P_low)', range=[0, global_max]), yaxis=dict(title='F(P_high)', range=[0, global_max]), zaxis=dict(title='F(Offspring)', range=[0, global_max]), aspectmode='cube'),
            width=900, height=750, margin=dict(l=10, r=10, b=10, t=50)
        )
        fig.write_html(os.path.join(out_dir, f"crossover_3d_f{fmt}.html"), include_plotlyjs='cdn')


def plot_parents_distribution(dfs: Dict[str, pd.DataFrame], out_dir: str, global_max: float):
    """Figure 0: 2x2 grid of Sampled Parent Pairs with desaturated symbols and a unified common legend."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12.5), sharex=True, sharey=True)
    margin = global_max * 0.05
    axis_lim = [0.0 - margin * 0.2, global_max + margin]

    round_markers = {1: 'o', 2: 's', 3: '^', 4: 'D', 5: 'v'}

    def _desaturate(color, factor=0.50):
        rgb = mcolors.to_rgb(color)
        hsv = mcolors.rgb_to_hsv(rgb)
        return mcolors.hsv_to_rgb((hsv[0], hsv[1] * factor, hsv[2]))

    for idx, fmt in enumerate(['0', '1', '4', 'H']):
        ax = axes.flatten()[idx]
        df = dfs.get(fmt, pd.DataFrame())
        if df.empty:
            continue
        pairs_df = df[['pair_id', 'shuffle_round', 'p_low_fitness', 'p_high_fitness']].drop_duplicates('pair_id')
        base_color = _desaturate(REPRESENTATION_COLORS.get(fmt, '#1f77b4'), factor=0.55)

        for r in sorted(pairs_df['shuffle_round'].unique()):
            r_df = pairs_df[pairs_df['shuffle_round'] == r]
            ax.scatter(r_df['p_low_fitness'], r_df['p_high_fitness'],
                       marker=round_markers.get(int(r), 'o'),
                       c=[base_color], alpha=0.60, s=26, edgecolors='black', linewidths=0.35)

        ax.plot(axis_lim, axis_lim, 'r--', lw=1.5)
        ax.set_title(f"{FORMAT_NAMES[fmt]}\n500 Parent Pairs across 5 Shuffle Rounds", fontsize=12, fontweight='bold', pad=8)
        ax.set_xlim(axis_lim); ax.set_ylim(axis_lim); ax.set_aspect('equal'); ax.grid(True, linestyle=':', alpha=0.6)
        if idx in [2, 3]:
            ax.set_xlabel(r'Lower-Fitness Parent $F(P_{low})$', fontsize=11, fontweight='bold')
        if idx in [0, 2]:
            ax.set_ylabel(r'Higher-Fitness Parent $F(P_{high})$', fontsize=11, fontweight='bold')

    # Common unified legend across all 4 subplots with desaturated neutral markers
    legend_elements = [
        Line2D([0], [0], marker='o', color='none', label='Round 1 (n=100)',
               markerfacecolor='#888888', markeredgecolor='black', markersize=7.5, markeredgewidth=0.5),
        Line2D([0], [0], marker='s', color='none', label='Round 2 (n=100)',
               markerfacecolor='#888888', markeredgecolor='black', markersize=7.5, markeredgewidth=0.5),
        Line2D([0], [0], marker='^', color='none', label='Round 3 (n=100)',
               markerfacecolor='#888888', markeredgecolor='black', markersize=7.5, markeredgewidth=0.5),
        Line2D([0], [0], marker='D', color='none', label='Round 4 (n=100)',
               markerfacecolor='#888888', markeredgecolor='black', markersize=7.5, markeredgewidth=0.5),
        Line2D([0], [0], marker='v', color='none', label='Round 5 (n=100)',
               markerfacecolor='#888888', markeredgecolor='black', markersize=7.5, markeredgewidth=0.5),
        Line2D([0], [0], linestyle='--', color='red', lw=1.5, label=r'$P_{high} = P_{low}$')
    ]

    fig.legend(handles=legend_elements, loc='lower center', ncol=6, fontsize=9.5,
               framealpha=0.92, edgecolor='gray', bbox_to_anchor=(0.5, 0.012))

    plt.suptitle("Verification of Parent Pair Uniformity on 2D Fitness Plane\n"
                 r"Fixed Globally Unified Scale $[0, F_{max}^{global}]$ with $P_{high} \geq P_{low}$ Triangle",
                 fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0.045, 1, 0.95])
    plt.savefig(os.path.join(out_dir, "crossover_parents_distribution_2x2.png"), dpi=300)
    plt.close()


def plot_phase_portrait(dfs: Dict[str, pd.DataFrame], out_dir: str, global_max: float):
    """Figure 3: 2D Hexbin Phase Portrait of Mean Gain over Higher-Fitness Parent (Delta F = F(O) - F(P_high))."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12), sharex=True, sharey=True)
    margin = global_max * 0.05
    axis_lim = [0.0 - margin * 0.2, global_max + margin]

    for idx, fmt in enumerate(['0', '1', '4', 'H']):
        ax = axes.flatten()[idx]
        df = dfs.get(fmt, pd.DataFrame())
        if df.empty:
            continue

        hb = ax.hexbin(df['p_low_fitness'], df['p_high_fitness'], C=df['delta_high'],
                       gridsize=22, reduce_C_function=np.mean, cmap='coolwarm_r',
                       extent=[axis_lim[0], axis_lim[1], axis_lim[0], axis_lim[1]], mincnt=1)
        ax.plot(axis_lim, axis_lim, 'k--', lw=1.2, alpha=0.7)
        cb = fig.colorbar(hb, ax=ax)
        cb.set_label(r'Mean $\Delta F = F(O) - F(P_{high})$', fontsize=10)

        ax.set_title(f"{FORMAT_NAMES[fmt]}\nMean Gain over Best Parent: " + r"$\Delta F = F(O) - F(P_{high})$", fontsize=11, fontweight='bold', pad=8)
        ax.set_xlim(axis_lim); ax.set_ylim(axis_lim); ax.set_aspect('equal'); ax.grid(True, linestyle=':', alpha=0.6)
        if idx in [2, 3]:
            ax.set_xlabel(r'Lower-Fitness Parent $F(P_{low})$', fontsize=11, fontweight='bold')
        if idx in [0, 2]:
            ax.set_ylabel(r'Higher-Fitness Parent $F(P_{high})$', fontsize=11, fontweight='bold')

    plt.suptitle("Crossover Recombination Phase Portraits\n"
                 r"Mean Fitness Advantage $\Delta F = F(O) - F(P_{high})$ across the $(F(P_{low}), F(P_{high}))$ Domain",
                 fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(os.path.join(out_dir, "crossover_phase_portrait_2x2.png"), dpi=300)
    plt.close()


# ==============================================================================
# 4. Main Entry Point
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Task 2: Fitness Landscape Exploration under Crossover.")
    parser.add_argument('--formats', nargs='+', default=['0', '1', '4', 'H'])
    parser.add_argument('--frams-path', default=os.path.join(REPO_ROOT, "Framsticks55"))
    parser.add_argument('--sim-settings', default="eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim")
    parser.add_argument('--task1-dir', default=os.path.join(REPO_ROOT, "assignments", "Assignment 6 - Fitness Landscape Exploration", "task1", "results", "landscape"))
    parser.add_argument('--out-dir', default=os.path.join(TASK2_DIR, "results", "crossover"))
    parser.add_argument('--shuffle-rounds', type=int, default=5, help="Rounds of shuffling (5 rounds x 100 pairs = 500 pairs)")
    parser.add_argument('--reps', type=int, default=4, help="Reps per reciprocal direction (4 reps x 2 = 8 offspring/pair)")
    parser.add_argument('--max-retries', type=int, default=20)
    parser.add_argument('--workers', type=int, default=min(os.cpu_count() or 1, 24))
    parser.add_argument('--dry-run', action='store_true', help="Run small dry run with 10 pairs")
    parser.add_argument('--plot-only', action='store_true', help="Skip simulations and re-plot from existing CSVs")

    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Load parents directly from Task 1 CSVs
    parents_by_fmt, max_f = {}, 0.0
    for fmt in args.formats:
        df_p = pd.read_csv(os.path.join(args.task1_dir, f"landscape_data_f{fmt}.csv"))[['parent_fitness', 'parent_genotype', 'parent_run']].drop_duplicates()
        parents_by_fmt[fmt] = df_p.to_dict('records')
        max_f = max(max_f, float(df_p['parent_fitness'].max()))
        print(f"[LOAD] f{fmt}: Loaded {len(parents_by_fmt[fmt])} parents from Task 1 (Max F = {df_p['parent_fitness'].max():.6f})")

    # 2. Run Crossover or Load Existing Data
    dfs = {}
    for fmt in args.formats:
        csv_path = os.path.join(args.out_dir, f"crossover_data_f{fmt}.csv")
        if args.plot_only and os.path.exists(csv_path):
            dfs[fmt] = pd.read_csv(csv_path)
            continue

        pairs = generate_shuffled_pairs(parents_by_fmt[fmt], rounds=1 if args.dry_run else args.shuffle_rounds)
        if args.dry_run:
            pairs = pairs[:10]

        reps = 1 if args.dry_run else args.reps
        batches = [b.tolist() for b in np.array_split(pairs, args.workers) if len(b) > 0]
        tasks = [(b, args.frams_path, args.sim_settings, reps, args.max_retries) for b in batches]

        print(f"[EVAL] f{fmt}: Running crossover for {len(pairs)} pairs across {len(tasks)} workers (Target: {len(pairs)*2*reps} offspring)...")
        t0 = time.time()
        with mp.Pool(processes=len(tasks)) as pool:
            res_nested = pool.starmap(_worker_crossover, tasks)
        results = [item for sublist in res_nested for item in sublist]
        print(f"[EVAL] f{fmt}: Completed {len(results)} offspring in {time.time()-t0:.1f}s")

        df = pd.DataFrame(results)
        df.to_csv(csv_path, index=False)
        dfs[fmt] = df

    # 3. Export Tables & Plots
    export_tables(dfs, args.out_dir)
    plot_2d_scatter(dfs, args.out_dir, max_f)
    plot_parents_distribution(dfs, args.out_dir, max_f)
    plot_phase_portrait(dfs, args.out_dir, max_f)
    plot_3d_interactive(dfs, args.out_dir, max_f)
    print(f"\n[DONE] All Task 2 crossover deliverables saved to: {args.out_dir}")


if __name__ == "__main__":
    main()
