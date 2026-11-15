#!/usr/bin/env python3
"""
print_epistasis_table.py

Loads 3D epistasis summary statistics from CSV (or computes them),
calculates the derived epistasis metrics:
  - Directedness: dir(eps) = sum(eps) / sum(|eps|)
  - Mean absolute triplet epistasis: |bar(eps)| = sum(|eps|) / C(L, 3)

Colors the font (or optionally background) according to project specifications:
  - Directedness: mapped to the red-white-green colormap spanning [-1.0, +1.0]
    (-1 is dark red #b2182b, 0 is neutral gray #d0d0d0, +1 is dark green #006837).
  - Mean absolute triplet epistasis: mapped according to [0, max_val]
    (0 is dark red #b2182b, midpoint 0.5 * max_val is neutral gray #d0d0d0, max_val is dark green #006837;
     values below the midpoint are reddish, and values above it are greenish).

Bolding policy:
  - Bold is NOT used in general (e.g. creature numbers, genotypes, and standard cells are plain).
  - Bold is ONLY applied to the lowest/largest extreme values across all baselines
    (Baseline 1 metrics, Baseline 2 metrics) or optionally per-baseline.

Outputs a GitHub-flavored Markdown table or HTML table, and can update README.md directly via --update-readme.
"""

import os
import sys
import argparse
from typing import List, Dict, Any, Optional, Tuple, Set

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(SCRIPT_DIR, "results", "epistasis", "epistasis_3d_summary.csv")
DEFAULT_README = os.path.join(SCRIPT_DIR, "README.md")
SELECTED_DIR = os.path.join(SCRIPT_DIR, "selected")

# Centered Red-White-Green colormap (darker tone for clear text legibility on light background)
RWG_CMAP = LinearSegmentedColormap.from_list('red_white_green', ["#b2182b", "#d0d0d0", "#006837"], N=256)


def compute_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Computes directedness and mean absolute triplet epistasis for each baseline."""
    df = df.copy()

    # Baseline 1, 2
    for i in (1, 2):
        df[f'Dir_Triplets_B{i}']     = df.apply(lambda r: (r[f'SumRaw_Triplets_B{i}'] / r[f'SumAbs_Triplets_B{i}']) if r[f'SumAbs_Triplets_B{i}'] != 0 else 0.0, axis=1)
        df[f'MeanAbs_Triplets_B{i}'] = df.apply(lambda r: (r[f'SumAbs_Triplets_B{i}'] / r['NumTriplets']) if r['NumTriplets'] != 0 else 0.0,               axis=1)

    return df


def val_to_font_color(val: float, vmin: float, vmax: float) -> str:
    """Maps a value within [vmin, vmax] to a hex color using RWG_CMAP."""
    u = 0.5 if vmax<=vmin else float(np.clip((val - vmin) / (vmax - vmin), 0.0, 1.0))

    rgba = RWG_CMAP(u)
    r, g, b = (int(round(rgba[i] * 255)) for i in range(3))
    return f"#{r:02x}{g:02x}{b:02x}"


def val_to_badge_colors(val: float, vmin: float, vmax: float) -> Tuple[str, str]:
    """Maps a value within [vmin, vmax] to (bg_hex, fg_hex) for background badges."""
    bg_hex = val_to_font_color(val, vmin, vmax)
    r = int(bg_hex[1:3], 16)
    g = int(bg_hex[3:5], 16)
    b = int(bg_hex[5:7], 16)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    fg_hex = "#ffffff" if lum < 145 else "#0f172a"
    return bg_hex, fg_hex


def format_cell_value(val: float, vmin_cmap: Optional[float] = None, vmax_cmap: Optional[float] = None, is_extreme: bool = False, 
                        fmt: str = "{:+.2f}", color_target: str = "font") -> str:
    """
    Formats a table cell value with optional font/badge coloring and conditional bolding.
    """
    val_str = fmt.format(val)

    if vmin_cmap is not None and vmax_cmap is not None:
        if color_target == "font":
            hex_color = val_to_font_color(val, vmin_cmap, vmax_cmap)
            inner = f'<span style="color: {hex_color};">{val_str}</span>'
            return f"<b>{inner}</b>" if is_extreme else inner
        elif color_target == "background":
            bg_hex, fg_hex = val_to_badge_colors(val, vmin_cmap, vmax_cmap)
            fw = "bold" if is_extreme else "normal"
            return (
                f'<span style="background-color: {bg_hex}; color: {fg_hex}; '
                f'padding: 2px 6px; border-radius: 4px; font-weight: {fw}; '
                f'display: inline-block;">{val_str}</span>'
            )

    # Uncolored plain cell
    return f"**{val_str}**" if is_extreme else val_str


def find_extremes(df: pd.DataFrame, bold_mode: str = "all-baselines") -> Dict[str, Tuple[float, float]]:
    """
    Determines minimum and maximum values for metric columns based on bold_mode:
      - 'all-baselines': Extremes pooled across both baselines for each metric type:
          raw sum, abs sum, directedness, mean abs.
      - 'per-baseline': Extremes calculated individually for each column.
      - 'none': No extremes identified.
    """
    if bold_mode == "none":
        return {}

    extremes = {}

    if bold_mode == "all-baselines":
        # Pool Baseline 1 and Baseline 2 metrics together
        raw_pooled = pd.concat([df['SumRaw_Triplets_B1'], df['SumRaw_Triplets_B2']])
        abs_pooled = pd.concat([df['SumAbs_Triplets_B1'], df['SumAbs_Triplets_B2']])
        dir_pooled = pd.concat([df['Dir_Triplets_B1'], df['Dir_Triplets_B2']])
        mean_pooled = pd.concat([df['MeanAbs_Triplets_B1'], df['MeanAbs_Triplets_B2']])

        min_raw, max_raw = float(raw_pooled.min()), float(raw_pooled.max())
        min_abs, max_abs = float(abs_pooled.min()), float(abs_pooled.max())
        min_dir, max_dir = float(dir_pooled.min()), float(dir_pooled.max())
        min_mean, max_mean = float(mean_pooled.min()), float(mean_pooled.max())

        for i in (1,2):
            extremes[f'SumRaw_Triplets_B{i}']   = (min_raw, max_raw)
            extremes[f'SumAbs_Triplets_B{i}']   = (min_abs, max_abs)
            extremes[f'Dir_Triplets_B{i}']      = (min_dir, max_dir)
            extremes[f'MeanAbs_Triplets_B{i}']  = (min_mean, max_mean)

    elif bold_mode == "per-baseline":
        # Calculate min and max per individual column
        cols = [f'{metric}_Triplets_B{i}' for i in (1,2) 
                                          for metric in ('SumRaw', 'SumAbs', 'Dir', 'MeanAbs')]
        for c in cols:
            if c in df:
                extremes[c] = (float(df[c].min()), float(df[c].max()))

    return extremes


def generate_markdown_table(df: pd.DataFrame, selected_dir: str = "./selected",
    max_val: Optional[float] = None, color_target: str = "font", bold_mode: str = "all-baselines"
) -> str:
    """
    Generates a GitHub-flavored Markdown table from the dataframe.
    """
    if 'Dir_Triplets_B1' not in df.columns or 'MeanAbs_Triplets_B1' not in df.columns:
        df = compute_derived_metrics(df)

    if max_val is None or max_val <= 0:
        max_b1 = df['MeanAbs_Triplets_B1'].max() if 'MeanAbs_Triplets_B1' in df else 0.0
        max_b2 = df['MeanAbs_Triplets_B2'].max() if 'MeanAbs_Triplets_B2' in df else 0.0
        max_val = max(float(max_b1), float(max_b2), 1e-6)

    extremes = find_extremes(df, bold_mode=bold_mode)

    def check_extreme(col: str, val: float) -> bool:
        if col not in extremes:
            return False
        min_v, max_v = extremes[col]
        return abs(val - min_v) < 1e-5 or abs(val - max_v) < 1e-5

    lines = [
        "| Creature | Genotype | $L$ | Triplet Count<br>$\\binom{L}{3}$ |<br>$\\sum \\varepsilon^{(1)}$ | Baseline<br>$\\sum \\lvert\\varepsilon^{(1)}\\rvert$ |1<br>$\\text{dir}\\varepsilon^{(1)}$ |<br>$\\lvert\\bar{\\varepsilon}^{(1)}\\rvert$ |<br>$\\sum \\varepsilon^{(2)}$ | Baseline<br>$\\sum \\lvert\\varepsilon^{(2)}\\rvert$ |2<br>$\\text{dir}\\varepsilon^{(2)}$ |<br>$\\lvert\\bar{\\varepsilon}^{(2)}\\rvert$ |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for idx, row in df.iterrows():
        c_num = idx + 1
        g = row['Genotype']
        L = int(row['Length'])
        n_triplets = int(row['NumTriplets'])

        # Check for matching .gen file in selected_dir
        gen_link = f"`/*9*/{g}`"
        if selected_dir and os.path.exists(selected_dir):
            for fname in os.listdir(selected_dir):
                if fname.startswith(f"selected_{c_num}_") and fname.endswith(".gen"):
                    gen_link = f"[`/*9*/{g}`](./selected/{fname})"
                    break

        cells = []
        for i in (1, 2):
            cells.extend([
                format_cell_value(row[f'SumRaw_Triplets_B{i}'],
                    is_extreme=check_extreme(f'SumRaw_Triplets_B{i}', row[f'SumRaw_Triplets_B{i}']),
                    fmt="{:+.2f}", color_target=color_target
                ),
                format_cell_value(row[f'SumAbs_Triplets_B{i}'],
                    is_extreme=check_extreme(f'SumAbs_Triplets_B{i}', row[f'SumAbs_Triplets_B{i}']),
                    fmt="{:.2f}", color_target=color_target
                ),
                format_cell_value(row[f'Dir_Triplets_B{i}'],
                    vmin_cmap=-1.0, vmax_cmap=1.0,
                    is_extreme=check_extreme(f'Dir_Triplets_B{i}', row[f'Dir_Triplets_B{i}']),
                    fmt="{:+.3f}", color_target=color_target
                ),
                format_cell_value(row[f'MeanAbs_Triplets_B{i}'],
                    vmin_cmap=0, vmax_cmap=max_val,
                    is_extreme=check_extreme(f'MeanAbs_Triplets_B{i}', row[f'MeanAbs_Triplets_B{i}']),
                    fmt="{:.3f}", color_target=color_target
                ),
            ])

        lines.append(f"| {c_num} | {gen_link} | {L} | {n_triplets} | " + " | ".join(cells) + " |")

    return "\n".join(lines)


def generate_html_table(df: pd.DataFrame, selected_dir: str = "./selected",
    max_val: Optional[float] = None, color_target: str = "font", bold_mode: str = "all-baselines"
) -> str:
    """
    Generates a full HTML table with optional font/background coloring and bolding.
    """
    if max_val is None or max_val <= 0:
        max_b1 = df['MeanAbs_Triplets_B1'].max() if 'MeanAbs_Triplets_B1' in df else 0.0
        max_b2 = df['MeanAbs_Triplets_B2'].max() if 'MeanAbs_Triplets_B2' in df else 0.0
        max_val = max(float(max_b1), float(max_b2), 1e-6)

    extremes = find_extremes(df, bold_mode=bold_mode)

    def check_extreme(col: str, val: float) -> bool:
        if col not in extremes:
            return False
        min_v, max_v = extremes[col]
        return abs(val - min_v) < 1e-5 or abs(val - max_v) < 1e-5

    def format_html_td(val: float, col: str, vmin_cmap: Optional[float] = None, vmax_cmap: Optional[float] = None, fmt: str = "{:+.2f}") -> str:
        is_ext = check_extreme(col, val)
        fw = "font-weight: bold;" if is_ext else "font-weight: normal;"
        val_str = fmt.format(val)

        if vmin_cmap is not None and vmax_cmap is not None:
            if color_target == "font":
                c = val_to_font_color(val, vmin_cmap, vmax_cmap)
                return f'<td style="padding: 6px; border: 1px solid #e2e8f0; color: {c}; {fw}">{val_str}</td>'
            else:
                bg, fg = val_to_badge_colors(val, vmin_cmap, vmax_cmap)
                return f'<td style="padding: 6px; border: 1px solid #e2e8f0; background-color: {bg}; color: {fg}; {fw}">{val_str}</td>'
        return f'<td style="padding: 6px; border: 1px solid #e2e8f0; {fw}">{val_str}</td>'

    html_lines = [
        '<table style="border-collapse: collapse; width: 100%; text-align: center;">',
        '  <thead>',
        '    <tr style="background-color: #f1f5f9; border-bottom: 2px solid #cbd5e1;">',
        '      <th rowspan="2" style="padding: 8px; border: 1px solid #cbd5e1;">Creature</th>',
        '      <th rowspan="2" style="padding: 8px; border: 1px solid #cbd5e1; text-align: left;">Genotype</th>',
        '      <th rowspan="2" style="padding: 8px; border: 1px solid #cbd5e1;"><i>L</i></th>',
        '      <th rowspan="2" style="padding: 8px; border: 1px solid #cbd5e1;">Triplet Count<br>&binom;(<i>L</i>, 3)</th>',
        '      <th colspan="4" style="padding: 8px; border: 1px solid #cbd5e1;">Baseline 1 (Relative to Individual Genes)</th>',
        '      <th colspan="4" style="padding: 8px; border: 1px solid #cbd5e1;">Baseline 2 (Relative to Pairwise Interactions)</th>',
        '    </tr>',
        '    <tr style="background-color: #f8fafc; border-bottom: 2px solid #cbd5e1;">',
        '      <th style="padding: 6px; border: 1px solid #cbd5e1;">&sum; &epsilon;<sup>(1)</sup></th>',
        '      <th style="padding: 6px; border: 1px solid #cbd5e1;">&sum; |&epsilon;<sup>(1)</sup>|</th>',
        '      <th style="padding: 6px; border: 1px solid #cbd5e1;">dir &epsilon;<sup>(1)</sup></th>',
        '      <th style="padding: 6px; border: 1px solid #cbd5e1;">|&epsilon;&#772;<sup>(1)</sup>|</th>',
        '      <th style="padding: 6px; border: 1px solid #cbd5e1;">&sum; &epsilon;<sup>(2)</sup></th>',
        '      <th style="padding: 6px; border: 1px solid #cbd5e1;">&sum; |&epsilon;<sup>(2)</sup>|</th>',
        '      <th style="padding: 6px; border: 1px solid #cbd5e1;">dir &epsilon;<sup>(2)</sup></th>',
        '      <th style="padding: 6px; border: 1px solid #cbd5e1;">|&epsilon;&#772;<sup>(2)</sup>|</th>',
        '    </tr>',
        '  </thead>',
        '  <tbody>'
    ]

    for idx, row in df.iterrows():
        c_num = idx + 1
        g = row['Genotype']
        L = int(row['Length'])
        n_triplets = int(row['NumTriplets'])

        gen_link = f"<code>/*9*/{g}</code>"
        if selected_dir and os.path.exists(selected_dir):
            for fname in os.listdir(selected_dir):
                if fname.startswith(f"selected_{c_num}_") and fname.endswith(".gen"):
                    gen_link = f'<a href="./selected/{fname}"><code>/*9*/{g}</code></a>'
                    break

        td_cells = []
        for i in (1, 2):
            td_cells.extend([
                format_html_td(row[f'SumRaw_Triplets_B{i}'], f'SumRaw_Triplets_B{i}', fmt="{:+.2f}"),
                format_html_td(row[f'SumAbs_Triplets_B{i}'], f'SumAbs_Triplets_B{i}', fmt="{:.2f}"),
                format_html_td(row[f'Dir_Triplets_B{i}'], f'Dir_Triplets_B{i}', -1.0, 1.0, fmt="{:+.3f}"),
                format_html_td(row[f'MeanAbs_Triplets_B{i}'], f'MeanAbs_Triplets_B{i}', 0, max_val, fmt="{:.3f}"),
            ])

        html_lines.append('    <tr style="border-bottom: 1px solid #e2e8f0;">')
        html_lines.append(f'      <td style="padding: 6px; border: 1px solid #e2e8f0;">{c_num}</td>')
        html_lines.append(f'      <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: left;">{gen_link}</td>')
        html_lines.append(f'      <td style="padding: 6px; border: 1px solid #e2e8f0;">{L}</td>')
        html_lines.append(f'      <td style="padding: 6px; border: 1px solid #e2e8f0;">{n_triplets}</td>')
        html_lines.extend(f'      {td}' for td in td_cells)
        html_lines.append('    </tr>')

    html_lines.append('  </tbody>')
    html_lines.append('</table>')
    return "\n".join(html_lines)


def update_readme_table(readme_path: str, table_content: str, marker:str='<a id="table-3d-epistasis-sums"></a>') -> bool:
    """Replaces the table under `marker` tag in README.md."""
    if not os.path.exists(readme_path):
        print(f"[Error] README file not found: {readme_path}")
        return False

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    marker = '<a id="table-3d-epistasis-sums"></a>'
    if marker not in content:
        print(f"[Error] Marker '{marker}' not found in {readme_path}")
        return False

    parts = content.split(marker)
    before = parts[0] + marker + "\n\n"
    after_part = parts[1].lstrip()

    # Find where the table ends (first heading or next non-table section)
    lines_after = after_part.split("\n")
    table_end_idx = 0
    in_table = False
    for i, line in enumerate(lines_after):
        sline = line.strip()
        if sline.startswith("|") or sline.startswith("<table") or sline.startswith("<tr") or sline.startswith("</table"):
            in_table = True
        elif in_table and not (sline.startswith("|") or sline.startswith("<") or sline == ""):
            table_end_idx = i
            break
        elif in_table and sline.startswith("###"):
            table_end_idx = i
            break

    after = "\n".join(lines_after[table_end_idx:]).lstrip()

    new_content = before + table_content + "\n\n\n" + after

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[Success] Updated epistasis table in: {readme_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Calculate derived epistasis metrics and print/update table with font coloring and extreme bolding.")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to epistasis_3d_summary.csv.")
    parser.add_argument("--readme", default=DEFAULT_README, help="Path to README.md to update.")
    parser.add_argument("--update-readme", action="store_true", help="Update the table directly in README.md.")
    parser.add_argument("--out-csv", default=None, help="Save updated CSV with derived metrics.")
    parser.add_argument("--format", choices=["markdown", "html"], default="markdown",
                        help="Table format: 'markdown' or 'html'. Default: 'markdown'.")
    parser.add_argument("--color-target", choices=["font", "background"], default="font",
                        help="Target element to color: 'font' (default) or 'background'.")
    parser.add_argument("--bold-mode", choices=["all-baselines", "per-baseline", "none"], default="all-baselines",
                        help="Bolding policy: 'all-baselines' (lowest/largest across all baselines combined, default), "
                             "'per-baseline' (lowest/largest per individual baseline column), or 'none'.")
    parser.add_argument("--max-val", type=float, default=None,
                        help="Override maximum value for mean absolute epistasis scaling domain [-max_val, +max_val].")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"[Error] CSV not found at: {args.csv}")
        sys.exit(1)

    df = pd.read_csv(args.csv)
    df_metrics = compute_derived_metrics(df)

    if args.out_csv:
        df_metrics.to_csv(args.out_csv, index=False)
        print(f"[CSV] Saved updated metrics CSV to: {args.out_csv}")

    gen_table_callable = generate_html_table if args.format == "html" else generate_markdown_table

    table_output = gen_table_callable(df_metrics, selected_dir=SELECTED_DIR,
            max_val=args.max_val, color_target=args.color_target, bold_mode=args.bold_mode
        )

    print("\n--- 3D Triplet Epistasis Summary Table ---")
    print(table_output)
    print("------------------------------------------\n")

    if args.update_readme:
        update_readme_table(args.readme, table_output)


if __name__ == "__main__":
    main()
