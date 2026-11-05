r"""
estimate_epistasis.py
Computes and visualizes pairwise epistasis matrices for selected genotypes in Framsticks.

Epistasis formulation:
For wild-type genotype g with fitness F(g):
- F(g \ {i}): fitness when gene i is knocked out
- F(g \ {j}): fitness when gene j is knocked out
- F(g \ {i, j}): fitness when both genes i and j are knocked out

Single-gene knockout effect (main effect / additive component):
  dF_i = F(g \ {i}) - F(g)
  dF_j = F(g \ {j}) - F(g)

Expected double knockout under additive (null) model (assuming linear additivity of ind. genes' effects):
  F_add(g \ {i, j}) = F(g) + dF_i + dF_j

Epistasis (interaction deviation):
  e_{i,j} = F(g \ {i, j}) - F_add(g \ {i, j}) # the non-linear effect of interaction of ij.
          = [F(g \ {i, j}) - F(g)] - [F(g \ {i}) - F(g)] - [F(g \ {j}) - F(g)]
          = dF_ij - (dF_i + dF_j)

On the diagonal (i == j):
  Stores the single knockout effect dF_i = F(g \ {i}) - F(g).
"""

import os
import sys
import glob
import re
import math
import argparse
import itertools
from typing import List, Tuple, Dict, Optional, Any

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import LinearSegmentedColormap

# Ensure repository paths are configured
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRAMSPY_DIR = os.path.join(REPO_ROOT, "framspy-download")
if FRAMSPY_DIR not in sys.path:
    sys.path.insert(0, FRAMSPY_DIR)

try:
    from FramsticksLib import FramsticksLib
except ImportError:
    try:
        from FramsticksLibCompetition import FramsticksLib
    except ImportError:
        FramsticksLib = None

# Centered Red-White-Green colormap shared across 2D and 3D epistasis visualizations
RWG_CMAP = LinearSegmentedColormap.from_list(
    'red_white_green', ["#d73027", "#f7f7f7", "#1a9850"], N=256
)


def setstr(s: str, pos: int, char: str = ' ') -> str:
    """Replaces character at `pos` with `char`."""
    assert len(char) == 1
    assert 0 <= pos < len(s)
    return s[:pos] + char + s[pos + 1:]


def knockout_genes(geno: str, *indices: int) -> str:
    """
    Returns genotype string with specified 0-based gene indices removed.
    Supports single, double, triple, or N-gene knockouts efficiently.
    Example:
        geno = "ABCDE"
        knockout_genes(geno, 1, 3) == "ACE"
    """
    idx_set = set(indices)
    return "".join(c for pos, c in enumerate(geno) if pos not in idx_set)


def load_genotypes_from_folder(folder_path: str, genformat: str = "9") -> List[Tuple[str, str]]:
    """
    Scans a folder for *.gen files and parses genotype strings.
    Returns list of tuples: (raw_genotype, source_label)
    """
    if not os.path.isdir(folder_path):
        print(f"[Warning] Genotypes folder not found: {folder_path}")
        return []

    pattern = os.path.join(folder_path, "*.gen")
    gen_files = sorted(glob.glob(pattern))
    results = []

    for path in gen_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Search for f<genformat> string
            geno_match = re.search(r"genotype:~?(/\*" + re.escape(str(genformat)) + r"\*/[^\r\n~]+)~?", content)
            if not geno_match:
                geno_match = re.search(r"(/\*" + re.escape(str(genformat)) + r"\*/[A-Za-z]+)", content)

            if geno_match:
                raw_geno = geno_match.group(1).strip("~")
                label = os.path.basename(path)
                results.append((raw_geno, label))
        except Exception as e:
            print(f"[Error] Failed to read {path}: {e}")
            continue

    print(f"Loaded {len(results)} genotypes from folder: '{folder_path}'")
    return results


def collect_genotypes(folder: Optional[str] = None, genotypes: Optional[List[str]] = None, genformat: str = "9") -> List[Dict[str, str]]:
    """
    Collects and deduplicates genotypes from folder and/or explicit string list.
    Returns list of dicts: {'raw': raw_geno, 'clean': clean_geno, 'title': label}
    """
    collected = []
    seen = set()
    prefix = f"/*{genformat}*/"

    if folder:
        folder_items = load_genotypes_from_folder(folder, genformat=genformat)
        for raw_g, label in folder_items:
            clean_g = raw_g.replace(prefix, "").strip().upper()
            if clean_g not in seen:
                seen.add(clean_g)
                collected.append({"raw": raw_g, "clean": clean_g, "title": label })

    if genotypes:
        for idx, g in enumerate(genotypes, 1):
            clean_g = g.replace(prefix, "").strip().upper()
            if clean_g not in seen:
                seen.add(clean_g)
                collected.append({"raw": g, "clean": clean_g, "title": f"Genotype {idx}"})

    return collected


def evaluate_genotypes_chunk(frams_lib, full_genos_chunk: List[str], fitness_metric: str = "vertpos", default_val: float = np.nan) -> List[float]:
    """
    Evaluates a chunk of full genotype strings (including prefix) using FramsticksLib. Returns list of fitness scores (default_val if invalid).
    """
    scores = []
    try:
        res = frams_lib.evaluate(full_genos_chunk) # <------- main action (calls Framsticks)
        if not res or len(res) == 0:
            scores.extend([default_val] * len(full_genos_chunk))
            return scores

        for eval_dict in res:
            if 'evaluations' in eval_dict and '' in eval_dict['evaluations']:
                fit = eval_dict['evaluations'][''].get(fitness_metric, default_val)
                if fit < -900000.0:
                    scores.append(default_val)
                else:
                    scores.append(float(fit))
            elif fitness_metric in eval_dict:
                scores.append(float(eval_dict[fitness_metric]))
            else:
                scores.append(default_val)
    except Exception as e:
        scores.extend([default_val] * len(full_genos_chunk))
    return scores

def evaluate_batch_genotypes(frams_lib, full_genos: List[str], fitness_metric: str = "vertpos", default_val: float = np.nan, batch_size: int = 150) -> List[float]:
    """
    _Wrapper for `evaluate_genotypes_chunk()` for multiple genotypes._
    Evaluates full genotype strings in chunks of size `batch_size` via FramsticksLib. Returns list of fitness scores (`default_val` if invalid).
    """
    scores = []
    total = len(full_genos)
    for start in range(0, total, batch_size):
        chunk = full_genos[start:start + batch_size]
        res = evaluate_genotypes_chunk(frams_lib, chunk, fitness_metric, default_val)
        scores.extend(res)
    return scores

def evaluate_genotype(frams_lib, prefix: str, geno_str: str, fitness_metric: str = "vertpos", default_val: float = 0.0) -> float:
    """
    _Wrapper for `evaluate_genotypes_chunk()` for single genotype._
    Evaluates a genotype in Framsticks and returns `crit` fitness.
    Catches invalid genotypes and returns `default_val`.
    """
    full_geno = prefix + geno_str
    return evaluate_genotypes_chunk(frams_lib, [full_geno], fitness_metric, default_val)[0]


def compute_epistasis_matrix(frams_lib, geno: str, prefix: str = "/*9*/", fitness_metric: str = "vertpos") -> Tuple[np.ndarray, np.ndarray, float, List[int]]:
    r"""
    Computes the pairwise epistasis matrix for a single genotype.
    Uses batch evaluation and NumPy vectorization for high efficiency.

    Returns:
    - epistasis_matrix: (L x L) float matrix of pairwise epistasis e_{i,j} (diagonal has single knockout effect)
    - raw_delta_matrix: (L x L) float matrix of raw fitness deltas dF_ij := F(g \ {i, j}) - F(g)
    - wild_type_fit: float baseline fitness
    - valid_gene_indices: list of gene positions that produce valid genotypes upon knockout
    """
    L = len(geno)
    wild_fit = evaluate_genotype(frams_lib, prefix, geno, fitness_metric=fitness_metric)
    print(f"Genotype: {geno} (length={L}), Wild-type fitness ({fitness_metric}): {wild_fit:.5f}")

    # Step 1: Single-gene knockouts in batch
    single_genos = [prefix + knockout_genes(geno, i) for i in range(L)]
    single_fits = np.array(evaluate_batch_genotypes(frams_lib, 
                                single_genos, fitness_metric=fitness_metric))

    valid_genes = [i for i, f in enumerate(single_fits) if not np.isnan(f)]
    invalid_genes = [i for i in range(L) if i not in valid_genes]
    for i in invalid_genes:
        print(f" [Warning] Gene {i} ('{geno[i]}') knockout produced invalid genotype; ignoring in epistasis.")

    # Step 2: Double-gene knockouts in batch across valid genes
    pairs = list(itertools.combinations(valid_genes, 2))
    pair_genos = [prefix + knockout_genes(geno, i, j) for i, j in pairs]

    if pair_genos:
        pair_fits_list = evaluate_batch_genotypes(frams_lib, pair_genos, fitness_metric=fitness_metric)
    else:
        pair_fits_list = []

    # Step 3: Vectorized delta and epistasis matrix computation
    
    # Individual single-gene knockout fitness changes:
    #   dF_i = F(g \ {i}) - F(g)
    dF = single_fits - wild_fit
    raw_delta_matrix = np.full((L, L), np.nan)
    raw_delta_matrix[np.arange(L), np.arange(L)] = dF

    if pairs:
        pi, pj = zip(*pairs)
        pi, pj = np.array(pi), np.array(pj)
        # Observed fitness change for double knockout: dF_ij = F(g \ {i, j}) - F(g)
        dF_pairs = np.array(pair_fits_list) - wild_fit
        valid_mask = ~np.isnan(dF_pairs)
        raw_delta_matrix[pi[valid_mask], pj[valid_mask]] = dF_pairs[valid_mask]
        raw_delta_matrix[pj[valid_mask], pi[valid_mask]] = dF_pairs[valid_mask]

    # Vectorized additive null model
    # Expected double knockout under additive null model:
    #   dF_add = dF_i + dF_j
    expected_add = dF[:, None] + dF[None, :]
    # Epistasis (interaction deviation):
            #   e_{i,j} = dF_ij - (dF_i + dF_j)
    epistasis_matrix = raw_delta_matrix - expected_add

    # Restore diagonal convention: e_{i,i} = dF_i
    np.fill_diagonal(epistasis_matrix, dF)

    return epistasis_matrix, raw_delta_matrix, wild_fit, valid_genes


def compute_epistasis_for_individuals(frams_lib, genotypes: List[str], prefix: str = "/*9*/", fitness_metric: str = "vertpos") -> Tuple[np.ndarray, ...]:
    """
    Computes pairwise epistasis for k individuals.
    
    Returns:
    - A k-tuple of 2D numpy arrays (or object array tuple if lengths vary).
    """
    epistasis_matrices = []
    for idx, g in enumerate(genotypes):
        clean_g = g.replace(prefix, "").strip().upper()
        print(f"\n[{idx + 1}/{len(genotypes)}] Evaluating epistasis for: {clean_g}")
        eps_mat, _, _, _ = compute_epistasis_matrix(frams_lib, clean_g, prefix, fitness_metric)
        epistasis_matrices.append(eps_mat)

    return tuple(epistasis_matrices)


def plot_epistasis_matrix(ax: plt.Axes, matrix: np.ndarray, geno: Optional[str] = None,
                          title: Optional[str] = None, cmap=None, norm: Optional[Any] = None,
                          show_cbar: bool = True) -> Any:
    """
    Renders a single 2D pairwise epistasis heatmap subplot.
    
    :param ax: Matplotlib Axes object.
    :param matrix: 2D numpy array containing epistasis values.
    :param geno: Genotype string for axis labels.
    :param title: Subplot title.
    :param cmap: Colormap.
    :param norm: Color normalization - the same scale will be used for all the visualized matrices.
    :param show_cbar: Whether to show colorbar for this matrix (True for the last matrix).
    """
    L = matrix.shape[0]
    if norm is None:
        valid_vals = matrix[~np.isnan(matrix)]
        vmax = np.nanmax(np.abs(valid_vals)) if len(valid_vals) > 0 and np.nanmax(np.abs(valid_vals)) > 0 else 1.0
        norm = colors.CenteredNorm(vcenter=0.0, halfrange=vmax)

    im = ax.imshow(matrix, cmap=cmap or RWG_CMAP, norm=norm, interpolation='nearest')

    if show_cbar:
        cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=8)
        cbar.set_label(r"Epistasis $\varepsilon_{ij}$", fontsize=8)

    if title:
        ax.set_title(title, fontsize=11, fontweight='bold', pad=8)

    if geno and len(geno) == L:
        step = max(1, L // 15)
        tick_locs = list(range(0, L, step))
        tick_labels = [f"{geno[p]}\n({p})" for p in tick_locs]
        ax.set_xticks(tick_locs)
        ax.set_xticklabels(tick_labels, fontsize=7)
        ax.set_yticks(tick_locs)
        ax.set_yticklabels([f"{geno[p]} ({p})" for p in tick_locs], fontsize=7)

    ax.set_xlabel("Gene index j", fontsize=9)
    ax.set_ylabel("Gene index i", fontsize=9)
    ax.grid(False)

    return im

def wrapper_plot_epistasis(ax: plt.Axes, idx: int, k: int, epistasis_matrices: Tuple[np.ndarray, ...] | List[np.ndarray], 
                            genotypes: Optional[List[str]], titles: Optional[List[str]], 
                            cmap, shared_norm: Optional[Any], show_cbar: bool,
                            genotype_prefix: str) -> Any:
    """
    Wrapper function for plot_epistasis_matrix to handle edge cases and formatting.
    """
    if idx >= k:
        ax.axis('off')
        return None
    arr = epistasis_matrices[idx]
    g_clean = genotypes[idx].replace(genotype_prefix, "").strip().upper() if (genotypes and idx < len(genotypes)) else None
    t = titles[idx] if (titles and idx < len(titles)) else f"Individual {idx + 1}"
    im = plot_epistasis_matrix(ax=ax, matrix=arr, geno=g_clean, title=t, cmap=cmap or RWG_CMAP, norm=shared_norm, show_cbar=show_cbar)
    return im

def visualize_epistasis_matrices(epistasis_matrices: Tuple[np.ndarray, ...] | List[np.ndarray],
                                genotypes: Optional[List[str]] = None,
                                titles: Optional[List[str]] = None,
                                save_path: Optional[str] = None,
                                genotype_prefix: str = "/*9*/",
                                cmap=None, same_scale: bool = True
):
    """
    Visualizes epistasis matrices in a floor(sqrt(k)) x ceil(sqrt(k)) grid. 
    Reuses `plot_epistasis_matrix` for rendering each subplot.

    :param epistasis_matrices: k-tuple of 2D numpy arrays containing epistasis values.
    :param genotypes: list of raw genotype strings for axis labels.
    :param titles: optional list of subplot titles.
    :param save_path: path to save figure (PNG / PDF).
    :param same_scale: whether to use the same colorbar scale for all plots (placing one colorbar per row).
    """
    k = len(epistasis_matrices)
    if k == 0:
        print("No epistasis matrices provided for visualization.")
        return

    n_rows = max(1, int(math.floor(math.sqrt(k))))
    n_cols = max(1, int(math.ceil(k / n_rows)))

    if same_scale:
        from matplotlib.gridspec import GridSpec
        all_valid = [arr[~np.isnan(arr)] for arr in epistasis_matrices if arr is not None]
        all_valid = np.concatenate([v.ravel() for v in all_valid if len(v) > 0]) if all_valid else np.array([])
        vmax = float(np.nanmax(np.abs(all_valid))) if len(all_valid) > 0 and np.nanmax(np.abs(all_valid)) > 0 else 1.0
        shared_norm = colors.CenteredNorm(vcenter=0.0, halfrange=vmax)

        fig = plt.figure(figsize=(5.5 * n_cols + 1.0, 5.0 * n_rows))
        gs = GridSpec(n_rows, n_cols + 1, figure=fig, width_ratios=[1.0] * n_cols + [0.035],
                      wspace=0.32, hspace=0.28, left=0.05, right=0.93, top=0.92, bottom=0.08)

        for r in range(n_rows):
            last_im = None
            for c in range(n_cols):
                idx = r * n_cols + c
                ax = fig.add_subplot(gs[r, c])
                im = wrapper_plot_epistasis(ax, idx, k, epistasis_matrices, genotypes, titles, cmap, shared_norm, show_cbar=False, genotype_prefix=genotype_prefix)
                if im is not None:
                    last_im = im

            if last_im is not None:
                cax = fig.add_subplot(gs[r, n_cols])
                pos = cax.get_position()
                cax.set_position([pos.x0, pos.y0 + 0.10 * pos.height, pos.width, pos.height * 0.80])
                cbar = fig.colorbar(last_im, cax=cax)
                cbar.ax.tick_params(labelsize=8)
                cbar.set_label(r"Epistasis $\varepsilon_{ij}$", fontsize=9, fontweight='bold', labelpad=8)
    else:
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5.5 * n_cols, 5.0 * n_rows), squeeze=False)
        for idx in range(n_rows * n_cols):
            ax = axes[idx // n_cols, idx % n_cols]
            wrapper_plot_epistasis(ax, idx, k, epistasis_matrices, genotypes, titles, cmap, shared_norm=None, show_cbar=True, genotype_prefix=genotype_prefix)
        plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"[PLOT] Saved epistasis matrix visualization to: {save_path}")
    else:
        plt.show()

    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Estimate and visualize pairwise epistasis in Framsticks f9 genotypes.")
    parser.add_argument("--frams-path", default=r"Framsticks55", help="Path to Framsticks installation directory.")
    parser.add_argument("--sim", default="eval-allcriteria.sim;deterministic.sim;sample-period-2.sim;only-body.sim",
                        help="Simulation settings files separated by semicolons.")
    parser.add_argument("--genformat", default="9", help="Genetic format to use (default: 9, e.g. /*9*/BLU).")
    parser.add_argument('--opt', default='vertpos', help="Fitness optimization criterion (default: 'vertpos').")
    parser.add_argument("--genotypes", nargs="*", default=None, help="List of genotype strings to evaluate.")
    parser.add_argument("--genotypes-folder", default=None, help="Folder containing .gen files to evaluate.")
    parser.add_argument("--out", default=r"assignments\Assignment 7 - Epistasis & Gene linkage\results\epistasis\epistasis_matrices.png",
                        help="Output image path for epistasis matrices.")
    parser.add_argument("--no-same-scale", "--independent-scale", dest="same_scale", action="store_false", default=True,
                        help="Use independent colorbar scales for each subplot instead of a unified row colorbar scale.")
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

    genotypes_to_eval = [item['raw'] for item in collected]
    titles_to_display = [f"{item['title']}\n({item['clean']})" for item in collected]

    print(f"\nTotal unique genotypes to analyze for epistasis: {len(genotypes_to_eval)}")
    for idx, item in enumerate(collected, 1):
        print(f" [{idx}] {item['title']} | Genotype: {item['raw']}")

    # Initialize FramsticksLib
    if FramsticksLib is None:
        raise RuntimeError("Could not import FramsticksLib from framspy-download.")
    frams_lib = FramsticksLib(args.frams_path, None, args.sim)

    # Compute epistasis tuple
    epistasis_tuple = compute_epistasis_for_individuals(frams_lib, genotypes_to_eval, prefix, args.opt)

    # Visualize
    visualize_epistasis_matrices(epistasis_tuple, genotypes=genotypes_to_eval,
                                    titles=titles_to_display, save_path=args.out,
                                    genotype_prefix=prefix, same_scale=args.same_scale)


if __name__ == "__main__":
    main()
