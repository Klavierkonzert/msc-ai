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

Expected(!) double knockout under additive (null) model - but this is true under linear additivity of ind. genes' effects
  F_add(g \ {i, j}) = F(g) + dF_i + dF_j

Epistasis (interaction deviation):
  e_{i,j} = F(g \ {i, j}) - F_add(g \ {i, j}) # the non-linear effect of interaction of ij.
          = [F(g \ {i, j}) - F(g)] - [F(g \ {i}) - F(g)] - [F(g \ {j}) - F(g)]

On the diagonal (i == j):
  Stores the single knockout effect dF_i = F(g \ {i}) - F(g).
"""

import os
import sys
import glob
import re
import math
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import LinearSegmentedColormap
from typing import List, Tuple, Dict, Optional

# Ensure repository paths are configured
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRAMSPY_DIR = os.path.join(REPO_ROOT, "framspy-download")
if FRAMSPY_DIR not in sys.path:
    sys.path.insert(0, FRAMSPY_DIR)

try:
    from FramsticksLib import FramsticksLib
except ImportError:
    # Alternative import path
    import frams
    FramsticksLib = None


def load_genotypes_from_folder(folder_path: str, genformat: str) -> List[Tuple[str, str]]:
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

            # Search for f<genformat>
            #  string
            geno_match = re.search(r"genotype:~?(/\*" + re.escape(str(genformat)) + r"\*/[^\r\n~]+)~?", content)
            if not geno_match:
                geno_match = re.search(r"(/\*"+genformat+r"\*/[A-Za-z]+)", content)

            if geno_match:
                raw_geno = geno_match.group(1).strip("~")
                label = os.path.basename(path)
                results.append((raw_geno, label))
        except Exception as e:
            print(f"[Error] Failed to read {path}: {e}")
            continue

    print(f"Loaded {len(results)} genotypes from folder: '{folder_path}'")
    return results


def setstr(s: str, pos: int, char: str = ' ') -> str:
    """Replaces character at `pos` with `char`."""
    assert len(char) == 1
    assert 0 <= pos < len(s)
    return s[:pos] + char + s[pos + 1:]


def evaluate_genotype(
    frams_lib,
    prefix: str,
    geno_str: str,
    fitness_metric: str = "vertpos",
    default_val: float = 0.0,
) -> float:
    """
    Evaluates a genotype in Framsticks and returns `crit` fitness.
    Catches invalid genotypes and returns default_val or None.
    """
    full_geno = prefix + geno_str
    try:
        res = frams_lib.evaluate([full_geno])
        if not res or len(res) == 0:
            return default_val
        eval_dict = res[0]
        # Check if valid evaluation occurred
        if 'evaluations' in eval_dict and '' in eval_dict['evaluations']:
            fit = eval_dict['evaluations'][''].get(fitness_metric, default_val)
            # Filter infeasible marker
            if fit < -900000.0:
                return default_val
            return float(fit)
        elif fitness_metric in eval_dict:
            return float(eval_dict[fitness_metric])
        return default_val
    except Exception as e:
        return default_val


def compute_epistasis_matrix(
    frams_lib,
    geno: str,
    prefix: str = "/*9*/",
    fitness_metric: str = "vertpos"
) -> Tuple[np.ndarray, np.ndarray, float, List[int]]:
    r"""
    Computes the epistasis matrix for a single genotype.

    Returns:
    - epistasis_matrix: (L x L) float matrix of pairwise epistasis e_{i,j} (diagonal has single knockout effect)
    - raw_delta_matrix: (L x L) float matrix of raw fitness deltas dF_ij := F(g \ {i, j}) - F(g)
    - wild_type_fit: float baseline fitness
    - valid_gene_indices: list of gene positions that produce valid genotypes upon knockout
    """
    L = len(geno)
    wild_fit = evaluate_genotype(frams_lib, prefix, geno, fitness_metric=fitness_metric)
    print(f"Genotype: {geno} (length={L}), Wild-type fitness ({fitness_metric}): {wild_fit:.5f}")

    # Step 1: Precompute single-gene knockouts & identify valid / essential genes
    single_fits = np.full(L, np.nan)
    valid_genes = []

    for i in range(L): #iterate over gene letters in `geno`me
        g_single = setstr(geno, i, ' ').replace(' ', '') #delete gene #i
        if len(g_single) == 0:
            continue
        f_single = evaluate_genotype(frams_lib, prefix, g_single, 
                                    fitness_metric = fitness_metric, default_val=np.nan)
        if not np.isnan(f_single):
            single_fits[i] = f_single
            valid_genes.append(i)
        else:
            print(f" [Warning] Gene {i} ('{geno[i]}') knockout produced invalid genotype; ignoring in epistasis.")

    # Step 2: Compute double-knockout matrix and epistasis
    raw_delta_matrix = np.full((L, L), np.nan)  # dF_ij = F(g \ {i, j}) - F(g)
    epistasis_matrix = np.full((L, L), np.nan)  # e_{i,j} = delta_F_ij - (delta_F_i + delta_F_j)

    for i in range(L):
        for j in range(i, L):
            # Diagonal stores single knockout effect: dF_i = F(g \ {i}) - F(g)
            if i == j:
                if not np.isnan(single_fits[i]):
                    dF_i = single_fits[i] - wild_fit
                    raw_delta_matrix[i, i] = dF_i
                    epistasis_matrix[i, i] = dF_i
                continue

            # If either gene produces an invalid genotype alone, skip pair
            if np.isnan(single_fits[i]) or np.isnan(single_fits[j]):
                continue

            # Double knockout: remove gene i and gene j
            g_double = setstr(geno, i, ' ')
            g_double = setstr(g_double, j, ' ')
            g_double = g_double.replace(' ', '')

            #F(g \ {i,j})
            f_double = evaluate_genotype(frams_lib, prefix, g_double, 
                                            fitness_metric=fitness_metric, default_val=np.nan)
            if np.isnan(f_double):
                continue

            # Observed fitness change for double knockout: dF_ij = F(g \ {i, j}) - F(g)
            dF_ij = f_double - wild_fit
            raw_delta_matrix[i, j] = dF_ij
            raw_delta_matrix[j, i] = dF_ij

            # Individual single-gene knockout fitness changes:
            #   dF_i = F(g \ {i}) - F(g)
            #   dF_j = F(g \ {j}) - F(g)
            dF_i = single_fits[i] - wild_fit
            dF_j = single_fits[j] - wild_fit

            # Expected double knockout under additive null model:
            #   dF_add = dF_i + dF_j
            # Epistasis (interaction deviation):
            #   e_{i,j} = dF_ij - (dF_i + dF_j)
            e_ij = dF_ij - (dF_i + dF_j) # <-------- The main formula

            epistasis_matrix[i, j] = e_ij
            epistasis_matrix[j, i] = e_ij

    return epistasis_matrix, raw_delta_matrix, wild_fit, valid_genes


def compute_epistasis_for_individuals(
    frams_lib,
    genotypes: List[str],
    prefix: str = "/*9*/",
    fitness_metric: str = "vertpos"
) -> Tuple[np.ndarray, ...]:
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


def visualize_epistasis_matrices(
    epistasis_matrices : Tuple[np.ndarray, ...]|List[np.ndarray],
    genotypes: Optional[List[str]] = None,
    titles: Optional[List[str]] = None,
    save_path: Optional[str] = None,
    genotype_prefix: str = "/*9*/", 
    cmap_name: str = "custom_rwg"
):
    """
    Visualizes epistatic matrices as subplots arranged in floor(sqrt(k)) x ceil(sqrt(k)) grid.

    Parameters:
    - epistasis_tuple: k-tuple of 2D numpy arrays containing epistasis values.
    - genotypes: list of raw genotype strings for axis labels.
    - titles: optional list of subplot titles.
    - save_path: path to save figure (PNG / PDF).
    """
    k = len(epistasis_matrices)
    if k == 0:
        print("No epistasis matrices provided for visualization.")
        return

    # Subplot grid dimensions: floor(sqrt(k)) rows x ceil(sqrt(k)) cols
    n_rows = max(1, int(math.floor(math.sqrt(k))))
    n_cols = max(1, int(math.ceil(k / n_rows)))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5.5 * n_cols, 5.0 * n_rows), squeeze=False)

    # Custom Red-White-Green colormap centered at 0
    # Red: Negative epistasis (decompensatory / antagonistic interaction)
    # White: Zero epistasis (pure additivity / independent genes)
    # Green: Positive epistasis (synergistic cooperation)
    red_white_green = LinearSegmentedColormap.from_list(
        'red_white_green', ["#d73027", "#f7f7f7", "#1a9850"], N=256
    )

    for idx in range(n_rows * n_cols):
        r = idx // n_cols
        c = idx % n_cols
        ax = axes[r, c]

        if idx >= k:
            ax.axis('off')
            continue

        arr = epistasis_matrices[idx]
        L = arr.shape[0]

        # Determine symmetric normalization range around 0
        valid_vals = arr[~np.isnan(arr)]
        vmax = np.nanmax(np.abs(valid_vals)) if len(valid_vals) > 0 and np.nanmax(np.abs(valid_vals)) > 0 else 1.0
        norm = colors.CenteredNorm(vcenter=0.0, halfrange=vmax)

        im = ax.imshow(arr, cmap=red_white_green, norm=norm, interpolation='nearest')

        # Add colorbar for each subplot
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=8)

        # Title
        t = titles[idx] if (titles and idx < len(titles)) else f"Individual {idx + 1}"
        ax.set_title(t, fontsize=11, fontweight='bold', pad=8)

        # Ticks and gene character labels
        if genotypes and idx < len(genotypes):
            g_str = genotypes[idx].replace(genotype_prefix, "").strip().upper()
            if len(g_str) == L:
                step = max(1, L // 15)
                tick_locs = list(range(0, L, step))
                tick_labels = [f"{g_str[p]}\n({p})" for p in tick_locs]
                ax.set_xticks(tick_locs)
                ax.set_xticklabels(tick_labels, fontsize=7)
                ax.set_yticks(tick_locs)
                ax.set_yticklabels([f"{g_str[p]} ({p})" for p in tick_locs], fontsize=7)

        ax.set_xlabel("Gene index j", fontsize=9)
        ax.set_ylabel("Gene index i", fontsize=9)
        ax.grid(False)

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
    parser.add_argument('--opt', default='vertpos', help="Target to be optimized. By default, 'vertpos'")
    parser.add_argument("--genotypes", nargs="*", default=None,help="List of genotype strings to evaluate (e.g. /*9*/BLU).")
    parser.add_argument("--genotypes-folder", default=None, help="Folder containing .gen files to evaluate (e.g. ./selected).")
    parser.add_argument("--out", default=r"assignments\Assignment 7 - Epistasis & Gene linkage\results\epistasis\epistasis_matrices.png",
                        help="Output image path for epistasis matrices.")
    args = parser.parse_args()

    # Collect genotypes from both --genotypes and --genotypes-folder without duplicates
    # Store as list of dicts: {'clean': ..., 'raw': ..., 'title': ...}
    collected = []
    seen = set()

    prefix = "/*" + args.genformat + "*/"

    # 1. From --genotypes-folder if provided
    if args.genotypes_folder:
        folder_items = load_genotypes_from_folder(args.genotypes_folder, genformat=args.genformat)
        for raw_g, label in folder_items:
            clean_g = raw_g.replace(prefix, "").strip().upper()
            if clean_g not in seen:
                seen.add(clean_g)
                collected.append({
                    "raw": raw_g,
                    "clean": clean_g,
                    "title": f"{label}\n({clean_g})"
                })

    # 2. From --genotypes if provided
    if args.genotypes:
        for idx, g in enumerate(args.genotypes, 1):
            clean_g = g.replace(prefix, "").strip().upper()
            if clean_g not in seen:
                seen.add(clean_g)
                collected.append({
                    "raw": g,
                    "clean": clean_g,
                    "title": f"Genotype {idx}\n({clean_g})"
                })

    # Fallback default if neither is provided
    if not collected:
        raise Exception("No genotypes provided. Use --genotypes or --genotypes-folder.")

    genotypes_to_eval = [item['raw'] for item in collected]
    titles_to_display = [item['title'] for item in collected]

    print(f"\nTotal unique genotypes to analyze for epistasis: {len(genotypes_to_eval)}")
    for idx, item in enumerate(collected, 1):
        print(f" [{idx}] {item['title'].replace(chr(10), ' - ')} | Genotype: {item['raw']}")

    # Initialize FramsticksLib
    frams_lib = FramsticksLib(args.frams_path, None, args.sim)

    # Compute epistasis tuple
    epistasis_tuple = compute_epistasis_for_individuals(frams_lib, genotypes_to_eval, prefix, args.opt)

    # Visualize
    visualize_epistasis_matrices(
        epistasis_tuple,
        genotypes=genotypes_to_eval,
        titles=titles_to_display,
        save_path=args.out,
        genotype_prefix=prefix
    )


if __name__ == "__main__":
    main()

