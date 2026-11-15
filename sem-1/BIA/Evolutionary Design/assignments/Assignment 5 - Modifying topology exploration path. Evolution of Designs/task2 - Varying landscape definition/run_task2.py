"""
Task 2 in Assignment 5: Varying landscape definition
Evaluating walking creatures from walking.gen with varying perfperiod values.
"""

import sys
import os
import argparse
import csv
import json
import matplotlib.pyplot as plt
import numpy as np

def find_evolutionary_design_dir():
    """
    Locates the 'Evolutionary Design' folder containing 'framspy-download' and 'Framsticks*'.
    """
    curr = os.path.dirname(os.path.abspath(__file__))
    while curr:
        if os.path.isdir(os.path.join(curr, "framspy-download")) or os.path.basename(curr) == "Evolutionary Design":
            return curr
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    # Fallback to relative path: ../../..
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


EVO_DESIGN_DIR = find_evolutionary_design_dir()
sys.path.append(os.path.join(EVO_DESIGN_DIR, "framspy-download"))

from FramsticksLib import FramsticksLib
import frams


def get_latest_framsticks_dir(evo_dir):
    """
    Finds the latest FramsticksXY directory within Evolutionary Design (e.g. Framsticks55, Framsticks56).
    """
    if not os.path.isdir(evo_dir):
        raise FileNotFoundError(f"Evolutionary Design directory does not exist: {evo_dir}")
    candidates = [
        os.path.join(evo_dir, d) for d in os.listdir(evo_dir)
        if os.path.isdir(os.path.join(evo_dir, d)) and d.lower().startswith("framsticks")
    ]
    if not candidates:
        raise FileNotFoundError(
            f"Could not find any 'FramsticksXY' directory in '{evo_dir}'. Please ensure Framsticks is uncompressed there."
        )
    candidates.sort()  # Sort to pick the latest version (e.g. Framsticks55)
    return candidates[-1]


def parse_gen_file(file_path, limit=28):
    creatures = []
    current = {}
    in_genotype_multiline = False
    multiline_geno = []
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_str = line.rstrip("\r\n")
            if in_genotype_multiline:
                if line_str.endswith("~"):
                    multiline_geno.append(line_str[:-1])
                    current["genotype"] = "\n".join(multiline_geno)
                    in_genotype_multiline = False
                    multiline_geno = []
                else:
                    multiline_geno.append(line_str)
                continue
            
            if line_str.startswith("org:"):
                if "genotype" in current:
                    creatures.append(current)
                    if limit and len(creatures) >= limit:
                        break
                current = {}
            elif line_str.startswith("name:"):
                current["name"] = line_str[5:].strip()
            elif line_str.startswith("genotype:"):
                geno_val = line_str[9:].strip()
                if geno_val.startswith("~"):
                    if geno_val.endswith("~") and len(geno_val) > 1 and not (len(geno_val) == 2 and geno_val == "~~"):
                        current["genotype"] = geno_val[1:-1]
                    else:
                        in_genotype_multiline = True
                        multiline_geno = [geno_val[1:]] if len(geno_val) > 1 else []
                else:
                    current["genotype"] = geno_val
        if "genotype" in current and (not limit or len(creatures) < limit):
            creatures.append(current)
            
    # Fallback names if missing
    for idx, c in enumerate(creatures):
        if "name" not in c or not c["name"]:
            c["name"] = f"Creature_{idx+1}"
    return creatures


def main():
    evo_dir = find_evolutionary_design_dir()
    latest_frams_dir = get_latest_framsticks_dir(evo_dir)

    parser = argparse.ArgumentParser(description="Evaluate walking structures under varying perfperiod.")
    parser.add_argument("--frams-path", default=latest_frams_dir, help="Path to Framsticks distribution (defaults to latest FramsticksXY)")
    parser.add_argument("--gen-file", default=None, help="Path to walking.gen (defaults to <frams-path>/data/walking.gen)")
    parser.add_argument("--num-creatures", type=int, default=28, help="Number of creatures to evaluate (default 28)")
    parser.add_argument("--perfperiods", nargs="+", type=int, default=[1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2000, 5000, 10000], help="List of perfperiod values to test")
    parser.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)), help="Output directory for results and plots")
    args = parser.parse_args()

    # Validate Framsticks directory existence
    if not os.path.isdir(args.frams_path):
        raise FileNotFoundError(f"Framsticks directory does not exist: {args.frams_path}")

    # Resolve gen-file if not explicitly passed
    if args.gen_file is None:
        args.gen_file = os.path.join(args.frams_path, "data", "walking.gen")

    if not os.path.isfile(args.gen_file):
        raise FileNotFoundError(f"Genotypes file does not exist: {args.gen_file}")

    os.makedirs(args.outdir, exist_ok=True)

    print(f"Detected latest Framsticks directory: {args.frams_path}")
    print(f"Loading creatures from {args.gen_file}...")
    creatures = parse_gen_file(args.gen_file, limit=args.num_creatures)
    print(f"Loaded {len(creatures)} creatures.")

    print(f"Initializing Framsticks from {args.frams_path}...")
    frams_lib = FramsticksLib(args.frams_path, None, "eval-allcriteria.sim;deterministic.sim")

    genotypes = [c["genotype"] for c in creatures]
    perfperiods = sorted(args.perfperiods)

    # Dictionary to store results: {pp: [vel_c1, vel_c2, ...]}
    velocity_data = {pp: [] for pp in perfperiods}
    distance_data = {pp: [] for pp in perfperiods}
    all_rows = []

    print(f"\nBeginning evaluation across perfperiod values: {perfperiods}\n")
    for pp in perfperiods:
        print(f"--> Evaluating {len(creatures)} creatures with frams.Populations[0].perfperiod = {pp}...")
        frams.Populations[0].perfperiod = pp
        eval_results = frams_lib.evaluate(genotypes)

        for idx, res in enumerate(eval_results):
            c_name = creatures[idx]["name"]
            try:
                eval_dict = res["evaluations"][""]
                vel = eval_dict.get("velocity", 0.0)
                dist = eval_dict.get("distance", 0.0)
                vertpos = eval_dict.get("vertpos", 0.0)
                vertvel = eval_dict.get("vertvel", 0.0)
            except Exception as e:
                print(f"Warning: Failed to extract stats for creature {idx+1} ({c_name}): {e}")
                vel, dist, vertpos, vertvel = 0.0, 0.0, 0.0, 0.0

            velocity_data[pp].append(vel)
            distance_data[pp].append(dist)
            all_rows.append({
                "creature_index": idx + 1,
                "creature_name": c_name,
                "perfperiod": pp,
                "velocity": vel,
                "distance": dist,
                "vertpos": vertpos,
                "vertvel": vertvel
            })

    # Save to CSV
    csv_path = os.path.join(args.outdir, "task2_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["creature_index", "creature_name", "perfperiod", "velocity", "distance", "vertpos", "vertvel"])
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nSaved raw data to {csv_path}")

    # Generate Primary Plot
    # Horizontal axis = individual genotypes, Vertical axis = "velocity" for different frams.Populations[0].perfperiod
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, ax = plt.subplots(figsize=(16, 8), dpi=300)

    x_indices = np.arange(len(creatures))
    # Labels: index + short name
    x_labels = [f"#{i+1} {c['name'][:18]}" for i, c in enumerate(creatures)]

    colors = plt.cm.viridis(np.linspace(0.1, 0.95, len(perfperiods)))
    markers = ['o', 's', '^', 'D', 'v', 'p', '*']

    for i, pp in enumerate(perfperiods):
        marker = markers[i % len(markers)]
        color = colors[i]
        label = f"perfperiod = {pp}"
        if pp in (1, 2):
            label += " (path/odometry)"
        elif pp == 100:
            label += " (default)"
        elif pp == 10000:
            label += " (rectilinear displacement / lifespan)"
        
        ax.plot(x_indices, velocity_data[pp], marker=marker, markersize=6, linewidth=1.8, 
                label=label, color=color, alpha=0.9)

    ax.set_title("Velocity vs. Individual Genotypes under Varying Performance Sampling Periods (`perfperiod`)", 
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Individual Genotypes (walking.gen creatures)", fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel("Measured Velocity", fontsize=12, fontweight='bold', labelpad=10)
    ax.set_xticks(x_indices)
    ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=9)
    ax.legend(title="Sampling Period (`perfperiod`)", fontsize=10, title_fontsize=11, frameon=True)
    ax.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()

    def safe_savefig(figure, path):
        tmp_path = path + ".tmp.png"
        figure.savefig(tmp_path)
        for _ in range(5):
            try:
                if os.path.exists(path):
                    os.remove(path)
                os.replace(tmp_path, path)
                return
            except Exception:
                import time
                time.sleep(0.3)
        try:
            os.replace(tmp_path, path)
        except Exception:
            pass

    plot_path = os.path.join(args.outdir, "velocity_vs_perfperiod.png")
    safe_savefig(fig, plot_path)
    plt.close(fig)
    print(f"Saved primary plot to {plot_path}")

    # Generate Auxiliary Plot: Rectilinear Locomotion Ratio (Straightness Index)
    # Ratio = Velocity at pp_max / Velocity at pp_min
    pp_min = perfperiods[0]
    pp_max = perfperiods[-1]
    ratios = []
    names = []
    for idx in range(len(creatures)):
        v_short = velocity_data[pp_min][idx]
        v_long = velocity_data[pp_max][idx]
        ratio = (v_long / v_short) if v_short > 1e-6 else 0.0
        ratios.append(min(1.0, max(0.0, ratio)))
        names.append(f"#{idx+1} {creatures[idx]['name'][:16]}")

    sorted_indices = np.argsort(ratios)
    sorted_ratios = [ratios[i] for i in sorted_indices]
    sorted_names = [names[i] for i in sorted_indices]

    fig2, ax2 = plt.subplots(figsize=(14, 8), dpi=300)
    bars = ax2.barh(np.arange(len(sorted_ratios)), sorted_ratios, color=plt.cm.coolwarm(sorted_ratios), edgecolor='black', alpha=0.85)
    ax2.set_yticks(np.arange(len(sorted_ratios)))
    ax2.set_yticklabels(sorted_names, fontsize=9)
    ax2.set_xlabel(f"Rectilinear Locomotion Ratio ($v_{{\\mathrm{{net}}}} / v_{{\\mathrm{{path}}}} = v_{{{pp_max}}} / v_{{{pp_min}}}$)", fontsize=12, fontweight='bold', labelpad=10)
    ax2.set_title(f"Locomotion Straightness Ratio ($v_{{{pp_max}}} / v_{{{pp_min}}}$): Straight Walkers vs. Oscillators/Turners", fontsize=14, fontweight='bold', pad=15)
    ax2.set_xlim(0, 1.05)
    ax2.axvline(0.5, color='gray', linestyle=':', alpha=0.7)
    ax2.grid(True, linestyle='--', alpha=0.5, axis='x')

    # Value labels on bars
    for bar in bars:
        w = bar.get_width()
        ax2.text(w + 0.01, bar.get_y() + bar.get_height() / 2, f"{w:.2f}", va='center', fontsize=8)

    plt.tight_layout()
    ratio_plot_path = os.path.join(args.outdir, "locomotion_straightness_ratio.png")
    safe_savefig(fig2, ratio_plot_path)
    plt.close(fig2)
    print(f"Saved straightness ratio plot to {ratio_plot_path}")

    print("\nExperiment completed successfully!")


if __name__ == "__main__":
    main()
