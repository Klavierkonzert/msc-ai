#!/usr/bin/env python3
"""Parse and analyze HoF-*.gen files produced by FramsticksEvolution.

Produces a CSV summary `hof_summary.csv` and (if available) plots in `hof_plots/`.

Usage: python scripts/analyze_hof.py [--pattern HoF-*.gen] [--outdir results]
"""
from __future__ import annotations
import argparse
import csv
import glob
import os
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any, overload

import pandas as pd
import sys
import matplotlib
if os.environ.get('MPLBACKEND') == 'Agg' or '--headless' in sys.argv:
    matplotlib.use('Agg')
else:
    try:
        matplotlib.use("TkAgg")
    except Exception:
        matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import seaborn as sns
import numpy as np
import math


def parse_hof_file(path: str) -> List[Dict[str, Any]]:
    """Parse a HoF .gen file into a list of records (one per entry).
    Expected entry format (example):
    org:
    genotype:/*9*/LRBFUUU
    vertpos:0.7591413372346053

    Returns list of dicts with keys parsed from file plus special `source_file` and `raw_entry`.
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split entries by two or more newlines
    entries = [e.strip() for e in re.split(r"\n\s*\n", content) if e.strip()]
    records = []
    for rank, entry in enumerate(entries, start=1):
        rec: Dict[str, Any] = {"source_file": os.path.basename(path), "hof_rank": rank, "raw_entry": entry}
        for line in entry.splitlines():
            line = line.strip()
            if not line or line.endswith(":"):
                # lines like 'org:' have no value
                continue
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            # try to convert numeric values
            try:
                if v == "":
                    val = v
                else:
                    if re.match(r"^-?\d+$", v):
                        val = int(v)
                    else:
                        val = float(v)
            except Exception:
                val = v
            # strip leading prefix like /*9*/ from genotype strings
            if k == 'genotype' and isinstance(val, str):
                val = re.sub(r'^/\*.*?\*/', '', val)
            rec[k] = val
        records.append(rec)
    return records


def discover_files(pattern: str) -> List[str]:
    return sorted(glob.glob(pattern))


def parse_filename(fname: str) -> Dict[str, Any]:
    # Match HoF-<enc>-<M>-<N>.gen or HoF-<enc>-<N>.gen
    m = re.match(r"^HoF-(?P<enc>f[a-zA-Z0-9]+)(?:-(?P<M>.+))?-(?P<N>\d+)\.gen$", fname)
    if m:
        return {"enc": m.group("enc"), "run_M": m.group("M"), "run_N": int(m.group("N"))}
    return {"enc": None, "run_M": None, "run_N": None}


# def write_csv(records: List[Dict[str, Any]], outpath: str):
#     if not records:
#         print("No records to write")
#         return
#     # collect fieldnames
#     keys = set()
#     for r in records:
#         keys.update(r.keys())
#     fieldnames = ["source_file", "run_M", "run_N", "hof_rank", "genotype"] + sorted(k for k in keys if k not in ("source_file", "run_M", "run_N", "hof_rank", "genotype", "raw_entry"))
#     with open(outpath, "w", newline="", encoding="utf-8") as csvf:
#         writer = csv.DictWriter(csvf, fieldnames=fieldnames, extrasaction="ignore")
#         writer.writeheader()
#         for r in records:
#             row = {k: r.get(k, "") for k in fieldnames}
#             writer.writerow(row)
#     print(f"Wrote CSV summary to {outpath}")


def basic_stats(records: List[Dict[str, Any]]):
    print("--- Basic statistics ---")
    files = Counter(r["source_file"] for r in records)
    print(f"Total HoF files parsed: {len(files)}")
    print("Entries per file (sample):")
    for fname, cnt in files.most_common(10):
        print(f"  {fname}: {cnt}")

    genotypes = [r.get("genotype", "") for r in records]
    total = len(genotypes)
    unique = len(set(genotypes))
    clones = total - unique
    print(f"Total individuals: {total}")
    print(f"Unique genotypes: {unique}")
    print(f"Clones detected (identical genotypes repeated): {clones}")


# def try_plot(records: List[Dict[str, Any]], outdir: str):
#     try:
#         import pandas as pd
#         import matplotlib.pyplot as plt
#         import seaborn as sns
#     except Exception:
#         print("pandas/matplotlib/seaborn not available; skipping plots.")
#         return

#     os.makedirs(outdir, exist_ok=True)
#     df = pd.DataFrame(records)
#     # add parsed filename fields
#     parsed = df['source_file'].apply(parse_filename).apply(pd.Series)
#     df['run_M'] = parsed['run_M']
#     df['run_N'] = parsed['run_N']

#     # histogram: entries per file (horizontal bar chart rotated 90 degrees)
#     entries_per_file = df.groupby('source_file').size().sort_values(ascending=False)
#     plt.figure(figsize=(6, 10))
#     sns.barplot(y=entries_per_file.index, x=entries_per_file.values)
#     plt.xlabel('Entries')
#     plt.ylabel('HoF file')
#     plt.title('Entries per HoF file')
#     plt.tight_layout()
#     plt.savefig(os.path.join(outdir, 'entries_per_file.png'))
#     plt.close()

#     # clones: top genotypes
#     top = df['genotype'].value_counts().head(30)
#     plt.figure(figsize=(8, 6))
#     sns.barplot(y=top.index.astype(str), x=top.values)
#     plt.title('Top genotype frequencies')
#     plt.tight_layout()
#     plt.savefig(os.path.join(outdir, 'top_genotype_freq.png'))
#     plt.close()

#     # if numeric criterion exists, plot best vertpos per run if present
#     numeric_cols = [c for c in df.columns if c not in ('source_file', 'run_M', 'run_N', 'hof_rank', 'genotype', 'raw_entry')]
#     numeric_cols = [c for c in numeric_cols if df[c].dtype.kind in 'ifu']
#     if numeric_cols:
#         crit = numeric_cols[0]
#         # best per file (assuming hof_rank 1 is best)
#         bests = df[df['hof_rank'] == 1].sort_values(['run_M', 'run_N'])
#         plt.figure(figsize=(8, 4))
#         sns.lineplot(x=bests.index, y=bests[crit])
#         plt.title(f'Best {crit} across runs (by file)')
#         plt.tight_layout()
#         plt.savefig(os.path.join(outdir, f'best_{crit}_series.png'))
#         plt.close()

#     print(f"Saved plots (when possible) to {outdir}")


def find_newest_subfolder(base_dir: str = 'stats') -> str | None:
    """Return the newest subfolder inside `base_dir`, or None if none exists."""
    if not os.path.isdir(base_dir):
        return None
    subdirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not subdirs:
        return None
    subdirs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return subdirs[0]

# helpers:
# helper to split path into folder and filename
def logbook_stem(fname: str,  suffix:str = ".logbook.pkl") -> tuple[str, str]:
        """Returns directory and filename of the file"""
        base = os.path.basename(fname)
        d = os.path.dirname(fname)
        if base.endswith(suffix):
            return d, base[:-len(suffix)]
        return d, os.path.splitext(base)[0]
def parse_lb_filename(fname: str) -> dict[str, str]:
    d, base = logbook_stem(fname)
    m = re.match(r"^HoF-(?P<enc>f[a-zA-Z0-9]+)(?:-(?P<param>.+))?-(?P<experiment>\d+)$", base)
    if m:
        res = m.groupdict()
        return {"enc": res["enc"], "param": res["param"], "experiment": res["experiment"], "dir": d, "base": base}
    parts = base.split("-")
    if len(parts) >= 3:
        _, enc, *params, experiment = parts
        param = "-".join(params) if params else None
        return {"enc": enc, "param": param, "experiment": experiment, "dir": d, "base": base}
    return {"enc": "unknown", "param": None, "experiment": "0", "dir": d, "base": base}

def read_logs(paths: list[str]):
    """Read all `*.logbook.pkl` files from `path` and return a pandas DataFrame.

    DataFrame columns: filename, enc, param, experiment, gen, best, nevals
    """
    import glob
    import pickle

    def get_best_and_nevals(lb_obj):
        """Return (best_series, nevals_series) extracted from a DEAP Logbook-like object."""
        bests = [float(v['max']) for v in lb_obj]
        cumnevals = [int(v['nevals']) for v in lb_obj]
        return bests, cumnevals

    rows = []
    for path in paths:
        files = sorted(glob.glob(os.path.join(path, '*.logbook.pkl')))
        if not files:
            print(f"No .logbook.pkl files found in {path}")
            return pd.DataFrame(rows)
        failed_files = []
        for f in files:
            try:
                with open(f, 'rb') as fh:
                    lb = pickle.load(fh)
            except Exception as e:
                failed_files.append((f, e))
                continue
            meta = parse_lb_filename(f)
            best_series, nevals_series = get_best_and_nevals(lb)
            for gen_idx, (val, ne) in enumerate(zip(best_series, nevals_series)):
                rows.append({
                    'dir': meta['dir'],
                    'filename': meta['base'],
                    'enc': meta['enc'],
                    'param': meta.get('param', None),
                    'experiment': meta['experiment'],
                    'gen': gen_idx,
                    'best': val,
                    'nevals': ne,
                })
        if failed_files:
            print(f"Could not load {len(failed_files)}/{len(files)} logbook file(s). First failure: {failed_files[0][0]}: {failed_files[0][1]}")
        if files and not rows:
            print("No logbook rows were read. Check that you are running this script with the same Python environment that has DEAP installed.")
    return pd.DataFrame(rows)


DEFAULT_PALETTES: list[str] = [
    "RdPu",      # 1. Red-Purple
    "GnBu",      # 2. Green-Blue / Cyan
    "YlOrRd",    # 3. Yellow-Orange-Red
    "PuBu",      # 4. Purple-Blue
    "YlGn",      # 5. Yellow-Green
    "Oranges",   # 6. Amber-Orange
    "mako",      # 7. Teal-Navy (perceptually uniform)
    "flare",     # 8. Coral-Gold
    "crest",     # 9. Mint-Forest
    "rocket",    # 10. Violet-Crimson
    "Purples",   # 11. Indigo-Purple
    "Blues",     # 12. Ocean Blue
]

DEFAULT_LINESTYLES: list[str] = [
    '-.',
    ':',
    '-',
    '--',
]

LINESTYLE_ALIASES: dict[str, str] = {
    '-.': '-.', 'dashdot': '-.',
    ':': ':', 'dotted': ':',
    '-': '-', 'solid': '-',
    '--': '--', 'dashed': '--',
}


def get_experiment_palette(dir_path: str | None, default_palette: str) -> str:
    """Infers the dedicated experiment palette from DEFAULT_PALETTES if 'exp\\d+' or 'Exp\\d+' is in dir_path."""
    if dir_path:
        base = os.path.basename(os.path.normpath(str(dir_path)))
        m = re.search(r'(?:exp|experiment)[_-]?(\d+)', base, re.IGNORECASE)
        if not m:
            matches = list(re.finditer(r'(?:exp|experiment)[_-]?(\d+)', str(dir_path), re.IGNORECASE))
            m = matches[-1] if matches else None
        if m:
            exp_num = int(m.group(1))
            if 1 <= exp_num <= len(DEFAULT_PALETTES):
                return DEFAULT_PALETTES[exp_num - 1]
    return default_palette


def main():
    # Pre-extract --linestyles from sys.argv so that leading dashes ('-', '--', '-.')
    # are treated as values rather than option flags by argparse
    clean_argv = []
    custom_linestyles = None
    i = 1
    while i < len(sys.argv):
        tok = sys.argv[i]
        if tok == '--linestyles':
            custom_linestyles = []
            i += 1
            while i < len(sys.argv):
                val = sys.argv[i]
                if val.startswith('--') and val not in LINESTYLE_ALIASES and val not in DEFAULT_LINESTYLES:
                    break
                for part in val.split(','):
                    part = part.strip()
                    if part:
                        custom_linestyles.append(part)
                i += 1
        else:
            clean_argv.append(tok)
            i += 1

    ap = argparse.ArgumentParser()
    # HoF parsing is kept for legacy but disabled by default when using logbooks
    ap.add_argument('--pattern', default='HoF-*.gen', help='glob pattern for HoF files')
    ap.add_argument('--outdir', default='hof_results', help='output directory for CSV and plots')
    ap.add_argument('--logbook-dirs', nargs='+', default=None, help='directory containing .logbook.pkl files (default: newest subfolder in stats/)')
    ap.add_argument('--group-by', default='param', help='Column to group runs by for boxplots (default: param)')
    ap.add_argument('--time-unit', choices=['s', 'm', 'h'], default='s', help='Time unit for duration plots')
    ap.add_argument('--log-time', action='store_true', help='Plot runtime on a log scale')
    ap.add_argument('--min-samples', type=int, default=1, help='Minimum runs per parameter to include in boxplots')
    ap.add_argument('--nevals-as-time', action='store_true', help='Use total_nevals as runtime proxy (plot evaluations instead of seconds)')
    ap.add_argument('--colors', '--palettes', dest='colors', nargs='+', default=None, help='List of seaborn color palette names for folder subgroups (e.g. RdPu GnBu). Must belong to DEFAULT_PALETTES.')
    ap.add_argument('--linestyles', nargs='+', default=None, help='List of linestyles to use for curves (e.g. -. : - --). Must belong to DEFAULT_LINESTYLES.')
    ap.add_argument('--headless', action='store_true', help='Run headless without interactive GUI popups')
    ap.add_argument('--extension', default='png', choices=['png', 'pdf', 'svg'], help='Image extension for plots (default: png)')
    ap.add_argument('--xscale', nargs='+', default=['linlog'], help='X-axis scale for history and confidence plots: linlog (default), linlog<N> (e.g. linlog 400), lin, log, symlog')
    args = ap.parse_args(clean_argv)

    # Parse --xscale scale type and optional linear threshold
    raw_xscale = " ".join(args.xscale) if isinstance(args.xscale, list) else str(args.xscale)
    m_scale = re.match(r'^(linlog|symlog|lin|log|linear)(?:[\s_:-]?(\d+))?$', raw_xscale.strip(), re.IGNORECASE)
    if m_scale:
        xscale_type = m_scale.group(1).lower()
        if xscale_type == 'linear':
            xscale_type = 'lin'
        xscale_threshold = int(m_scale.group(2)) if m_scale.group(2) else None
    else:
        ap.error(f"Invalid --xscale value: '{raw_xscale}'. Supported: linlog, linlog<N>, lin, log, symlog.")

    # Validate that user-supplied colors belong to DEFAULT_PALETTES
    if args.colors is not None and any(c not in DEFAULT_PALETTES for c in args.colors):
        ap.error(f"Invalid color/palette: must belong to DEFAULT_PALETTES: {DEFAULT_PALETTES}")

    # Validate that user-supplied linestyles belong to DEFAULT_LINESTYLES
    if custom_linestyles is not None and any(ls not in DEFAULT_LINESTYLES and ls not in LINESTYLE_ALIASES for ls in custom_linestyles):
        ap.error(f"Invalid linestyle: must belong to DEFAULT_LINESTYLES: {DEFAULT_LINESTYLES}")
    
    active_linestyles = [LINESTYLE_ALIASES.get(ls, ls) for ls in custom_linestyles] if custom_linestyles is not None else DEFAULT_LINESTYLES
    
    # Determine logbook directory: use provided, else newest subfolder under 'stats'
    logbook_dirs:list[str]|None = args.logbook_dirs or [find_newest_subfolder('stats')]

    if args.colors is None and logbook_dirs and len(logbook_dirs) == 1:
        exp_pal = get_experiment_palette(logbook_dirs[0], DEFAULT_PALETTES[0])
        active_palettes = [exp_pal] + [p for p in DEFAULT_PALETTES if p != exp_pal]
    else:
        active_palettes = args.colors or DEFAULT_PALETTES
    if logbook_dirs:
        # try:
            df = read_logs(logbook_dirs) #reads one or several log folders
            print(f"Reading logbooks from {logbook_dirs}")
            print(df.head())
            print("...")
            try:
                df.to_csv("stats\\last_stats.csv")
            except:
                pass
            

            if not df.empty:
                if args.group_by in df.columns and not df[args.group_by].isna().all():
                    subgroup_var = args.group_by
                else:
                    subgroup_var = 'param' if 'param' in df.columns and not df['param'].isna().all() else 'enc'
                # plot and save curves
                print(f"Subgroup variable for analysis: {subgroup_var}")
                plots_dir = os.path.join(args.outdir, 'plots')
                hist_thresh = xscale_threshold if xscale_threshold is not None else 3500
                conf_thresh = xscale_threshold if xscale_threshold is not None else 50
                plot_HoF_history(df, param=subgroup_var, outdir=plots_dir, palettes=active_palettes, linestyles=active_linestyles, extension=args.extension, xscale=xscale_type, _symlog_threshold=hist_thresh)
                plot_HoF_confidence(df, param=subgroup_var, outdir=plots_dir, palettes=active_palettes, linestyles=active_linestyles, extension=args.extension, xscale=xscale_type, _symlog_threshold=conf_thresh)


                # aggregated summary and boxplots
                summary = collect_run_summary(logbook_dirs, df)
                os.makedirs(args.outdir, exist_ok=True)
                csvpath = os.path.join(args.outdir, 'boxplot_summary.csv')
                summary.to_csv(csvpath, index=False)
                print(f'Wrote per-run summary to {csvpath}')
                if not summary.empty:
                    # if requested, use total_nevals as runtime proxy
                    if args.nevals_as_time:
                        summary['duration_s'] = summary['total_nevals']
                        # pass a special time_unit marker to plotting
                        plot_boxplot_summary(summary, outdir=plots_dir, 
                                             time_unit='eval', log_time=False, min_samples=args.min_samples, palettes=active_palettes, extension=args.extension)
                    else:
                        plot_boxplot_summary(summary, outdir=plots_dir, 
                                             time_unit=args.time_unit, log_time=args.log_time, min_samples=args.min_samples, palettes=active_palettes, extension=args.extension)

        # except Exception as e:
        #     print(f'Error reading logbooks from {logbook_dirs}: {e}')
    else:
        # The original HoF parsing/writing block is commented out to focus on logbook analysis.
        # files = discover_files(args.pattern)
        # if not files:
        #     print(f"No files found matching pattern: {args.pattern}")
        #     return
        # all_recs: List[Dict[str, Any]] = []
        # for f in files:
        #     recs = parse_hof_file(f)
        #     meta = parse_filename(os.path.basename(f))
        #     for r in recs:
        #         r.update(meta)
        #     all_recs.extend(recs)
        # os.makedirs(args.outdir, exist_ok=True)
        # csvpath = os.path.join(args.outdir, 'hof_summary.csv')
        # write_csv(all_recs, csvpath)
        # basic_stats(all_recs)
        # try_plot(all_recs, os.path.join(args.outdir, 'plots'))
        print('No logbook directory provided and HoF parsing is disabled in this run.')



def extract_scheme_group(s: Any) -> str:
    """Extracts base scheme group up to and including the scheme index digit(s).
    Groups together schemes with alphabetic/refinement postfixes (e.g. scheme-3b, scheme-3_b)
    as well as trailing numeric variation postfixes like '-\\d+' (e.g. scheme-8-100, scheme-8-200 -> scheme-8).
    Also strips leading prefixes (e.g. scaled-, scale-, ext-, extended-) and normalizes shorthand 'sch' -> 'scheme'
    so that scaled and extended variants group identically with their base counterparts.
    e.g. 'scheme-3' -> 'scheme-3'
         'scaled-sch-3' -> 'scheme-3'
         'scheme-8-100' -> 'scheme-8'
         'scaled-sch-8-100' -> 'scheme-8'
         'scheme-12' -> 'scheme-12'
         'scaled-sch-12' -> 'scheme-12'
         'sch-7c' -> 'scheme-7'
         'Baseline' -> 'Baseline'
    """
    if s is None:
        return ''
    s_str = str(s).strip()
    # Strip leading prefixes: scaled-, scale-, ext-, extended-
    s_clean = re.sub(r'^(?:scaled?|ext(?:ended)?)[_-]', '', s_str, flags=re.IGNORECASE)
    # Normalize shorthand prefix 'sch' to 'scheme'
    s_clean = re.sub(r'^(?:scheme|sch)[_-]?', 'scheme-', s_clean, flags=re.IGNORECASE)

    # 1. Trailing -\\d+ variation (e.g. scheme-8-100, scheme-8-200 -> scheme-8)
    if (m_num := re.match(r'^(.*?(?:scheme|sch)[_-]?\d+)-(\d+)$', s_clean, re.IGNORECASE)):
        return m_num.group(1)
    # 2. Trailing alphabetic or non-digit postfix (e.g. scheme-3b, scheme-3_refined -> scheme-3)
    if (m := re.match(r'^(.*?(?:scheme|sch)[_-]?\d+)([-_a-zA-Z].*)$', s_clean, re.IGNORECASE)):
        return m.group(1)
    # 3. Short format s3b or s8-100
    if (m2_num := re.match(r'^(s?\d+)-(\d+)$', s_clean, re.IGNORECASE)):
        return m2_num.group(1)
    if (m2 := re.match(r'^(s?\d+)([-_a-zA-Z].*)$', s_clean, re.IGNORECASE)):
        return m2.group(1)
    return s_clean


def shorten_scheme_label(s: Any) -> str:
    """Shortens scheme names for compact x-tick labeling, e.g. 'scheme-8-100' -> 'sch.-8-100'."""
    if s is None:
        return ''
    s_str = str(s)
    return re.sub(r'^(?:scheme|sch)[_-]', 'sch.-', s_str, flags=re.IGNORECASE)


def natural_sort_key(s: Any) -> list:
    """Natural alphanumeric sort key (e.g. converts digits to int so scheme-2 comes before scheme-10)."""
    if s is None:
        return []
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]


def get_ordered_params(df: pd.DataFrame, param: str = 'param', directories: list[str | None] | None = None) -> list[str]:
    """Returns parameter values ordered by the directories in which they first appear,
    with natural alphanumeric sorting within each directory."""
    if df is None or df.empty or param not in df.columns:
        return []
    if not directories or 'dir' not in df.columns:
        return sorted(df[param].dropna().unique(), key=natural_sort_key)

    ordered = []
    seen = set()
    for d in directories:
        d_params = sorted(df[df['dir'] == d][param].dropna().unique(), key=natural_sort_key)
        for p in d_params:
            if p not in seen:
                seen.add(p)
                ordered.append(p)
    for p in sorted(df[param].dropna().unique(), key=natural_sort_key):
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered


@overload
def get_colormaps(palettes:list[str], param_vals:list[str|None], directories:list[str|None], df:pd.DataFrame|None=None, param:str|None=None) -> dict[str, dict[str, tuple[float, float, float]]]:...
@overload
def get_colormaps(palettes:list[str], param_vals:list[str|None], directories:None, df:pd.DataFrame|None=None, param:str|None=None) -> dict[str, tuple[float, float, float]]:...

def get_colormaps(palettes:list[str], param_vals:list[str|None], directories:list[str|None]|None=None, df:pd.DataFrame|None=None, param:str|None=None) ->Any:
    """Returns dict of dir->colormap if list of directories is not dummy, otherwise returns one colormap"""
    is_custom_palettes = (palettes != DEFAULT_PALETTES)
    if directories is not None:
        res = {}
        for d_idx, d in enumerate(directories):
            pal_name = palettes[d_idx % len(palettes)] if is_custom_palettes else get_experiment_palette(d, palettes[d_idx % len(palettes)])
            cmap = sns.color_palette(pal_name, as_cmap=True)
            if df is not None and param is not None and 'dir' in df.columns and param in df.columns:
                d_params = sorted(df[df['dir'] == d][param].dropna().unique(), key=natural_sort_key)
            else:
                d_params = sorted(param_vals, key=natural_sort_key)
            n_d = len(d_params)
            sample_pts_d = [0.7] if n_d <= 1 else np.linspace(0.35, 0.9, n_d)
            colors = [cmap(float(pt)) for pt in sample_pts_d]
            res[d] = {p: colors[i] for i, p in enumerate(d_params)}
        return res
    else:
        pal_name = palettes[0]
        cmap = sns.color_palette(pal_name, as_cmap=True)
        sorted_params = sorted(param_vals, key=natural_sort_key)
        n_params = len(sorted_params)
        sample_pts = [0.7] if n_params <= 1 else np.linspace(0.35, 0.9, n_params)
        colors = [cmap(float(pt)) for pt in sample_pts]
        return {p: colors[i] for i, p in enumerate(sorted_params)}

    
    
# --- Original patch-based legend implementation (does not reflect linestyle) ---
# def get_legend_handles( param_vals:list[str],directories:list[str]|None,color_maps:dict[str, dict[str, tuple[float, float, float]]]) -> list[mpatches.Patch]:
#     return [mpatches.Patch(color=c, label=d[d.rfind('\\')+1:]+':\n'+ v if directories is not None and len(directories)>0 and param_vals.index(v)==0 
#                                                       else v ) 
#                              for d,color_map in color_maps.items() for v,c in color_map.items() ]

def get_legend_handles(param_vals: list[str], directories: list[str] | None,color_maps: dict[str, dict[str, tuple[float, float, float]]], linestyle_cycle: list[str] | None = None) -> list[mlines.Line2D]:
    handles = []
    has_multiple_dirs = directories is not None and len(directories) > 1
    for d, color_map in color_maps.items():
        dir_name = d[max(d.rfind('\\'), d.rfind('/')) + 1:] if d else ''
        for i, (v, c) in enumerate(color_map.items()):
            if linestyle_cycle is not None and param_vals and v in param_vals:
                ls = linestyle_cycle[param_vals.index(v) % len(linestyle_cycle)]
            else:
                ls = '-'
            if has_multiple_dirs:
                label = f"{dir_name}: {v}"
            else:
                label = str(v)
            handles.append(mlines.Line2D([], [], color=c, linestyle=ls, linewidth=2.0, label=label))
    return handles

def get_legend(param_vals: list[str], directories: list[str] | None,color_maps: dict[str, dict[str, tuple[float, float, float]]], linestyle_cycle: list[str] | None = None):
    # plt.legend(title=param+' value:')
    # plt.legend(handles=get_legend_handles( param_vals,directories,color_maps))
    fig = plt.gcf()

    # remove axis legend if present
    ax = plt.gca()
    if ax.get_legend() is not None:
        ax.get_legend().remove()

    n_dirs = len(directories) if (directories is not None and len(directories) > 0) else (len(color_maps) if color_maps else 1)
    ncols = min(n_dirs, 5) if n_dirs > 1 else 4

    fig.legend(
        handles=get_legend_handles(param_vals, directories, color_maps, linestyle_cycle=linestyle_cycle),
        loc='center',
        bbox_to_anchor=(0.5, -0.1),   # 2% above bottom edge of figure
        # ncol=2,
        ncol=ncols,
    )
    fig.subplots_adjust(bottom=0.60)



def set_scale_ticks(symlog_threshold: int, max_x_value: int = None, xscale: str = 'linlog'):
    ax = plt.gca()
    scale = (xscale or 'linlog').lower()
    if scale in ('linlog', 'symlog'):
        ax.set_xscale('symlog', linthresh=symlog_threshold)
        raw_ticks = [t for t in ax.get_xticks() if t >= 0]
        if max_x_value is not None:
            raw_ticks = [t for t in raw_ticks if t <= max_x_value * 1.01]
            raw_ticks.append(max_x_value)
        if symlog_threshold not in raw_ticks:
            raw_ticks.append(symlog_threshold)
        ticks = sorted(set(int(round(t)) for t in raw_ticks))
        ax.set_xlim(left=0, right=max_x_value * 1.02 if max_x_value else None)
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(int(t)) if t != symlog_threshold else f'.. lin scale.. {symlog_threshold}.. log scale..' for t in ticks])
        if max_x_value and symlog_threshold < max_x_value:
            ax.axvline(symlog_threshold, color='#64748b', linestyle='--', linewidth=1.2, alpha=0.7)
    elif scale in ('log',):
        ax.set_xscale('log', nonpositive='clip')
        if max_x_value is not None:
            xlim = ax.get_xlim()
            ax.set_xlim(left=max(1, xlim[0]), right=max_x_value * 1.05)
    elif scale in ('lin', 'linear'):
        ax.set_xscale('linear')
        if max_x_value is not None:
            ax.set_xlim(left=0, right=max_x_value * 1.02)
    else:
        ax.set_xscale(scale)

def plot_HoF_history(df_logbook: pd.DataFrame, outdir: str|None = None, param = "param", extension="pdf", 
                     # palettes: list[str] = ["RdPu", "GnBu", "YlOrRd"],
                     palettes: list[str] = DEFAULT_PALETTES, _figsize:tuple[int, int]=(10, 6),
                     _symlog_threshold: int = 3500, xscale: str = 'linlog',
                     linestyles: list[str] | None = None):

    """Plot best curves; x-axis is cumulative evaluated individuals when available."""
    sns.set(style='whitegrid')
    plt.figure(figsize=_figsize)

    directories:list[str|None]= list(dict.fromkeys(df_logbook['dir'].dropna())) if 'dir' in df_logbook.columns else [None]
    param_vals:list[str|None] = get_ordered_params(df_logbook, param, directories)

    print(f"The following '{param}' values will be analyzed: {param_vals}")

    has_nevals = 'nevals' in df_logbook.columns and df_logbook['nevals'].notna().any()

    # iterate per (param, experiment, filename) so each curve is one experiment run
    linestyle_cycle = linestyles if linestyles else DEFAULT_LINESTYLES
    curve_count = 0

    # plt.ion()

    max_x_value = 0

    color_maps = get_colormaps(palettes, param_vals, directories, df=df_logbook, param=param)
    for (par_val, _i_experiment, _fname, _dir), group in df_logbook.groupby([param, 'experiment', 'filename', 'dir'] if param in df_logbook.columns else ['experiment', 'filename', 'dir']
                                                                            ):
        #change palette depending on directory:
        color_map = color_maps[_dir] if _dir is not None else color_maps

        # handle possible tuple when param not present
        if param in df_logbook.columns:
            par = par_val
            # exp = _i_experiment
        else:
            par = None
            # exp = par_val
        color: str|tuple[float, float, float] = color_map.get(par, 'gray')
        group_sorted = group.sort_values('gen').reset_index(drop=True)

        if has_nevals and group_sorted['nevals'].notna().any():
            ne = group_sorted['nevals'].astype(float)
            # detect whether nevals is already cumulative (non-decreasing) or per-generation
            is_non_decreasing = ne.dropna().empty or (ne.dropna().diff().min() >= 0)
            if is_non_decreasing and (ne.iloc[0] > 0):
                cum = ne
            else:
                cum = ne.cumsum()
            x = cum
        else:
            x = group_sorted['gen']

        # choose linestyle based on experiment index or curve count
        ls = linestyle_cycle[param_vals.index(par_val) % len(linestyle_cycle)]
        # label = f"{par} (exp{exp})" if par is not None else f"exp{exp}"
        plt.plot(x, group_sorted['best'], color=color, alpha=0.7, linestyle=ls)
        curve_count += 1

        max_x_value = max(max_x_value, x.max())

    set_scale_ticks(_symlog_threshold, max_x_value=max_x_value, xscale=xscale)

    if has_nevals:
        plt.xlabel('Cumulative evaluated individuals')
    else:
        plt.xlabel('Generation')
    plt.ylabel('Best (max) fitness')
    plt.title(f'Best result vs evaluations (colored by {param})')
    # plt.legend(handles=get_legend_handles( param_vals,directories,color_maps),
    #             #  bbox_to_anchor=(1.05,1), 
    # get_legend(param_vals, directories, color_maps)
    get_legend(param_vals, directories, color_maps, linestyle_cycle=linestyle_cycle)

    plt.tight_layout()

    save_dir = outdir or os.path.join('hof_results', 'plots')
    os.makedirs(save_dir, exist_ok=True)
    figpath = os.path.join(save_dir, 'logbooks_best_series.'+extension)
    plt.savefig(figpath, format=extension, bbox_inches="tight"  )
    print(f"Note: figure saved to {figpath}")
    if '--headless' in sys.argv or os.environ.get('MPLBACKEND') == 'Agg':
        plt.close()
    else:
        plt.show()
    print(f"Saved logbook curves to {figpath}")

 
def plot_HoF_confidence(df_logbook: pd.DataFrame, outdir: str|None = None, param: str = "param", ci: float = 1.0,  alpha: float = 0.12, extension: str = "pdf",
                        # palettes: list[str]=["RdPu", "GnBu", "YlOrRd"],
                        palettes: list[str] = DEFAULT_PALETTES, _figsize:tuple[int, int]=(10, 6), 
                        _symlog_threshold: int =50, xscale: str = 'linlog',
                        linestyles: list[str] | None = None):

    """Plot shaded confidence intervals for each `param` value.

    - `ci`: Scales confidence limits: (mean +/- ci*std).
    - `alpha`: opacity of shaded area.
    """
    sns.set(style='whitegrid')
    if df_logbook is None or df_logbook.empty:
        print('No logbook data to plot confidence intervals.')
        return

    save_dir = outdir or os.path.join('hof_results', 'plots')
    os.makedirs(save_dir, exist_ok=True)
    directories:list[str|None]= list(dict.fromkeys(df_logbook['dir'].dropna())) if 'dir' in df_logbook.columns else [None]
    param_vals:list[str|None] = get_ordered_params(df_logbook, param, directories)

    color_maps = get_colormaps(palettes, param_vals, directories, df=df_logbook, param=param)
    linestyle_cycle = linestyles if linestyles else DEFAULT_LINESTYLES

    max_gens = 0

    plt.figure(figsize=_figsize)
    for p in param_vals:
        subset: pd.DataFrame = df_logbook[df_logbook[param] == p] if p is not None else df_logbook
        if subset.empty:
            continue
        
        for _dir in directories:
            if 'dir' in subset.columns and _dir is not None: 
                dsubset = subset[subset['dir']==_dir]
                color_map = color_maps[_dir]
            else:
                dsubset = subset
                color_map = color_maps

            if dsubset.empty:
                continue

            g = dsubset.groupby('gen')['best']
            ## aggregate across experiments by generation
            # agg = g.agg(list)
            # gens = sorted(agg.index)
            lower_bound = g.min().min()
            means = g.mean()
            std = g.std() # std in Pandas provides unbiased estimate
            lower = (means - ci * std).clip(lower_bound)
            upper = means + ci * std

            gens = means.index
            if gens.max() > max_gens:
                max_gens = gens.max()

            color: str|tuple[float,float,float] = color_map.get(p, 'gray')
            ls = linestyle_cycle[param_vals.index(p) % len(linestyle_cycle)] if (param_vals and p in param_vals) else '-'
            plt.plot(gens, means, color=color, label=str(p), linestyle=ls)
            plt.fill_between(gens, lower, upper, color=color, alpha=alpha)

    set_scale_ticks(_symlog_threshold, max_x_value=max_gens, xscale=xscale)
    plt.xlabel('Generation')
    plt.ylabel('Best (mean) fitness')
    plt.title(f'Confidence intervals ({"mean +-" + str(ci) + ' std'})')

    get_legend(param_vals, directories, color_maps, linestyle_cycle=linestyle_cycle)

    plt.tight_layout()
    figpath = os.path.join(save_dir, f'logbooks_confidence_std_{ci}.' + extension)
    plt.savefig(  figpath, format=extension, bbox_inches="tight" )
    if '--headless' in sys.argv or os.environ.get('MPLBACKEND') == 'Agg':
        plt.close()
    else:
        plt.show()
    print(f"Saved confidence-interval plot to {figpath}")


def collect_run_summary(logbook_dirs: list[str]|None = None, df_logbook: pd.DataFrame = None, runs_search_dirs: list | None = None) -> pd.DataFrame:
    """Collect one-row-per-run summary from `*.logbook.pkl` files.

    Returns DataFrame with columns: filename, enc, param, experiment, hof_best, duration_s, total_nevals, n_generations
    """
    import glob
    import pickle
    import math

    runs_search_dirs = runs_search_dirs or ['out', 'runs']
    rows = []

    if df_logbook is None:
        if not logbook_dir:
            return pd.DataFrame(rows)
        df_logbook = read_logs(logbook_dirs)

    def extract_from_logbook(lb_obj):
        # returns (hof_best, nevals_series (list or None), duration_candidates(list))
        bests = []
        nevals = []
        durations = []
        try:
            top_duration = getattr(lb_obj, 'run_duration_s', None)
  
            for entry in lb_obj:
                if isinstance(entry, dict):
                    if 'max' in entry:
                        try:
                            bests.append(float(entry['max']))
                        except Exception:
                            pass
                    elif 'fitness' in entry:
                        try:
                            f = entry['fitness']
                            if isinstance(f, (list, tuple)):
                                bests.append(float(max(f)))
                            else:
                                bests.append(float(f))
                        except Exception:
                            pass
                    for k in ('nevals', 'n_evals', 'nfevals', 'evaluations'):
                        if k in entry:
                            try:
                                nevals.append(int(entry[k]))
                            except Exception:
                                try:
                                    nevals.append(int(float(entry[k])))
                                except Exception:
                                    pass

            # durations: use top-level attr if present, else look for duration-like fields in entries
            if top_duration is not None:
                try:
                    durations = [float(top_duration)]
                except Exception:
                    durations = []
            else:
                for entry in lb_obj:
                    if not isinstance(entry, dict):
                        continue
                    for dk in ('run_duration_s', 'duration', 'time', 'running_time', 'elapsed', 'time_elapsed'):
                        if dk in entry:
                            try:
                                durations.append(float(entry[dk]))
                            except Exception:
                                pass
            
        except Exception:
            pass

        hof_best = max(bests) if bests else None
        return hof_best, nevals, durations

    def parse_duration_text(text: str):
        # try several heuristics: numeric+unit, hh:mm:ss
        import re
        # hh:mm:ss
        m = re.search(r"(\d{1,2}:\d{2}:\d{2})", text)
        if m:
            s = m.group(1)
            parts = [int(x) for x in s.split(':')]
            return parts[0]*3600 + parts[1]*60 + parts[2]
        # numeric with unit
        m = re.search(r"(?i)(?:elapsed|duration|total time|completed in)[:\s]*([0-9]+(?:\.[0-9]+)?)\s*(ms|s|sec|secs|seconds|m|min|mins|minutes|h|hr|hours)?", text)
        if m:
            val = float(m.group(1))
            unit = (m.group(2) or '').lower()
            if unit.startswith('ms'):
                return val/1000.0
            if unit.startswith('m') and not unit.startswith('ms'):
                return val*60.0
            if unit.startswith('h'):
                return val*3600.0
            # default seconds
            return val
        return None

    #iterate over logbook_dirs:
    for logbook_dir in logbook_dirs:
        # iterate over pickle files in logbook_dir (if available)
        if logbook_dir and os.path.isdir(logbook_dir):
            files = sorted(glob.glob(os.path.join(logbook_dir, '*.logbook.pkl')))
        else:
            # try to infer from df_logbook if provided
            files = []
        for fpath in files:
            try:
                with open(fpath, 'rb') as fh:
                    lb = pickle.load(fh)
            except Exception:
                continue
            meta = parse_lb_filename(fpath)
            hof_best, nevals_list, durations = extract_from_logbook(lb)

            # total_nevals: detect cumulative vs per-gen
            total_nevals = None
            if nevals_list:
                try:
                    arr = [float(x) for x in nevals_list]
                    # monotonic -> cumulative
                    if all(arr[i] >= arr[i-1] for i in range(1, len(arr))):
                        total_nevals = arr[-1]
                    else:
                        total_nevals = sum(arr)
                except Exception:
                    total_nevals = None

            # duration: prefer durations from logbook; else search job logs
            duration_s = None
            if durations:
                try:
                    duration_s = float(durations[-1])
                except Exception:
                    duration_s = None

            if duration_s is None:
                # search job logs under runs/out directories
                base = meta.get('base')
                if base:
                    for root_d in runs_search_dirs:
                        pattern = os.path.join(root_d, '**', 'logs', base + '.log')
                        for candidate in glob.glob(pattern, recursive=True):
                            try:
                                with open(candidate, 'r', encoding='utf-8', errors='ignore') as cf:
                                    txt = cf.read()
                                    d = parse_duration_text(txt)
                                    if d is not None:
                                        duration_s = d
                                        break
                            except Exception:
                                continue
                        if duration_s is not None:
                            break

            # last fallback: attempt to derive duration from total_nevals (not a time but a proxy)
            if duration_s is None and total_nevals is not None:
                duration_s = None

            rows.append({
                'dir': meta.get('dir'),
                'filename': meta.get('base'),
                'enc': meta.get('enc'),
                'param': meta.get('param') if 'param' in meta else None,
                'experiment': meta.get('experiment'),
                'hof_best': hof_best,
                'duration_s': duration_s,
                'total_nevals': total_nevals,
                'n_generations': len(nevals_list) if nevals_list else None,
            })

    # If there were no pickle files, but df_logbook provided, aggregate from it
    if not rows and df_logbook is not None and not df_logbook.empty:
        gb_cols = [c for c in ('enc', 'param', 'experiment', 'filename', 'dir') if c in df_logbook.columns]
        for keys, g in df_logbook.groupby(gb_cols):
            # keys may be tuple
            rec = dict(zip(gb_cols, keys if isinstance(keys, tuple) else (keys,)))
            hof_best = None
            try:
                hof_best = float(g['best'].dropna().astype(float).max())
            except Exception:
                hof_best = None
            total_nevals = None
            if 'nevals' in g.columns and g['nevals'].notna().any():
                arr = g['nevals'].dropna().astype(float).tolist()
                if all(arr[i] >= arr[i-1] for i in range(1, len(arr))):
                    total_nevals = arr[-1]
                else:
                    total_nevals = sum(arr)
            rows.append({
                'dir': rec.get('dir'),
                'filename': rec.get('filename'),
                'enc': rec.get('enc'),
                'param': rec.get('param'),
                'experiment': rec.get('experiment'),
                'hof_best': hof_best,
                'duration_s': None,
                'total_nevals': total_nevals,
                'n_generations': int(g['gen'].max())+1 if 'gen' in g else None,
            })

    return pd.DataFrame(rows)


def plot_boxplot_summary(df_summary: pd.DataFrame, outdir: str = 'hof_results', group_by: list[str] = [ 'dir', 'enc', 'param'], time_unit: str = 's', log_time: bool = False, min_samples: int = 1, extension: str = 'pdf',
                         palettes: list[str] = DEFAULT_PALETTES, _figsize:tuple[int,int]=(14, 6)
                         ):

    """Create side-by-side boxplots: (1) solution quality per group, (2) runtime per group.

    - `group_by` is the column name used to group runs (defaults to 'param').
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    if df_summary is None or df_summary.empty:
        print('No per-run summary available for boxplots.')
        return

    active_group_by = []
    for grpb in group_by:
        if grpb in df_summary.columns and not df_summary[grpb].isna().all():
            if df_summary[grpb].nunique() > 1:
                active_group_by.append(grpb)
    if not active_group_by:
        active_group_by = [c for c in ('param', 'enc') if c in df_summary.columns and not df_summary[c].isna().all()][:1]
    group_by = active_group_by
    df_summary['multigroup'] = df_summary[group_by].astype(str).agg(', '.join, axis=1).str.strip()

    directories:list[str|None]= list(dict.fromkeys(df_summary['dir'].dropna())) if 'dir' in df_summary.columns else [None]

    if len(group_by)>2:
        raise NotImplemented("Support of more than 2 grouping vars is not yet implemented.")

    print("Boxplots: the following subgroups will be analyzed: 'multigroup' <-- ", *group_by)

    os.makedirs(outdir, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=_figsize)

    quality_df = df_summary.copy()
    subgroup_col = group_by[-1]

    # Extract base scheme groups so schemes with the same index but different postfix (e.g. scheme-8-100, scheme-8-200)
    # share the same base group tick position on the x-axis.
    scheme_group_col = f'{subgroup_col}_group'
    quality_df[scheme_group_col] = quality_df[subgroup_col].apply(extract_scheme_group)

    param_vals = get_ordered_params(quality_df, scheme_group_col, directories)
    color_maps = get_colormaps(palettes, param_vals, directories)

    is_multi_dir = len(directories) > 1

    if is_multi_dir:
        is_custom_palettes = (palettes != DEFAULT_PALETTES)
        dir_palette = {
            d: sns.color_palette(palettes[i % len(palettes)] if is_custom_palettes else get_experiment_palette(d, palettes[i % len(palettes)]), as_cmap=True)(0.7)
            for i, d in enumerate(directories)
        }
    else:
        d = directories[0] if directories else None
        base_cmap = color_maps.get(d, color_maps) if isinstance(color_maps, dict) and d in color_maps else color_maps

    # Check duration availability
    has_duration = 'duration_s' in df_summary.columns and df_summary['duration_s'].notna().any()
    if has_duration:
        factor = 1.0
        label_unit = 's'
        if time_unit == 'm':
            factor = 60.0
            label_unit = 'min'
        elif time_unit == 'h':
            factor = 3600.0
            label_unit = 'h'
        elif time_unit == 'eval':
            label_unit = 'evaluations'

    # Render boxplots and scatter points per group
    for i, grp in enumerate(param_vals):
        grp_df = quality_df[quality_df[scheme_group_col] == grp]
        if grp_df.empty:
            continue

        if is_multi_dir:
            # Multi-directory: item per (dir, variant)
            items = sorted(grp_df[['dir', subgroup_col]].drop_duplicates().values.tolist(),
                           key=lambda x: (directories.index(x[0]) if x[0] in directories else 99, natural_sort_key(x[1])))
        else:
            # Single-directory: item per variant
            variants = sorted(grp_df[subgroup_col].dropna().unique(), key=natural_sort_key)
            items = [(directories[0], v) for v in variants]

        M = len(items)
        if M == 0:
            continue

        total_width = min(0.8, 0.22 * M) if M > 1 else 0.45
        w = total_width / M
        centers = [i] if M == 1 else np.linspace(i - total_width / 2 + w / 2, i + total_width / 2 - w / 2, M)
        box_w = w * 0.85

        for (d_val, v_val), c in zip(items, centers):
            cond = (grp_df[subgroup_col] == v_val)
            if is_multi_dir and d_val is not None:
                cond = cond & (grp_df['dir'] == d_val)
            item_df = grp_df[cond]

            box_color = dir_palette[d_val] if is_multi_dir else base_cmap.get(grp, (0.5, 0.5, 0.5))

            # 1. Quality plot
            vals_q = item_df['hof_best'].dropna().values
            if len(vals_q) > 0:
                bp = axes[0].boxplot([vals_q], positions=[c], widths=[box_w], patch_artist=True, manage_ticks=False)
                for patch in bp['boxes']:
                    patch.set_facecolor(box_color)
                    patch.set_edgecolor('black')
                    patch.set_linewidth(1.0)
                for median in bp['medians']:
                    median.set_color('black')
                    median.set_linewidth(1.2)
                for whisker in bp['whiskers']:
                    whisker.set_color('black')
                for cap in bp['caps']:
                    cap.set_color('black')
                for flier in bp['fliers']:
                    flier.set(marker='o', markeredgecolor='black', markerfacecolor='none', alpha=0.7, markersize=4)

                np.random.seed(42 + i * 10 + int(c * 100) % 100)
                jitter = np.random.uniform(-box_w * 0.2, box_w * 0.2, size=len(vals_q))
                axes[0].scatter(c + jitter, vals_q, color='black', alpha=0.5, s=12, zorder=3)

            # 2. Duration plot
            if has_duration:
                dur_col = 'total_nevals' if time_unit == 'eval' and 'total_nevals' in item_df.columns else 'duration_s'
                vals_d = item_df[dur_col].dropna().values
                if len(vals_d) > 0:
                    if time_unit != 'eval':
                        vals_d = vals_d / factor
                    bp2 = axes[1].boxplot([vals_d], positions=[c], widths=[box_w], patch_artist=True, manage_ticks=False)
                    for patch in bp2['boxes']:
                        patch.set_facecolor(box_color)
                        patch.set_edgecolor('black')
                        patch.set_linewidth(1.0)
                    for median in bp2['medians']:
                        median.set_color('black')
                        median.set_linewidth(1.2)
                    for whisker in bp2['whiskers']:
                        whisker.set_color('black')
                    for cap in bp2['caps']:
                        cap.set_color('black')
                    for flier in bp2['fliers']:
                        flier.set(marker='o', markeredgecolor='black', markerfacecolor='none', alpha=0.7, markersize=4)

                    jitter = np.random.uniform(-box_w * 0.2, box_w * 0.2, size=len(vals_d))
                    axes[1].scatter(c + jitter, vals_d, color='black', alpha=0.5, s=12, zorder=3)

    axes[0].set_title('Hall-of-Fame fitness (per run)')
    axes[0].set_xlabel('Strategy / Scheme' if subgroup_col == 'param' else ', '.join(group_by))
    axes[0].set_ylabel('Fitness')

    if has_duration:
        axes[1].set_title('Run duration per run')
        axes[1].set_xlabel('Strategy / Scheme' if subgroup_col == 'param' else ', '.join(group_by))
        axes[1].set_ylabel(f'Duration ({label_unit})')
        if log_time and time_unit != 'eval':
            axes[1].set_yscale('log')
    else:
        axes[1].text(0.5, 0.5, 'No duration data available', ha='center', va='center')
        axes[1].set_axis_off()

    # Build tick labels: group name
    tick_labels = [str(grp) for grp in param_vals]

    rot = 45
    for ax in axes:
        ax.set_xticks(range(len(param_vals)))
        ax.set_xticklabels(tick_labels, rotation=rot, ha='right', va='top', rotation_mode='anchor')
        ax.set_xlim(-0.6, len(param_vals) - 0.4)

    ############### Legend #####################################
    if is_multi_dir:
        legend_handles = [
            mpatches.Patch(facecolor=dir_palette[d], edgecolor='black',
                           label=os.path.basename(os.path.normpath(d)) if ('\\' in str(d) or '/' in str(d)) else str(d))
            for d in directories if d in dir_palette
        ]
        legend_title = "Directories"
    else:
        legend_handles = [
            mpatches.Patch(facecolor=base_cmap.get(grp, (0.5, 0.5, 0.5)), edgecolor='black', label=str(grp))
            for grp in param_vals if grp in base_cmap
        ]
        legend_title = subgroup_col

    ncols = min(len(legend_handles), 4) if legend_handles else 1

    fig.legend(
        handles=legend_handles,
        title=legend_title,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=ncols
    )

    fig.subplots_adjust(bottom=0.25)
    ##########################################################

    plt.tight_layout()
    figpath = os.path.join(outdir, f'boxplot_summary.{extension}')
    plt.savefig(  figpath, format=extension, bbox_inches="tight" )
    if '--headless' in sys.argv or os.environ.get('MPLBACKEND') == 'Agg':
        plt.close()
    else:
        plt.show()
    print(f'Saved boxplot summary to {figpath}')



if __name__ == '__main__':
    print("Backend:", matplotlib.get_backend())
    main()
