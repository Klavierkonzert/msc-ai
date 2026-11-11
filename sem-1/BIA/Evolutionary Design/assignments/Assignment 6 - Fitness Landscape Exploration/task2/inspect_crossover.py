#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_crossover.py: General-purpose interactive crossover inspection and export tool.

Loads a pool of individuals (e.g. from Task 1 landscape dataset or any custom CSV),
auto-detects the genetic representation directly from the genotypes, randomly selects
two distinct parents satisfying a minimum fitness threshold, evaluates recombinant
offspring fitness (velocity, PJNC, Delta F) across crossover replicates, and exports
the generated parents and offspring to a .txt file (default: experiments/example_crossover.txt) in
either overwrite (default) or append mode.
"""

import os
import sys
import argparse
import random
import re
from datetime import datetime
import pandas as pd
import numpy as np

# Setup paths to import FramsticksLib
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "framspy-download"))

from FramsticksLib import FramsticksLib

FORMAT_LABELS = {
    '0': 'f0 (Direct Low-level)',
    '1': 'f1 (Recurrent Tree)',
    '4': 'f4 (Developmental Grammar)',
    'H': 'fH (Handle-based)',
    'invalid': 'Invalid/Unknown'
}


def clean_genotype_string(geno: str) -> str:
    """Removes CSV quote-escaping artifacts (e.g. double double-quotes \"\") from neuron attributes."""
    if not isinstance(geno, str):
        return ""
    return geno.replace('""', '"').strip()


def detect_genotype_format(geno: str) -> str:
    """Fast detection of genetic format header from genotype string."""
    cleaned = geno.strip()
    match = re.match(r'^(?://|/\*)([0-9A-Za-z]+)(?:\*/)?', cleaned)
    if match:
        tag = match.group(1).strip()
        tag = tag[1:] if tag.lower().startswith('f') else tag
        return tag.upper() if tag.lower() == 'h' else tag
    if cleaned.startswith('p:'):
        return '4'
    if cleaned.startswith('X') or '[' in cleaned:
        return '1'
    return 'unknown'


def main():
    parser = argparse.ArgumentParser(
        description="Inspect sexual crossover between two randomly selected parents satisfying a minimum fitness threshold.\n"
                    "Encoding format is auto-detected directly from the individuals in the pool."
    )
    parser.add_argument(
        "parents_file", nargs="?", type=str, default=None,
        help="Path to CSV containing selected parents. If omitted, defaults to Task 1 landscape dataset."
    )
    parser.add_argument(
        "-p", "--parents-file", dest="parents_file_opt", type=str, default=None,
        help="Alternative flag to specify parents file."
    )
    parser.add_argument(
        "-m", "--min-fitness", type=float, default=0.0,
        help="Minimum parent fitness threshold to filter candidates (default: 0.0)"
    )
    parser.add_argument(
        "-r", "--reps", type=int, default=4,
        help="Number of crossover offspring replicates to generate and evaluate (default: 4)"
    )
    parser.add_argument(
        "-o", "--output", type=str, default="experiments/example_crossover.txt",
        help="Path or name of output .txt file to export generated crossover (default: 'experiments/example_crossover.txt')"
    )
    parser.add_argument(
        "-a", "--append", action="store_true", default=False,
        help="Append offspring to output file instead of creating a new file / overwriting (default: overwrite)"
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=None,
        help="Random seed for deterministic parent selection (optional)"
    )
    parser.add_argument(
        "-f", "--format", type=str, default=None,
        help="Optional format override (e.g. 0, 1, 4, H, fH). By default auto-detected from genotype headers."
    )
    parser.add_argument(
        "--frams-path", type=str, default=os.path.join(REPO_ROOT, "Framsticks55"),
        help="Path to Framsticks installation directory."
    )
    parser.add_argument(
        "--sim-settings", type=str, default="eval-allcriteria.sim;deterministic.sim",
        help="Semicolon-separated simulation settings files."
    )

    args = parser.parse_args()

    # Determine parents file path
    parents_path = args.parents_file or args.parents_file_opt
    if parents_path is None:
        # Default to Task 1 fH dataset if nothing is specified
        target_fmt = args.format or 'H'
        fmt_clean = target_fmt[1:] if target_fmt.lower().startswith('f') else target_fmt
        fmt_clean = fmt_clean.upper() if fmt_clean.lower() == 'h' else fmt_clean
        parents_path = os.path.join(
            REPO_ROOT, "assignments", "Assignment 6 - Fitness Landscape Exploration",
            "task1", "results", "landscape", f"landscape_data_f{fmt_clean}.csv"
        )

    if not os.path.exists(parents_path):
        print(f"[ERROR] Parents dataset not found at: {parents_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[LOAD] Reading parent pool from: {parents_path}")
    raw_df = pd.read_csv(parents_path)

    # Validate required columns
    required_cols = {'parent_fitness', 'parent_genotype'}
    if not required_cols.issubset(raw_df.columns):
        print(f"[ERROR] CSV must contain columns: {required_cols}. Found: {list(raw_df.columns)}", file=sys.stderr)
        sys.exit(1)

    # Deduplicate unique parents
    keep_cols = ['parent_fitness', 'parent_genotype']
    if 'parent_run' in raw_df.columns:
        keep_cols.append('parent_run')
    df_parents = raw_df[keep_cols].drop_duplicates().copy()

    total_pool_size = len(df_parents)
    if total_pool_size == 0:
        print("[ERROR] Parent pool is empty.", file=sys.stderr)
        sys.exit(1)

    # Auto-detect format from the first non-empty genotype in the pool
    sample_geno = df_parents['parent_genotype'].iloc[0]
    detected_fmt = detect_genotype_format(sample_geno)
    fmt_label = FORMAT_LABELS.get(detected_fmt, f"f{detected_fmt}")

    print(f"[AUTO-DETECT] Representation: {fmt_label}")
    max_pool_fitness = float(df_parents['parent_fitness'].max())
    min_pool_fitness = float(df_parents['parent_fitness'].min())
    print(f"[INFO] Loaded {total_pool_size} unique parents. Fitness range: [{min_pool_fitness:.6f}, {max_pool_fitness:.6f}]")

    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    # Filter parents by minimum fitness
    candidates = df_parents[df_parents['parent_fitness'] >= args.min_fitness].copy()
    num_candidates = len(candidates)

    print(f"[FILTER] Threshold >= {args.min_fitness:.6f} -> {num_candidates} eligible candidate(s)")

    if num_candidates < 2:
        print(
            f"\n[ERROR] Not enough parents meet threshold >= {args.min_fitness:.6f} "
            f"(found {num_candidates}, need at least 2).",
            file=sys.stderr
        )
        print(f"[HINT] Maximum fitness in this pool is {max_pool_fitness:.6f}. Try lowering --min-fitness.", file=sys.stderr)
        sys.exit(1)

    # Randomly select two distinct parents
    selected_indices = random.sample(range(num_candidates), 2)
    p1 = candidates.iloc[selected_indices[0]]
    p2 = candidates.iloc[selected_indices[1]]

    p1_geno = clean_genotype_string(p1['parent_genotype'])
    p2_geno = clean_genotype_string(p2['parent_genotype'])
    p1_fit_csv = float(p1['parent_fitness'])
    p2_fit_csv = float(p2['parent_fitness'])
    p1_run = p1.get('parent_run', 'N/A')
    p2_run = p2.get('parent_run', 'N/A')

    # Initialize FramsticksLib
    print(f"\n[INIT] Initializing Framsticks simulator at: {args.frams_path}")
    flib = FramsticksLib(args.frams_path, None, args.sim_settings)
    flib.PRINT_FRAMSTICKS_OUTPUT = False
    flib.GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL = False

    # Check parent validity and evaluate
    eval_parents = flib.evaluate([p1_geno, p2_geno])
    p1_eval = eval_parents[0].get("evaluations", {}).get("", {}) if eval_parents[0].get("evaluations") else {}
    p2_eval = eval_parents[1].get("evaluations", {}).get("", {}) if eval_parents[1].get("evaluations") else {}

    p1_fit = float(p1_eval.get('velocity', p1_fit_csv))
    p2_fit = float(p2_eval.get('velocity', p2_fit_csv))
    p_high = max(p1_fit, p2_fit)
    p_low = min(p1_fit, p2_fit)

    p1_pjnc = flib.getPJNC(p1_geno)
    p2_pjnc = flib.getPJNC(p2_geno)

    print("\n" + "=" * 75)
    print("SELECTED PARENTS:")
    print("=" * 75)
    print(f"Parent 1 (Base Chassis):")
    print(f"  - Source Run:   {p1_run}")
    print(f"  - Velocity (F): {p1_fit:.6f} (Recorded in CSV: {p1_fit_csv:.6f})")
    print(f"  - Phenotype:    PJNC = {p1_pjnc} (Parts, Joints, Neurons, Connections)")
    print(f"  - Genotype:")
    for line in p1_geno.splitlines()[:5]:
        print(f"      {line}")
    if len(p1_geno.splitlines()) > 5:
        print(f"      ... [{len(p1_geno.splitlines()) - 5} more lines]")

    print(f"\nParent 2 (Donor Graft):")
    print(f"  - Source Run:   {p2_run}")
    print(f"  - Velocity (F): {p2_fit:.6f} (Recorded in CSV: {p2_fit_csv:.6f})")
    print(f"  - Phenotype:    PJNC = {p2_pjnc}")
    print(f"  - Genotype:")
    for line in p2_geno.splitlines()[:5]:
        print(f"      {line}")
    if len(p2_geno.splitlines()) > 5:
        print(f"      ... [{len(p2_geno.splitlines()) - 5} more lines]")

    print(f"\nBaseline Context:")
    print(f"  Best Parent (P_high): {p_high:.6f} | Lower Parent (P_low): {p_low:.6f} | Mid-Parent: {(p1_fit + p2_fit)/2:.6f}")
    print("=" * 75)

    # Perform Crossover Replicates
    print(f"\n[CROSSOVER] Generating {args.reps} valid offspring via flib.crossOver(P1, P2)...")
    print("=" * 75)

    valid_offspring_list = []
    attempt = 0
    max_attempts = max(args.reps * 10, 50)

    while len(valid_offspring_list) < args.reps and attempt < max_attempts:
        attempt += 1
        rep_idx = len(valid_offspring_list) + 1
        offspring_geno = flib.crossOver(p1_geno, p2_geno)
        is_valid = flib.isValid([offspring_geno])[0] if offspring_geno else False
        pjnc = flib.getPJNC(offspring_geno) if is_valid else None

        if not is_valid or pjnc is None:
            print(f"[Attempt {attempt}] Replicate {rep_idx}: LETHAL / INVALID (Unviable structure), retrying...")
            continue

        print(f"\n--- Replicate {rep_idx} of {args.reps} (Attempt {attempt}) ---")
        data = flib.evaluate([offspring_geno])
        eval_dict = data[0].get("evaluations", {}).get("", {}) if data[0].get("evaluations") else {}
        off_fit = float(eval_dict.get('velocity', 0.0))
        delta_f = off_fit - p_high
        pct_change = ((off_fit / p_high) - 1.0) * 100.0 if p_high > 1e-12 else 0.0

        if off_fit > p_high + 1e-6:
            outcome = "POSITIVE HETEROSIS (Exceeds best parent!)"
        elif off_fit >= p_low - 1e-6:
            outcome = "INTERMEDIATE BLENDING (Between parents)"
        else:
            outcome = "DESTRUCTIVE (Below lower parent)"

        print(f"  Status:             VALID")
        print(f"  Phenotype:          PJNC = {pjnc}")
        print(f"  Offspring Velocity: {off_fit:.8f}")
        print(f"  Advantage (Delta F):{delta_f:+.8f} ({pct_change:+.1f}%)")
        print(f"  Outcome Class:      {outcome}")

        lines_off = offspring_geno.strip().splitlines()
        print(f"  Offspring Genotype Snippet (total {len(lines_off)} lines):")
        for line in lines_off[:4]:
            print(f"      {line}")
        if len(lines_off) > 4:
            print(f"      ... [{len(lines_off) - 4} more lines]")

        valid_offspring_list.append({
            "rep": rep_idx,
            "genotype": offspring_geno.strip(),
            "velocity": off_fit,
            "pjnc": pjnc,
            "delta_f": delta_f,
            "pct_change": pct_change,
            "outcome": outcome,
        })

    if len(valid_offspring_list) < args.reps:
        print(f"\n[WARNING] Reached maximum attempts ({max_attempts}). Collected {len(valid_offspring_list)} valid offspring.", file=sys.stderr)

    # Resolve output file path (.txt extension guaranteed; relative paths resolve to task2)
    output_path = args.output
    if not output_path.lower().endswith(".txt"):
        output_path += ".txt"
    if not os.path.isabs(output_path):
        output_path = os.path.join(SCRIPT_DIR, output_path)
    output_abs = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_abs), exist_ok=True)
    file_mode = "a" if args.append else "w"
    file_existed = os.path.exists(output_abs) and os.path.getsize(output_abs) > 0

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Export to text file
    with open(output_abs, file_mode, encoding="utf-8") as f:
        # Write batch header
        if file_mode == "a" and file_existed:
            f.write(f"\n\n{'=' * 80}\n")
            f.write(f"# APPENDED CROSSOVER BATCH: {timestamp_str}\n")
        else:
            f.write(f"{'=' * 80}\n")
            f.write(f"# Framsticks Crossover Offspring Recombination Export\n")
            f.write(f"# Timestamp: {timestamp_str}\n")
            f.write(f"# Mode: {'APPEND' if args.append else 'CREATE / OVERWRITE'}\n")

        f.write(f"# Genetic Encoding: {fmt_label}\n")
        f.write(f"# Parent 1 (Base):  Run = {p1_run} | Velocity = {p1_fit:.8f} | PJNC = {p1_pjnc}\n")
        f.write(f"# Parent 2 (Donor): Run = {p2_run} | Velocity = {p2_fit:.8f} | PJNC = {p2_pjnc}\n")
        f.write(f"# Baseline: P_high = {p_high:.8f} | P_low = {p_low:.8f} | Mid-Parent = {(p1_fit + p2_fit)/2:.8f}\n")
        f.write(f"{'=' * 80}\n\n")

        # Write Selected Parents
        p1_geno_str = f"genotype:~\n{p1_geno}\n~" if "\n" in p1_geno else f"genotype:{p1_geno}"
        f.write(f"# " + "-" * 78 + "\n")
        f.write(f"# PARENT 1 (Base Chassis / Recipient)\n")
        f.write(f"# Source: {p1_run} | Velocity: {p1_fit:.8f} (CSV: {p1_fit_csv:.8f}) | PJNC: {p1_pjnc}\n")
        f.write(f"# " + "-" * 78 + "\n")
        f.write(f"org:\n")
        f.write(f"name:Parent_1_Base\n")
        f.write(f"{p1_geno_str}\n")
        f.write(f"velocity:{p1_fit:.8f}\n")
        f.write(f"pjnc:{p1_pjnc}\n")
        f.write(f"role:Base Chassis (Recipient)\n")
        f.write(f"source_run:{p1_run}\n")
        f.write(f"info:Parent 1 Base Chassis | Velocity: {p1_fit:.6f} | PJNC: {p1_pjnc} | Run: {p1_run}\n\n")

        p2_geno_str = f"genotype:~\n{p2_geno}\n~" if "\n" in p2_geno else f"genotype:{p2_geno}"
        f.write(f"# " + "-" * 78 + "\n")
        f.write(f"# PARENT 2 (Donor Graft / Source)\n")
        f.write(f"# Source: {p2_run} | Velocity: {p2_fit:.8f} (CSV: {p2_fit_csv:.8f}) | PJNC: {p2_pjnc}\n")
        f.write(f"# " + "-" * 78 + "\n")
        f.write(f"org:\n")
        f.write(f"name:Parent_2_Donor\n")
        f.write(f"{p2_geno_str}\n")
        f.write(f"velocity:{p2_fit:.8f}\n")
        f.write(f"pjnc:{p2_pjnc}\n")
        f.write(f"role:Donor Graft (Source)\n")
        f.write(f"source_run:{p2_run}\n")
        f.write(f"info:Parent 2 Donor Graft | Velocity: {p2_fit:.6f} | PJNC: {p2_pjnc} | Run: {p2_run}\n\n")

        # Section header for Recombinant Offspring
        f.write(f"# " + "=" * 78 + "\n")
        f.write(f"# RECOMBINANT OFFSPRING ({len(valid_offspring_list)} Replicates from P1 x P2)\n")
        f.write(f"# " + "=" * 78 + "\n\n")

        # Write each offspring
        for off in valid_offspring_list:
            rep = off["rep"]
            geno = off["genotype"]
            fit = off["velocity"]
            pjnc = off["pjnc"]
            df = off["delta_f"]
            pct = off["pct_change"]
            outcome = off["outcome"]

            # Multi-line vs single-line genotype formatting
            if "\n" in geno:
                geno_str = f"genotype:~\n{geno}\n~"
            else:
                geno_str = f"genotype:{geno}"

            f.write(f"# --- Offspring {rep} of {len(valid_offspring_list)} | Velocity: {fit:.8f} | Delta F: {df:+.8f} ({pct:+.1f}%) ---\n")
            f.write(f"org:\n")
            f.write(f"name:Offspring_{rep}\n")
            f.write(f"{geno_str}\n")
            f.write(f"velocity:{fit:.8f}\n")
            f.write(f"pjnc:{pjnc}\n")
            f.write(f"delta_fitness:{df:+.8f}\n")
            f.write(f"outcome:{outcome}\n")
            f.write(f"info:Rep {rep} | P1(run={p1_run}, vel={p1_fit:.6f}) x P2(run={p2_run}, vel={p2_fit:.6f}) | Delta F={df:+.6f}\n\n")

    print("\n" + "=" * 75)
    print(f"[EXPORT] Successfully saved 2 parents and {len(valid_offspring_list)} offspring to:")
    print(f"         {output_abs}")
    print(f"         (Mode: {'APPEND' if args.append else 'CREATE / OVERWRITE'})")
    print("=" * 75)
    print("[DONE]")


if __name__ == '__main__':
    main()
