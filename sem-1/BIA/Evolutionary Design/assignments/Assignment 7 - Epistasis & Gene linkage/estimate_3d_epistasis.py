#!/usr/bin/env python3
"""
estimate_3d_epistasis.py

Empirical estimation and 3D visualization of triplet gene epistasis in Framsticks f9 genotypes.
Reuses 2D epistasis estimation, genotype collection, and colormap from estimate_epistasis.py:
  - collect_genotypes
  - knockout_genes
  - evaluate_batch_genotypes
  - compute_epistasis_matrix
  - RWG_CMAP

Evaluates all gene triplets (i, j, k) across two null-model baselines:
  - Baseline 1 (Individual genes / 1st-order null model):
      eps_{ijk}^{(1)} = dF_{ijk} - (dF_i + dF_j + dF_k)
  - Baseline 2 (Pairwise epistasis / 2nd-order null model):
      eps_{ijk}^{(2)} = dF_{ijk} - (dF_i + dF_j + dF_k + eps_{ij} + eps_{ik} + eps_{jk})
                      = dF_{ijk} - (dF_{ij} + dF_{jk} + dF_{ik}) + (dF_i + dF_j + dF_k)

Visualizes results as 3D scatter heatmaps with a centered Red-White-Green colormap.
Modular visualization functions:
  - plot_creature_3d_heatmap: renders a single 3D scatter subplot on an Axes3D
  - visualize_3d_heatmaps: renders a single baseline (1 x k) or plots on provided axes
  - visualize_combined_3d_heatmaps: multi-baseline orchestrator (mode bitmask, default 3)
                                   reusing visualize_3d_heatmaps
"""

import os
import sys
import argparse
import itertools
from typing import List, Tuple, Dict, Optional, Any

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import CenteredNorm

# Ensure access to sibling scripts and FramsticksLib
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
FRAMSPY_DOWNLOAD = os.path.join(WORKSPACE_ROOT, "framspy-download")
if FRAMSPY_DOWNLOAD not in sys.path:
    sys.path.insert(0, FRAMSPY_DOWNLOAD)

try:
    from FramsticksLib import FramsticksLib
except ImportError:
    try:
        from FramsticksLibCompetition import FramsticksLib
    except ImportError:
        FramsticksLib = None

# Reuse functions directly from estimate_epistasis
from estimate_epistasis import (
    load_genotypes_from_folder,
    collect_genotypes,
    knockout_genes,
    setstr,
    evaluate_batch_genotypes,
    compute_epistasis_matrix,
    RWG_CMAP,
)


def compute_3d_epistasis_for_genotype(
    frams_lib,
    geno: str,
    prefix: str = "/*9*/",
    fitness_metric: str = "vertpos"
) -> Dict[str, Any]:
    r"""
    Computes 3D epistasis tensors for all gene triplets in `geno` across two null baselines:
      1. Baseline 1 (Individual genes / 1st-order null model):
           eps_{ijk}^{(1)} = dF_{ijk} - (dF_i + dF_j + dF_k)
      2. Baseline 2 (Pairwise epistasis / 2nd-order null model):
           eps_{ijk}^{(2)} = dF_{ijk} - (dF_i + dF_j + dF_k + eps_{ij} + eps_{ik} + eps_{jk})
                           = dF_{ijk} - (dF_{ij} + dF_{jk} + dF_{ik}) + (dF_i + dF_j + dF_k)

    Diagonal conventions in tensor:
      - (i, i, i): single knockout effect dF_i
      - (i, i, j): pairwise epistasis eps_{ij}
      - (i, j, k) with distinct i, j, k: triplet epistasis eps_{ijk}
    Reuses compute_epistasis_matrix from estimate_epistasis.py for wild-type fitness,
    valid genes, single knockouts (dF_i), and pairwise epistasis (eps_ij).
    Uses NumPy vectorization for rapid tensor calculations.
    """
    L = len(geno)

    # Step 1 & 2: Reuse compute_epistasis_matrix for single and pairwise epistasis
    print(f"\n--- Computing single and pairwise epistasis for: {geno} (L={L}) ---")
    eps_2d, raw_delta_2d, wild_fit, valid_genes = compute_epistasis_matrix(
        frams_lib, geno, prefix=prefix, fitness_metric=fitness_metric
    )

    # Step 3: Triplet knockouts across valid genes in batch
    triplet_list = list(itertools.combinations(valid_genes, 3))
    triplet_genos = [prefix + knockout_genes(geno, i, j, k) for i, j, k in triplet_list]

    print(f" Evaluating {len(triplet_list)} gene triplets in batches...")
    triplet_fits_list = evaluate_batch_genotypes(frams_lib, triplet_genos, fitness_metric=fitness_metric)

    # Step 4: Populate 3D Tensors (Vectorized)
    tensor_base1 = np.full((L, L, L), np.nan)
    raw_delta_3d = np.full((L, L, L), np.nan)

    # 1D Diagonals: (i, i, i) -> single knockout effect dF_i
    v_idx = np.array(valid_genes, dtype=int)
    tensor_base1[v_idx, v_idx, v_idx] = raw_delta_2d[v_idx, v_idx]
    raw_delta_3d[v_idx, v_idx, v_idx] = raw_delta_2d[v_idx, v_idx]

    # 2D Lateral Diagonals: (i, i, j), (i, j, i), (j, i, i) -> pairwise epistasis eps_ij
    pairs = np.array(list(itertools.permutations(valid_genes, 2)), dtype=int)
    if len(pairs) > 0:
        pi, pj = pairs[:, 0], pairs[:, 1]
        eps_pairs = eps_2d[pi, pj]
        dF_pairs = raw_delta_2d[pi, pj]
        for p1, p2, p3 in [(pi, pi, pj), (pi, pj, pi), (pj, pi, pi)]:
            tensor_base1[p1, p2, p3] = eps_pairs
            raw_delta_3d[p1, p2, p3] = dF_pairs

    tensor_base2 = tensor_base1.copy()

    # 3D Triplet entries: Vectorized calculation across all triplets
    triplet_records = []
    if triplet_list:
        triplet_arr = np.array(triplet_list, dtype=int)
        ti, tj, tk = triplet_arr[:, 0], triplet_arr[:, 1], triplet_arr[:, 2]
        dF_ijk = np.array(triplet_fits_list) - wild_fit

        dF_i = raw_delta_2d[ti, ti]
        dF_j = raw_delta_2d[tj, tj]
        dF_k = raw_delta_2d[tk, tk]

        eps_ij = eps_2d[ti, tj]
        eps_jk = eps_2d[tj, tk]
        eps_ik = eps_2d[ti, tk]

        # Vectorized Baseline 1: Individual Genes (1st-order null model)
        eps1_all = dF_ijk - (dF_i + dF_j + dF_k)

        # Vectorized Baseline 2: Pairwise Epistasis (2nd-order null model)
        eps2_all = eps1_all - (eps_ij + eps_jk + eps_ik)

        valid_mask = (
            ~np.isnan(dF_ijk) &
            ~np.isnan(eps_ij) &
            ~np.isnan(eps_jk) &
            ~np.isnan(eps_ik)
        )

        # Vectorized assignment of all 6 permutations into the 3D tensor
        perms = [
            (ti[valid_mask], tj[valid_mask], tk[valid_mask]),
            (ti[valid_mask], tk[valid_mask], tj[valid_mask]),
            (tj[valid_mask], ti[valid_mask], tk[valid_mask]),
            (tj[valid_mask], tk[valid_mask], ti[valid_mask]),
            (tk[valid_mask], ti[valid_mask], tj[valid_mask]),
            (tk[valid_mask], tj[valid_mask], ti[valid_mask]),
        ]
        for p1, p2, p3 in perms:
            tensor_base1[p1, p2, p3] = eps1_all[valid_mask]
            tensor_base2[p1, p2, p3] = eps2_all[valid_mask]
            raw_delta_3d[p1, p2, p3] = dF_ijk[valid_mask]

        # Build triplet records for scatter plotting
        valid_indices = np.where(valid_mask)[0]
        triplet_records = [
            {
                'i': int(ti[idx]),
                'j': int(tj[idx]),
                'k': int(tk[idx]),
                'genes': f"{geno[ti[idx]]}{geno[tj[idx]]}{geno[tk[idx]]}",
                'f_triple': float(triplet_fits_list[idx]),
                'dF_ijk': float(dF_ijk[idx]),
                'eps1': float(eps1_all[idx]),
                'eps2': float(eps2_all[idx]),
            }
            for idx in valid_indices
        ]

        eps1_valid = eps1_all[valid_mask]
        eps2_valid = eps2_all[valid_mask]
        sum_raw_triplets_b1 = float(np.sum(eps1_valid)) if len(eps1_valid) else 0.0
        sum_abs_triplets_b1 = float(np.sum(np.abs(eps1_valid))) if len(eps1_valid) else 0.0
        sum_raw_triplets_b2 = float(np.sum(eps2_valid)) if len(eps2_valid) else 0.0
        sum_abs_triplets_b2 = float(np.sum(np.abs(eps2_valid))) if len(eps2_valid) else 0.0
    else:
        sum_raw_triplets_b1 = sum_abs_triplets_b1 = 0.0
        sum_raw_triplets_b2 = sum_abs_triplets_b2 = 0.0

    # Full tensor sums (including 1D, 2D diagonals and 6x permutations)
    sum_raw_tensor_b1 = float(np.nansum(tensor_base1))
    sum_abs_tensor_b1 = float(np.nansum(np.abs(tensor_base1)))

    sum_raw_tensor_b2 = float(np.nansum(tensor_base2))
    sum_abs_tensor_b2 = float(np.nansum(np.abs(tensor_base2)))

    # Pure 3D off-diagonal tensor sums (distinct i != j != k != i, 6x unique)
    print(f" Summary of epistasis sums for {geno}:")
    print(f"   Baseline 1 (Individual): Triplet sum raw = {sum_raw_triplets_b1:+.4f}, abs = {sum_abs_triplets_b1:.4f} | Tensor sum raw = {sum_raw_tensor_b1:+.4f}, abs = {sum_abs_tensor_b1:.4f}")
    print(f"   Baseline 2 (Pairwise)  : Triplet sum raw = {sum_raw_triplets_b2:+.4f}, abs = {sum_abs_triplets_b2:.4f} | Tensor sum raw = {sum_raw_tensor_b2:+.4f}, abs = {sum_abs_tensor_b2:.4f}")

    return {
        'geno': geno,
        'wild_fit': wild_fit,
        'valid_genes': valid_genes,
        'tensor_base1': tensor_base1,
        'tensor_base2': tensor_base2,
        'raw_delta_3d': raw_delta_3d,
        'triplet_records': triplet_records,
        'stats': {
            'num_triplets': len(triplet_records),
            'sum_raw_triplets_b1': sum_raw_triplets_b1,
            'sum_abs_triplets_b1': sum_abs_triplets_b1,
            'sum_raw_triplets_b2': sum_raw_triplets_b2,
            'sum_abs_triplets_b2': sum_abs_triplets_b2,
            'sum_raw_tensor_b1': sum_raw_tensor_b1,
            'sum_abs_tensor_b1': sum_abs_tensor_b1,
            'sum_raw_tensor_b2': sum_raw_tensor_b2,
            'sum_abs_tensor_b2': sum_abs_tensor_b2,
        }
    }


BASELINE_DEFS = {
    1: {
        'tensor_key': 'tensor_base1',
        'eps_key': 'eps1',
        'stat_suffix': 'b1',
        'title': 'Baseline 1: Individual Genes (1st-Order Null Model)'
    },
    2: {
        'tensor_key': 'tensor_base2',
        'eps_key': 'eps2',
        'stat_suffix': 'b2',
        'title': 'Baseline 2: Pairwise Epistasis (2nd-Order Null Model)'
    }
}


def _resolve_baseline_config(baseline: Any) -> Tuple[int, Dict[str, str]]:
    """Resolves baseline parameter into baseline number (1 or 2) and its metadata dictionary."""
    if isinstance(baseline, str):
        b_num = 2 if ('2' in baseline or 'pairwise' in baseline.lower()) else 1
    else:
        b_num = 2 if int(baseline) == 2 else 1
    return b_num, BASELINE_DEFS[b_num]


def plot_creature_3d_heatmap(
    ax: Axes3D,
    res: Dict[str, Any],
    baseline: int = 1,
    creature_idx: Optional[int] = None,
    elev: float = 24,
    azim: float = 48,
    ball_size: float = 32.0,
    cmap: Optional[Any] = None
) -> Optional[Any]:
    """
    Renders a single 3D scatter heatmap subplot ("small balls arranged in a 3D grid")
    for one creature on the provided 3D Axes.
    """
    b_num, cfg = _resolve_baseline_config(baseline)
    eps_key = cfg['eps_key']
    b_suffix = cfg['stat_suffix']

    geno = res['geno']
    L = len(geno)
    triplets = res.get('triplet_records', [])

    if not triplets:
        prefix_lbl = f"Creature {creature_idx}: " if creature_idx is not None else ""
        ax.set_title(f"{prefix_lbl}{geno}\nNo data", fontsize=10)
        return None

    xs = [r['i'] for r in triplets]
    ys = [r['j'] for r in triplets]
    zs = [r['k'] for r in triplets]
    vals = np.array([r[eps_key] for r in triplets])

    vmax = np.nanmax(np.abs(vals)) if len(vals) > 0 and np.nanmax(np.abs(vals)) > 0 else 1.0
    norm = CenteredNorm(vcenter=0.0, halfrange=vmax)

    abs_vals = np.abs(vals)
    max_abs = np.nanmax(abs_vals) if len(abs_vals) > 0 and np.nanmax(abs_vals) > 0 else 1.0
    sizes = ball_size * (0.6 + 0.8 * (abs_vals / max_abs))

    sc = ax.scatter(
        xs, ys, zs,
        c=vals,
        cmap=cmap or RWG_CMAP,
        norm=norm,
        s=sizes,
        alpha=0.85,
        edgecolors='k',
        linewidth=0.2,
        depthshade=True
    )

    ax.view_init(elev=elev, azim=azim)

    stat = res.get('stats', {})
    raw_s = stat.get(f'sum_raw_triplets_{b_suffix}', 0.0)
    abs_s = stat.get(f'sum_abs_triplets_{b_suffix}', 0.0)

    prefix_lbl = f"Creature {creature_idx}: " if creature_idx is not None else ""
    ax.set_title(
        f"{prefix_lbl}{geno}\n"
        rf"$\Sigma\varepsilon^{{({b_num})}}={raw_s:+.3f}$, $\Sigma|\varepsilon^{{({b_num})}}|={abs_s:.3f}$",
        fontsize=9.5,
        fontweight='bold',
        pad=8
    )

    step = max(1, L // 5)
    tick_locs = list(range(0, L, step))
    if (L - 1) not in tick_locs:
        tick_locs.append(L - 1)
    tick_labels = [f"{geno[p]}({p})" for p in tick_locs]

    ax.set_xticks(tick_locs)
    ax.set_xticklabels(tick_labels, fontsize=6.5)
    ax.set_yticks(tick_locs)
    ax.set_yticklabels(tick_labels, fontsize=6.5)
    ax.set_zticks(tick_locs)
    ax.set_zticklabels(tick_labels, fontsize=6.5)

    ax.set_xlabel("i", fontsize=8, labelpad=2)
    ax.set_ylabel("j", fontsize=8, labelpad=2)
    ax.set_zlabel("k", fontsize=8, labelpad=2)

    ax.set_xlim(-0.5, L - 0.5)
    ax.set_ylim(-0.5, L - 0.5)
    ax.set_zlim(-0.5, L - 0.5)

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.035, pad=0.08, shrink=0.7)
    cbar.ax.tick_params(labelsize=6.5)
    cbar.set_label(rf"$\varepsilon_{{ijk}}^{{({b_num})}}$", fontsize=7.5)

    return sc


def visualize_3d_heatmaps(
    results_list: List[Dict[str, Any]],
    baseline: int = 1,
    fig: Optional[plt.Figure] = None,
    axes: Optional[List[Axes3D]] = None,
    save_path: Optional[str] = None,
    elev: float = 24,
    azim: float = 48,
    ball_size: float = 32.0
) -> Tuple[Optional[plt.Figure], Optional[List[Axes3D]]]:
    """
    Renders 3D scatter heatmaps for a single epistasis baseline across tested creatures.
    Can be used standalone to create and save a 1 x k figure, or embedded into an existing
    multi-row figure by passing `fig` and `axes`.
    """
    k = len(results_list)
    if k == 0:
        return fig, axes

    b_num, cfg = _resolve_baseline_config(baseline)
    created_fig = False

    if fig is None or axes is None:
        created_fig = True
        fig = plt.figure(figsize=(5.6 * k, 5.2))
        axes = [fig.add_subplot(1, k, col_idx + 1, projection='3d') for col_idx in range(k)]

    for col_idx, (ax, res) in enumerate(zip(axes, results_list)):
        plot_creature_3d_heatmap(
            ax=ax,
            res=res,
            baseline=b_num,
            creature_idx=col_idx + 1,
            elev=elev,
            azim=azim,
            ball_size=ball_size
        )

    if created_fig:
        fig.suptitle(cfg['title'], fontsize=12, fontweight='bold', y=0.98)
        plt.subplots_adjust(left=0.04, right=0.96, top=0.93, bottom=0.06, wspace=0.20, hspace=0.30)
        if save_path:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[PLOT] Saved 3D heatmap (Baseline {b_num}) to: {save_path}")
            plt.close(fig)
        else:
            plt.show()
            plt.close(fig)

    return fig, axes


def visualize_combined_3d_heatmaps(
    results_list: List[Dict[str, Any]],
    mode: int = 3,
    save_path: Optional[str] = None,
    elev: float = 24,
    azim: float = 48,
    ball_size: float = 32.0
):
    """
    Renders 3D scatter subplots ("small balls arranged in a 3D grid")
    for the tested creatures, comparing baselines according to `mode`.
    Reuses `visualize_3d_heatmaps` for rendering each baseline row.

    The `mode` argument is a bitmask (unsigned int / 1 byte):
      - Bit 0 (0b01 = 1): Baseline 1 (Individual Genes / 1st-Order Null Model)
      - Bit 1 (0b10 = 2): Baseline 2 (Pairwise Epistasis / 2nd-Order Null Model)
      - Both bits (0b11 = 3): Both baselines arranged as a 2 x k grid.
    """
    k = len(results_list)
    if k == 0:
        return

    # Check that at least one of the first two bits is set
    b_enabled = (bool(mode & 0b01), bool(mode & 0b10))
    if not any(b_enabled):
        raise ValueError(
            f"Invalid mode={mode} (0b{mode:08b}): at least bit 0 (Baseline 1) or bit 1 (Baseline 2) must be set."
        )

    active_baselines = [i + 1 for i, b in enumerate(b_enabled) if b]
    n_rows = len(active_baselines)
    fig = plt.figure(figsize=(5.6 * k, 5.2 * n_rows))

    for row_idx, b_num in enumerate(active_baselines):
        row_axes = [
            fig.add_subplot(n_rows, k, row_idx * k + col_idx + 1, projection='3d')
            for col_idx in range(k)
        ]
        # Modularity: Reuse visualize_3d_heatmaps for rendering the row
        visualize_3d_heatmaps(
            results_list=results_list,
            baseline=b_num,
            fig=fig,
            axes=row_axes,
            elev=elev,
            azim=azim,
            ball_size=ball_size
        )

    # Suptitles and Layout
    if n_rows == 1:
        cfg = BASELINE_DEFS[active_baselines[0]]
        fig.suptitle(cfg['title'], fontsize=12, fontweight='bold', y=0.98)
    else:
        fig.text(0.5, 0.99, BASELINE_DEFS[1]['title'], ha='center', fontsize=12, fontweight='bold')
        fig.text(0.5, 0.495, BASELINE_DEFS[2]['title'], ha='center', fontsize=12, fontweight='bold')

    plt.subplots_adjust(
        left=0.04, right=0.96,
        top=0.93 if n_rows == 1 else 0.95,
        bottom=0.06,
        wspace=0.20,
        hspace=0.30
    )

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"[PLOT] Saved combined 3D heatmap (mode={mode}) to: {save_path}")
    else:
        plt.show()
    plt.close(fig)


def save_summary_table_csv(results_list: List[Dict[str, Any]], csv_path: str):
    """
    Saves quantitative epistasis sums across baselines and genotypes to CSV.
    """
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("Creature,Genotype,Length,WildFitness,NumTriplets,"
                "SumRaw_Triplets_B1,SumAbs_Triplets_B1,SumRaw_Tensor_B1,SumAbs_Tensor_B1,"
                "SumRaw_Triplets_B2,SumAbs_Triplets_B2,SumRaw_Tensor_B2,SumAbs_Tensor_B2\n")
        for idx, res in enumerate(results_list, 1):
            g = res['geno']
            L = len(g)
            fit = res['wild_fit']
            s = res['stats']
            f.write(
                f"Creature {idx},{g},{L},{fit:.5f},{s['num_triplets']},"
                f"{s['sum_raw_triplets_b1']:.5f},{s['sum_abs_triplets_b1']:.5f},"
                f"{s['sum_raw_tensor_b1']:.5f},{s['sum_abs_tensor_b1']:.5f},"
                f"{s['sum_raw_triplets_b2']:.5f},{s['sum_abs_triplets_b2']:.5f},"
                f"{s['sum_raw_tensor_b2']:.5f},{s['sum_abs_tensor_b2']:.5f}\n"
            )
    print(f"[CSV] Saved epistasis comparison table to: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Estimate and visualize 3D triplet epistasis in Framsticks f9 genotypes.")
    parser.add_argument("--frams-path", default=r"Framsticks55", help="Path to Framsticks installation directory.")
    parser.add_argument("--sim", default="eval-allcriteria.sim;deterministic.sim;sample-period-2.sim;only-body.sim",
                        help="Simulation settings files separated by semicolons.")
    parser.add_argument("--genformat", default="9", help="Genetic format to use (default: 9).")
    parser.add_argument('--opt', default='vertpos', help="Fitness optimization criterion (default: 'vertpos').")
    parser.add_argument("--genotypes", nargs="*", default=None, help="List of genotype strings to evaluate.")
    parser.add_argument("--genotypes-folder", default=r"assignments\Assignment 7 - Epistasis & Gene linkage\selected",
                        help="Folder containing .gen files to evaluate.")
    parser.add_argument("--mode", type=int, default=3,
                        help="1-byte bitmask for epistasis baselines to visualize: "
                             "bit 0 (1) -> Baseline 1; bit 1 (2) -> Baseline 2; 3 -> both. Default: 3.")
    parser.add_argument("--out", default=None,
                        help="Output image path for 3D epistasis plot. If omitted, saves based on --mode to <outdir>.")
    parser.add_argument("--outdir", default=r"assignments\Assignment 7 - Epistasis & Gene linkage\results\epistasis",
                        help="Output directory for 3D epistasis plots and summary CSV.")
    args = parser.parse_args()

    # Collect genotypes using shared collect_genotypes helper
    prefix = f"/*{args.genformat}*/"
    collected = collect_genotypes(
        folder=args.genotypes_folder,
        genotypes=args.genotypes,
        genformat=args.genformat
    )

    if not collected:
        raise ValueError("No genotypes provided. Use --genotypes or --genotypes-folder.")

    print(f"Total genotypes to analyze in 3D: {len(collected)}")
    for idx, c in enumerate(collected, 1):
        print(f" [{idx}] {c['title']} : {c['raw']}")

    # Initialize FramsticksLib
    if FramsticksLib is None:
        raise RuntimeError("Could not import FramsticksLib from framspy-download.")
    frams_lib = FramsticksLib(args.frams_path, None, args.sim)

    # Compute 3D epistasis for each creature
    results_list = []
    for c in collected:
        res = compute_3d_epistasis_for_genotype(frams_lib, c['clean'], prefix, args.opt)
        results_list.append(res)

    # Generate Visualizations
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    csv_file = os.path.join(outdir, "epistasis_3d_summary.csv")
    save_summary_table_csv(results_list, csv_file)

    if args.out:
        out_plot = args.out
    else:
        if args.mode == 1:
            out_plot = os.path.join(outdir, "epistasis_3d_baseline1.png")
        elif args.mode == 2:
            out_plot = os.path.join(outdir, "epistasis_3d_baseline2.png")
        else:
            out_plot = os.path.join(outdir, "epistasis_3d_combined.png")

    visualize_combined_3d_heatmaps(
        results_list,
        mode=args.mode,
        save_path=out_plot
    )

    print("\n[Done] All 3D triplet epistasis analyses and visualizations complete!")


if __name__ == "__main__":
    main()
