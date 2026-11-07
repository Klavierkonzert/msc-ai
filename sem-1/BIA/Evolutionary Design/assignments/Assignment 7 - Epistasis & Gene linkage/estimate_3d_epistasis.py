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
from matplotlib.gridspec import GridSpec

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
    collect_genotypes,
    knockout_genes,
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

    :param frams_lib: FramsticksLib object.
    :param geno: Genotype string.
    :param prefix: Prefix for genotype strings.
    :param fitness_metric: Fitness metric to use.
    :return: Dictionary containing epistasis results.
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

    # 1D Diagonals: (i, i, i) -> single knockout effect dF_i
    v_idx = np.array(valid_genes, dtype=int)
    tensor_base1[v_idx, v_idx, v_idx] = raw_delta_2d[v_idx, v_idx]

    # 2D Lateral Diagonals: (i, i, j), (i, j, i), (j, i, i) -> pairwise epistasis eps_ij
    pairs = np.array(list(itertools.permutations(valid_genes, 2)), dtype=int)
    if len(pairs) > 0:
        pi, pj = pairs[:, 0], pairs[:, 1]
        eps_pairs = eps_2d[pi, pj]
        for p1, p2, p3 in [(pi, pi, pj), (pi, pj, pi), (pj, pi, pi)]:
            tensor_base1[p1, p2, p3] = eps_pairs

    tensor_base2 = tensor_base1.copy()

    # 3D Triplet entries: Vectorized calculation across all triplets
    num_triplets = 0
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

        num_triplets = int(np.count_nonzero(valid_mask))
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
        'stats': {
            'num_triplets': num_triplets,
            'sum_raw_triplets_b1': sum_raw_triplets_b1,
            'sum_abs_triplets_b1': sum_abs_triplets_b1,
            'dir_triplets_b1': (sum_raw_triplets_b1 / sum_abs_triplets_b1) if sum_abs_triplets_b1 != 0 else 0.0,
            'mean_abs_triplets_b1': (sum_abs_triplets_b1 / num_triplets) if num_triplets else 0.0,
            'sum_raw_triplets_b2': sum_raw_triplets_b2,
            'sum_abs_triplets_b2': sum_abs_triplets_b2,
            'dir_triplets_b2': (sum_raw_triplets_b2 / sum_abs_triplets_b2) if sum_abs_triplets_b2 != 0 else 0.0,
            'mean_abs_triplets_b2': (sum_abs_triplets_b2 / num_triplets) if num_triplets else 0.0,
            'sum_raw_tensor_b1': sum_raw_tensor_b1,
            'sum_abs_tensor_b1': sum_abs_tensor_b1,
            'sum_raw_tensor_b2': sum_raw_tensor_b2,
            'sum_abs_tensor_b2': sum_abs_tensor_b2,
        }
    }


BASELINE_DEFS = {
    i: {
        'tensor_key': f'tensor_base{i}',
        'eps_key': f'eps{i}',
        'stat_suffix': f'b{i}',
        'title': f'Baseline {i}: Individual Genes ('+ ('1st' if i==1 else '2nd')+ '-Order Null Model)'
    } for i in (1,2)
}


def _resolve_baseline_config(baseline: Any) -> Tuple[int, Dict[str, str]]:
    """Resolves baseline parameter into baseline number (1 or 2) and its metadata dictionary."""
    if isinstance(baseline, str):
        b_num = 2 if ('2' in baseline or 'pairwise' in baseline.lower()) else 1
    else:
        b_num = 2 if int(baseline) == 2 else 1
    return b_num, BASELINE_DEFS[b_num]


def extract_plotted_points(res: Dict[str, Any], baseline: int = 1,
    include_lateral: bool = True, include_diagonal: bool = True, opposite_corner: bool = False,
) -> Tuple[List[int], List[int], List[int], np.ndarray]:
    """
    Extracts (xs, ys, zs, vals) for a single creature and baseline where
    coordinates directly correspond 1-to-1 via identity to gene indices:
    x = gene i, y = gene j, z = gene k, and val = tensor[i, j, k].

    Canonical triplets domain: 0 <= i <= j <= k < L:
    - Strict triplets: i < j < k (canonical ordered combinations, C(L, 3))
    - Lateral pairwise epistasis: (i == j < k) or (i < j == k)
    - Diagonal single knockouts: i == j == k (spatial diagonal)
    """
    geno = res['geno']
    L = len(geno)
    b_num, cfg = _resolve_baseline_config(baseline)
    tensor_key = cfg['tensor_key']
    tensor = res.get(tensor_key)
    if tensor is None:
        return [], [], [], np.array([], dtype=float)

    xs, ys, zs, vals = [], [], [], []
    for i in range(L):
        for j in range(i, L):
            for k in range(j, L):
                is_diag = (i == j == k)
                is_lat = (i == j or j == k) and not is_diag
                if not include_diagonal and is_diag:
                    continue
                if not include_lateral and is_lat:
                    continue
                val = tensor[i, j, k]
                if not np.isnan(val):
                    xs.append(i)
                    ys.append(j)
                    zs.append(k)
                    vals.append(val)

    return xs, ys, zs, np.array(vals, dtype=float)


def plot_creature_3d_heatmap(ax: Axes3D,
    res: Dict[str, Any], baseline: int = 1, creature_idx: Optional[int] = None,
    elev: float = 24, azim: float = -8, ball_size: float = 32.0,
    cmap: Optional[Any] = None, norm: Optional[Any] = None, show_cbar: bool = True,
    include_lateral: bool = True, include_diagonal: bool = True, invert_i: bool = True,  opposite_corner: bool = True,
    stretch_k: float = 2.0, stretch_xy: float = 1.5,
) -> Optional[Any]:
    """
    Renders a single 3D scatter heatmap subplot ("small balls arranged in a 3D grid")
    for one creature on the provided 3D Axes.

    :param include_lateral: If True (default), includes lateral pairwise epistasis entries.
    :param include_diagonal: If True (default), includes single knockout diagonal entries.
    :param invert_i: If True (default), inverts the i-axis direction.
    :param opposite_corner: If True (default), places the pyramid on the opposite corner of the ji-plane.
    :param stretch_k: Stretch factor for the k (vertical) axis (default: 2.0).
    :param stretch_xy: Stretch factor for the i and j (horizontal) axes (default: 1.5).
    """
    b_num, cfg = _resolve_baseline_config(baseline)
    b_suffix = cfg['stat_suffix']

    geno = res['geno']
    L = len(geno)
    xs, ys, zs, vals = extract_plotted_points(
        res, baseline=baseline,
        include_lateral=include_lateral, include_diagonal=include_diagonal,
        opposite_corner=opposite_corner,
    )

    if len(vals) == 0:
        prefix_lbl = f"Creature {creature_idx}: " if creature_idx is not None else geno
        ax.set_title(f"{prefix_lbl}\nNo data",#f"{prefix_lbl}{geno}\nNo data", 
                    fontsize=10)
        return None

    if norm is None:
        vmax = np.nanmax(np.abs(vals)) if len(vals) > 0 and np.nanmax(np.abs(vals)) > 0 else 1.0
        norm = CenteredNorm(vcenter=0.0, halfrange=vmax)

    abs_vals = np.abs(vals)
    ref_max = norm.halfrange if (hasattr(norm, 'halfrange') and norm.halfrange is not None and norm.halfrange > 0) else (np.nanmax(abs_vals) if len(abs_vals) > 0 and np.nanmax(abs_vals) > 0 else 1.0)
    sizes = ball_size * (0.6 + 0.8 * (abs_vals / ref_max))

    sc = ax.scatter(xs, ys, zs,
                    c=vals, cmap=cmap or RWG_CMAP, norm=norm,
                    s=sizes, alpha=0.88, edgecolors='k', linewidth=0.2, depthshade=True
                )

    ax.view_init(elev=elev, azim=azim)
    ax.dist = 8.5
    ax.set_box_aspect((stretch_xy, stretch_xy, stretch_k))

    # Clean panes: eliminate distracting empty cube background fills
    # ax.xaxis.pane.fill = ax.yaxis.pane.fill = ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('none'), ax.yaxis.pane.set_edgecolor('none'), ax.zaxis.pane.set_edgecolor('none')

    #stat = res.get('stats', {})
    #raw_s, abs_s = stat.get(f'sum_raw_triplets_{b_suffix}', 0.0), stat.get(f'sum_abs_triplets_{b_suffix}', 0.0)

    prefix_lbl = f"Creature {creature_idx}: " if creature_idx is not None else ""
    ax.set_title(f"{prefix_lbl}{geno}", fontsize=9.5, fontweight='bold', pad=8)

    step = max(1, L // 3)
    tick_locs = list(range(0, L, step))
    if (L - 1) not in tick_locs:
        tick_locs.append(L - 1)
        if L-1 - tick_locs[-2]<step//2:
            tick_locs.pop(-2)     

    tick_labels = [f"{geno[p]}({p})" for p in tick_locs]

    ax.set_xticks(tick_locs)
    ax.set_xticklabels(tick_labels, fontsize=6.5, rotation=0, ha='right', va='center')
    
    yang = 90
    ytick_locs = list(range(0, L, int(round(90/yang))))
    ytick_labels = [f"{geno[p]}({p})" for p in ytick_locs]
    ax.set_yticks(ytick_locs)
    ax.set_yticklabels(ytick_labels, fontsize=6.5, rotation=yang, ha='left', va='center')

    z_tick_locs = range(0, L, 1)
    z_tick_labels = [f"{geno[p]}({p})" for p in z_tick_locs]
    ax.set_zticks(z_tick_locs)
    ax.set_zticklabels(z_tick_labels, fontsize=6.5)

    # Decouple x-axis (i) ticks from vertical z-displacement so i labels stay higher on screen
    ax.xaxis._axmask = lambda: [False, True, False]
    ax.tick_params(axis='x', pad=0)
    ax.tick_params(axis='y', pad=-1.5)

    ax.set_xlabel("i", fontsize=8, labelpad=20)
    ax.set_ylabel("j", fontsize=8, labelpad=2, y=0.5)
    ax.set_zlabel("k", fontsize=8, labelpad=2)

    # place ticks/axes on the opposite corners to match the pyramide's edges
    ax.xaxis._axinfo['juggled'] = (2,2,2)
    ax.yaxis._axinfo['juggled'] = (2,2,2)
    ax.zaxis._axinfo['juggled'] = (1,1,1)

    #desaturating redundant coordinate planes:
    ax.xaxis.set_pane_color((1, 1, 1, 0.2))  # yz-plane
    ax.yaxis.set_pane_color((1, 1, 1, 0.2))  # xz-plane
    # Leave ax.zaxis pane unchanged for xy-plane

    # Desaturate background gridlines across all 3D axes
    for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
        axis._axinfo['grid']['color'] = (0.75, 0.75, 0.75, 0.35)
        axis._axinfo['grid']['linewidth'] = 0.4

    if invert_i:
        ax.set_xlim(L - 0.5, -0.5)
    else:
        ax.set_xlim(-0.5, L - 0.5)

    ax.set_ylim(-0.5, L - 0.5)
    ax.set_zlim(-0.1, L - 0.5)

    if show_cbar:
        cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.035, pad=0.08, shrink=0.7)
        cbar.ax.tick_params(labelsize=6.5)
        cbar.set_label(rf"$\varepsilon_{{ijk}}^{{({b_num})}}$", fontsize=7.5)

    return sc


def visualize_3d_heatmaps(results_list: List[Dict[str, Any]], baseline: int = 1,
    fig: Optional[plt.Figure] = None, axes: Optional[List[Axes3D]] = None, save_path: Optional[str] = None,
    elev: float = 24, azim: float = -8, ball_size: float = 32.0,
    same_scale: bool = True, shared_norm: Optional[Any] = None, show_row_cbar: bool = True, cax: Optional[plt.Axes] = None,
    include_lateral: bool = True, include_diagonal: bool = True, invert_i: bool = True, opposite_corner: bool = True,
    stretch_k: float = 2.0, stretch_xy: float = 1.5,
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

    if same_scale and shared_norm is None:
        all_vals = []
        for res in results_list:
            _, _, _, vals = extract_plotted_points(
                res, baseline=baseline, include_lateral=include_lateral, include_diagonal=include_diagonal,
                opposite_corner=opposite_corner
            )
            all_vals.extend(vals.tolist())
        vmax = float(np.nanmax(np.abs(all_vals))) if len(all_vals) > 0 and np.nanmax(np.abs(all_vals)) > 0 else 1.0
        shared_norm = CenteredNorm(vcenter=0.0, halfrange=vmax)

    if fig is None or axes is None:
        created_fig = True
        if same_scale:
            fig = plt.figure(figsize=(5.4 * k + 1.2, 6.0))
            gs = GridSpec(1, k + 1, figure=fig, width_ratios=[1.0] * k + [0.035],
                          wspace=0.08, left=0.03, right=0.94, top=0.93, bottom=0.05)
            axes = [fig.add_subplot(gs[0, col_idx], projection='3d') for col_idx in range(k)]
            cax = fig.add_subplot(gs[0, k])
        else:
            fig = plt.figure(figsize=(5.4 * k, 6.0))
            axes = [fig.add_subplot(1, k, col_idx + 1, projection='3d') for col_idx in range(k)]

    last_sc = None
    for col_idx, (ax, res) in enumerate(zip(axes, results_list)):
        sc = plot_creature_3d_heatmap(ax=ax, res=res, baseline=b_num, creature_idx=col_idx + 1,
                        elev=elev, azim=azim, ball_size=ball_size,
                        norm=shared_norm if same_scale else None, show_cbar=(not same_scale),
                        include_lateral=include_lateral, include_diagonal=include_diagonal, invert_i=invert_i,
                        opposite_corner=opposite_corner, stretch_k=stretch_k, stretch_xy=stretch_xy,
                    )
        if sc is not None:
            last_sc = sc

    if same_scale and show_row_cbar and last_sc is not None and cax is not None:
        pos = cax.get_position()
        cax.set_position([pos.x0, pos.y0 + 0.12 * pos.height, pos.width, pos.height * 0.76])
        cb = fig.colorbar(last_sc, cax=cax)
        cb.ax.tick_params(labelsize=7.5)
        cb.set_label(rf"$\varepsilon_{{ijk}}^{{({b_num})}}$", fontsize=9, fontweight='bold', labelpad=8)

    if created_fig:
        fig.suptitle(cfg['title'], fontsize=12, fontweight='bold', y=0.98)
        if not same_scale:
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


def visualize_combined_3d_heatmaps(results_list: List[Dict[str, Any]], mode: int = 3, save_path: Optional[str] = None,
                                    elev:           float = 24,   azim:           float = -8,   ball_size:      float = 32.0,
                                    same_scale:     bool  = True, include_lateral: bool = True, include_diagonal: bool = True,
                                    invert_i:       bool  = True, opposite_corner: bool = True, stretch_k:      float = 2.0,
                                    stretch_xy:     float = 1.5,
):
    """
    Renders 3D scatter subplots ("small balls arranged in a 3D grid")
    for the tested creatures, comparing baselines according to `mode`.
    Reuses `visualize_3d_heatmaps` for rendering each baseline row.

    The `mode` argument is a bitmask (unsigned int / 1 byte):
      - Bit 0 (0b01 = 1): Baseline 1 (Individual Genes / 1st-Order Null Model)
      - Bit 1 (0b10 = 2): Baseline 2 (Pairwise Epistasis / 2nd-Order Null Model)
      - Both bits (0b11 = 3): Both baselines arranged as a 2 x k grid.

    :param same_scale: If True (default), uses the same colorbar scale for all plots
                       (even across both baselines) and renders one colorbar per row.
    :param include_lateral: If True (default), includes lateral pairwise epistasis entries.
    :param include_diagonal: If True (default), includes diagonal single knockout entries.
    :param invert_i: If True (default), inverts i-axis direction.
    :param opposite_corner: If True (default), places the pyramid on the opposite corner of the ji-plane.
    :param stretch_k: Stretch factor for the k (vertical) axis (default: 2.0).
    :param stretch_xy: Stretch factor for the i and j (horizontal) axes (default: 1.5).
    """
    k = len(results_list)
    if k == 0:
        return

    # Check that at least one of the first two bits is set
    b_enabled = (bool(mode & 0b01), bool(mode & 0b10))
    if not any(b_enabled):
        raise ValueError(f"Invalid mode={mode} (0b{mode:08b}): at least bit 0 (Baseline 1) or bit 1 (Baseline 2) must be set.")

    active_baselines = [i + 1 for i, b in enumerate(b_enabled) if b]
    n_rows = len(active_baselines)

    if same_scale:
        all_vals = []
        for b_num in active_baselines:
            for res in results_list:
                _, _, _, vals = extract_plotted_points(
                    res, baseline=b_num, include_lateral=include_lateral, include_diagonal=include_diagonal,
                    opposite_corner=opposite_corner
                )
                all_vals.extend(vals.tolist())
        vmax = float(np.nanmax(np.abs(all_vals))) if len(all_vals) > 0 and np.nanmax(np.abs(all_vals)) > 0 else 1.0
        shared_norm = CenteredNorm(vcenter=0.0, halfrange=vmax)

        fig = plt.figure(figsize=(5.4 * k + 1.2, 5.8 * n_rows))
        gs = GridSpec(n_rows, k + 1, figure=fig, width_ratios=[1.0] * k + [0.035],
                      wspace=0.08, hspace=0.18, left=0.03, right=0.94,
                      top=0.94 if n_rows == 1 else 0.95, bottom=0.05)

        for row_idx, b_num in enumerate(active_baselines):
            row_axes = [fig.add_subplot(gs[row_idx, col_idx], projection='3d')  for col_idx in range(k)]
            row_cax = fig.add_subplot(gs[row_idx, k])
            visualize_3d_heatmaps(results_list=results_list, baseline=b_num, fig=fig, axes=row_axes, elev=elev, azim=azim,
                ball_size=ball_size, same_scale=same_scale, shared_norm=shared_norm, show_row_cbar=True, cax=row_cax,
                include_lateral=include_lateral, include_diagonal=include_diagonal, invert_i=invert_i, opposite_corner=opposite_corner,
                stretch_k=stretch_k, stretch_xy=stretch_xy,
            )
    else:
        fig = plt.figure(figsize=(5.4 * k, 5.8 * n_rows))
        for row_idx, b_num in enumerate(active_baselines):
            row_axes = [fig.add_subplot(n_rows, k, row_idx * k + col_idx + 1, projection='3d') for col_idx in range(k)]
            visualize_3d_heatmaps(results_list=results_list, baseline=b_num, fig=fig, axes=row_axes, elev=elev, azim=azim,
                ball_size=ball_size, same_scale=False, show_row_cbar=False,
                include_lateral=include_lateral, include_diagonal=include_diagonal, invert_i=invert_i, opposite_corner=opposite_corner,
                stretch_k=stretch_k, stretch_xy=stretch_xy,
            )
        plt.subplots_adjust(left=0.03, right=0.97, top=0.93 if n_rows == 1 else 0.95, bottom=0.05, wspace=0.08, hspace=0.22)

    # Suptitles
    if n_rows == 1:
        cfg = BASELINE_DEFS[active_baselines[0]]
        fig.suptitle(cfg['title'], fontsize=12, fontweight='bold', y=0.98)
    else:
        fig.text(0.48, 0.985, BASELINE_DEFS[1]['title'], ha='center', fontsize=12, fontweight='bold')
        fig.text(0.48, 0.490, BASELINE_DEFS[2]['title'], ha='center', fontsize=12, fontweight='bold')

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"[PLOT] Saved combined 3D heatmap (mode={mode}) to: {save_path}")
    else:
        plt.show()
    plt.close(fig)


def save_summary_table_csv(results_list: List[Dict[str, Any]], csv_path: str):
    """
    Saves quantitative epistasis sums and derived metrics across baselines and genotypes to CSV.
    """
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("Creature,Genotype,Length,WildFitness,NumTriplets,"
                "SumRaw_Triplets_B1,SumAbs_Triplets_B1,Dir_Triplets_B1,MeanAbs_Triplets_B1,"
                "SumRaw_Tensor_B1,SumAbs_Tensor_B1,"
                "SumRaw_Triplets_B2,SumAbs_Triplets_B2,Dir_Triplets_B2,MeanAbs_Triplets_B2,"
                "SumRaw_Tensor_B2,SumAbs_Tensor_B2\n")
        for idx, res in enumerate(results_list, 1):
            g = res['geno']
            L = len(g)
            fit = res['wild_fit']
            s = res['stats']
            f.write(
                f"Creature {idx},{g},{L},{fit:.5f},{s['num_triplets']},"
                f"{s['sum_raw_triplets_b1']:.5f},{s['sum_abs_triplets_b1']:.5f},"
                f"{s['dir_triplets_b1']:.5f},{s['mean_abs_triplets_b1']:.5f},"
                f"{s['sum_raw_tensor_b1']:.5f},{s['sum_abs_tensor_b1']:.5f},"
                f"{s['sum_raw_triplets_b2']:.5f},{s['sum_abs_triplets_b2']:.5f},"
                f"{s['dir_triplets_b2']:.5f},{s['mean_abs_triplets_b2']:.5f},"
                f"{s['sum_raw_tensor_b2']:.5f},{s['sum_abs_tensor_b2']:.5f}\n"
            )
    print(f"[CSV] Saved epistasis comparison table to: {csv_path}")


def format_markdown_summary_table(results_or_csv: Any, selected_dir: Optional[str] = None,
                                    bold_mode: str = "all-baselines", max_val: Optional[float] = None) -> str:
    """
    Formats the 3D triplet epistasis summary table by delegating to print_epistasis_table.
    Accepts either a results_list, a CSV file path string, or a pandas DataFrame.
    """
    import pandas as pd
    from print_epistasis_table import generate_markdown_table

    if isinstance(results_or_csv, str):
        df = pd.read_csv(results_or_csv)
    elif isinstance(results_or_csv, pd.DataFrame):
        df = results_or_csv
    elif isinstance(results_or_csv, list):
        rows = []
        for idx, res in enumerate(results_or_csv, 1):
            s = res.get('stats', {})
            row = {
                'Creature': f"Creature {idx}", 'Genotype': res['geno'], 'Length': len(res['geno']),
                'WildFitness': res.get('wild_fit', 0.0), 'NumTriplets': s.get('num_triplets', 0),
            }
            for i in (1, 2):
                row.update({
                    f'SumRaw_Triplets_B{i}':    s.get(f'sum_raw_triplets_b{i}', 0.0),
                    f'SumAbs_Triplets_B{i}':    s.get(f'sum_abs_triplets_b{i}', 0.0),
                    f'Dir_Triplets_B{i}':       s.get(f'dir_triplets_b{i}',     0.0),
                    f'MeanAbs_Triplets_B{i}':   s.get(f'mean_abs_triplets_b{i}', 0.0),
                    f'SumRaw_Tensor_B{i}':      s.get(f'sum_raw_tensor_b{i}',   0.0),
                    f'SumAbs_Tensor_B{i}':      s.get(f'sum_abs_tensor_b{i}',   0.0),
                })
            rows.append(row)
        df = pd.DataFrame(rows)
    else:
        raise TypeError(f"Unsupported results type for table formatting: {type(results_or_csv)}")

    return generate_markdown_table(df, selected_dir=selected_dir, max_val=max_val, bold_mode=bold_mode)


def _worker_compute_creature_epistasis(creature_idx: int, geno_clean: str, prefix: str,
                                        opt: str,frams_path: str, sim_settings: str) -> Tuple[int, Dict[str, Any]]:
    """
    Worker process: initializes an isolated FramsticksLib instance and computes 3D epistasis
    for a single creature.
    """
    if FramsticksLib is None:
        raise RuntimeError("Could not import FramsticksLib from framspy-download.")
    frams_lib = FramsticksLib(frams_path, None, sim_settings) # it's necessary to instantiate a FramsticksLib instance due to (1) Unpicklable Ctypes Objects in FramsticksLib and (2) C Library Global State Isolation
    res = compute_3d_epistasis_for_genotype(frams_lib, geno_clean, prefix=prefix, fitness_metric=opt)
    return creature_idx, res

def  compute_epistasis_parallel(genotypes: List[Dict[str, Any]],num_workers: int,prefix: str,opt: str,frams_path: str,sim: str):
    from concurrent.futures import ProcessPoolExecutor, as_completed

    indexed_results = {}
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {
                executor.submit(
                    _worker_compute_creature_epistasis,
                    idx,
                    c['clean'], prefix, opt, frams_path, sim,
                ): idx
            for idx, c in enumerate(genotypes)
        }
        for fut in as_completed(futures):
            idx, res = fut.result()
            indexed_results[idx] = res

    return [indexed_results[i] for i in range(len(genotypes))]
def compute_epistasis_sequentially(genotypes: List[Dict[str, Any]],prefix: str,opt: str,frams_path: str,sim: str):
    
    if FramsticksLib is None:
            raise RuntimeError("Could not import FramsticksLib from framspy-download.")
    frams_lib = FramsticksLib(frams_path, None, sim)
    results = [compute_3d_epistasis_for_genotype(frams_lib, c['clean'], prefix, opt)
                for c in genotypes]
    return results

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
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of parallel worker processes for creature evaluation (default: min(number of genotypes, CPU count)).")
    parser.add_argument("--mode", type=int, default=3,
                        help="1-byte bitmask for epistasis baselines to visualize: "
                             "bit 0 (1) -> Baseline 1; bit 1 (2) -> Baseline 2; 3 -> both. Default: 3.")
    parser.add_argument("--out", default=None,
                        help="Output image path for 3D epistasis plot. If omitted, saves based on --mode to <outdir>.")
    parser.add_argument("--outdir", default=r"assignments\Assignment 7 - Epistasis & Gene linkage\results\epistasis",
                        help="Output directory for 3D epistasis plots and summary CSV.")

    ############################ Geometry arguments ##################################################
    parser.add_argument("--no-same-scale", "--independent-scale", dest="same_scale", action="store_false", default=True,
                        help="Use independent colorbar scales for each subplot instead of a unified row colorbar scale.")
    parser.add_argument("--lateral", "--include-lateral", dest="include_lateral", action=argparse.BooleanOptionalAction,
                        default=True, help="Include lateral pairwise epistasis entries (default: True).")
    parser.add_argument("--diagonal", "--include-diagonal", dest="include_diagonal", action=argparse.BooleanOptionalAction,
                        default=True, help="Include diagonal single knockout entries (default: True).")
    parser.add_argument("--invert-i", dest="invert_i", action=argparse.BooleanOptionalAction,
                        default=True, help="Invert i-axis direction (default: True).")
    parser.add_argument("--opposite-corner", dest="opposite_corner", action=argparse.BooleanOptionalAction,
                        default=True, help="Place the pyramid on the opposite corner of the ji-plane (default: True).")
    parser.add_argument("--stretch-k", type=float, default=2.5, help="Box aspect stretch factor for the k (vertical) axis (default: 2.0).")
    parser.add_argument("--stretch-xy", type=float, default=2, help="Box aspect stretch factor for the i and j (horizontal) axes (default: 1.5).")
    parser.add_argument("--elev", type=float, default=8.0, help="3D camera elevation angle in degrees (default: 8).")
    parser.add_argument("--azim", type=float, default=-170, help="3D camera azimuth angle in degrees (default: 15).")

    args = parser.parse_args()

    # Collect genotypes using shared collect_genotypes helper
    prefix = f"/*{args.genformat}*/"
    collected = collect_genotypes(folder=args.genotypes_folder, genotypes=args.genotypes, genformat=args.genformat)

    if not collected:
        raise ValueError("No genotypes provided. Use --genotypes or --genotypes-folder.")

    print(f"Total genotypes to analyze in 3D: {len(collected)}")
    for idx, c in enumerate(collected, 1):
        print(f" [{idx}] {c['title']} : {c['raw']}")

    # Compute 3D epistasis for each creature (sequential or parallel)
    k_creatures = len(collected)
    num_workers = max(1, args.workers) if args.workers is not None else min(k_creatures, os.cpu_count() or 4)

    results_list = []
    if num_workers <= 1 or k_creatures <= 1:
        # Sequential execution
        print("\nEvaluating creatures sequentially (single worker)...")
        results_list = compute_epistasis_sequentially(collected, prefix, args.opt, args.frams_path, args.sim)
    else:
        # Parallel execution across worker processes
        print(f"\nEvaluating {k_creatures} creatures in parallel across {num_workers} worker processes...")
        results_list = compute_epistasis_parallel(collected,num_workers,prefix,args.opt,args.frams_path,args.sim)

    # Generate Visualizations
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    csv_file = os.path.join(outdir, "epistasis_3d_summary.csv")
    save_summary_table_csv(results_list, csv_file)

    if args.out:
        out_plot = args.out
    else:
        if args.mode in (1,2):
            out_plot = os.path.join(outdir, f"epistasis_3d_baseline{args.mode}.png")
        else:
            out_plot = os.path.join(outdir, "epistasis_3d_combined.png")
    visualize_combined_3d_heatmaps(results_list, mode=args.mode, save_path=out_plot,
                elev=args.elev, azim=args.azim, same_scale=args.same_scale,
                include_lateral=args.include_lateral, include_diagonal=args.include_diagonal,
                invert_i=args.invert_i, opposite_corner=args.opposite_corner, stretch_k=args.stretch_k,
                stretch_xy=args.stretch_xy,
            )

    print("\n--- 3D Triplet Epistasis Summary Table ---")
    md_table = format_markdown_summary_table(results_list, selected_dir=args.genotypes_folder)
    print(md_table)
    print("------------------------------------------\n")
    print("\n[Done] All 3D triplet epistasis analyses and visualizations complete!")


if __name__ == "__main__":
    main()
