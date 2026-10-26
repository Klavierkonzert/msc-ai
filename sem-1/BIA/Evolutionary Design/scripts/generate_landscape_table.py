#!/usr/bin/env python3
"""
generate_landscape_table.py

Constructs the reorganized Quantitative Landscape Metrics Markdown table using pandas.
For each genetic representation:
  - Row 1: Entire data (All runs)
  - Row 2: Standard data (Without outliers)
Merges count and percentage columns to optimize horizontal space.
Applies conditional formatting with:
  - Dark Blue for Max Pearson r, lowest Worse rate, max Better rate, max Parent/Mutant fitness, max Lethality.
  - Dark Red for lowest Better rate, min Parent/Mutant fitness, min Lethality.
No dollar signs are included in fitness metrics.
"""

import os
import pickle
import pandas as pd
import numpy as np


def generate_landscape_metrics_table(
    landscape_dir: str = "assignments/Assignment 6 - Fitness Landscape Exploration/task1/results/landscape",
    include_outliers_row: bool = False,
    compact: bool = True,
    eps: float = 1e-6,
    highlight_extremes: bool = True
) -> pd.DataFrame:
    """
    Generates a quantitative landscape metrics table from landscape_data_f*.csv files.
    
    Args:
        landscape_dir: Directory containing the landscape data files
        include_outliers_row: Whether to include an outliers only row
        compact: If True, uses the 8-column layout from README.md (Representation as Row header)
        eps: Tolerance for neutral mutants (default 1e-6)
        highlight_extremes: Emphasize max/min extremes with dark blue and dark red
    
    Returns:
        pd.DataFrame: DataFrame containing the landscape metrics
    """
    # 1. Load identified outlier runs from cache
    cache_path = os.path.join(landscape_dir, "climbers_cache.pkl")
    outliers = {}
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
            outliers = cache.get("outliers", {})

    formats = ["0", "1", "4", "H"]
    records = []

    for fmt in formats:
        csv_path = os.path.join(landscape_dir, f"landscape_data_f{fmt}.csv")
        if not os.path.exists(csv_path):
            continue

        df = pd.read_csv(csv_path)

        # Normalize outlier set for matching parent_run column
        out_set = outliers.get(fmt, set())
        normalized_out_set = set()
        for o in out_set:
            normalized_out_set.add(str(o).strip())
            normalized_out_set.add(str(o).replace(".logbook", "").strip())
            normalized_out_set.add(f"{str(o).strip()}.logbook")

        df["is_outlier"] = df["parent_run"].astype(str).isin(normalized_out_set)

        # Define evaluation scopes
        subsets = [
            ("All", df),
            ("Without Outliers", df[~df["is_outlier"]])
        ]
        if include_outliers_row:
            subsets.append(("Outliers Only", df[df["is_outlier"]]))

        for scope_name, sub in subsets:
            n_mut = len(sub)
            if n_mut == 0:
                continue

            n_parents = sub["parent_fitness"].nunique()

            # Categorize mutational neighborhood (tolerance eps = 1e-6)
            n_better = int(sub["is_improved"].sum())
            pct_better = n_better / n_mut * 100.0

            n_neutral = int((np.abs(sub["fitness_delta"]) < eps).sum())
            pct_neutral = n_neutral / n_mut * 100.0

            n_worse = int((sub["fitness_delta"] < -eps).sum())
            pct_worse = n_worse / n_mut * 100.0

            # Pearson correlation coefficient
            if sub["parent_fitness"].std() > 0 and sub["mutant_fitness"].std() > 0:
                r_val = float(sub["parent_fitness"].corr(sub["mutant_fitness"]))
                r_str = f"{r_val:.4f}"
            else:
                r_val = np.nan
                r_str = "N/A"

            # Fragility / Lethality rate from retry attempts
            parent_group = sub.groupby(["parent_run", "parent_fitness", "parent_genotype"])["total_attempts"].max()
            tot_attempts = int(parent_group.sum())
            infeasible = max(0, tot_attempts - n_mut)
            lethality = (infeasible / tot_attempts * 100.0) if tot_attempts > 0 else 0.0

            max_parent = float(sub["parent_fitness"].max())
            max_mutant = float(sub["mutant_fitness"].max())

            worse_str = f"{n_worse:,} ({pct_worse:.2f}%)"
            records.append({
                "fmt": fmt,
                "Representation": f"**f{fmt}**" if scope_name == "All" else ("No outliers" if scope_name == "Without Outliers" else "Outliers only"),
                "Scope": scope_name,
                "Parents": n_parents,
                "Mutants": f"{n_mut:,}",
                "Better ($y > x$)": f"{n_better} ({pct_better:.2f}%)",
                "Neutral ($y \\approx x$)": f"{n_neutral:,} ({pct_neutral:.2f}%)",
                "Worse ($y < x$)": worse_str,
                "Pearson $r$": r_str,
                "Lethality Rate": f"{lethality:.2f}%",
                "Max Parent Fitness": f"{max_parent:.6f}",
                "Max Mutant Fitness": f"{max_mutant:.6f}",
                # Raw numerical metrics for highlighting
                "_pct_better": pct_better,
                "_pct_worse": pct_worse,
                "_r_val": r_val,
                "_lethality": lethality,
                "_max_parent": max_parent,
                "_max_mutant": max_mutant,
            })

    table_df = pd.DataFrame(records)

    def blue(s: str) -> str:
        return f'<span style="color: darkblue; font-weight: bold;">{s}</span>'

    def red(s: str) -> str:
        return f'<span style="color: darkred; font-weight: bold;">{s}</span>'

    # Apply conditional color highlighting within each scope if requested
    if highlight_extremes and not table_df.empty:
        scopes = table_df["Scope"].unique()
        for sc in scopes:
            mask = table_df["Scope"] == sc
            sub_indices = table_df[mask].index

            # 1. Pearson r: darkblue for max
            valid_r = table_df.loc[sub_indices, "_r_val"].dropna()
            if not valid_r.empty:
                max_r_idx = valid_r.idxmax()
                table_df.loc[max_r_idx, "Pearson $r$"] = blue(table_df.loc[max_r_idx, "Pearson $r$"])

            # 2. Worse rate: darkblue for lowest
            min_w_idx = table_df.loc[sub_indices, "_pct_worse"].idxmin()
            table_df.loc[min_w_idx, "Worse ($y < x$)"] = blue(table_df.loc[min_w_idx, "Worse ($y < x$)"])

            # 3. Better rate: darkblue for max, darkred for min
            max_b_idx = table_df.loc[sub_indices, "_pct_better"].idxmax()
            min_b_idx = table_df.loc[sub_indices, "_pct_better"].idxmin()
            table_df.loc[max_b_idx, "Better ($y > x$)"] = blue(table_df.loc[max_b_idx, "Better ($y > x$)"])
            table_df.loc[min_b_idx, "Better ($y > x$)"] = red(table_df.loc[min_b_idx, "Better ($y > x$)"])

            # 4. Lethality rate: darkred for max (highest lethality), darkblue for min (lowest lethality)
            max_l_idx = table_df.loc[sub_indices, "_lethality"].idxmax()
            min_l_idx = table_df.loc[sub_indices, "_lethality"].idxmin()
            table_df.loc[max_l_idx, "Lethality Rate"] = red(table_df.loc[max_l_idx, "Lethality Rate"])
            table_df.loc[min_l_idx, "Lethality Rate"] = blue(table_df.loc[min_l_idx, "Lethality Rate"])

            # 5. Max Parent Fitness: darkblue for max, darkred for min
            max_p_idx = table_df.loc[sub_indices, "_max_parent"].idxmax()
            min_p_idx = table_df.loc[sub_indices, "_max_parent"].idxmin()
            table_df.loc[max_p_idx, "Max Parent Fitness"] = blue(table_df.loc[max_p_idx, "Max Parent Fitness"])
            table_df.loc[min_p_idx, "Max Parent Fitness"] = red(table_df.loc[min_p_idx, "Max Parent Fitness"])

            # 6. Max Mutant Fitness: darkblue for max, darkred for min
            max_m_idx = table_df.loc[sub_indices, "_max_mutant"].idxmax()
            min_m_idx = table_df.loc[sub_indices, "_max_mutant"].idxmin()
            table_df.loc[max_m_idx, "Max Mutant Fitness"] = blue(table_df.loc[max_m_idx, "Max Mutant Fitness"])
            table_df.loc[min_m_idx, "Max Mutant Fitness"] = red(table_df.loc[min_m_idx, "Max Mutant Fitness"])

    # Drop intermediate numerical columns
    raw_cols = [c for c in table_df.columns if c.startswith("_") or c == "fmt"]
    table_df = table_df.drop(columns=raw_cols)

    if compact:
        table_df = table_df.drop(columns=["Scope", "Parents", "Mutants"])

    return table_df


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    df_compact = generate_landscape_metrics_table(compact=True)
    print("### Compact Table (Matches task1/README.md):\n")
    print(df_compact.to_markdown(index=False))

    df_full = generate_landscape_metrics_table(compact=False)
    print("\n\n### Full Table (With Scope, Parents, Mutants):\n")
    print(df_full.to_markdown(index=False))
