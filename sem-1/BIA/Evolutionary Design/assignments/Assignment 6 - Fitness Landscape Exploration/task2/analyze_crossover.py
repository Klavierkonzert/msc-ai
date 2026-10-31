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

import numpy as np
from scipy import stats

def test_triangle_uniformity(points, L: float|None=None, case='upper', grid_size=4, eps = 1e-6):
    """
    Tests uniformity of points inside a diagonal half of a square (O, (0, L), (L, L), (L, 0)) of side L (if set up, otherwise max value used L:=max(max(x), max(y))).
    
    Parameters:
    - points: array-like of shape (N, 2)
    - L: the maximum coordinate value (X_max or Y_max)
    - case: 'lower' for lower triangle (y <= x), 'upper' for upper triangle (y >= x)
    - grid_size: matrix size for the Chi-Square binning (e.g., 4x4 = 16 bins)
    """
    points = np.asarray(points)
    x = points[:, 0]
    y = points[:, 1]
    if L is None:
        L = max(x.max(), y.max()) + eps
    
    # Avoid division by exact zeros at the origin/boundaries
    x = np.where(x == 0, eps, x)
    
    # 1. Apply Direct Probability Integral Transform
    if case.upper() == 'LOWER':
        # Bounded by y <= x
        u1 = (x / L) ** 2
        u2 = y / x
    elif case.upper() == 'UPPER':
        u1 = 1.0 - (1.0 - x / L) ** 2
        denom = L - x
        denom = np.where(denom == 0, eps, denom)
        u2 = (y - x) / denom
    else:
        raise ValueError("Case must be 'lower' or 'upper'")
        
    # Clip to ensure minor float noise doesn't escape [0, 1]
    u1, u2 = np.clip(u1, 0, 1), np.clip(u2, 0, 1)
    
    # 2. Map to 2D Histogram bins
    edges = np.linspace(0, 1, grid_size + 1)
    observed, _, _ = np.histogram2d(u1, u2, bins=[edges, edges])
    observed_flat = observed.flatten()
    
    # 3. Calculate Chi-Square Expected Frequencies
    total_dots = len(points)
    total_bins = grid_size * grid_size
    expected_flat = np.full(total_bins, total_dots / total_bins)
    
    # 4. Compute Statistical Metrics
    chi2_stat, p_val = stats.chisquare(f_obs=observed_flat, f_exp=expected_flat)
    
    # Compute KL Divergence (P || Q)
    p_empirical = observed_flat / total_dots
    q_uniform = np.ones(total_bins) / total_bins
    p_empirical = np.where(p_empirical == 0, eps, p_empirical) # Smooth zeros
    kl_div = stats.entropy(p_empirical, q_uniform)
    
    return {
        "chi2_stat": chi2_stat,
        "p_value": p_val,
        "kl_divergence_nats": kl_div,
        "is_uniform": p_val > 0.05
    }

def _worker_crossover(batch, frams_path, sim_settings, reps: int, max_retries: int, eps: float =1e-6):
    """Worker process evaluating crossover offspring for a chunk of parent pairs."""
    from FramsticksLib import FramsticksLib
    flib = FramsticksLib(frams_path, None, sim_settings)
    flib.PRINT_FRAMSTICKS_OUTPUT = False
    flib.GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL = False

    records = []
    for p_low, p_high, s_round, pair_id in batch:
        p_low_f, p_high_f = float(p_low['parent_fitness']), float(p_high['parent_fitness'])
        p_mid_f = 0.5 * (p_low_f + p_high_f)

        # crossover will be performed for two pairs of parents (p_low, p_high) and (p_high, p_low)
        # the offspring O(p_low, p_high) -> 'low_x_high'
        #               O(p_high, p_low) -> 'high_x_low'
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
                            "p_base_fitness": p_high_f if dir_name == 'high_x_low' else p_low_f,
                            "p_donor_fitness": p_low_f if dir_name == 'high_x_low' else p_high_f,
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

def compute_metrics(df: pd.DataFrame, label: str, exclude_metrics: List[str] = None) -> Dict[str, Any]:
    """Calculates summary crossover statistics including Heritability and Multiple Correlation on Base and Donor.
    
    Args:
        df: DataFrame containing crossover results.
        label: Label for the metric set.
        exclude_metrics: List of metrics to exclude from the results. Valid values are (not case sensitive):
            'Heterosis', 'Intermediate', 'Destructive', 'Heritability', 'Multiple R', 
            'Weights', 'Pearson', 'Lethality Rate', 'Max Parent', 'Max Offspring'
    Returns:
        Dictionary containing computed metrics.
    """
    if df.empty:
        return {}
    n = len(df)
    y = df['offspring_fitness'].values
    var_mid = float(np.var(df['p_mid_fitness']))
    h2 = float(np.cov(y, df['p_mid_fitness'])[0, 1] / var_mid) if var_mid > 1e-12 else 0.0

    # Ensure p_base_fitness and p_donor_fitness exist
    if 'p_base_fitness' not in df.columns:
        is_hl = df['direction'] == 'high_x_low'
        df['p_base_fitness'] = np.where(is_hl, df['p_high_fitness'], df['p_low_fitness'])
        df['p_donor_fitness'] = np.where(is_hl, df['p_low_fitness'], df['p_high_fitness'])

    # Multiple linear regression via statsmodels OLS: F(O) ~ beta_0 + beta_base * P_base + beta_donor * P_donor
    X = sm.add_constant(df[['p_base_fitness', 'p_donor_fitness']])
    ols_res = sm.OLS(y, X).fit()
    beta_base, beta_donor = ols_res.params['p_base_fitness'], ols_res.params['p_donor_fitness']
    R_mult = float(np.sqrt(max(0.0, ols_res.rsquared)))

    # Pearson correlation between Delta F and mid-parent fitness
    r_delta_mid = float(df['delta_high'].corr(df['p_mid_fitness'])) if df['p_mid_fitness'].std() > 1e-12 else 0.0

    tot_att = df['attempts'].sum()
    lethality = float((tot_att - n) / tot_att * 100.0) if tot_att > 0 else 0.0

    res = {
        "Representation": label,
        r"Heterosis $H^+$ ($\Delta F > \epsilon$)": f"{df['is_better_high'].sum():,} ({df['is_better_high'].mean()*100:.2f}%)",
        r"Intermediate ($P_{low} \le O \le P_{high}$)": f"{df['is_intermediate'].sum():,} ({df['is_intermediate'].mean()*100:.2f}%)",
        "Destructive ($O < P_{low}$)": f"{df['is_worse_low'].sum():,} ({df['is_worse_low'].mean()*100:.2f}%)",
        "Heritability $h^2_{cross}$": f"{h2:.4f}" ,
        "Multiple $R$": f"{R_mult:.4f}",
        "Weights $(\\beta_{base}, \\beta_{donor})$": f"({beta_base:.3f}, {beta_donor:.3f})",
        r"Pearson $r(\Delta F, \bar{F}(P))$": f"{r_delta_mid:.4f}",
        "Lethality Rate": f"{lethality:.2f}%",
        "Max Parent": f"{df['p_high_fitness'].max():.6f}",
        "Max Offspring": f"{df['offspring_fitness'].max():.6f}",
        "_heterosis": int(df['is_better_high'].sum()),
        "_intermediate": int(df['is_intermediate'].sum()),
        "_destructive": int(df['is_worse_low'].sum()),
        "_heritability": float(h2),
        "_multiple_r": float(R_mult),
        "_beta_base": float(beta_base),
        "_beta_donor": float(beta_donor),
        "_r_delta_mid": float(r_delta_mid),
        "_lethality": float(lethality),
        "_max_parent": float(df['p_high_fitness'].max()),
        "_max_offspring": float(df['offspring_fitness'].max())
    }
    if exclude_metrics:
        exclude_set = {m.lower().strip() for m in exclude_metrics}
        keys_to_del = [k for k in list(res.keys()) if not k.startswith("_") and any(m in k.lower() for m in exclude_set)]
        for k in keys_to_del:
            del res[k]
    return res


def export_tables(dfs: Dict[str, pd.DataFrame], out_dir: str, exclude_metrics: List[str] = None, highlight_extremes: bool = True):
    """Builds and saves the metrics summary table in Markdown and CSV with extreme highlights."""
    rows = []
    for fmt in FORMAT_NAMES:
        df = dfs.get(fmt, pd.DataFrame())
        if not df.empty:
            rows.append(compute_metrics(df, f"**f{fmt}**", exclude_metrics=exclude_metrics))

    raw_df = pd.DataFrame(rows)

    # Save clean unstyled CSV
    csv_cols = [c for c in raw_df.columns if not c.startswith("_")]
    raw_df[csv_cols].to_csv(os.path.join(out_dir, "crossover_metrics_summary.csv"), index=False)

    styled_df = raw_df.copy()

    if highlight_extremes and not styled_df.empty:
        def green(s: str) -> str:
            return f'**<span style="color: darkgreen; font-weight: bold;">{s}</span>**'

        def blue(s: str) -> str:
            return f'**<span style="color: darkblue; font-weight: bold;">{s}</span>**'

        def red(s: str) -> str:
            return f'**<span style="color: darkred; font-weight: bold;">{s}</span>**'

        def grad_color(val: float) -> str:
            """Gradient from dark red (0.0) to dark blue (1.0)."""
            t = max(0.0, min(1.0, float(val)))
            r = int(round(139 * (1.0 - t)))
            b = int(round(139 * t))
            return f"#{r:02x}00{b:02x}"

        def style_grad(text: str, val: float, is_bold: bool = False) -> str:
            color = grad_color(val)
            if is_bold:
                return f'**<span style="color: {color}; font-weight: bold;">{text}</span>**'
            return f'<span style="color: {color};">{text}</span>'

        # 1. Heterosis: largest in darkgreen
        c_het = [c for c in styled_df.columns if "heterosis" in c.lower()]
        if c_het and "_heterosis" in styled_df.columns:
            col = c_het[0]
            max_idx = styled_df["_heterosis"].idxmax()
            styled_df.loc[max_idx, col] = green(styled_df.loc[max_idx, col])

        # 2. Intermediate: largest in darkblue
        c_inter = [c for c in styled_df.columns if "intermediate" in c.lower()]
        if c_inter and "_intermediate" in styled_df.columns:
            col = c_inter[0]
            max_idx = styled_df["_intermediate"].idxmax()
            styled_df.loc[max_idx, col] = blue(styled_df.loc[max_idx, col])

        # 3. Destructive: largest in darkred
        c_dest = [c for c in styled_df.columns if "destructive" in c.lower()]
        if c_dest and "_destructive" in styled_df.columns:
            col = c_dest[0]
            max_idx = styled_df["_destructive"].idxmax()
            styled_df.loc[max_idx, col] = red(styled_df.loc[max_idx, col])

        # 4. Multiple R: gradient from dark red (0.0) to dark blue (1.0), bold for extreme absolute values only
        c_r = [c for c in styled_df.columns if "multiple" in c.lower() and "r" in c.lower()]
        if c_r and "_multiple_r" in styled_df.columns:
            col = c_r[0]
            abs_vals = styled_df["_multiple_r"].abs()
            max_idx = abs_vals.idxmax()
            min_idx = abs_vals.idxmin()
            for i in styled_df.index:
                val = styled_df.loc[i, "_multiple_r"]
                is_extreme = (i == max_idx or i == min_idx)
                styled_df.loc[i, col] = style_grad(styled_df.loc[i, col], val, is_bold=is_extreme)

        # 5. Weights: largest individual values in darkblue
        c_w = [c for c in styled_df.columns if "weights" in c.lower()]
        if c_w and "_beta_base" in styled_df.columns and "_beta_donor" in styled_df.columns:
            col = c_w[0]
            max_base = styled_df["_beta_base"].max()
            max_donor = styled_df["_beta_donor"].max()
            for i in styled_df.index:
                b_val = styled_df.loc[i, "_beta_base"]
                d_val = styled_df.loc[i, "_beta_donor"]
                b_str = blue(f"{b_val:.3f}") if b_val == max_base else f"{b_val:.3f}"
                d_str = blue(f"{d_val:.3f}") if d_val == max_donor else f"{d_val:.3f}"
                styled_df.loc[i, col] = f"({b_str}, {d_str})"

        # 6. Pearson r(Delta F, mid-parent): gradient from dark red (|r|=0.0) to dark blue (|r|=1.0), bold for extreme absolute values only
        c_p = [c for c in styled_df.columns if "pearson" in c.lower()]
        if c_p and "_r_delta_mid" in styled_df.columns:
            col = c_p[0]
            abs_vals = styled_df["_r_delta_mid"].abs()
            max_idx = abs_vals.idxmax()
            min_idx = abs_vals.idxmin()
            for i in styled_df.index:
                r_val = styled_df.loc[i, "_r_delta_mid"]
                is_extreme = (i == max_idx or i == min_idx)
                styled_df.loc[i, col] = style_grad(styled_df.loc[i, col], abs(r_val), is_bold=is_extreme)

        # 7. Lethality Rate: largest in darkred, smallest in darkblue
        c_leth = [c for c in styled_df.columns if "lethality" in c.lower()]
        if c_leth and "_lethality" in styled_df.columns:
            col = c_leth[0]
            max_idx = styled_df["_lethality"].idxmax()
            min_idx = styled_df["_lethality"].idxmin()
            styled_df.loc[max_idx, col] = red(styled_df.loc[max_idx, col])
            styled_df.loc[min_idx, col] = blue(styled_df.loc[min_idx, col])

        # 8. Max Parent: largest in darkblue, smallest in darkred
        c_mp = [c for c in styled_df.columns if "max parent" in c.lower()]
        if c_mp and "_max_parent" in styled_df.columns:
            col = c_mp[0]
            max_idx = styled_df["_max_parent"].idxmax()
            min_idx = styled_df["_max_parent"].idxmin()
            styled_df.loc[max_idx, col] = blue(styled_df.loc[max_idx, col])
            styled_df.loc[min_idx, col] = red(styled_df.loc[min_idx, col])

        # 9. Max Offspring: largest in darkblue, smallest in darkred
        c_mo = [c for c in styled_df.columns if "max offspring" in c.lower()]
        if c_mo and "_max_offspring" in styled_df.columns:
            col = c_mo[0]
            max_idx = styled_df["_max_offspring"].idxmax()
            min_idx = styled_df["_max_offspring"].idxmin()
            styled_df.loc[max_idx, col] = blue(styled_df.loc[max_idx, col])
            styled_df.loc[min_idx, col] = red(styled_df.loc[min_idx, col])

    disp_cols = [c for c in styled_df.columns if not c.startswith("_")]
    styled_df = styled_df[disp_cols]

    with open(os.path.join(out_dir, "crossover_metrics_summary.md"), "w", encoding="utf-8") as f:
        f.write(styled_df.to_markdown(index=False))
    print("\n" + styled_df.to_markdown(index=False) + "\n")


# ==============================================================================
# 3. Visualizations (2D Publication Scatter & 3D Interactive Plotly)
# ==============================================================================

def plot_2d_scatter(dfs: Dict[str, pd.DataFrame], out_dir: str, global_max: float):
    """Figure 1: 2x2 grid of Offspring Fitness vs. Mid-Parent Fitness on fixed shared axes."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12), sharex=True, sharey=True)
    pad = global_max * 0.03
    axis_lim = [-pad * 0.5, global_max + pad]

    for idx, fmt in enumerate(FORMAT_NAMES):
        ax = axes.flatten()[idx]
        df = dfs.get(fmt, pd.DataFrame())
        if df.empty:
            continue

        x, y = df['p_mid_fitness'], df['offspring_fitness']
        b_mask, w_mask = df['is_better_high'], df['is_worse_low']
        i_mask = ~(b_mask | w_mask)

        ax.scatter(x[w_mask], y[w_mask], c='#d62728', alpha=0.30, s=16, label=r'Destructive ($O < P_{low}$)')
        ax.scatter(x[i_mask], y[i_mask], c='#1f77b4', alpha=0.35, s=16, label=r'Intermediate ($P_{low} \leq O \leq P_{high}$)')
        ax.scatter(x[b_mask], y[b_mask], c='#2ca02c', alpha=0.85, s=28, edgecolors='black', lw=0.5, label=r'Positive Heterosis ($\Delta F > \epsilon$)')

        ax.plot(axis_lim, axis_lim, 'r--', lw=1.5, label=r'Mid-Parent Neutrality ($y = \bar{F}(P)$)')

        # Metrics for annotation box via statsmodels
        var_mid = float(np.var(x))
        h2 = float(np.cov(y, x)[0, 1] / var_mid) if var_mid > 1e-12 else 0.0
        X_mat = sm.add_constant(df[['p_base_fitness', 'p_donor_fitness']])
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
                 r"Global Scale $[0, F_{max}^{global}]$ with Mid-Parent Reference Diagonal $y = x$",
                 fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(os.path.join(out_dir, "crossover_scatter_midparent_2x2.png"), dpi=300)
    plt.close()


def plot_3d_interactive(dfs: Dict[str, pd.DataFrame], out_dir: str, global_max: float, vrange: tuple[float, float]):
    """Generates interactive 3D HTML scatter plots with reference surfaces on shared (P_base, P_donor) square axes."""
    grid_vals = np.linspace(0, global_max, 30)
    X_grid, Y_grid = np.meshgrid(grid_vals, grid_vals)

    # Reference surfaces across the full square [0, global_max]^2:
    # 1. Best-Parent Ceiling: Upper triangle (Y >= X, Z = Y = P_donor)
    Z_semi1 = np.where(Y_grid >= X_grid, Y_grid, np.nan)
    # 2. Best-Parent Ceiling: Lower triangle (X >= Y, Z = X = P_base)
    Z_semi2 = np.where(X_grid >= Y_grid, X_grid, np.nan)
    # 3. Blue Mid-Parent Plane: Z = 0.5 * (X + Y)
    Z_mid = 0.5 * (X_grid + Y_grid)
    # 4. Vertical Mid-Parent Projection Plane: X = Y spanning Z in [0, global_max]
    U_proj, V_proj = np.meshgrid(grid_vals, grid_vals)
    X_proj = U_proj
    Y_proj = U_proj
    Z_proj = V_proj
    for fmt in FORMAT_NAMES:
        df = dfs.get(fmt, pd.DataFrame())
        if df.empty:
            continue
        if 'p_base_fitness' not in df.columns:
            is_hl = df['direction'] == 'high_x_low'
            df['p_base_fitness'] = np.where(is_hl, df['p_high_fitness'], df['p_low_fitness'])
            df['p_donor_fitness'] = np.where(is_hl, df['p_low_fitness'], df['p_high_fitness'])

        sample_df = df.sample(min(len(df), 2000), random_state=42) if len(df) > 2000 else df
        fig = go.Figure()

        # 1. Main sampled offspring scatter
        fig.add_trace(go.Scatter3d(
            x=sample_df['p_base_fitness'], y=sample_df['p_donor_fitness'], z=sample_df['offspring_fitness'],
            mode='markers', marker=dict(
                size=3.5,
                color=sample_df['delta_high'],
                colorscale='RdBu',
                cmin=vrange[0], cmid=(vrange[0]+vrange[1])/2, cmax=vrange[1],
                colorbar=dict(title=dict(text='ΔF<sub>high</sub>', font=dict(size=13)), ticks='outside'),
                opacity=0.75
            ),
            text=[f"P_base: {r['p_base_fitness']:.5f}<br>P_donor: {r['p_donor_fitness']:.5f}<br>Offspring: {r['offspring_fitness']:.5f}<br>Delta_F: {r['delta_high']:+.5f}" for _, r in sample_df.iterrows()],
            hoverinfo='text', name=f'Offspring Sample (n={len(sample_df)})'
        ))

        # 2. Highlight trace: Successful offspring (\Delta F > \epsilon)
        pos_df = df[df['is_better_high']]
        if not pos_df.empty:
            fig.add_trace(go.Scatter3d(
                x=pos_df['p_base_fitness'], y=pos_df['p_donor_fitness'], z=pos_df['offspring_fitness'],
                mode='markers',
                marker=dict(size=8, symbol='circle', color='green', line=dict(color='black', width=1.2)),
                text=[f"Successful Offspring: {r['p_base_fitness']:.5f}<br>P_donor: {r['p_donor_fitness']:.5f}<br>Offspring: {r['offspring_fitness']:.5f}<br>Delta_F: +{r['delta_high']:.5f}" for _, r in pos_df.iterrows()],
                hoverinfo='text', name=rf'Successful Offspring: \Delta F > \epsilon (n={len(pos_df)})'
            ))
        else:
            fig.add_trace(go.Scatter3d(
                x=[None], y=[None], z=[None],
                mode='markers',
                marker=dict(size=8, symbol='circle', color='green', line=dict(color='black', width=1.2)),
                name=r'Successful Offspring: \Delta F > \epsilon (n=0)',
                showlegend=True
            ))

        # 3. Two Soft Red Semiplanes forming the Best-Parent Ceiling Z = max(P_base, P_donor) (softened)
        fig.add_trace(go.Surface(
            x=X_grid, y=Y_grid, z=Z_semi1,
            colorscale=[[0, 'rgba(215, 45, 45, 0.08)'], [1, 'rgba(215, 45, 45, 0.08)']],
            showscale=False, showlegend=True,
            name='Best-Parent Ceiling (Z = P_donor, Y >= X)'
        ))
        fig.add_trace(go.Surface(
            x=X_grid, y=Y_grid, z=Z_semi2,
            colorscale=[[0, 'rgba(185, 30, 30, 0.07)'], [1, 'rgba(185, 30, 30, 0.07)']],
            showscale=False, showlegend=True,
            name='Best-Parent Ceiling (Z = P_base, X >= Y)'
        ))

        # 4. Soft Blue Mid-Parent Neutrality Plane Z = (P_base + P_donor) / 2 (softened)
        fig.add_trace(go.Surface(
            x=X_grid, y=Y_grid, z=Z_mid,
            colorscale=[[0, 'rgba(40, 105, 230, 0.075)'], [1, 'rgba(40, 105, 230, 0.075)']],
            showscale=False, showlegend=True,
            name='Mid-Parent Plane (Z = (X+Y)/2)'
        ))

        # 5. Vertical Mid-Parent Projection Plane: X = Y (Figure 1 projection screen, slightly visible)
        fig.add_trace(go.Surface(
            x=X_proj, y=Y_proj, z=Z_proj,
            colorscale=[[0, 'rgba(110, 120, 145, 0.065)'], [1, 'rgba(110, 120, 145, 0.065)']],
            showscale=False, showlegend=True,
            name='Projection Plane: Mid-Parent vs. Offspring (P_base = P_donor)'
        ))

        # 6. Neutrality Line on the projection plane: Z = X = Y (O = Mid-Parent diagonal from Figure 1)
        fig.add_trace(go.Scatter3d(
            x=[0, global_max], y=[0, global_max], z=[0, global_max],
            mode='lines',
            line=dict(color='rgba(215, 45, 45, 0.65)', width=2.5, dash='dash'),
            hoverinfo='none',
            name='Mid-Parent Neutrality Line (y = x)'
        ))

        fig.update_layout(
            title=dict(
                text=f"3D Crossover Fitness Landscape - f<sub>{fmt}</sub> ({FORMAT_NAMES[fmt].split('(')[1]}<br><sup>Dependence of Offspring Fitness (O) on Parental Fitness (P<sub>base</sub>, P<sub>donor</sub>)</sup>",
                font=dict(size=14)
            ),
            scene=dict(
                xaxis=dict(title='F(P<sub>base</sub>)', range=[0, global_max]),
                yaxis=dict(title='F(P<sub>donor</sub>)', range=[0, global_max]),
                zaxis=dict(title='F(O)', range=[0, global_max]),
                aspectmode='cube'
            ),
            legend=dict(
                x=0.01, y=0.99,
                bgcolor='rgba(255, 255, 255, 0.90)',
                bordercolor='rgba(160, 160, 160, 0.8)',
                borderwidth=1,
                font=dict(size=11)
            ),
            width=960, height=780, margin=dict(l=10, r=10, b=10, t=60)
        )
        fig.write_html(os.path.join(out_dir, f"crossover_3d_f{fmt}.html"), include_plotlyjs='cdn')


def plot_parents_distribution(dfs: Dict[str, pd.DataFrame], out_dir: str, global_max: float, 
                                round_markers = ['o', 's', '^', 'D', 'v', 'p', '*', 'h'], eps=1e-6
                                ):
    """Figure 0: 2x2 grid of Directed Parent Pairs (P_base, P_donor) samples distribution spanning the full symmetric square domain."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12.8), sharex=True, sharey=True)
    pad = global_max * 0.03
    axis_lim = [-pad * 0.5, global_max + pad]

    def _desaturate(color, factor=0.50):
        rgb = mcolors.to_rgb(color)
        hsv = mcolors.rgb_to_hsv(rgb)
        return mcolors.hsv_to_rgb((hsv[0], hsv[1] * factor, hsv[2]))

    n_rounds = max(d['shuffle_round'].nunique() for d in dfs.values() if not d.empty)
    for idx, fmt in enumerate(FORMAT_NAMES):
        ax = axes.flatten()[idx]
        df = dfs.get(fmt, pd.DataFrame())
        if df.empty:
            continue
        if 'p_base_fitness' not in df.columns:
            is_hl = df['direction'] == 'high_x_low'
            df['p_base_fitness'] = np.where(is_hl, df['p_high_fitness'], df['p_low_fitness'])
            df['p_donor_fitness'] = np.where(is_hl, df['p_low_fitness'], df['p_high_fitness'])

        pairs_df = df[['pair_id', 'shuffle_round', 'direction', 'p_base_fitness', 'p_donor_fitness']].drop_duplicates(['pair_id', 'direction'])

        # Colors: Saturated for upper half (P_donor >= P_base), Desaturated for lower half (P_donor < P_base)
        upper_color, lower_color = _desaturate(REPRESENTATION_COLORS.get(fmt, '#1f77b4'), factor=0.90), _desaturate(REPRESENTATION_COLORS.get(fmt, '#1f77b4'), factor=0.20)

        upper_mask = pairs_df['p_donor_fitness'] >= pairs_df['p_base_fitness']
        upper_pts = pairs_df[upper_mask][['p_base_fitness', 'p_donor_fitness']].values
        
        # Uniformity testing on upper and lower triangles
        u_res = test_triangle_uniformity(upper_pts, case='upper',eps=eps)
        
        for r in range(1, n_rounds+1):
            r_df = pairs_df[pairs_df['shuffle_round'] == r]
            r_upper = r_df[r_df['p_donor_fitness'] >= r_df['p_base_fitness']]
            r_lower = r_df[r_df['p_donor_fitness'] < r_df['p_base_fitness']]

            # Plot upper half (saturated)
            ax.scatter(r_upper['p_base_fitness'], r_upper['p_donor_fitness'],
                       marker=round_markers[(r-1)%len(round_markers)],
                       c=[upper_color], alpha=0.72, s=24, edgecolors='black', linewidths=0.35)
            # Plot lower half (desaturated)
            ax.scatter(r_lower['p_base_fitness'], r_lower['p_donor_fitness'],
                       marker=round_markers[(r-1)%len(round_markers)],
                       c=[lower_color], alpha=0.45, s=20, edgecolors='#555555', linewidths=0.30)

        ax.plot(axis_lim, axis_lim, 'r--', lw=1.5)

        title_text = (
            f"{FORMAT_NAMES[fmt]} (N={len(pairs_df)})\n"
            rf"$\mathbf{{\triangle_{{upper}}}}$: $\chi^2={u_res['chi2_stat']:.1f}$ ($p={0 if u_res['p_value'] < eps else u_res['p_value']:.2g}$), $D_{{KL}}={u_res['kl_divergence_nats']:.3f}$"
            # "\n"
            # rf"$\mathbf{{\triangledown_{{lower}}}}$: $\chi^2={l_res['chi2_stat']:.1f}$ ($p={l_res['p_value']:.2g}$), $D_{{KL}}={l_res['kl_divergence_nats']:.3f}$ (desaturated)"
        )
        ax.set_title(title_text, fontsize=10.5, fontweight='bold', pad=8)
        ax.set_xlim(axis_lim); ax.set_ylim(axis_lim); ax.set_aspect('equal'); ax.grid(True, linestyle=':', alpha=0.6)
        if idx in [2, 3]:
            ax.set_xlabel(r'Base Parent Fitness $F(P_{base})$ (Recipient)', fontsize=11, fontweight='bold')
        if idx in [0, 2]:
            ax.set_ylabel(r'Donor Parent Fitness $F(P_{donor})$ (Graft)', fontsize=11, fontweight='bold')

    # Common unified legend across all 4 subplots with desaturated neutral markers
    legend_elements = [Line2D([0], [0], marker=round_markers[(r-1)%len(round_markers)], color='none', label=f'Round {r}',  
                              markerfacecolor='#888888', markeredgecolor='black', markersize=7.5, markeredgewidth=0.5) 
                       for r in range(1, n_rounds+1)
                      ] + [
                       Line2D([0], [0], linestyle='--', color='red', lw=1.5, label=r'$P_{base} = P_{donor}$')
                      ]

    fig.legend(handles=legend_elements, loc='lower center', ncol=4, fontsize=9.5,
               framealpha=0.92, edgecolor='gray', bbox_to_anchor=(0.5, 0.010))

    plt.suptitle("Distribution of Directed Parent Pair Samples on 2D Fitness Plane\n"
                #  r"Full Globally Unified Square Domain $[0, F_{max}^{global}] \times [0, F_{max}^{global}]$ with Reciprocal Symmetry Diagonal"
                , fontsize=13.5, fontweight='bold', y=0.985)
    plt.tight_layout(rect=[0, 0.055, 1, 0.955])
    plt.savefig(os.path.join(out_dir, "crossover_parents_distribution_2x2.png"), dpi=300)
    plt.close()


def plot_phase_portrait(dfs: Dict[str, pd.DataFrame], out_dir: str, global_max: float, vrange: tuple[float, float],
                        show_better_crosses: bool = True, eps: float = 1e-6):
    r"""Figure 2: 2D Hexbin Phase Portrait across the full square (P_base, P_donor) domain on shared axes.
    
    Args:
        dfs: Mapping of format to crossover DataFrame.
        out_dir: Output directory to save the figure.
        global_max: Maximum fitness across all representations.
        vrange: Symmetric colorbar range for delta_high.
        show_better_crosses: If True (default), overlays dark green crosses for recombinant solutions with \Delta F > \epsilon.
        eps: Numerical tolerance threshold for identifying positive heterosis.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 12), sharex=True, sharey=True)
    pad = global_max * 0.03
    axis_lim = [-pad * 0.5, global_max + pad]

    # Unified symmetric diverging norm centered at 0.0 with dynamic bounds [-vmax, +vmax]
    norm = mcolors.TwoSlopeNorm(vmin=vrange[0], vcenter=(vrange[0]+vrange[1])/2, vmax=vrange[1])
    cmap = 'coolwarm_r'

    hb_last = None
    for idx, fmt in enumerate(FORMAT_NAMES):
        ax = axes.flatten()[idx]
        df = dfs.get(fmt, pd.DataFrame())
        if df.empty:
            continue
        if 'p_base_fitness' not in df.columns:
            is_hl = df['direction'] == 'high_x_low'
            df['p_base_fitness'] = np.where(is_hl, df['p_high_fitness'], df['p_low_fitness'])
            df['p_donor_fitness'] = np.where(is_hl, df['p_low_fitness'], df['p_high_fitness'])

        hb = ax.hexbin(df['p_base_fitness'], df['p_donor_fitness'], C=df['delta_high'],
                       gridsize=22, reduce_C_function=np.median, cmap=cmap, norm=norm,
                       extent=[axis_lim[0], axis_lim[1], axis_lim[0], axis_lim[1]], mincnt=1)
        hb_last = hb
        ax.plot(axis_lim, axis_lim, 'k--', lw=1.2, alpha=0.7, label=r'$P_{donor} = P_{base}$')

        # Overlay dark green crosses for solutions with \Delta F > \epsilon on top of bins
        if show_better_crosses:
            p_max = np.maximum(df['p_base_fitness'], df['p_donor_fitness'])
            better_mask = df['offspring_fitness'] > p_max + eps
            better_df = df[better_mask]
            if not better_df.empty:
                ax.scatter(better_df['p_base_fitness'], better_df['p_donor_fitness'],
                           marker='x', color='darkgreen', s=45, lw=1.6, zorder=5,
                           label=rf'$\Delta F > \epsilon$ ($n={len(better_df)}$)')
                ax.legend(loc='upper left', fontsize=9.0, framealpha=0.88)

        ax.set_title(f"{FORMAT_NAMES[fmt]}", fontsize=12, fontweight='bold', pad=8)
        ax.set_xlim(axis_lim); ax.set_ylim(axis_lim); ax.set_aspect('equal'); ax.grid(True, linestyle=':', alpha=0.6)
        if idx in [2, 3]:
            ax.set_xlabel(r'Base Parent Fitness $F(P_{base})$ (Recipient)', fontsize=11, fontweight='bold')
        if idx in [0, 2]:
            ax.set_ylabel(r'Donor Parent Fitness $F(P_{donor})$ (Graft)', fontsize=11, fontweight='bold')

    # Common unified colorbar on the right across all 4 subplots
    fig.subplots_adjust(right=0.88, top=0.89, bottom=0.07, left=0.08, hspace=0.22, wspace=0.12)
    cbar_ax = fig.add_axes([0.90, 0.15, 0.025, 0.68])
    cb = fig.colorbar(hb_last, cax=cbar_ax)
    cb.set_label(r'Median $\Delta F = F(O) - \max(P_{base}, P_{donor})$ (Global Scale $[-F(O)_{max}, +F(O)_{max}]$)', fontsize=11, fontweight='bold')

    plt.suptitle("Crossover Recombination Phase Portraits\n"
                 r"Median Advantage $\Delta F = F(O) - \max(P_{base}, P_{donor})$ across $F(P_{base}) \times F(P_{donor})$ Domain",
                 fontsize=13.5, fontweight='bold', y=0.975)
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
    parser.add_argument('--no-better-crosses', action='store_false', dest='show_better_crosses',
                        help=r"Disable plotting green crosses for solutions with \Delta F > \epsilon on Figure 2")
    parser.set_defaults(show_better_crosses=True)
    parser.add_argument('--dry-run', action='store_true', help="Run small dry run with 10 pairs")
    parser.add_argument('--plot-only', action='store_true', help="Skip simulations and re-plot from existing CSVs")

    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Load parents directly from Task 1 CSVs
    parents_by_fmt = {}
    for fmt in args.formats:
        df_p = pd.read_csv(os.path.join(args.task1_dir, f"landscape_data_f{fmt}.csv"))[['parent_fitness', 'parent_genotype', 'parent_run']].drop_duplicates()
        parents_by_fmt[fmt] = df_p.to_dict('records')
        print(f"[LOAD] f{fmt}: Loaded {len(parents_by_fmt[fmt])} parents from Task 1 (Max F = {df_p['parent_fitness'].max():.6f})")

    # 2. Run Crossover or Load Existing Data
    dfs = {}
    for fmt in args.formats:
        csv_path = os.path.join(args.out_dir, f"crossover_data_f{fmt}.csv")
        if args.plot_only and os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if 'p_base_fitness' not in df.columns:
                is_hl = df['direction'] == 'high_x_low'
                df['p_base_fitness'] = np.where(is_hl, df['p_high_fitness'], df['p_low_fitness'])
                df['p_donor_fitness'] = np.where(is_hl, df['p_low_fitness'], df['p_high_fitness'])
            dfs[fmt] = df
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
    # Compute global bounds dynamically across all representations (no hardcoding)
    min_parent_fitness, max_parent_fitness = min(df['p_low_fitness'].min() for df in dfs.values() if not df.empty), max(df['p_high_fitness'].max() for df in dfs.values() if not df.empty)
    min_offspring_fitness, max_offspring_fitness = min(df['offspring_fitness'].min() for df in dfs.values() if not df.empty), max(df['offspring_fitness'].max() for df in dfs.values() if not df.empty)
    global_max = float(max(max_parent_fitness, max_offspring_fitness))
    # Colorbar range for delta_high: symmetric around 0.0 so (vmin+vmax)/2 == 0.0 (neutral threshold)
    max_delta = max(abs(df['delta_high']).max() for df in dfs.values() if not df.empty)
    vrange = (-float(max_delta), float(max_delta))

    export_tables(dfs, args.out_dir, exclude_metrics=["heritability"])
    plot_2d_scatter(dfs, args.out_dir, global_max)
    plot_parents_distribution(dfs, args.out_dir, global_max)
    plot_phase_portrait(dfs, args.out_dir, global_max, vrange, show_better_crosses=args.show_better_crosses)
    plot_3d_interactive(dfs, args.out_dir, global_max, vrange)
    print(f"\n[DONE] All Task 2 crossover deliverables saved to: {args.out_dir}")


if __name__ == "__main__":
    main()
