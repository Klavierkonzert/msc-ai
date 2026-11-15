"""
select_dissimilar.py
Extracts evolved genotypes from Assignment 7 runs, computes pairwise dissimilarities,
and selects k=3 most dissimilar tall structures via Max-Min Diversity (or k-medoids).
"""

from sys import prefix
import os
import glob
import re
import shutil
import argparse
from typing import Optional, List, Tuple, Dict
import numpy as np


def clean_genformat(geno_str: str, genformat:str) -> str:
    """Extract raw f9 string by removing /*9*/ prefix and whitespace."""
    s = geno_str.strip()
    if s.startswith(pref:=("/*" + genformat + "*/")):
        s = s[len(pref):].strip()
    return s.upper()


# -------------------------------------------------------------------------
# Distance / Dissimilarity Metrics for f9
# -------------------------------------------------------------------------

def edit_distance(s1: str, s2: str) -> float:
    """Normalized Levenshtein string edit distance in [0, 1]."""
    n, m = len(s1), len(s2)
    if max(n, m) == 0:
        return 0.0
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # deletion
                dp[i][j - 1] + 1,       # insertion
                dp[i - 1][j - 1] + cost # substitution
            )
    return dp[n][m] / max(n, m)


def directional_profile_distance(s1: str, s2: str) -> float:
    """
    Cosine distance between 6D directional letter frequency histograms (F, B, L, R, U, D).
    Captures structural orientation divergence (e.g. upward column vs flat branching base).
    """
    chars = ['F', 'B', 'L', 'R', 'U', 'D']
    v1 = np.array([s1.count(c) for c in chars], dtype=float)
    v2 = np.array([s2.count(c) for c in chars], dtype=float)
    norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 1.0
    cosine_sim = np.dot(v1, v2) / (norm1 * norm2)
    return float(1.0 - np.clip(cosine_sim, 0.0, 1.0))


def f9_combined_dissimilarity(s1: str, s2: str, w_edit: float = 0.6, w_dir: float = 0.4) -> float:
    """
    Hybrid distance:
    - w_edit: Levenshtein sequence alignment (order & branch positions)
    - w_dir: 6D directional composition vector divergence
    """
    d_edit = edit_distance(s1, s2)
    d_dir = directional_profile_distance(s1, s2)
    return w_edit * d_edit + w_dir * d_dir


# -------------------------------------------------------------------------
# Diverse Subset Selection (Max-Min / Farthest Point Traversal)
# -------------------------------------------------------------------------

def select_max_min_diverse(
    genotypes: List[Dict],
    k: Optional[int] = None,
    metric_func=f9_combined_dissimilarity
) -> List[Dict]:
    """
    Greedy max-min diversity picker:
    1. First element: highest fitness solution (tallest champion).
    2. Second element: candidate maximizing distance to the first.
    3. Subsequent elements: candidate maximizing minimum distance to all selected.
    """
    if len(genotypes) <= k:
        return genotypes

    # Compute full pairwise distance matrix
    n = len(genotypes)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = metric_func(genotypes[i]['clean_geno'], genotypes[j]['clean_geno'])
            D[i, j] = d
            D[j, i] = d

    # 1. Start with the top-fitness individual
    selected_indices = [int(np.argmax([g['fitness'] for g in genotypes]))]

    # 2. Iteratively pick candidate with largest min-distance to selected set
    for _ in range(k - 1):
        remaining = [idx for idx in range(n) if idx not in selected_indices]
        best_candidate = None
        best_min_dist = -1.0

        for r in remaining:
            min_dist_to_selected = min(D[r, s] for s in selected_indices)
            if min_dist_to_selected > best_min_dist:
                best_min_dist = min_dist_to_selected
                best_candidate = r

        if best_candidate is not None:
            selected_indices.append(best_candidate)

    return [genotypes[i] for i in selected_indices]


# -------------------------------------------------------------------------
# Genotype File Loader
# -------------------------------------------------------------------------

def load_genotypes_from_directory(runs_dir: str, genformat: str, fitness_metric:str="vertpos") -> List[Dict]:
    """Scans for *.gen files in runs directory and parses genotype & fitness."""
    pattern = os.path.join(runs_dir, "**", "*.gen")
    gen_files = glob.glob(pattern, recursive=True)
    results = []

    for path in gen_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse genotype and fitness from Framsticks .gen file format
            # Format typically contains lines:
            # org:
            # ...
            # numparts: ...
            # fitness:...
            # [or in standard format: genotype:~/*9*/...~]
            geno_match = re.search(r"genotype:~?(/\*" + re.escape(str(genformat)) + r"\*/[^\r\n~]+)~?", content)
            if not geno_match:
                # Alternate pattern
                geno_match = re.search(r"genotype:~?(/\*" + re.escape(str(genformat)) + r"\*/[^\r\n~]+)~?", content)

            # Search for vertpos or fitness
            fit_match = re.search(r"(?:"+fitness_metric+r"|fitness):\s*([0-9\.\-eE]+)", content)
            
            if geno_match:
                raw_geno = geno_match.group(1).strip("~")
                fitness = float(fit_match.group(1)) if fit_match else 0.0
                clean_g = clean_genformat(raw_geno, genformat)
                results.append({
                    "file": path,
                    "raw_geno": raw_geno,
                    "clean_geno": clean_g,
                    "length": len(clean_g),
                    "fitness": fitness
                })
        except Exception as e:
            continue

    # De-duplicate identical genotypes, keeping best fitness
    unique = {}
    for r in results:
        g = r['clean_geno']
        if g not in unique or r['fitness'] > unique[g]['fitness']:
            unique[g] = r

    return list(unique.values())


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_selected_dir = os.path.join(script_dir, "selected")

    parser = argparse.ArgumentParser(description="Select k dissimilar evolved f9 structures.")
    parser.add_argument("--runs-dir", default=r"assignments\Assignment 7 - Epistasis & Gene linkage\runs",
                        help="Directory containing HoF *.gen files.")

    parser.add_argument("--genformat", default="9", help="Genetic format to use (default: 9, e.g. /*9*/BLU).")
    parser.add_argument('--opt', default='vertpos', help="Target to be optimized. By default, 'vertpos'")
    

    parser.add_argument("--k", type=int, default=3, help="Number of dissimilar structures to select.")
    parser.add_argument("--out-dir", default=default_selected_dir, help="Folder to copy selected .gen files to (default: ./selected relative to script).")
    args = parser.parse_args()

    candidates = load_genotypes_from_directory(args.runs_dir, args.genformat, args.opt)
    print(f"Loaded {len(candidates)} unique candidates from '{args.runs_dir}'.")
    if not candidates:
        print("No genotypes found yet. Wait for evolution runs to produce *.gen files.")
        return

    selected = select_max_min_diverse(candidates, k=args.k)
    print(f"\nSelected k={len(selected)} dissimilar solutions:")
    for idx, s in enumerate(selected, 1):
        print(f" [{idx}] Fitness: {s['fitness']:.4f} | Len: {s['length']} | Geno: {s['raw_geno']} | Source: {os.path.basename(s['file'])}")

    # Copy selected .gen files to output folder
    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        print(f"\nCopying selected .gen files to '{args.out_dir}':")
        for idx, s in enumerate(selected, 1):
            src_path = s['file']
            src_name = os.path.basename(src_path)
            # Create a clean target filename preserving rank and source
            dest_name = f"selected_{idx}_{src_name}"
            dest_path = os.path.join(args.out_dir, dest_name)
            shutil.copy2(src_path, dest_path)
            print(f"  -> Copied {src_name} to {dest_name}")


if __name__ == "__main__":
    main()

