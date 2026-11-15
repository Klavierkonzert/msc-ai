#!/usr/bin/env python3
"""
Run FramsticksEvolution experiments in parallel using the exact PowerShell-style
argument layout you provided.

This runner only uses the arguments present in your template command and builds
commands of the form:

  python <scriptPath> \
    -path <framsPath> \
    -sim <sim> \
    -opt vertpos \
    -max_numparts 30 \
    -initialgenotype '/*9*/BLU' \

    -popsize 50 \
    -generations 50 \
    -hof_size 1 \
    -hof_savefile runs/<timestamp>/gens/HoF-f9-{M}-{N}.gen \
    --save-stats <statsPath>

Usage:
  python scripts/run_parallel.py --script framspy-download/FramsticksEvolution.py \
      --frams-path C:/.../Framsticks55 --sim eval-allcriteria.sim \
      --mutintensities 0 0.05 0.1 --num-experiments 3 --stats-dir stats \
      --python-exec C:/Users/.../.conda/envs/framsticks/python.exe --workers 8

The script saves each job's log and Hall-of-Fame genotype under the same run:
`runs/<timestamp>/logs/HoF-f9-{M}-{N}.log` and
`runs/<timestamp>/gens/HoF-f9-{M}-{N}.gen`.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import subprocess
import sys
import os
import datetime

import typing
import re

def normalize_genformat(fmt: str | None) -> str | None:
    if fmt is None:
        return None
    s = str(fmt).strip()
    if s.lower().startswith('f') and len(s) > 1:
        return s[1:]
    return s

def format_mut_tag(val: float | str) -> str:
    f_val = float(val)
    if f_val == 0:
        return '0'
    s = f"{f_val:.2f}".replace('.', '')
    if round(f_val, 2) != f_val:
        s = str(f_val).replace('.', '')
    return s

def get_frams_data_dir(frams_path: str) -> str:
    data_dir = os.path.join(frams_path, 'data')
    if os.path.isdir(data_dir):
        return data_dir
    return frams_path

def resolve_sim_path(sim_path: str, frams_path: str | None = None) -> str:
    """Resolves a .sim file path:
    1. Checks the path directly.
    2. Checks subfolders of current working directory: 'sims' and 'sim'.
    3. If present in Framsticks data dir, keeps the relative filename for native Framsticks loading.
    Returns the resolved absolute path (forward slashes) or original filename."""
    if not sim_path:
        return sim_path

    # 1. As provided
    if os.path.exists(sim_path):
        return os.path.abspath(sim_path).replace('\\', '/')

    # 2. Check subfolders 'sims' and 'sim' of current working directory
    cwd = os.getcwd()
    for sub in ('sims', 'sim'):
        cand = os.path.join(cwd, sub, sim_path)
        if os.path.exists(cand):
            return os.path.abspath(cand).replace('\\', '/')

    # 3. If present in Framsticks data dir, let Framsticks resolve it natively
    if frams_path:
        frams_data = get_frams_data_dir(frams_path)
        if os.path.exists(os.path.join(frams_data, sim_path)):
            return sim_path

    return sim_path

def ensure_mutation_sim_file(frams_path: str, genformat: str | int | None, mut_intensity: float | str) -> str:
    """Ensures f{genformat}-mut-{tag}.sim exists in Framsticks data dir, creating it if needed.
    Returns the sim filename (e.g. 'f9-mut-050.sim')."""
    f = genformat if genformat is not None else '9'
    tag = format_mut_tag(mut_intensity)
    filename = f"f{f}-mut-{tag}.sim"

    data_dir = get_frams_data_dir(frams_path)
    file_path = os.path.join(data_dir, filename)

    if not os.path.exists(file_path):
        f_val = float(mut_intensity)
        val_str = f"{f_val}" if f_val != 0 else "0.0"
        content = f"sim_params:\nf{f}_mut:{val_str}\n"
        try:
            with open(file_path, 'w', encoding='utf-8') as fp:
                fp.write(content)
            print(f"Created mutation sim file: {file_path}")
        except Exception as e:
            print(f"Warning: Could not create {file_path}: {e}")

    return filename

def encode_filename(param_value: str | None, idx_experiment: str | int, genformat: str | int | None = '9') -> str:
    f_prefix = f"f{genformat}-" if genformat is not None else ""
    if param_value is not None:
        return f"HoF-{f_prefix}{param_value}-{idx_experiment}"
    return f"HoF-{f_prefix}{idx_experiment}"

def combine_sim_strings(base_sim: str, extra_sim: str | None) -> str:
    parts = [p.strip() for p in (base_sim or '').split(';') if p.strip()]
    if extra_sim:
        parts.extend([p.strip() for p in extra_sim.split(';') if p.strip()])
    return ';'.join(parts)

def build_cmd(python_exec: str, script_path: str, frams_path: str, optimization_target: str, sim: str, stats_dir: str, hof_dir: str, popsize: int, generations: int, tournament: int, 
              param_value: str|None, idx_experiment: int,
              genformat: str|int|None = None, initialgenotype: str|None = None,
              max_numparts: int|None = 30, max_numjoints: int|None = None,
              max_numneurons: int|None = None, max_numconnections: int|None = None,
              max_numgenochars: str|int|None = None,
              pxov: float|None = None, pmut: float|None = None,
              schedule: str|None = None
              ) -> tuple[list[str], str]:
    hof_path = os.path.join(hof_dir, encode_filename(param_value, idx_experiment, genformat) + ".gen")
    cmd: list[str] = [python_exec, script_path,
           '-path', frams_path,
           '-sim', sim,
           '-opt', optimization_target,
           '-popsize', str(popsize),
           '-generations', str(generations),
           '-tournament', str(tournament),
           '-hof_size', '1',
           '-hof_savefile', hof_path,
           '--save-stats', stats_dir]

    if schedule is not None:
        cmd.extend(['--schedule', schedule])

    if max_numparts is not None:
        cmd.extend(['-max_numparts', str(max_numparts)])
    if max_numjoints is not None:
        cmd.extend(['-max_numjoints', str(max_numjoints)])
    if max_numneurons is not None:
        cmd.extend(['-max_numneurons', str(max_numneurons)])
    if max_numconnections is not None:
        cmd.extend(['-max_numconnections', str(max_numconnections)])
    if max_numgenochars is not None:
        cmd.extend(['-max_numgenochars', str(max_numgenochars)])
    if pxov is not None:
        cmd.extend(['-pxov', str(pxov)])
    if pmut is not None:
        cmd.extend(['-pmut', str(pmut)])

    if initialgenotype is not None:
        cmd.extend(['-initialgenotype', initialgenotype])
    elif genformat is not None:
        cmd.extend(['-genformat', str(genformat)])

    return cmd, hof_path



def run_one(cmd, cwd, logfile):
    with open(logfile, 'wb') as lf:
        proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=cwd)
    return proc.returncode

def parse_arg_values_list[T](values: list[T] | str, desired_type: type[T]= str) -> list[T]:
    # Accept space-separated floats or a single comma-separated string
    if not values:
        return []
    out = []
    for v in values:
        if isinstance(v, str) and ',' in v:
            parts = [p.strip() for p in v.split(',') if p.strip()]
            out.extend(parts)
        else:
            out.append(str(v))
    # convert to float/other desired type when possible
    res = []
    for x in out:
        try:
            res.append(desired_type(x))
        except Exception:
            res.append(x)
    return res




def main():
    p = argparse.ArgumentParser()
    p.add_argument('--script', required=True, help='Path to FramsticksEvolution.py')
    p.add_argument('--frams-path', required=True, help='Path to Framsticks library (Framsticks55)')
    p.add_argument('--opt', default='vertpos', help="Target to be optimized. By default, 'vertpos'")
    p.add_argument('--sim', default="eval-allcriteria.sim;deterministic.sim;sample-period-2.sim", help='Sim filename to pass to -sim')
    p.add_argument('--sim-variants', nargs='+', required=False, help='Sim variants/filenames to evaluate in parallel')
    p.add_argument('--schedules', '--schemes', dest='schedules', nargs='+', required=False, help='Schedules in format tag=schedule_str (e.g. sw1=0:sim1.sim;150:sim2.sim)')
    p.add_argument('--mutints', '--mutintensities', '--values', dest='mutints', nargs='+', required=False, help='Mutation intensities (e.g. 0 0.05 0.10). Ignored if --sim-variants is provided.')
    p.add_argument('--num-experiments', type=int, required=True, help='Number of experiments')
    p.add_argument('--popsize', type=int, default=50, help="Population size")
    p.add_argument('--generations', type=int, default=50, help='Number of generations')
    p.add_argument('--tournament', type=int, default=5, help='Number of individuals participating in an tournament')
    p.add_argument('--max-numparts', type=int, default=30, help='Maximum number of parts (default: 30)')
    p.add_argument('--max-numjoints', type=int, default=None, help='Maximum number of joints (default: None)')
    p.add_argument('--max-numneurons', type=int, default=None, help='Maximum number of neurons (default: None)')
    p.add_argument('--max-numconnections', type=int, default=None, help='Maximum number of connections (default: None)')
    p.add_argument('--max-numgenochars', default=None, required=False, help='The maximum number of characters in genotype. Default is unlimited.')
    p.add_argument('--pxov', type=float, default=None, help='Probability of crossover (default: None, FramsticksEvolution default 0.2)')
    p.add_argument('--pmut', type=float, default=None, help='Probability of mutation (default: None, FramsticksEvolution default 0.9)')
    p.add_argument('--stats-dir', default='stats', help='Base folder passed to --save-stats')
    p.add_argument('--out', default='runs', help='Output base folder for timestamped run folders')
    p.add_argument('--workers', type=int, default=os.cpu_count(), help='Parallel workers')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--python-exec', default=sys.executable, help='Python executable used to run FramsticksEvolution.py. Use the framsticks conda env Python when dependencies are installed there.')
    p.add_argument('--genformats', nargs='+', default=['1'], help='Genetic format for the simplest initial genotype, for example 4, 9, or B. If not given, f1 is assumed.')
    p.add_argument('--initialgenotype', required=False, help='The genotype used to seed the initial population. If given, the -genformat argument is ignored.')

    args = p.parse_args()

    script_path = os.path.abspath(args.script)
    frams_path = os.path.abspath(args.frams_path)
    sim = ';'.join([resolve_sim_path(s.strip(), frams_path) for s in (args.sim or '').split(';') if s.strip()])
    stats_dir = os.path.abspath(args.stats_dir)
    out_base = os.path.abspath(args.out)
    os.makedirs(out_base, exist_ok=True)
    os.makedirs(stats_dir, exist_ok=True)

    # Gen format values, e.g. f0, f1, f4, f9, fH, f0s...
    genformat_values: list[str|None]
    if args.initialgenotype is not None:
        print(f"Initial genotype provided: {args.initialgenotype}, skipping all the irrelevant genome formats.")
        found_fmts = re.findall(r'/\*([a-zA-Z0-9_]+)\*/', args.initialgenotype)
        genformat_values = [normalize_genformat(fmt) for fmt in found_fmts] if found_fmts else [None]
    else:
        raw_fmts = parse_arg_values_list(args.genformats, desired_type=str)
        genformat_values = [normalize_genformat(fmt) for fmt in raw_fmts]
    print("Genome format(s):", genformat_values)

    if args.sim_variants is not None:
        print("Sim variants:", parse_arg_values_list(args.sim_variants, desired_type=str))
    elif args.mutints is not None:
        print("Mutation intensity values:", parse_arg_values_list(args.mutints, desired_type=float))

    experiment_idc = [i for i in range(int(args.num_experiments))]

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    run_dir = os.path.join(out_base, timestamp)
    log_dir = os.path.join(run_dir, 'logs')
    gens_dir = os.path.join(run_dir, 'gens')
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(gens_dir, exist_ok=True)

    python_exec = os.path.abspath(args.python_exec)

    jobs: list[tuple[list[str], str, str, str]] = []

    for f in genformat_values:
        if args.schedules is not None:
            variants = []
            for s in parse_arg_values_list(args.schedules, desired_type=str):
                if '=' in s:
                    t, sched = s.split('=', 1)
                else:
                    t = f"sched{len(variants)+1}"
                    sched = s
                norm_parts = []
                for entry in sched.split(';'):
                    entry = entry.strip()
                    if not entry:
                        continue
                    if ':' in entry:
                        g, sf = entry.split(':', 1)
                        sf = resolve_sim_path(sf, frams_path)
                        norm_parts.append(f"{g}:{sf}")
                    else:
                        norm_parts.append(entry)
                variants.append((t, None, ';'.join(norm_parts)))
        elif args.sim_variants is not None:
            variants = [
                (
                    os.path.splitext(os.path.basename(v))[0],
                    resolve_sim_path(v, frams_path),
                    None
                )
                for v in parse_arg_values_list(args.sim_variants, desired_type=str)
            ]
        elif args.mutints is not None:
            variants = [
                (format_mut_tag(m), ensure_mutation_sim_file(frams_path, f, m), None)
                for m in parse_arg_values_list(args.mutints, desired_type=float)
            ]
        else:
            variants = [(None, None, None)]

        for tag, extra_sim, schedule_str in variants:
            full_sim = combine_sim_strings(sim, extra_sim)
            for n in experiment_idc:
                cmd, hof_path = build_cmd(
                    python_exec, script_path, frams_path, args.opt, full_sim, stats_dir, gens_dir,
                    args.popsize, args.generations, args.tournament,
                    param_value=tag, idx_experiment=n,
                    genformat=f, initialgenotype=args.initialgenotype,
                    max_numparts=args.max_numparts,
                    max_numjoints=args.max_numjoints,
                    max_numneurons=args.max_numneurons,
                    max_numconnections=args.max_numconnections,
                    max_numgenochars=args.max_numgenochars,
                    pxov=args.pxov, pmut=args.pmut,
                    schedule=schedule_str
                )
                logfile = os.path.join(log_dir, encode_filename(tag, n, f) + '.log')
                cwd = os.path.dirname(script_path) if os.path.dirname(script_path) else os.getcwd()
                jobs.append((cmd, str(cwd), logfile, hof_path))

    print(f'Prepared {len(jobs)} jobs; logs -> {log_dir}; genotypes -> {gens_dir}; stats base -> {stats_dir}')

    if args.dry_run:
        for cmd, cwd, logfile, hof_path in jobs:
            print('DRY:', ' '.join(cmd))
            print('cwd=', cwd, 'log=', logfile, 'gen=', hof_path)
        return

    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(run_one, cmd, cwd, logfile): (cmd, logfile) for (cmd, cwd, logfile, _) in jobs}
        for fut in as_completed(futures):
            cmd, logfile = futures[fut]
            try:
                rc = fut.result()
                results[logfile] = rc
                print(f'Finished {os.path.basename(logfile)} -> rc={rc}')
            except Exception as e:
                results[logfile] = -1
                print(f'Job {os.path.basename(logfile)} failed: {e}')

    ok = sum(1 for rc in results.values() if rc == 0)
    print(f'{ok}/{len(results)} jobs succeeded')
    print('Logs:', log_dir)
    print('Genotypes:', gens_dir)
    print('Stats base passed to experiments:', stats_dir)


if __name__ == '__main__':
    main()
