"""
FramsticksEvolutionScheduled.py

Extends the standard Framsticks-DEAP evolutionary algorithm with support for
dynamic, in-memory mutation strategy switching across generations.

Reuses original FramsticksEvolution logic:
- Argument parsing & validation
- FramsticksLib initialization & random seeds
- DEAP toolbox setup (crossover, mutation, evaluation, constraints)
- Statistics and feasible fitness filtering
- Hall of Fame tracking & genotype serialization (*.gen)
- Logbook pickling into dated subdirectories (*.logbook.pkl)

The only modification is intercepting the generational loop (eaSimple) to
trigger dynamic mutation strategy adjustments at specified breakpoints.
"""

import os
import sys
import random
import argparse
# Ensure framspy-download is on sys.path before importing frams
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRAMSPY_DIR = os.path.join(REPO_ROOT, "framspy-download")
if FRAMSPY_DIR not in sys.path:
    sys.path.insert(0, FRAMSPY_DIR)

import frams
from deap import tools
import FramsticksEvolution as fe


def parse_schedule(schedule_str: str) -> dict[int, str]:
    """
    Parses a schedule string formatted as:
      "0:path/to/sim1.sim;150:path/to/sim2.sim;200:path/to/sim3.sim"
    Returns a dictionary mapping generation (int) -> sim file path (str).
    """
    if not schedule_str:
        return {}
    schedule = {}
    for entry in schedule_str.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            raise ValueError(f"Invalid schedule entry '{entry}'. Format must be '<gen>:<sim_file_path>'.")
        gen_str, sim_file = entry.split(":", 1)
        schedule[int(gen_str.strip())] = sim_file.strip()
    return schedule


def apply_sim_strategy(sim_path: str):
    """Dynamically imports a .sim settings file into the running Framsticks simulator."""
    abs_path = os.path.abspath(sim_path)
    if not os.path.exists(abs_path):
        candidate = os.path.abspath(os.path.join(REPO_ROOT, sim_path))
        if os.path.exists(candidate):
            abs_path = candidate
        else:
            raise FileNotFoundError(f"Scheduled sim file not found: {abs_path} (also checked {candidate})")

    ec = frams.MessageCatcher.new()
    ec.store = 2
    frams.Simulator.ximport(abs_path, 4 + 8 + 16)
    ec.close()
    if ec.error_count._value() > 0:
        raise ValueError(f"Error while dynamically importing '{abs_path}': {ec.messages}")


def scheduled_eaSimple(pop, toolbox, cxpb, mutpb, ngen, stats=None, halloffame=None, verbose=True):
    """
    Replaces DEAP algorithms.eaSimple to apply mutation strategy switches mid-evolution.
    """
    schedule = parse_schedule(getattr(fe.parsed_args, 'schedule', None))
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals', 'strategy'] + (stats.fields if stats else [])
    current_strategy = "default"

    # Initial strategy at gen 0 if defined
    if 0 in schedule:
        sim_file = schedule[0]
        apply_sim_strategy(sim_file)
        current_strategy = os.path.splitext(os.path.basename(sim_file))[0]
        print(f"\n[SCHEDULE] Gen 0: Activated initial strategy '{current_strategy}' ({sim_file})")

    # Evaluate initial population
    invalid_ind = [ind for ind in pop if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    if halloffame is not None:
        halloffame.update(pop)

    record = stats.compile(pop) if stats else {}
    logbook.record(gen=0, nevals=len(invalid_ind), strategy=current_strategy, **record)
    if verbose:
        print(logbook.stream)

    # Generational loop
    for gen in range(1, ngen + 1):
        if gen in schedule:
            sim_file = schedule[gen]
            apply_sim_strategy(sim_file)
            current_strategy = os.path.splitext(os.path.basename(sim_file))[0]
            print(f"\n>>> [SCHEDULE TRIGGER] Generation {gen}: Switched mutation strategy to '{current_strategy}' ({sim_file})\n")

        offspring = toolbox.select(pop, len(pop))
        offspring = [toolbox.clone(ind) for ind in offspring]

        for i in range(1, len(offspring), 2):
            if random.random() < cxpb:
                offspring[i - 1], offspring[i] = toolbox.mate(offspring[i - 1], offspring[i])
                del offspring[i - 1].fitness.values, offspring[i].fitness.values

        for i in range(len(offspring)):
            if random.random() < mutpb:
                offspring[i], = toolbox.mutate(offspring[i])
                del offspring[i].fitness.values

        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        if halloffame is not None:
            halloffame.update(offspring)

        pop[:] = offspring

        record = stats.compile(pop) if stats else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), strategy=current_strategy, **record)
        if verbose:
            print(logbook.stream)

    return pop, logbook


def main():
    # 1. Reuse FramsticksEvolution parser and inject --schedule
    orig_parse_args = argparse.ArgumentParser.parse_args
    try:
        argparse.ArgumentParser.parse_args = lambda self, *args, **kwargs: self
        parser = fe.parseArguments()
    finally:
        argparse.ArgumentParser.parse_args = orig_parse_args

    parser.add_argument('--schedule', required=False, default=None,
        help='Dynamic mutation schedule, e.g. "0:f1-equal-probs.sim;150:f1-probs10.sim;200:f1-probs01.sim"'
    )
    fe.parseArguments = parser.parse_args

    # 2. Intercept DEAP eaSimple with this scheduled variant
    fe.algorithms.eaSimple = scheduled_eaSimple

    # 3. Execute original FramsticksEvolution.main() with full feature parity
    fe.main()

if __name__ == "__main__":
    main()
