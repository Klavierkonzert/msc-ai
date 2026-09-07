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
    -max_numgenochars 50 \
    -initialgenotype '/*9*/BLU' \
    -popsize 50 \
    -generations 50 \
    -hof_size 1 \
    -hof_savefile runs/<timestamp>/gens/HoF-f9-{M}-{N}.gen \
    --save-stats <statsPath>

Usage:
  python scripts/run_parallel.py --script framspy-download/FramsticksEvolution.py \
      --frams-path C:/.../Framsticks55 --sim eval-allcriteria.sim \
      --values 0 0.05 0.1 --num-experiments 3 --stats-dir stats \
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

def encode_mutation(mutation_intensity: float|str, genformat : str='9'):
    return f"f{genformat}-mut-{fmt_float_value(mutation_intensity)}.sim"
def encode_filename(param_value:str|float|None, idx_experiment:str|int, genformat : str='9') -> str:
    if param_value is not None:
        return f"HoF-f{genformat}-{fmt_float_value(param_value)}-{idx_experiment}"
    else:
        return f"HoF-f{genformat}-{idx_experiment}"

def fmt_float_value(m: str|float, decimal_places: int=2):
    # represent M similarly to PowerShell's default formatting (minimal)
    if isinstance(m, float):
        m = str(m)

    if (float(m)>0):
        return str(m).replace('.', '')+'0'*(decimal_places+1 - len(str(m)))
    elif (float(m)==0):
        return '0'
    raise NotImplemented("fmt_float_value: Invalid input value")


def build_cmd(python_exec:str, script_path:str, frams_path:str, optimization_target:str, sim:str, stats_dir:str, hof_dir:str, popsize:int, generations:int, tournament:int, 
              param_value:str|None, idx_experiment:int
             , genformat:str|int|None =None, initialgenotype:str|None=None
             ) -> tuple[list[str|int], str]:
    """:params:
            :param: genformat - specifies genome format used in Framsticks experiments. Should be one of follows: 0, 1, 4, 9.
            :param: initialgenotype - defines initial genome sequence with a specified genome format. For instance, set to '/*9*/BLU'. If set, `genformat` has no effect.
    """
    hof_path = os.path.join(hof_dir, encode_filename(param_value, idx_experiment, genformat) + ".gen")
    cmd:list[str|int] = [python_exec, script_path,
           '-path', frams_path,
           '-sim', sim,
           '-opt', optimization_target,
           '-max_numparts', '30',
           '-max_numgenochars', '50',
           '-popsize', popsize,
           '-generations', generations,
           '-tournament', tournament,
           '-hof_size', '1',
           '-hof_savefile', hof_path,
           '--save-stats', stats_dir]
    if initialgenotype is not None:
        cmd.extend([ '-initialgenotype', initialgenotype])
    elif genformat is not None:
        cmd.extend(['-genformat', genformat])

    return cmd, hof_path


def run_one(cmd, cwd, logfile):
    with open(logfile, 'wb') as lf:
        proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=cwd)
    return proc.returncode

def parse_arg_values_list[T](values: str, desired_type: type[T]= str) -> list[T]:
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
    p.add_argument('--sim', default="eval-allcriteria.sim;deterministic.sim;sample-period-2.sim;", help='Sim filename to pass to -sim')
    p.add_argument('--values', nargs='+', required=False, help='Parameter (mutation intensity) values (e.g. 0 0.05 0.10)')
    p.add_argument('--num-experiments', required=True, help='Number of experiments')
    p.add_argument('--popsize', default='50', help="Population size")
    p.add_argument('--generations', default='50', help='Number of experiments')
    p.add_argument('--tournament', default ='5', help = 'Number of individuals participating in an tournament')
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
    sim = args.sim
    stats_dir = os.path.abspath(args.stats_dir)
    out_base = os.path.abspath(args.out)
    os.makedirs(out_base, exist_ok=True)
    os.makedirs(stats_dir, exist_ok=True)


    print("Values of the parameter", args.values)
    genformat_values: list[str]#list[str|None]
    if args.initialgenotype is not None:
        print(f"Initial genotype provided: {args.initialgenotype}, skipping all the irrelevant genome formats.")
        genformat_values = re.findall(r'/\*(\d+)\*/', args.initialgenotype)
        # if not len(genformat_values):
        #     genformat_values = [None]
    else:
        genformat_values= parse_arg_values_list(args.genformats, desired_type=str)
    print("Genome format(s): ", genformat_values )

    param_values = parse_arg_values_list(args.values, desired_type=float)
    if not len(param_values):
        param_values = [None]
    experiment_idc = [i for i in range(int(args.num_experiments))]

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    run_dir = os.path.join(out_base, timestamp)
    log_dir = os.path.join(run_dir, 'logs')
    gens_dir = os.path.join(run_dir, 'gens')
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(gens_dir, exist_ok=True)

    python_exec = os.path.abspath(args.python_exec)

    combos = [(f, fmt_float_value(m) if m is not None else None, n) #pad with 0 on the right
              for f in genformat_values 
              for m in param_values for n in experiment_idc]
    print(f'Prepared {len(combos)} jobs; logs -> {log_dir}; genotypes -> {gens_dir}; stats base -> {stats_dir}')

    jobs:  list[tuple[ list[str|int], str,str,str]] = []
    for f, m, n in combos:
        # f can be None, default format will be used then
        cmd, hof_path = build_cmd(python_exec, script_path, frams_path, args.opt, sim + (encode_mutation(m, f) if m is not None else ''), stats_dir, gens_dir,
                                 args.popsize, args.generations, args.tournament,
                                 param_value=m, idx_experiment=n,
                                 genformat=f, initialgenotype=args.initialgenotype)
        logfile = os.path.join(log_dir, encode_filename(m,n, f)+'.log')
        cwd = os.path.dirname(script_path) if os.path.dirname(script_path) else os.getcwd()
        jobs.append((cmd, str(cwd), logfile, hof_path))

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
