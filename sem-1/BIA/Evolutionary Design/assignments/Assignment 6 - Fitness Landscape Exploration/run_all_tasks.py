#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all_tasks.py: Master Pipeline Orchestrator for Assignment 6.

Executes the complete, end-to-end fitness landscape exploration pipeline
across 4 genetic encodings (f0, f1, f4, fH):

  Stage 1: Evolution (Climbing Run: 48 runs x 600 generations per encoding)
  Stage 2: Optimization Analysis (HoF history, confidence curves, boxplot summary)
  Stage 3: Task 1 - 1-Step Mutational Neighborhood Probing & Topology Analysis
  Stage 4: Task 2 - Crossover Recombination Landscape Exploration (500 pairs x 8 offspring)
  Stage 5: Task 3 - Sequential Chained Random Walks (30 steps x 20 stratified parents)

All results, statistics, plots, tables, and raw data are output into the target
subfolder (default: "rerun 600") preserving the canonical directory layout:
  <out_base>/Task1/runs/<timestamp>/...
  <out_base>/Task1/stats/<timestamp>/...
  <out_base>/Task1/results/optimization/...
  <out_base>/Task1/results/landscape/...
  <out_base>/Task2/results/crossover/...
  <out_base>/Task3/results/random_walks/...

Usage:
  # 1. Full dry-run verification:
  python run_all_tasks.py --dry-run

  # 2. Complete execution with 600 generations (default):
  python run_all_tasks.py --generations 600 --workers 24

  # 3. Modular execution (e.g., re-running only tasks 1, 2, and 3 from existing stats):
  python run_all_tasks.py --stages task1 task2 task3

  # 4. Plot-only mode (re-generating all figures/tables without running simulations):
  python run_all_tasks.py --stages task1 task2 task3 --plot-only
"""

import os
import sys
import time
import glob
import shutil
import argparse
import datetime
import subprocess
from typing import List, Dict, Any, Optional

# Setup directories
ASSIGNMENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(ASSIGNMENT_DIR, "..", ".."))

SCRIPT_RUN_PARALLEL = os.path.join(REPO_ROOT, "scripts", "run_parallel.py")
SCRIPT_EVOLUTION = os.path.join(REPO_ROOT, "scripts", "FramsticksEvolutionScheduled.py")
SCRIPT_ANALYZE_HOF = os.path.join(REPO_ROOT, "scripts", "analyze_hof.py")
SCRIPT_TASK1 = os.path.join(ASSIGNMENT_DIR, "task1", "analyze_fitness_landscape.py")
SCRIPT_TASK1_TABLE = os.path.join(ASSIGNMENT_DIR, "task1", "generate_landscape_table.py")
SCRIPT_TASK2 = os.path.join(ASSIGNMENT_DIR, "task2", "analyze_crossover.py")
SCRIPT_TASK3 = os.path.join(ASSIGNMENT_DIR, "task3", "analyze_random_walks.py")

DEFAULT_OUT_BASE = os.path.join(ASSIGNMENT_DIR, "rerun 600")
DEFAULT_FRAMS_PATH = os.path.join(REPO_ROOT, "Framsticks55")
DEFAULT_SIM = "eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim"


def log_banner(title: str, fill: str = "="):
    line = fill * 80
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n", flush=True)


def find_latest_stats_dir(stats_base: str) -> Optional[str]:
    """Finds the most recent directory containing .logbook.pkl files."""
    if not os.path.isdir(stats_base):
        return None

    # Check if files exist directly in stats_base
    direct_files = glob.glob(os.path.join(stats_base, "*.logbook.pkl"))
    if direct_files:
        return stats_base

    # Otherwise search subfolders sorted by modification time
    subdirs = [os.path.join(stats_base, d) for d in os.listdir(stats_base) if os.path.isdir(os.path.join(stats_base, d))]
    subdirs.sort(key=lambda d: os.path.getmtime(d), reverse=True)

    for sd in subdirs:
        if glob.glob(os.path.join(sd, "*.logbook.pkl")):
            return sd

    return None


def run_command(cmd: List[str], desc: str, dry_run: bool = False, cwd: str = REPO_ROOT) -> int:
    """Executes a command with pretty logging and error handling."""
    print(f"[CMD] {desc}")
    print(f"      {' '.join(cmd)}\n", flush=True)

    if dry_run:
        print("      [DRY-RUN] Command skipped.")
        return 0

    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=cwd, check=True)
        elapsed = time.time() - t0
        print(f"\n[DONE] {desc} completed in {elapsed:.1f}s (Exit code: {proc.returncode})\n", flush=True)
        return proc.returncode
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Command failed with exit code {e.returncode}: {desc}", file=sys.stderr)
        raise e


def main():
    parser = argparse.ArgumentParser(
        description="Assignment 6: Master Pipeline Orchestrator (Evolution + Tasks 1, 2, 3)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Global paths and directories
    parser.add_argument("--out-base", default=DEFAULT_OUT_BASE,
                        help="Base output folder for all rerun deliverables (e.g. 'rerun 600')")
    parser.add_argument("--frams-path", default=DEFAULT_FRAMS_PATH,
                        help="Path to Framsticks library folder")
    parser.add_argument("--python-exec", default=sys.executable,
                        help="Python executable to invoke sub-scripts")
    parser.add_argument("--workers", type=int, default=min(os.cpu_count() or 1, 24),
                        help="Number of parallel worker processes")

    # Evolutionary simulation parameters
    parser.add_argument("--generations", type=int, default=600,
                        help="Number of generations for evolutionary climb")
    parser.add_argument("--popsize", type=int, default=100,
                        help="Population size for evolutionary climb")
    parser.add_argument("--num-experiments", type=int, default=48,
                        help="Number of independent evolutionary runs per encoding")
    parser.add_argument("--tournament", type=int, default=5,
                        help="Tournament selection size")
    parser.add_argument("--pxov", type=float, default=0.0,
                        help="Crossover probability during evolution climb (0.0 = pure mutation climb)")
    parser.add_argument("--pmut", type=float, default=0.9,
                        help="Mutation probability during evolution climb")
    parser.add_argument("--max-numparts", type=int, default=30,
                        help="Maximum structural parts limit")
    parser.add_argument("--opt", default="velocity",
                        help="Optimization criterion target")
    parser.add_argument("--sim", default=DEFAULT_SIM,
                        help="Simulation environment settings string")
    parser.add_argument("--genformats", nargs="+", default=["0", "1", "4", "H"],
                        help="Genetic formats to evaluate")

    # Task-specific sample parameters
    parser.add_argument("--task1-samples", type=int, default=200,
                        help="Number of parents sampled for Task 1 landscape probing")
    parser.add_argument("--task1-mutants", type=int, default=20,
                        help="Number of mutants evaluated per parent in Task 1")
    parser.add_argument("--task2-rounds", type=int, default=5,
                        help="Number of shuffle rounds for Task 2 crossover (5 rounds x 100 pairs = 500 pairs)")
    parser.add_argument("--task2-reps", type=int, default=4,
                        help="Reps per reciprocal direction in Task 2 (4 reps x 2 directions = 8 offspring/pair)")
    parser.add_argument("--task3-parents", type=int, default=20,
                        help="Number of stratified parents sampled for Task 3 random walk")
    parser.add_argument("--task3-steps", type=int, default=30,
                        help="Number of sequential chained mutation steps for Task 3 random walk")

    # Pipeline control & stages
    parser.add_argument("--stages", nargs="+", default=["all"],
                        choices=["all", "evolution", "optimization", "task1", "task2", "task3"],
                        help="Stages to execute: all, evolution, optimization, task1, task2, task3")
    parser.add_argument("--stats-dir", default=None,
                        help="Explicit stats directory containing .logbook.pkl files (auto-detected if omitted)")
    parser.add_argument("--task1-dir", default=None,
                        help="Explicit Task 1 landscape directory (auto-detected if omitted)")
    parser.add_argument("--timestamp", default=None,
                        help="Custom timestamp string for stats/runs (defaults to current datetime)")
    parser.add_argument("--plot-only", action="store_true",
                        help="Skip simulation probing and regenerate plots and summary tables from existing CSVs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate directories and display all commands without executing simulations")

    args = parser.parse_args()

    # Determine active stages
    active_stages = set(args.stages)
    run_all = "all" in active_stages
    do_evolution = run_all or "evolution" in active_stages
    do_opt = run_all or "optimization" in active_stages or "evolution" in active_stages
    do_task1 = run_all or "task1" in active_stages
    do_task2 = run_all or "task2" in active_stages
    do_task3 = run_all or "task3" in active_stages

    # Generate or reuse timestamp
    timestamp = args.timestamp or datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")

    # Canonical Directory Hierarchy
    out_base = os.path.abspath(args.out_base)
    task1_dir = os.path.join(out_base, "Task1")
    task2_dir = os.path.join(out_base, "Task2")
    task3_dir = os.path.join(out_base, "Task3")

    runs_base = os.path.join(task1_dir, "runs")
    stats_base = os.path.join(task1_dir, "stats")
    
    if do_evolution:
        target_stats_dir = args.stats_dir or os.path.join(stats_base, timestamp)
    elif args.stats_dir:
        target_stats_dir = os.path.abspath(args.stats_dir)
    else:
        # Auto-detect existing stats in out_base or fallback to original Task 1 stats
        detected = find_latest_stats_dir(stats_base)
        if detected:
            target_stats_dir = detected
        else:
            fallback = os.path.join(ASSIGNMENT_DIR, "task1", "stats", "2026-10-24_19")
            target_stats_dir = fallback if os.path.isdir(fallback) else os.path.join(stats_base, timestamp)

    opt_results_dir = os.path.join(task1_dir, "results", "optimization")
    opt_plots_dir = os.path.join(opt_results_dir, "plots")
    landscape_results_dir = args.task1_dir or os.path.join(task1_dir, "results", "landscape")
    crossover_results_dir = os.path.join(task2_dir, "results", "crossover")
    random_walks_results_dir = os.path.join(task3_dir, "results", "random_walks")

    # Create destination directories
    for d in [out_base, task1_dir, task2_dir, task3_dir, runs_base, stats_base,
              opt_results_dir, opt_plots_dir, landscape_results_dir,
              crossover_results_dir, random_walks_results_dir]:
        if not args.dry_run:
            os.makedirs(d, exist_ok=True)

    log_banner("Assignment 6: Master Pipeline Orchestrator")
    print(f"Target Output Base:     {out_base}")
    print(f"Evolution Generations:  {args.generations}")
    print(f"Active Stages:          {[s for s in ['evolution', 'optimization', 'task1', 'task2', 'task3'] if (run_all or s in active_stages)]}")
    print(f"Target Stats Directory: {target_stats_dir}")
    print(f"Task 1 Landscape Dir:   {landscape_results_dir}")
    print(f"Task 2 Crossover Dir:   {crossover_results_dir}")
    print(f"Task 3 Random Walk Dir: {random_walks_results_dir}")
    print(f"Parallel Workers:       {args.workers}")
    print(f"Dry-Run Mode:           {args.dry_run}")
    print(f"Plot-Only Mode:         {args.plot_only}\n")

    pipeline_start_time = time.time()

    # --------------------------------------------------------------------------
    # STAGE 1: Evolution (Climbing Run)
    # --------------------------------------------------------------------------
    if do_evolution:
        log_banner(f"STAGE 1: Evolutionary Climb ({args.num_experiments} runs x {args.generations} gens per encoding)")
        evo_cmd = [
            args.python_exec, SCRIPT_RUN_PARALLEL,
            "--script", SCRIPT_EVOLUTION,
            "--frams-path", args.frams_path,
            "--sim", args.sim,
            "--opt", args.opt,
            "--max-numparts", str(args.max_numparts),
            "--popsize", str(args.popsize),
            "--generations", str(args.generations),
            "--tournament", str(args.tournament),
            "--pxov", str(args.pxov),
            "--pmut", str(args.pmut),
            "--genformats", *args.genformats,
            "--num-experiments", str(args.num_experiments),
            "--workers", str(args.workers),
            "--out", runs_base,
            "--stats-dir", target_stats_dir
        ]
        if args.dry_run:
            evo_cmd.append("--dry-run")
        run_command(evo_cmd, "Parallel Evolutionary Climb", dry_run=args.dry_run)

    # --------------------------------------------------------------------------
    # STAGE 2: Optimization Analysis (HoF history, confidence curves, boxplot summary)
    # --------------------------------------------------------------------------
    if do_opt:
        log_banner("STAGE 2: Optimization Analysis & HoF Convergence Curves")
        opt_cmd = [
            args.python_exec, SCRIPT_ANALYZE_HOF,
            "--logbook-dirs", target_stats_dir,
            "--outdir", opt_results_dir,
            "--group-by", "enc",
            "--time-unit", "s",
            "--headless"
        ]
        run_command(opt_cmd, "Analyze HoF & Generate Optimization Plots", dry_run=args.dry_run)

    # --------------------------------------------------------------------------
    # STAGE 3: Task 1 - Fitness Landscape Neighborhood Probing
    # --------------------------------------------------------------------------
    if do_task1:
        log_banner(f"STAGE 3: Task 1 - Fitness Landscape Probing ({args.task1_samples} parents x {args.task1_mutants} mutants)")
        task1_cmd = [
            args.python_exec, SCRIPT_TASK1,
            "--stats-dir", target_stats_dir,
            "--out-dir", landscape_results_dir,
            "--frams-path", args.frams_path,
            "--sim", args.sim,
            "--opt", args.opt,
            "--formats", *args.genformats,
            "--num-samples", str(args.task1_samples),
            "--num-mutants", str(args.task1_mutants),
            "--workers", str(args.workers)
        ]
        if args.plot_only:
            task1_cmd.append("--plot-only")

        run_command(task1_cmd, "Task 1 Landscape Probing & Analysis", dry_run=args.dry_run)

        # Generate reorganized compact landscape metrics table
        task1_table_cmd = [
            args.python_exec, SCRIPT_TASK1_TABLE,
            "--landscape-dir", landscape_results_dir,
            "--out-dir", landscape_results_dir
        ]
        run_command(task1_table_cmd, "Task 1 Reorganized Landscape Metrics Table", dry_run=args.dry_run)

    # --------------------------------------------------------------------------
    # STAGE 4: Task 2 - Crossover Recombination Landscape Exploration
    # --------------------------------------------------------------------------
    if do_task2:
        log_banner(f"STAGE 4: Task 2 - Crossover Recombination Exploration ({args.task2_rounds*100} pairs x {args.task2_reps*2} offspring)")
        task2_cmd = [
            args.python_exec, SCRIPT_TASK2,
            "--task1-dir", landscape_results_dir,
            "--out-dir", crossover_results_dir,
            "--frams-path", args.frams_path,
            "--sim-settings", args.sim,
            "--formats", *args.genformats,
            "--shuffle-rounds", str(args.task2_rounds),
            "--reps", str(args.task2_reps),
            "--workers", str(args.workers)
        ]
        if args.plot_only:
            task2_cmd.append("--plot-only")

        run_command(task2_cmd, "Task 2 Crossover Recombination Analysis", dry_run=args.dry_run)

    # --------------------------------------------------------------------------
    # STAGE 5: Task 3 - Sequential Chained Random Walks
    # --------------------------------------------------------------------------
    if do_task3:
        log_banner(f"STAGE 5: Task 3 - Sequential Random Walks ({args.task3_parents} parents x {args.task3_steps} steps)")
        task3_cmd = [
            args.python_exec, SCRIPT_TASK3,
            "--stats-dir", target_stats_dir,
            "--out-dir", random_walks_results_dir,
            "--frams-path", args.frams_path,
            "--sim-settings", args.sim,
            "--formats", *args.genformats,
            "--num-parents", str(args.task3_parents),
            "--walk-steps", str(args.task3_steps),
            "--workers", str(args.workers)
        ]
        if args.plot_only:
            task3_cmd.append("--plot-only")

        run_command(task3_cmd, "Task 3 Random Walk Fitness Landscape Exploration", dry_run=args.dry_run)

    # --------------------------------------------------------------------------
    # Final Execution Summary
    # --------------------------------------------------------------------------
    total_time = time.time() - pipeline_start_time
    log_banner("ASSIGNMENT 6 PIPELINE EXECUTION COMPLETE")
    print(f"Total Pipeline Duration: {total_time:.1f}s ({total_time/60.0:.2f} min)")
    print(f"All deliverables successfully saved to:\n  {out_base}")
    print("\nDeliverables Directory Summary:")
    print(f"  Task 1 Optimization Plots: {opt_plots_dir}")
    print(f"  Task 1 Landscape Probing:  {landscape_results_dir}")
    print(f"  Task 2 Crossover Analysis: {crossover_results_dir}")
    print(f"  Task 3 Random Walk Plots:  {random_walks_results_dir}\n")


if __name__ == "__main__":
    main()
