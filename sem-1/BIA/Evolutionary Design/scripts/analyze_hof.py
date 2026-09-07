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
import matplotlib
# try:
#     matplotlib.use('Agg')
# except Exception:
#     pass
matplotlib.use("TkAgg")

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
    # try pattern HoF-f9-<M>-<N>.gen
    m = re.match(r"HoF-[^-]+-(?P<M>[^-]+)-(?P<N>\d+)\.gen$", fname)
    if m:
        return {"run_M": m.group("M"), "run_N": int(m.group("N"))}
    # fallback
    return {"run_M": None, "run_N": None}


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
# helper to parse filename (same convention as read_logs)
def parse_lb_filename(fname: str) ->dict[str, str]:
        d, base = logbook_stem(fname)
        parts = base.split("-")
        _, enc, *params, experiment = parts
        dpars = {"param" + (str(i) if i>0 else ""): p for i,p in enumerate(params)}
        return {"enc": enc, **dpars, "experiment": experiment, 'dir':d, "base": base}

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


def main():
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
    ap.add_argument('--palettes', nargs='+', default=None, help='List of seaborn color palette names for folder subgroups')
    args = ap.parse_args()

    # Determine logbook directory: use provided, else newest subfolder under 'stats'
    logbook_dirs:list[str]|None = args.logbook_dirs or [find_newest_subfolder('stats')]
    if logbook_dirs:
        # try:
            df = read_logs(logbook_dirs) #reads one or several log folders
            print(f"Reading logbooks from {logbook_dirs}")
            print(df.head())
            print("...")
            try:
                df.to_csv("stats\\last_stats.csv")
            except:
                raise Exception("Unsuccesfull writing to .csv")
            

            if not df.empty:
                if args.group_by in df.columns and not df[args.group_by].isna().all():
                    subgroup_var = args.group_by
                else:
                    subgroup_var = 'param' if 'param' in df.columns and not df['param'].isna().all() else 'enc'
                # plot and save curves
                print(f"Subgroup variable for analysis: {subgroup_var}")
                plots_dir = os.path.join(args.outdir, 'plots')
                active_palettes = args.palettes or DEFAULT_PALETTES
                plot_HoF_history(df, param=subgroup_var, outdir=plots_dir, palettes=active_palettes)
                plot_HoF_confidence(df, param=subgroup_var, outdir=plots_dir, palettes=active_palettes)


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
                        plot_boxplot_summary(summary, outdir=plots_dir, #group_by=subgroup_var,#args.group_by, 
                                             time_unit='eval', log_time=False, min_samples=args.min_samples, palettes=active_palettes)
                    else:
                        plot_boxplot_summary(summary, outdir=plots_dir, #group_by=subgroup_var,#args.group_by, 
                                             time_unit=args.time_unit, log_time=args.log_time, min_samples=args.min_samples, palettes=active_palettes)

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

@overload
def get_colormaps(palettes:list[str], param_vals:list[str|None], directories:list[str|None]) -> dict[str, dict[str, tuple[float, float, float]]]:...
@overload
def get_colormaps(palettes:list[str], param_vals:list[str|None], directories:None) -> dict[str, tuple[float, float, float]]:...

def get_colormaps(palettes:list[str], param_vals:list[str|None], directories:list[str|None]|None=None) ->Any:
    """Returns dict of dir->colormap if list of directories is not dummy, otherwise returns one colormap"""
    if directories is not None:
        dpalettes = {d:sns.color_palette(palette=palettes[directories.index(d) % len(palettes)], 
                                         n_colors=max(3, len(param_vals))) for d in directories}
        return {d:{p: palette[i % len(palette)] for i, p in enumerate(param_vals)} for d, palette in dpalettes.items()}
    else:
        return {p: palettes[0][i % len(palettes[0])] for i, p in enumerate(param_vals)}

    
    
# --- Original patch-based legend implementation (does not reflect linestyle) ---
# def get_legend_handles( param_vals:list[str],directories:list[str]|None,color_maps:dict[str, dict[str, tuple[float, float, float]]]) -> list[mpatches.Patch]:
#     return [mpatches.Patch(color=c, label=d[d.rfind('\\')+1:]+':\n'+ v if directories is not None and len(directories)>0 and param_vals.index(v)==0 
#                                                       else v ) 
#                              for d,color_map in color_maps.items() for v,c in color_map.items() ]

def get_legend_handles(param_vals: list[str], directories: list[str] | None,color_maps: dict[str, dict[str, tuple[float, float, float]]], linestyle_cycle: list[str] | None = None) -> list[mlines.Line2D]:
    handles = []
    for d, color_map in color_maps.items():
        for i, (v, c) in enumerate(color_map.items()):
            if linestyle_cycle is not None and param_vals and v in param_vals:
                ls = linestyle_cycle[param_vals.index(v) % len(linestyle_cycle)]
            else:
                ls = '-'
            dir_name = d[max(d.rfind('\\'), d.rfind('/')) + 1:] if d else ''
            label = (dir_name + ':\n' + v) if (directories is not None and len(directories) > 0 and param_vals.index(v) == 0) else v
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
    ncols = max(1, (n_dirs % 4) if n_dirs < 4 else 4)

    fig.legend(
        handles=get_legend_handles(param_vals, directories, color_maps, linestyle_cycle=linestyle_cycle),
        loc='center',
        bbox_to_anchor=(0.5, -0.1),   # 2% above bottom edge of figure
        # ncol=2,
        ncol=ncols,
    )
    fig.subplots_adjust(bottom=0.60)



def set_scale_ticks(symlog_threshold: int, max_x_value: int = None):
    ax = plt.gca()
    # adding final tick
    ax.set_xscale('symlog', linthresh=symlog_threshold)
    ticks = list(ax.get_xticks())
    if max_x_value is not None:
        ticks.append(max_x_value)
    if symlog_threshold not in ticks:
        ticks.append(symlog_threshold)
    ticks = sorted(ticks)
    
    ax.set_xticks(sorted(set(ticks)))
    ax.set_xticklabels([str(int(t)) if t !=symlog_threshold else '.. lin scale.. '+str(symlog_threshold)+'.. log scale..' for t in ticks])

def plot_HoF_history(df_logbook: pd.DataFrame, outdir: str|None = None, param = "param", extension="pdf", 
                     # palettes: list[str] = ["RdPu", "GnBu", "YlOrRd"],
                     palettes: list[str] = DEFAULT_PALETTES, _figsize:tuple[int, int]=(10, 6),
                     _symlog_threshold: int = 3500):

    """Plot best curves; x-axis is cumulative evaluated individuals when available."""
    sns.set(style='whitegrid')
    plt.figure(figsize=_figsize)

    param_vals:list[str|None] = sorted(df_logbook[param].dropna().unique()) if param in df_logbook.columns else [None]
    directories:list[str|None]= sorted(df_logbook['dir'].dropna().unique()) if 'dir' in df_logbook.columns else [None]

    print(f"The following '{param}' values will be analyzed: {param_vals}")

    has_nevals = 'nevals' in df_logbook.columns and df_logbook['nevals'].notna().any()

    # iterate per (param, experiment, filename) so each curve is one experiment run
    linestyle_cycle = [ '-.',':','-', '--']
    curve_count = 0

    # plt.ion()

    max_x_value = 0

    color_maps = get_colormaps(palettes, param_vals, directories)
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

    set_scale_ticks(_symlog_threshold, max_x_value=max_x_value)

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
    plt.show()
    # plt.close()
    print(f"Saved logbook curves to {figpath}")

 
def plot_HoF_confidence(df_logbook: pd.DataFrame, outdir: str|None = None, param: str = "param", ci: float = 1.0,  alpha: float = 0.12, extension: str = "pdf",
                        # palettes: list[str]=["RdPu", "GnBu", "YlOrRd"],
                        palettes: list[str] = DEFAULT_PALETTES, _figsize:tuple[int, int]=(10, 6), 
                        _symlog_threshold: int =50):

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
    param_vals:list[str|None] = sorted(df_logbook[param].dropna().unique()) if param in df_logbook.columns else [None]
    directories:list[str|None]= sorted(df_logbook['dir'].dropna().unique()) if 'dir' in df_logbook.columns else [None]

    color_maps = get_colormaps(palettes, param_vals, directories)

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
            plt.plot(gens, means, color=color, label=str(p))
            plt.fill_between(gens, lower, upper, color=color, alpha=alpha)

    set_scale_ticks(_symlog_threshold, max_x_value=max_gens)
    plt.xlabel('Generation')
    plt.ylabel('Best (mean) fitness')
    plt.title(f'Confidence intervals ({"mean +-" + str(ci) + ' std'})')

    get_legend(param_vals, directories, color_maps)

    plt.tight_layout()
    figpath = os.path.join(save_dir, f'logbooks_confidence_std_{ci}.' + extension)
    plt.savefig(  figpath, format=extension, bbox_inches="tight" )
    plt.show()
    plt.close()
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
                         # palettes:list[str]=["RdPu", "YlOrRd", "GnBu"],
                         palettes: list[str] = DEFAULT_PALETTES, _figsize:tuple[int,int]=(14, 6)
                         ):

    """Create side-by-side boxplots: (1) solution quality per group, (2) runtime per group.

    - `group_by` is the column name used to group runs (defaults to 'param').
    """
    import seaborn as sns
    import matplotlib.pyplot as plt

    if df_summary is None or df_summary.empty:
        print('No per-run summary available for boxplots.')
        return

    # print(df_summary)
    # expanding or truncating list of group vars
    if 'param' in group_by:
        group_by.extend(c for c in df_summary.columns if c.startswith('param') and c!='param')
    # df_summary.dropna(axis=1) #remooving missing cols. 'param' can be one of them
    for grpb in group_by:
        if grpb not in df_summary.columns or df_summary[grpb].isna().all():
            group_by.remove(grpb)
    df_summary['multigroup'] = df_summary[group_by].agg(', '.join, axis=1).str.strip()
    # print(df_summary)

    directories:list[str|None]= sorted(df_summary['dir'].dropna().unique()) if 'dir' in df_summary.columns else [None]

    if len(group_by)>2:
        raise NotImplemented("Support of more than 2 grouping vars is not yet implemented.")

    print("Boxplots: the following subgroups will be analyzed: 'multigroup' <-- ", *group_by)

    os.makedirs(outdir, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=_figsize)

    ## prepare data for quality boxplot
    # quality_df = df_summary[[*group_by, 'hof_best']].dropna()
    # counts = quality_df.groupby(group_by).size()
    # # filter by min_samples
    # valid_groups = counts[counts >= min_samples][group_by]
    # if not valid_groups:
    #     print('No groups with enough samples for boxplot (min_samples=%d)' % min_samples)
    #     return
    # quality_df = quality_df[quality_df[group_by].isin(valid_groups)]
    quality_df = df_summary
    

    # left plot: fitness
    # for i_dir, dir in enumerate(directories):
        # use same palette as other plots for consistent coloring
    # subgr = quality_df[quality_df[group_by[0]]==dir]
    # subgroups = sorted(subgr[group_by[-1]].unique())

    # palette = sns.color_palette(palette=palettes[i_dir % len(palettes)], n_colors=max(3, len(subgroups)))
    
    # palettes = get_colormaps(palettes, df_summary[group_by[-1]].tolist(), directories)


    aggregated_palettes = {
        dir: sns.color_palette(palettes[i % len(palettes)], 9)[5] for i, dir in enumerate(directories)
    }
    
    # groups = sorted(quality_df['multigroup'].unique())
    # palette = sns.color_palette(palette=palettes[0], n_colors=max(3, len(groups)))
    sns.boxplot(x=group_by[-1], y='hof_best', data=quality_df, ax=axes[0], 
                    hue="dir",
                    dodge=True,
                    palette=aggregated_palettes)
    sns.stripplot(x=group_by[-1],
                   y='hof_best', 
                   data=quality_df, 
                   hue="dir",
                    dodge=True,
                    # palette=aggregated_palettes,
                   ax=axes[0], 
                   color='k',
                     size=4, 
                     jitter=True, 
                     alpha=0.6)
    axes[0].set_title('Hall-of-Fame fitness (per run)')
    axes[0].set_xlabel(group_by)
    axes[0].set_ylabel('Fitness')

    # # annotate counts
    # # xticks = axes[0].get_xticks()
    # for i, grp in enumerate(valid_groups):
    #     n = int(counts.get(grp, 0))
    #     axes[0].text(i, 0.98, f'n={n}', transform=axes[0].get_xaxis_transform(), ha='center', va='top')


    # Right plot:
    # runtime boxplot
    if 'duration_s' in df_summary.columns and df_summary['duration_s'].notna().any():

        # runtimes = df_summary[df_summary[group_by[0]]==dir] [[*group_by, 'duration_s']].dropna()
        runtimes = df_summary[[*group_by, 'duration_s']].dropna()
        # runtimes = runtimes[runtimes[group_by].isin(valid_groups)]


        ## same as on the left plot, see above
        # subgr = quality_df[quality_df[group_by[0]]==dir]
        # subgroups = sorted(subgr[group_by[-1]].unique())
        # palette = sns.color_palette(palette=palettes[i_dir % len(palettes)], n_colors=max(3, len(subgroups)))

        # special case: evaluations as time proxy
        if time_unit == 'eval':
                runtimes['duration_unit'] = runtimes['duration_s']
                label_unit = 'evaluations'
        else:
                # convert units
                factor = 1.0
                label_unit = 's'
                if time_unit == 'm':
                    factor = 60.0
                    label_unit = 'min'
                elif time_unit == 'h':
                    factor = 3600.0
                    label_unit = 'h'
                runtimes['duration_unit'] = runtimes['duration_s'] / factor

        # reuse same RdPu palette for runtime plot as well
        sns.boxplot(x=group_by[-1], y='duration_unit', data=runtimes, ax=axes[1],
                    dodge=True, 
                    hue = group_by[0],
                    palette=aggregated_palettes)
        sns.stripplot(x=group_by[-1], y='duration_unit', data=runtimes, ax=axes[1],
                      dodge=True,
                        hue = group_by[0],
                        color='k', size=4, jitter=True, alpha=0.6)


        axes[1].set_title('Run duration per run')
        axes[1].set_xlabel(group_by)
        axes[1].set_ylabel(f'Duration ({label_unit})')
        if log_time and time_unit != 'eval':
            axes[1].set_yscale('log')
    else:
        axes[1].text(0.5, 0.5, 'No duration data available', ha='center', va='center')
        axes[1].set_axis_off()

    ############### Legend #####################################
    # remove legends generated by seaborn
    for ax in axes:
        leg = ax.get_legend()
        if leg is not None:
            leg.remove()

    # # build one shared legend
    handles, labels = axes[0].get_legend_handles_labels()

    unique = {}
    for h, l in zip(handles, labels):
        if l not in unique:
            # unique[l[l.rfind('\\')+1:]] = h
            unique[l] = h

    fig.legend(
        unique.values(),
        unique.keys(),
        title="Subgroups",
        loc="lower center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=1
    )

    fig.subplots_adjust(bottom=0.25)
    ##########################################################

    plt.tight_layout()
    figpath = os.path.join(outdir, f'boxplot_summary.{extension}')
    plt.savefig(  figpath, format=extension, bbox_inches="tight" )
    plt.show()
    # plt.close()
    print(f'Saved boxplot summary to {figpath}')



if __name__ == '__main__':
    print("Backend:", matplotlib.get_backend())
    main()
