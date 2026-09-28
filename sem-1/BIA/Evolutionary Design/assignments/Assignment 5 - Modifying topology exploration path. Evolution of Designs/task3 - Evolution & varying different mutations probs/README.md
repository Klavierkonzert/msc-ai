# Evolutionary Design #3
## Task 3: Evolution & Varying Mutation Probabilities
## Optimizing Locomotion Velocity in $f_1$ Genetic Format by Adjusting Mutation Operator Probabilities

### Objective and Setup

The objective of this experiment is to optimize **net rectilinear displacement speed** ([`velocity`](https://www.framsticks.com/a/al_params.html#exper-perfcalc)) of creatures encoded using the [**$f1$**](https://www.framsticks.com/a/al_geno_f1.html) (recurrent tree-like) genetic representation over **300-400 generations** under several mutation probability configurations (`.sim` files), which represent different relative probabilities (weights) of applying different mutation operators, forming different distributions over these operators, and thus representing different mutation strategies. We analyze how these strategies influence the evolutionary dynamics and the performance of the evolved solutions for locomotion velocity.

#### Simulation Constraints & Parameters
- **Objective (fitness)**: `velocity` (maximizing net displacement speed)
- **Genetic format**: $f_1$ (`-genformat 1`)
- **Simulation Environment (`eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim;*`)**:
  - **Lifespan Mechanism**: In Framsticks, lifespan is not a static timeout parameter; it is determined by metabolic energy depletion. Each creature receives starting energy proportional to its size: $E_0 = \text{Energy0} \times n$ (with $\text{Energy0} = 10\,000.0$, $n = \text{number of joints/sticks}$). Each simulation step consumes an idle metabolic cost of $e\_\text{meta} \times n$ energy (with $e\_\text{meta} = 1.0$). With constant metabolism (`aging: 0`) and no food replenishment (`feed: 0`), size $n$ cancels out, yielding an exact lifespan of:
    $$\text{lifespan} = \frac{\text{Energy0} \times n}{e\_\text{meta} \times n} = \frac{10\,000.0}{1.0} = 10\,000 \text{ simulation steps}$$
  - **Deterministic Physics (`deterministic.sim`)**: Eliminates stochastic sensory/neural noise (`randinit: 0.0`, `nnoise: 0.0`, `bnoise_vel: 0.0`) and fixes central spawn (`placement: 1`), enabling deterministic, repeatable single-trial evaluation (`evalcount: 1`).
  - **Performance Sampling (`perfperiod`)**: Across all experiments, `sample-period-longest.sim` sets `perfperiod: 999999`. Because $999\,999 > \text{lifespan}$ ($10\,000$), intermediate sampling never triggers. The simulator samples coordinates only twice (at birth $t=0$ and death $t=10\,000$), measuring strictly **net rectilinear displacement velocity**: $v = \frac{\|\mathbf{x}(T) - \mathbf{x}(0)\|}{T}$.
- **Morphological & Neural Limits**:
  - Max parts: `15`
  - Max joints: `30`
  - Max neurons: `20`
  - Max connections: `30`
- **EA Parameters**:
  - Population size: `50`
  - Generations: `300` (Exp 1) / `400` (Exp 2 & 3)
  - Selection: Tournament (`size = 5`)
  - Crossover probability (`pxov`): `0.0` (pure asexual mutation-driven search across all experiments)
  - Mutation probability (`pmut`): `0.9` (this is a default value in [Framsticks](../../../framspy-download/FramsticksEvolution.py#L177))
  - Hall of Fame size: `1`
  - Replications per setting: `10` independent runs with distinct random seeds

### Mutation Mechanics

1. **At the DEAP Algorithm Level (`mutpb`)**:
   - In `FramsticksEvolution.py` (via DEAP's `eaSimple` / `varAnd`), each offspring undergoes a single Bernoulli trial governed by `mutpb` (or `pmut`, default $0.90$):
     ```python
     if random.random() < mutpb:
         offspring[i] = toolbox.mutate(offspring[i])[0]
     ```
   - `mutpb` only controls whether an individual is selected to undergo mutation in that generation. It does **not** decide between body and brain.

2. **Inside the Framsticks C++ Engine (`GenMan.mutate`)**:
   - Once an individual is selected for mutation, Framsticks invokes `frams.GenMan.mutate(geno)`.
   - Morphology and neural mutations are **NOT performed independently**.
   - Instead, **all 9 mutation operators (4 morphology + 5 neural net) compete on a SINGLE roulette wheel** (categorical distribution).
   - In each mutation step, exactly **one** elementary mutation operator is chosen based on its relative weight:
     <div align="center" style="font-size: 130%;">

     $P(\text{op}_i) = \frac{w_i}{\sum_{j=0}^{8} w_j}$

     </div>


#### Mutation Intensity ($f_1$ vs. $f_9$)

In Framsticks, **mutation intensity** $\mu$ represents the fraction (probability per gene/symbol) of a genotype altered during a mutation event:

<div align="center">

$\mathbb{E}[\text{num mutated genes}] = L \times \mu$

</div>

*where $L$ is the number of genes / characters in the genotype*.

Unlike linear letter sequences ([see experiments](../../Assignment%203%20-%20Mutation%20Intensity%20in%20Evolutionary%20Algorithms/README.md) on $f_9$), $f_1$ is a recursive, tree-structured formal grammar with branching parentheses `()`, joint commas `,`, and neural brackets `[]`. Arbitrary per-character flips would violate syntactic validity. Consequently, **there is no continuous `f1_mut` intensity parameter in $f_1$**.

Instead, **every mutation event in $f_1$ performs exactly 1 atomic mutation operation** selected from the roulette wheel.

#### Operator Weights & Global Competition

When inspecting bare Framsticks without simulation override files, the built-in defaults are configured as shown in the GUI tabs:

<div align="center" style="display: flex; justify-content: center; gap: 20px; width: 80%;">

<img src="./images/default_f1_morphology_mutation_probs.png" width="48%"/>
<img src="./images/default_f1_neural_mutation_probs.png" width="48%"/>

</div>

**Morphology** contains detailed mutation probabilities concerning physical structure parts in genotypes. 
**Neuron net** contains detailed mutation probabilities concerning neuron net parts in genotypes. 
These values are **weights**, not probabilities. The probability of picking an operator is obtained by dividing its weight by the sum of all mutation weights.

## Tested configurations of mutation operators probabilities

### Experiment 1 (300 generations)
#### Settings and Rationale
Comparing baseline, high neural, weaker neural, and equal weights configurations:
   1. **[Baseline](f1-all-crit.sim)**: Emphasizes neural weight modifications (`f1_nmWei = 1.0`, $67.1\%$ probability) with low morphology ($12.8\%$ total probability).  
      - Structural neuron insertions/deletions are still relatively high (0.05), but low compared to synaptic weight changes.
      - On the morphology side, modifier adjustments are the most common type of mutation, favoring subtle geometric scaling over drastic topology disruptions.
      - This allocation allows evolution to primarily focus on calibrating muscle activation phases, frequencies, and sensory feedback loops on viable body chassis.
   2. **[High Neural](f1-probs01.sim)**: Doubles neural operator weights, further suppressing body topology perturbations to focus on controller coordination.
   3. **[Weaker Neural](f1-probs10.sim)**: Doubles morphological operator weights relative to neural operators (increasing body mutation proportion to $22.6\%$), fostering broader body shape exploration.
   4. **[Equal Weights](f1-equal-probs.sim)**: Sets all 9 mutation operator weights to $1.0$, providing an equal uniform distribution ($11.1\%$ each) across morphology ($44.4\%$) and brain ($55.5\%$).

The table below summarizes weights and probabilities of mutation operators in default and tuned settings:

<table tableId="table1">
  <thead>
    <tr>
      <th rowspan="2">Operator</th>
      <th rowspan="2">Description</th>
      <th colspan="2"><a href="./f1-all-crit.sim"><b>Baseline</b></a></th>
      <th colspan="2"><a href="./f1-probs01.sim"><b>High Neural</b></a></th>
      <th colspan="2"><a href="./f1-probs10.sim"><b>Weaker Neural</b></a></th>
      <th colspan="2"><a href="./f1-equal-probs.sim"><b>Equal Weights</b></a></th>
    </tr>
    <tr>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td colspan="10"><b>Morphology Mutation Operators</b></td>
    </tr>
    <tr>
      <td><code>f1_smX</code></td>
      <td>Add / remove stick X (part)</td>
      <td align="center">0.05</td>
      <td style="background-color: #c4e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.4%</td>
      <td align="center">0.05</td>
      <td style="background-color: #ceecfe; color: #0F172A; font-weight: 600; text-align: center;">1.8%</td>
      <td align="center">0.10</td>
      <td style="background-color: #b7e3fd; color: #0F172A; font-weight: 600; text-align: center;">6.0%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
    </tr>
    <tr>
      <td><code>f1_smJunct</code></td>
      <td>Add / remove branch junction <code>()</code></td>
      <td align="center">0.02</td>
      <td style="background-color: #d1edfe; color: #0F172A; font-weight: 600; text-align: center;">1.3%</td>
      <td align="center">0.02</td>
      <td style="background-color: #d6effe; color: #0F172A; font-weight: 600; text-align: center;">0.7%</td>
      <td align="center">0.04</td>
      <td style="background-color: #caebfd; color: #0F172A; font-weight: 600; text-align: center;">2.4%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
    </tr>
    <tr>
      <td><code>f1_smComma</code></td>
      <td>Add / remove joint separator <code>,</code></td>
      <td align="center">0.02</td>
      <td style="background-color: #d1edfe; color: #0F172A; font-weight: 600; text-align: center;">1.3%</td>
      <td align="center">0.02</td>
      <td style="background-color: #d6effe; color: #0F172A; font-weight: 600; text-align: center;">0.7%</td>
      <td align="center">0.04</td>
      <td style="background-color: #caebfd; color: #0F172A; font-weight: 600; text-align: center;">2.4%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
    </tr>
    <tr>
      <td><code>f1_smModif</code></td>
      <td>Add / remove / change limb modifier</td>
      <td align="center">0.10</td>
      <td style="background-color: #b2dffd; color: #0F172A; font-weight: 600; text-align: center;">6.7%</td>
      <td align="center">0.10</td>
      <td style="background-color: #c3e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.6%</td>
      <td align="center">0.20</td>
      <td style="background-color: #98c9fd; color: #0F172A; font-weight: 600; text-align: center;">11.9%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
    </tr>
    <tr>
      <td colspan="2"><b>Total Body</b></td>
      <td align="center"><b>0.19</b></td>
      <td style="background-color: #94c6fd; color: #0F172A; font-weight: 600; text-align: center;"><b>12.8%</b></td>
      <td align="center"><b>0.19</b></td>
      <td style="background-color: #b2dffd; color: #0F172A; font-weight: 600; text-align: center;"><b>6.8%</b></td>
      <td align="center"><b>0.38</b></td>
      <td style="background-color: #c0d0fe; color: #0F172A; font-weight: 600; text-align: center;"><b>22.6%</b></td>
      <td align="center"><b>4.0</b></td>
      <td style="background-color: #f27282; color: #0F172A; font-weight: 600; text-align: center;"><b>44.4%</b></td>
    </tr>
    <tr>
      <td colspan="10"><b>Neural Network Mutation Operators</b></td>
    </tr>
    <tr>
      <td><code>f1_nmNeu</code></td>
      <td>Add / remove neuron</td>
      <td align="center">0.05</td>
      <td style="background-color: #c4e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.4%</td>
      <td align="center">0.10</td>
      <td style="background-color: #c3e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.6%</td>
      <td align="center">0.05</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.0%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
    </tr>
    <tr>
      <td><code>f1_nmConn</code></td>
      <td>Add / remove neural connection</td>
      <td align="center">0.10</td>
      <td style="background-color: #b2dffd; color: #0F172A; font-weight: 600; text-align: center;">6.7%</td>
      <td align="center">0.20</td>
      <td style="background-color: #b0defd; color: #0F172A; font-weight: 600; text-align: center;">7.2%</td>
      <td align="center">0.10</td>
      <td style="background-color: #b7e3fd; color: #0F172A; font-weight: 600; text-align: center;">6.0%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
    </tr>
    <tr>
      <td><code>f1_nmProp</code></td>
      <td>Change neuron property setting</td>
      <td align="center">0.10</td>
      <td style="background-color: #b2dffd; color: #0F172A; font-weight: 600; text-align: center;">6.7%</td>
      <td align="center">0.20</td>
      <td style="background-color: #b0defd; color: #0F172A; font-weight: 600; text-align: center;">7.2%</td>
      <td align="center">0.10</td>
      <td style="background-color: #b7e3fd; color: #0F172A; font-weight: 600; text-align: center;">6.0%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
    </tr>
    <tr>
      <td><code>f1_nmWei</code></td>
      <td><b>Change connection weight</b></td>
      <td align="center"><b>1.00</b></td>
      <td style="background-color: #a9173d; color: #FFFFFF; font-weight: 600; text-align: center;">67.1%</td>
      <td align="center"><b>2.00</b></td>
      <td style="background-color: #96153a; color: #FFFFFF; font-weight: 600; text-align: center;">71.7%</td>
      <td align="center"><b>1.00</b></td>
      <td style="background-color: #cc1b44; color: #FFFFFF; font-weight: 600; text-align: center;">59.5%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
    </tr>
    <tr>
      <td><code>f1_nmVal</code></td>
      <td>Change property / state value</td>
      <td align="center">0.05</td>
      <td style="background-color: #c4e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.4%</td>
      <td align="center">0.10</td>
      <td style="background-color: #c3e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.6%</td>
      <td align="center">0.05</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.0%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
    </tr>
    <tr>
      <td colspan="2"><b>Total Brain</b></td>
      <td align="center"><b>1.30</b></td>
      <td style="background-color: #881337; color: #FFFFFF; font-weight: 600; text-align: center;"><b>87.2%</b></td>
      <td align="center"><b>2.60</b></td>
      <td style="background-color: #881337; color: #FFFFFF; font-weight: 600; text-align: center;"><b>93.2%</b></td>
      <td align="center"><b>1.30</b></td>
      <td style="background-color: #881337; color: #FFFFFF; font-weight: 600; text-align: center;"><b>77.4%</b></td>
      <td align="center"><b>5.0</b></td>
      <td style="background-color: #df1d48; color: #FFFFFF; font-weight: 600; text-align: center;"><b>55.5%</b></td>
    </tr>
    <tr>
      <td colspan="2"><b>Total Wheel Weight</b></td>
      <td align="center"><b>1.49</b></td>
      <td align="center"><b>100%</b></td>
      <td align="center"><b>2.79</b></td>
      <td align="center"><b>100%</b></td>
      <td align="center"><b>1.68</b></td>
      <td align="center"><b>100%</b></td>
      <td align="center"><b>9.0</b></td>
      <td align="center"><b>100%</b></td>
    </tr>
  </tbody>
</table>





#### Experimental Results

![Logbook Best Series](results/hof_results/plots/logbooks_best_series.png)
_Figure 1: Best-of-generation fitness trajectories across all 10 independent replications over 300 generations for all 4 mutation probability configurations (`f1-all-crit`, `f1-probs01`, `f1-probs10`, `f1-equal-probs`)._

![Confidence Intervals](results/hof_results/plots/logbooks_confidence_std_1.0.png)
_Figure 2: Mean best fitness and $\pm 1\sigma$ shaded confidence intervals over 300 generations. `f1-equal-probs` achieves the fastest growth rate and highest sustained trajectory._

![Boxplot Summary](results/hof_results/plots/boxplot_summary.png)
_Figure 3: Distribution of Hall-of-Fame final fitness (left) and total run duration (right) across 10 independent replications._



#### Quantitative Summary and Analysis

| Configuration | Mean HoF Velocity | Median HoF Velocity | Std Dev | Min Velocity | Max Velocity | Mean Duration (s) |
| :---:| :---: | :---: | :---: | :---: | :---: | :---: |
| [Baseline](./f1-all-crit.sim) | $0.004049$ | $0.003283$ | $0.002605$ | $0.001596$ | $0.008713$ | $580.0\text{ s}$ |
| [High Neural](./f1-probs01.sim) | $0.004866$ | $0.001850$ | $0.007047$ | $0.000299$ | $0.023336$ | $530.0\text{ s}$ |
| [Weaker Neural](./f1-probs10.sim) | $0.002860$ | $0.002117$ | $0.002869$ | $0.000240$ | $0.007896$ | $531.6\text{ s}$ |
| **[Equal Weights](./f1-equal-probs.sim)** |  $0.009062$| **$0.005134$** | $0.011422$ | $0.000398$ | **$0.038438$** | $587.4\text{ s}$ |

#### Key Findings

1. **[Equal Operator Weights](./f1-equal-probs.sim) Unlock Superior Locomotion**:
   - Achieves roughly double the mean and median velocity of the baseline and producing the highest peak performance ($v = 0.038438$).
   - In $f_1$, equal weights translate to a $4$-to-$5$ ratio between morphology and brain. This balanced ratio maintains structural diversity while preserving sufficient frequency of synaptic weight mutations ($11.1\%$) to coordinate newly emerging limbs.

2. **Impact of [Brain-Heavy Mutation](./f1-probs01.sim)**:
   - Doubling neural weights (brain changes total probability - $93.2\%$) increased the top-tier peak velocity to $v = 0.023336$ and raised mean velocity above the baseline ($0.004866$).
   - However, extreme suppression of body modifications ($6.8\%$ total probability) restricts morphological innovation, causing lower median performance ($0.001850$) when a run initializes with an unpromising body topology.

3. **Impact of [Weaker Neural Mutation](./f1-probs10.sim)**:
   - Doubling morphology weights relative to brain operators (body changes total probability - $22.6\%$, neural suppression) produced the lowest average velocity ($0.002860$).
   - More frequent stick additions and limb modifier alterations repeatedly disrupt coordinated oscillatory gaits without giving the neural network enough evolutionary iterations to adapt.

4. **Evolved Top-Performing Genotype**:
   - The fastest creature of all 40 runs evolved in `HoF-f1-f1-equal-probs-8.gen` achieving $v = 0.038438$:
     ```
     genotype: LFL(RFfMLX[N, 2:1,12:1,s:0][|, 12:0.902][*]((X[S][@, 1:1][Gpart,rz:-0.483][G][G][|, -6:1.62]q(, , , q(mMX[N, si:-2.924, 5:2.759, 3:1.073, 7:-4.331])), , lX[@, 2:1.495][S][G][S][G][|, -2:0.788])), QcX[G][|, -3:2.523, p:0.491])
     velocity: 0.038438129208658904
     ```
   - Morphology features an articulated branching body with rotational muscle joints (`*`), bending joints (`|`), and specialized ground-contact friction modifiers (`F, f, m`).
   - Neural controller incorporates tactile sensors (`S`), equilibrium sensors (`G`, `Gpart`), and sinusoidal pattern generators (`N`) with calibrated synaptic connections (`12:0.902`, `-6:1.62`, `-3:2.523`), achieving rapid propulsive crawling.


### Experiment 2: Targeted Mutation Strategies (Strategies A–D). Comparison with previous settings. 400 Generations

#### Settings
To move beyond blunt global morphology-vs-brain ratios, **four tuned operator probability distributions** based on the mechanical roles of the 9 operators in $f_1$:


#### Settings & Rationales
1. **[Strategy A (Continuous Fine-Tuning)](./f1-strat-a.sim)**: Heavy suppression of catastrophic structural additions/deletions (`smX`, `smJunct`, `nmNeu` at $0.2$) while prioritizing continuous physical and neural scaling (`smModif: 1.5`, `nmProp: 1.5`, `nmWei: 2.0`). Protects working gaits from being ripped apart.
2. **[Strategy B (Branching & Morphology Exploration)](./f1-strat-b.sim)**: Strongly promotes structural branching (`smJunct: 1.5`, `smComma: 1.5`) alongside balanced neural operators ($1.0$). Encourages bilateral limbs, outriggers, and multi-legged chassis.
3. **[Strategy C (CPG Resonance & Control Dynamics)](./f1-strat-c.sim)**: Minimizes body alterations ($20\%$ body share) and concentrates on central pattern generator frequency/phase coordination ($80\%$ brain share).
4. **[Strategy D (3-Tier Evolutionary Pyramid)](./f1-strat-d.sim)**: Hierarchical architecture allocating ~15% to macro-topology jumps, ~35% to mesoscale wiring and modifiers, and ~50% to continuous parameter calibration.

<table tableId="table2">
  <thead>
    <tr>
      <th rowspan="2">Operator</th>
      <th rowspan="2">Role in f<sub>1</sub> Phenotype</th>
      <th colspan="2"><a href="./f1-strat-a.sim"><b>Strategy A</b></a></th>
      <th colspan="2"><a href="./f1-strat-b.sim"><b>Strategy B</b></a></th>
      <th colspan="2"><a href="./f1-strat-c.sim"><b>Strategy C</b></a></th>
      <th colspan="2"><a href="./f1-strat-d.sim"><b>Strategy D</b></a></th>
    </tr>
    <tr>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td colspan="10"><b>Morphology Mutation Operators</b></td>
    </tr>
    <tr>
      <td><code>f1_smX</code></td>
      <td>Stick Append / Delete</td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">0.5</td>
      <td style="background-color: #bbe6fd; color: #0F172A; font-weight: 600; text-align: center;">5.3%</td>
      <td align="center">0.1</td>
      <td style="background-color: #ccecfd; color: #0F172A; font-weight: 600; text-align: center;">2.0%</td>
      <td align="center">0.3</td>
      <td style="background-color: #bde7fd; color: #0F172A; font-weight: 600; text-align: center;">4.7%</td>
    </tr>
    <tr>
      <td><code>f1_smJunct</code></td>
      <td>Branch Fork <code>()</code></td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">1.5</td>
      <td style="background-color: #a2c9fd; color: #0F172A; font-weight: 600; text-align: center;">15.8%</td>
      <td align="center">0.1</td>
      <td style="background-color: #ccecfd; color: #0F172A; font-weight: 600; text-align: center;">2.0%</td>
      <td align="center">0.3</td>
      <td style="background-color: #bde7fd; color: #0F172A; font-weight: 600; text-align: center;">4.7%</td>
    </tr>
    <tr>
      <td><code>f1_smComma</code></td>
      <td>Joint Sibling <code>,</code></td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">1.5</td>
      <td style="background-color: #a2c9fd; color: #0F172A; font-weight: 600; text-align: center;">15.8%</td>
      <td align="center">0.1</td>
      <td style="background-color: #ccecfd; color: #0F172A; font-weight: 600; text-align: center;">2.0%</td>
      <td align="center">0.5</td>
      <td style="background-color: #addbfd; color: #0F172A; font-weight: 600; text-align: center;">7.8%</td>
    </tr>
    <tr>
      <td><code>f1_smModif</code></td>
      <td>Modifiers (<code>LlRrCcQqFfMm</code>)</td>
      <td align="center">1.5</td>
      <td style="background-color: #c3d1fe; color: #0F172A; font-weight: 600; text-align: center;">23.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">0.7</td>
      <td style="background-color: #96c6fd; color: #0F172A; font-weight: 600; text-align: center;">13.7%</td>
      <td align="center">1.0</td>
      <td style="background-color: #a0c8fd; color: #0F172A; font-weight: 600; text-align: center;">15.6%</td>
    </tr>
    <tr>
      <td colspan="2"><b>Total Body</b></td>
      <td align="center"><b>2.10</b></td>
      <td style="background-color: #e6b7c9; color: #0F172A; font-weight: 600; text-align: center;"><b>32.3%</b></td>
      <td align="center"><b>4.50</b></td>
      <td style="background-color: #ee5c73; color: #0F172A; font-weight: 600; text-align: center;"><b>47.4%</b></td>
      <td align="center"><b>1.00</b></td>
      <td style="background-color: #b3cdfe; color: #0F172A; font-weight: 600; text-align: center;"><b>19.6%</b></td>
      <td align="center"><b>2.10</b></td>
      <td style="background-color: #e8b6c7; color: #0F172A; font-weight: 600; text-align: center;"><b>32.8%</b></td>
    </tr>
    <tr>
      <td colspan="10"><b>Neural Network Mutation Operators</b></td>
    </tr>
    <tr>
      <td><code>f1_nmNeu</code></td>
      <td>Neuron Insert / Delete</td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">0.3</td>
      <td style="background-color: #b7e3fd; color: #0F172A; font-weight: 600; text-align: center;">5.9%</td>
      <td align="center">0.3</td>
      <td style="background-color: #bde7fd; color: #0F172A; font-weight: 600; text-align: center;">4.7%</td>
    </tr>
    <tr>
      <td><code>f1_nmConn</code></td>
      <td>Synapse Link / Cut</td>
      <td align="center">0.5</td>
      <td style="background-color: #addbfd; color: #0F172A; font-weight: 600; text-align: center;">7.7%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">0.7</td>
      <td style="background-color: #96c6fd; color: #0F172A; font-weight: 600; text-align: center;">13.7%</td>
      <td align="center">0.8</td>
      <td style="background-color: #96c7fd; color: #0F172A; font-weight: 600; text-align: center;">12.5%</td>
    </tr>
    <tr>
      <td><code>f1_nmProp</code></td>
      <td>Frequency <i>f</i><sub>0</sub>, Phase <i>t</i></td>
      <td align="center">1.5</td>
      <td style="background-color: #c3d1fe; color: #0F172A; font-weight: 600; text-align: center;">23.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">1.5</td>
      <td style="background-color: #dbc1dc; color: #0F172A; font-weight: 600; text-align: center;">29.4%</td>
      <td align="center">1.2</td>
      <td style="background-color: #b0ccfe; color: #0F172A; font-weight: 600; text-align: center;">18.8%</td>
    </tr>
    <tr>
      <td><code>f1_nmWei</code></td>
      <td><b>Synaptic Weight</b></td>
      <td align="center"><b>2.0</b></td>
      <td style="background-color: #e0bdd4; color: #0F172A; font-weight: 600; text-align: center;">30.8%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">1.5</td>
      <td style="background-color: #dbc1dc; color: #0F172A; font-weight: 600; text-align: center;">29.4%</td>
      <td align="center"><b>1.8</b></td>
      <td style="background-color: #d6c5e4; color: #0F172A; font-weight: 600; text-align: center;">28.1%</td>
    </tr>
    <tr>
      <td><code>f1_nmVal</code></td>
      <td>Internal Bias / State</td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">0.1</td>
      <td style="background-color: #ccecfd; color: #0F172A; font-weight: 600; text-align: center;">2.0%</td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
    </tr>
    <tr>
      <td colspan="2"><b>Total Brain</b></td>
      <td align="center"><b>4.40</b></td>
      <td style="background-color: #a7163d; color: #FFFFFF; font-weight: 600; text-align: center;"><b>67.7%</b></td>
      <td align="center"><b>5.00</b></td>
      <td style="background-color: #e53055; color: #FFFFFF; font-weight: 600; text-align: center;"><b>52.6%</b></td>
      <td align="center"><b>4.10</b></td>
      <td style="background-color: #881337; color: #FFFFFF; font-weight: 600; text-align: center;"><b>80.4%</b></td>
      <td align="center"><b>4.30</b></td>
      <td style="background-color: #a9173d; color: #FFFFFF; font-weight: 600; text-align: center;"><b>67.2%</b></td>
    </tr>
    <tr>
      <td colspan="2"><b>Total Wheel Weight</b></td>
      <td align="center"><b>6.50</b></td>
      <td align="center"><b>100%</b></td>
      <td align="center"><b>9.50</b></td>
      <td align="center"><b>100%</b></td>
      <td align="center"><b>5.10</b></td>
      <td align="center"><b>100%</b></td>
      <td align="center"><b>6.40</b></td>
      <td align="center"><b>100%</b></td>
    </tr>
  </tbody>
</table>

### Comparative Results

Each strategy was evaluated across 10 independent runs over 400 generations (20 CPU workers).

![Comparative Best Series (Linear)](results/hof_results_comparison/plots/logbooks_best_series.png)
_Figure 4: Comparative best-of-generation fitness trajectories across all 8 configurations, 400 generations._

![Comparative Confidence Intervals (Linear)](results/hof_results_comparison/plots/logbooks_confidence_std_1.0.png)
_Figure 5: Mean fitness and shaded $\pm 1\sigma$ intervals comparing **Experiment 1** configurations (pink/purple) against **Experiment 2** strategies (cyan/blue), 400 generations._

![Comparative Boxplots](results/hof_results_comparison/plots/boxplot_summary.png)
_Figure 6: Final Hall-of-Fame velocity and run duration distributions across all 8 configurations, 400 generations._

### Summary

| Series | Configuration | Mean Velocity | **Median Velocity** | Std Dev | Min Velocity | Max Velocity | Mean Duration (s) |
| :--- | :--- | :---:| :---: | :---: | :---: | :---: | :---: |
| **[Experiment 1 rerun](./runs/2026-09-26_172452)** *(400 generations)* | **[Baseline](./f1-all-crit.sim)** | $0.005470$ | $0.003304$ | $0.005167$ | $0.001657$ | $0.018541$ | $737.9\text{ s}$ |
| | **[High Neural](./f1-probs01.sim)** | $0.003288$ | $0.003036$ | $0.002625$ | $0.000286$ | $0.007002$ | $723.8\text{ s}$ |
| | **[Weaker Neural](./f1-probs10.sim)** | $0.005603$ | $0.005615$ | $0.003776$ | $0.000890$ | $0.011583$ | $740.9\text{ s}$ |
| | **[Equal Weights](./f1-equal-probs.sim)** | **$0.007167$** | **$0.006500$** | $0.005391$ | $0.000574$ | **$0.019564$** | $758.5\text{ s}$ |
| **[Experiment 2](./runs/2026-09-26_180136)** *(400 generations)* | **[Strategy A (Fine-Tuning)](./f1-strat-a.sim)** | $0.005721$ | $0.004023$ | $0.005857$ | $0.000149$ | $0.017484$ | $693.0\text{ s}$ |
| | **[Strategy B (Branching)](./f1-strat-b.sim)** | $0.006325$ | $0.004553$ | $0.005191$ | $0.001025$ | $0.016070$ | $753.2\text{ s}$ |
| | **[Strategy C (CPG Resonance)](./f1-strat-c.sim)** | $0.002754$ | $0.002203$ | $0.001593$ | $0.000962$ | $0.005328$ | $715.3\text{ s}$ |
| | **[Strategy D (3-Tier Pyramid)](./f1-strat-d.sim)** | $0.005691$ | **$0.005484$** | **$0.003389$** | $0.001103$ | $0.010394$ | $695.9\text{ s}$ |

![Experiment 2 Best Creature](./images/Exp2-best-creature.png)
_Figure 6b: Phenotypic inspection of the fastest creature evolved in Experiment 2 (Strategy A), displaying its linear articulated chassis and synchronized neural motor driver._

#### Key Findings from Strategies A–D

1. **Strategy A Achieves the Highest Peak Fitness in Experiment 2 ($0.017484$)**:
   - Strategy A produced the fastest individual among strategies A-D.
   - By heavily penalizing destructive topology changes and favoring continuous phenotypic tuning (`f1_smModif: 1.5`, `f1_nmWei: 2.0`, `f1_nmProp: 1.5`), evolution refines functional oscillatory gaits to high speeds without suffering recurrent structural collapses.

2. **Strategy B**:
   - Strategy B achieved the highest average velocity among Strategies A–D ($0.006325$), closely tracking `f1-equal-probs`.
   - *It shows a rapid increase in average fitness, observed during generations 100-150.*
   - Promoting branch forks and joint separators (`smJunct: 1.5`, `smComma: 1.5`) alongside balanced neural mutation rates ($1.0$) reliably provides populations with stable, multi-point ground contact early in evolution.

3. **Comparison with Equal Weights**:
   - **Equal Weights** achieves the highest overall median ($0.006500$) and peak velocity ($0.019564$), benefiting from balanced structural and neural exploration. Across almost all the 400 generations this strategy retains the best average velocity.
   - *It demonstrates the highest increase in average fitness during the first 50 generations.*

4. **Strategy C** behaves similar to **High Neural** - both demonstrate underperforming, though with different orders of variance.

5. **Strategy D** behaves similar to **Weaker Neural** - both demonstrate similar performance trajectories with some noticeable gap during the course of evolution, which is closes at the end, showing similar final results in terms of median and variance. The latter performs better during the main part of the evolution, however the former shows accelerated improvement after 100th generation.

6. **Best Evolved Creature in Experiment 2 (`HoF-f1-f1-strat-a-7.gen`)**:
   - Achieved $v = 0.017484$:
     ```
     genotype: mf((fMm(FMX[*][|, r:0.846, r:1,1:3.431][S]LQLMmX[T][*][Gpart, rz:-1.725,ry:0](M(rFFCMmX[N, -4:4.187,-4:-0.104,-3:1][@,-5:1][|, -3:2.525, p:0.277, r:1])), rfCqX), ))
     velocity: 0.01748434347207931
     ```
   - Highly articulated morphology featuring rotational muscle joints (`*`), bending muscles with dynamic feedback (`|`, `-3:2.525, p:0.277`), tactile contact sensor (`S`), body gyroscope sensor (`Gpart, rz:-1.725`), sinusoidal pattern generator (`N`), and friction/joint modifiers (`mf, fMm, F, LQLMm, T, M, rFFC, rfCq`).


### Experiment 3: Switching between strategies in the course of evolution

**Equal weights** showed the best performance among the constant strategies (*see [*Figure 5*](#comparative-results)*), and thus can be used as the base stage of the evolutionary process, showing that early exploration (50-100 generations) boosts the performance of the population. 

For the early stages of evolution, *morphological scaffolding* rapidly branches out bilateral limbs, joints, and stable ground contact points. Once an effective physical chassis is discovered and selected, continuing high structural mutation is destructive: adding a random stick shifts the center of mass and derails the gait. Switching to neural fine-tuning freezes the physical chassis and dedicates main evolutionary budget to synchronizing muscle phases, oscillator frequencies, and synaptic feedback loops.


Based on this, the following mixtures were selected to test the scheme of early morphological exploration (*see performance of **Weaker Neural** and **Equal Weights** in [*Figure 5*](#comparative-results), first 50 generations*), then neural exploration (equalized neural operator weights in **Strategy B**), and then exploitation of the best brain during later stages:
  1. <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span> $ \xrightarrow{\text{150 gens }} $ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span>

  2. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $ \xrightarrow{\text{150 gens }} $ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span> $\xrightarrow{\text{50 gens }} $ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span> 

  3. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $ \xrightarrow{\text{100 gens }} $ <span style="color: #ee5c73; font-weight: 600; text-align: center;">Strategy B</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span>


  4. <span style="color: #ee5c73; font-weight: 600; text-align: center;">Strategy B</span> $\xrightarrow{\text{150 gens }}$ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span>

  5. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $\xrightarrow{\text{150 gens }}$ <span style="color: #e8b6c7; font-weight: 600; text-align: center;">Strategy D</span> $\xrightarrow{\text{75 gens }}$ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span>
  
  6. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $\xrightarrow{\text{150 gens }}$ <span style="color: #e8b6c7; font-weight: 600; text-align: center;">Strategy D</span> $\xrightarrow{\text{75 gens }}$ <span style="color: #e6b7c9; font-weight: 600; text-align: center;">Strategy A</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span>

  7. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $\xrightarrow{\text{100 gens }}$  <span style="color: #ee5c73; font-weight: 600; text-align: center;">Strategy B</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #e8b6c7; font-weight: 600; text-align: center;">Strategy D</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #e6b7c9; font-weight: 600; text-align: center;">Strategy A</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span>

#### Experimental Results

![Experiment 3 Fitness Trajectories](results/hof_results_exp3/plots/logbooks_best_series.png)
_Figure 7: Best-of-generation fitness trajectories across all 10 independent replications over 400 generations for all 7 scheduled mutation schemes (linear evaluations scale)._

![Experiment 3 Confidence Intervals](results/hof_results_exp3/plots/logbooks_confidence_std_1.0.png)
_Figure 8: Mean best fitness and $\pm 1\sigma$ shaded confidence intervals over 400 generations across Schemes 1–7 (linear generations scale). Multi-stage schemes consistently accelerate fitness accumulation during staged transitions._

![Experiment 3 Boxplot Summary](results/hof_results_exp3/plots/boxplot_summary.png)
_Figure 9: Distribution of Hall-of-Fame final fitness (left) and total run duration (right) across 10 independent replications for Schemes 1–7._

#### Quantitative Summary and Analysis

| Scheme #idx | Mean HoF Velocity | Median HoF Velocity | Std Dev | Min Velocity | Max Velocity | Mean Duration (s) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1  | $0.005944$ | **$0.006273$** | **$0.002468$** | $0.001006$ | $0.009180$ | $906.0\text{ s}$ |
| 2 | $0.005550$ | $0.003672$ | $0.005117$ | $0.001381$ | $0.017202$ | $906.4\text{ s}$ |
| **3** | **$0.007213$** | $0.005296$ | $0.006716$ | $0.001013$ | **$0.023459$** | $919.0\text{ s}$ |
| 4 | $0.005469$ | $0.004775$ | $0.003361$ | $0.001482$ | $0.012361$ | $941.8\text{ s}$ |
| 5 | $0.006551$ | $0.004666$ | $0.005132$ | $0.000363$ | $0.015115$ | $955.7\text{ s}$ |
| 6 | $0.004907$ | $0.003778$ | $0.003853$ | $0.000496$ | $0.012416$ | $1103.5\text{ s}$ |
| **7** | $0.006889$ | $0.005790$ | $0.005881$ | $0.000549$ | $0.014549$ | $1057.9\text{ s}$ |

#### Key Findings from Experiment 3

1. **Dynamic Scheduling Achieves New Peak Locomotion ($v = 0.023459$)**:
   - Under identical evaluation settings (`pxov = 0.0`, `max_numparts = 15`, `sample-period-longest.sim`), dynamic mutation scheduling outperformed constant mutation regimes.
   - **Scheme 3** achieved the highest overall mean velocity ($v = 0.007213$) and the single fastest creature of the entire benchmark ($v = 0.023459$, in `HoF-f1-scheme-3-3.gen`), surpassing the top performers from Experiment 2 (Strategy A: $v = 0.017484$, Strategy B: $v = 0.016070$).
   - This empirically confirms the *morphological scaffolding* principle: unconstrained exploration early on (Equal weights for 100 gens, then Strategy B branching for 50 gens) constructs a viable articulated frame; subsequent shift to weaker neural mutation (50 gens) stabilizes the topology, before 200 generations of high-neural mutation fine-tune the motor control signals.

2. **Scheme 7 (Multi-Stage Pipeline) Provides Exceptional Progression ($v_{mean} = 0.006889$, $v_{median} = 0.005790$)**:
   - Scheme 7 implements the full 6-stage evolutionary pipeline: Equal ($100$) $\to$ Strat B ($50$) $\to$ Strat D ($50$) $\to$ Strat A ($50$) $\to$ Weaker Neural ($50$) $\to$ High Neural ($100$).
   - It produced the second highest mean velocity ($0.006889$) and the second highest median ($0.005790$), demonstrating consistent, multi-stage gains without catastrophic fitness drops across intermediate phase transitions.

3. **Scheme 1 Displays Highest Stability ($v_{median} = 0.006273$, lowest $\sigma = 0.002468$)**:
   - Simply transitioning from Weaker Neural ($150$ gens) to High Neural ($250$ gens) yielded the most predictable outcomes with the highest median ($0.006273$) and lowest standard deviation across all replications.

4. **Best Evolved Creature in Experiment 3 (`HoF-f1-scheme-3-3.gen`)**:
   - Reached peak velocity $v = 0.023459$:
     ```
     genotype: qMLL(X[N, 12:12.399, 9:-1.407, 9:6.412, 12:4.867, fo:0.887,4:3.922][|, 8:1, r:0.929], (X[Gpart, ry:2.129]X[S]m((X[S][Gpart][Gpart]X[N, -4:-0.547, -1:1, -3:-1.7,3:11.708][|, -3:1, r:1][N, 0:0.987, -3:1.684, -4:-0.029, -4:1.827, fo:1, -6:12.219, -2:2.178, -6:3.295], , X[S][@, -9:1][Gpart]))))
     velocity: 0.023459246574864995
     ```
   - Morphology features an articulated bilateral body segment with rotational muscle joints, bending actuators (`|`), tactile touch sensors (`S`), equilibrium gyroscopes (`Gpart`), and neural network oscillators (`N`) with precisely calibrated synaptic weights driving an efficient crawling gait.


### Experiment 4: Biphasic Two-Stage Exploration Schemes

To address the disruptive operator shocks observed in the multi-stage schedules of Experiment 3, Experiment 4 evaluates **simpler, biphasic (single-transition) exploration strategies**. Each scheme executes a dedicated morphological exploration phase followed by a clean transition to continuous/neural exploitation over 400 generations across 25 parallel workers (50 runs total, executed in 2 consecutive loops of 25 workers). Under the unified global numbering system, adjusted baseline schemes retain their index (Scheme 1), while newly introduced strategies continue monotonically from Scheme 8 through Scheme 11:

1. **Scheme 1: Classic Scaffolding (Body First $\to$ Brain Second - Refinement of Exp 3 Scheme 1)**:
   <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span> $ \xrightarrow{\text{200 gens }} $ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span>
   *Rationale*: Dedicates 200 generations to structural and body-plan innovation (`f1-probs10.sim`), then locks down morphology to dedicate the remaining 200 generations entirely to neural motor synchronization (`f1-probs01.sim`).

2. **Scheme 8: Smooth Annealing (Unconstrained Exploration $\to$ Precision Fine-Tuning)**:
   <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $ \xrightarrow{\text{200 gens }} $ <span style="color: #e6b7c9; font-weight: 600; text-align: center;">Strategy A</span>
   *Rationale*: Uses unbiased uniform mutation across all operators (`f1-equal-probs.sim`) for the first half of evolution, then transitions smoothly into Strategy A (`f1-strat-a.sim`) to refine continuous parameters and synaptic weights without disruptive structural mutations.

3. **Scheme 9: Articulated Gait (Limb Branching $\to$ Neuromuscular Tuning)**:
   <span style="color: #ee5c73; font-weight: 600; text-align: center;">Strategy B</span> $ \xrightarrow{\text{200 gens }} $ <span style="color: #e6b7c9; font-weight: 600; text-align: center;">Strategy A</span>
   *Rationale*: Leverages Strategy B's branching and segmentation operators (`f1-strat-b.sim`) to synthesize multi-jointed articulated limbs, followed by 200 generations of Strategy A (`f1-strat-a.sim`) to coordinate joint angles and muscle actuation phases.

4. **Scheme 10: Early Freeze Timing Test (100 gens exploration - Optimal Champion)**:
   <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $ \xrightarrow{\text{100 gens }} $ <span style="color: #e6b7c9; font-weight: 600; text-align: center;">Strategy A</span>
   *Rationale*: Tests whether locking morphology early (generation 100) and dedicating 300 generations to fine-tuning yields faster gait convergence or suffers from premature structural convergence.

5. **Scheme 11: Late Freeze Timing Test (300 gens exploration)**:
   <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $ \xrightarrow{\text{300 gens }} $ <span style="color: #e6b7c9; font-weight: 600; text-align: center;">Strategy A</span>
   *Rationale*: Allows prolonged morphological exploration (300 generations) to discover complex, non-trivial chassis designs before a brief 100-generation final polishing phase.

#### Experimental Results

![Experiment 4 Fitness Trajectories](results/hof_results_exp4/plots/logbooks_best_series.png)
_Figure 10: Best-of-generation fitness trajectories across all 10 independent replications over 400 generations for all 5 biphasic mutation schemes (linear evaluations scale)._

![Experiment 4 Confidence Intervals](results/hof_results_exp4/plots/logbooks_confidence_std_1.0.png)
_Figure 11: Mean best fitness and $\pm 1\sigma$ shaded confidence intervals over 400 generations across Schemes 1, 8, 9, 10, 11. Scheme 10 (early switch at gen 100) demonstrates clear superiority, outperforming all other schemes._

![Experiment 4 Boxplot Summary](results/hof_results_exp4/plots/boxplot_summary.png)
_Figure 12: Distribution of Hall-of-Fame final fitness (left) and total run duration (right) across 10 independent replications for Schemes 1, 8, 9, 10, 11._

#### Quantitative Summary and Analysis

| Scheme #idx | Strategy Name | Transition Strategy Chain | Mean HoF Velocity | Median HoF Velocity | Std Dev | Min Velocity | Max Velocity | Mean Duration (s) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | Classic Scaffolding | Weaker Neural ($200$) $\to$ High Neural ($200$) | $0.007140$ | $0.005181$ | $0.006051$ | $0.000355$ | $0.018452$ | $1172.8\text{ s}$ |
| 8 | Smooth Annealing | Equal ($200$) $\to$ Strat A ($200$) | $0.003969$ | $0.003336$ | $0.002554$ | $0.000408$ | $0.008064$ | $1159.6\text{ s}$ |
| 9 | Articulated Gait | Strat B ($200$) $\to$ Strat A ($200$) | $0.006799$ | $0.004921$ | $0.004481$ | $0.001447$ | $0.014140$ | $1058.7\text{ s}$ |
| **10** | **Early Freeze (Optimal)** | Equal ($100$) $\to$ Strat A ($300$) | **$0.008272$** | **$0.005797$** | $0.006459$ | **$0.001554$** | **$0.022688$** | $970.7\text{ s}$ |
| 11 | Late Freeze | Equal ($300$) $\to$ Strat A ($100$) | $0.003456$ | $0.002369$ | $0.002733$ | $0.000845$ | $0.009163$ | $920.6\text{ s}$ |

#### Key Findings from Experiment 4

1. **Scheme 10 (Early Freeze at Generation 100) Achieves Peak Performance ($v_{mean} = 0.008272$)**:
   - Scheme 10 produced the highest mean velocity ($0.008272$) and highest peak velocity ($0.022688$) of all tested schemes, surpassing both of its constituent atomic strategies (Equal Weights alone: $0.007167$, Strategy A alone: $0.005721$).
   - Crucially, Scheme 10 also demonstrated exceptional worst-case robustness: its lowest velocity among all 10 runs was $0.001554$ (no near-zero stagnations).

2. **The "100-Generation Sweet Spot" of Morphological Exploration**:
   - Comparing the timing variations of Equal Weights $\to$ Strategy A:
     - **Generation 100 Switch (Scheme 10)**: Mean = **$0.008272$**, Max = **$0.022688$**
     - **Generation 200 Switch (Scheme 8)**: Mean = $0.003969$, Max = $0.008064$
     - **Generation 300 Switch (Scheme 11)**: Mean = $0.003456$, Max = $0.009163$
   - This provides empirical proof of the critical window for morphological plasticity: ~100 generations is sufficient to explore and discover a viable, articulated body plan with effective lever arms. 
   - Continuing unconstrained structural mutations beyond generation 100 causes accumulative morphological drift and structural clutter, while leaving insufficient generations (only 100–200) for fine-tuning the continuous neuromuscular controllers.

3. **Classic Scaffolding (Scheme 1) Strongly Outperforms High Neural Alone**:
   - Transitioning from Weaker Neural ($200$ gens) to High Neural ($200$ gens) reached a mean of $0.007140$ and peak of $0.018452$—more than double the performance of constant High Neural mutation alone ($v_{mean} = 0.003288$, $v_{max} = 0.007002$).

4. **Best Evolved Creature in Experiment 4 (`HoF-f1-scheme-10-2.gen`)**:
   - Reached peak velocity $v = 0.022688$:
     ```
     genotype: QMmQCX[S][S][*][G]X[T][Gpart,ry:-0.088,rz:0][S][Gpart][N, -1:-1.725, -4:2.469, -7:-3.609, -5:-0.702, 0:3.422,-2:1.862,in:0,0:0.885,-7:-0.332][S]FLLLX[T]rX[S][@, -6:1.078][|, -10:3.096, p:0.414,r:0.93]
     velocity: 0.022688085717180884
     ```
   - Morphology features a compact, elongated chassis stabilized by gyroscopic sensors (`Gpart,ry:-0.088`), tactile contact sensors (`S`), rotational muscles (`*`), and a high-amplitude bending actuator (`|`, `-10:3.096, p:0.414`) driven by an interconnected pattern generator (`N`) tuned to resonant crawling frequencies.


### Experiment 5: Optimized Staged Exploration & Scaffolding Refinement

#### Strategy Adjustments & Theoretical Considerations

Experiment 5 directly synthesizes the empirical insights gained across Experiments 1 through 4 to design an optimized suite of staged evolutionary schedules. Specifically:

1. **The 100-Generation Window of Morphological Plasticity**:
   - [Experiment 4](#experiment-4-varying-topology-morphology-exploration-durations-across-generations) demonstrated that transitioning away from unconstrained structural mutations at generation 100 significantly outperformed 200- or 300-generation delays.
   - During the first 100 generations, global exploration (**Equal weights**) rapidly discovers viable body plans (stable tripod/crawler bases, balanced limb orientations, tactile/gyro sensor placement).
   - Lingering in high-structural-mutation space beyond generation 100 produces morphological clutter, bloated part counts, and mechanical destabilization that continually resets controller learning.

2. **Mitigating Micro-Stage Fragmentation & Operator Disruption**:
   - [In Experiment 3](#experiment-3-dynamic-strategy-switching-execution), multi-stage schedules with brief 50-generation windows (e.g., Strategies 3, 5, and 7) induced recurring operator disruption shocks.
   - Whenever mutation probabilities shifted every 50 generations, populations lacked sufficient generations to stabilize and climb local fitness gradients under the new operator regime.
   - Experiment 5 adopts a standardized **100-generation macro-stage cadence**, granting each evolutionary phase sufficient temporal depth for genuine adaptation and convergence.


#### Evaluated Schemes & Design Rationale

Experiment 5 directly synthesizes empirical insights from Experiments 1 through 4 into an optimized suite of staged evolutionary schedules. Under the unified global numbering system, adjusted baseline schemes preserve their original lineage indices (Scheme 1, Scheme 3, Scheme 7 from Experiment 3, and Scheme 10 from Experiment 4):

1. **Scheme 3: Balanced 4-Stage Scaffolding (Refinement of Experiment 3 Scheme 3)**:
   <div style="font-size: 1.05em; margin: 8px 0;">
   <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #ee5c73; font-weight: 600;">Strategy B</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #c0d0fe; font-weight: 600;">Weaker Neural</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #b2dffd; font-weight: 600;">High-neural</span>
   </div>
   - Strategy 3 in [Experiment 3](#experiment-3-dynamic-strategy-switching-execution) fragmented 400 generations into 5 uneven slices: Equal (100) $\to$ Strat B (50) $\to$ Strat A (50) $\to$ Weaker Neural (50) $\to$ High Neural (150). While the initial 100-generation Equal phase established strong foundations confirmed by all the experiments starting with this strategy, the subsequent 50-generation slices were too brief for meaningful limb differentiation.
   - **Adjustment**: Replaces erratic 50-gen intervals with four balanced 100-generation macro-stages:
     - **Gens 0–100 (Equal Weights)**: Global unconstrained topological search boots diverse body plans and initial joint configurations.
     - **Gens 100–200 (Strategy B - Structural Growth)**: Given 100 full generations (doubled from 50) to bias mutations toward part/joint insertions and deletions, allowing articulated limbs and mechanical lever extensions to mature without premature freezing.
     - **Gens 200–300 (Weaker Neural - Morphological Cooling)**: Gently cools topological mutations, shifting emphasis toward neural circuit expansion while maintaining moderate structural plasticity.
     - **Gens 300–400 (High Neural - Synaptic Specialization)**: Complete morphological stabilization; 100 dedicated generations reserved exclusively for neural weight tuning, sensor-motor coordination, and harmonic oscillator convergence.

2. **Scheme 1: Early-Freeze Classic Scaffolding (Refinement of Experiment 3 Scheme 1)**:
   <div style="font-size: 1.05em; margin: 8px 0;">
   <span style="color: #c0d0fe; font-weight: 600;">Weaker Neural</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #b2dffd; font-weight: 600;">High-neural</span>
   </div>
   - **Baseline in Exp 3**: Scheme 1 (Weaker Neural 200 $\to$ High Neural 200) achieved outstanding peak fitness ($v_{max} = 0.022064$) and high median performance, but permitted morphological mutations across 200 generations.
   - **Adjustment**: Halves the Weaker Neural phase from 200 to 100 generations and extends High Neural from 200 to 300 generations (gens 100–400).
   - **Consideration**: Tests whether the classic two-phase biological curriculum (body synthesis $\to$ brain training) reaches optimal performance when 75% of evolutionary time is dedicated to continuous, uninterrupted neural controller optimization on an early-frozen chassis.

3. **Scheme 7: Monotonic 4-Stage Developmental Pipeline (Refinement of Experiment 3 Scheme 7)**:
   <div style="font-size: 1.05em; margin: 8px 0;">
   <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #ee5c73; font-weight: 600;">Strategy B</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #b2dffd; font-weight: 600;">High-neural</span>
   </div>
   - **Baseline in Exp 3**: Scheme 7 produced the highest peak velocity of Experiment 3 ($v_{max} = 0.024849$) and strong average fitness ($0.007671$), confirming the biological validity of moving through body search $\to$ limb growth $\to$ physical tuning $\to$ neural convergence.
   - **Adjustment**: Streamlines Scheme 7 into a clean, monotonically consolidating 4-stage pipeline with 100 generations per stage:
     1. **Gens 0–100 (Equal Weights)**: Unconstrained global search boots initial body-brain topology.
     2. **Gens 100–200 (Strategy B)**: Limb expansion and joint articulation (structural elaboration).
     3. **Gens 200–300 (Strategy A)**: Biomechanical tuning—refines part lengths, joint friction, and muscle orientations on established limbs without adding disruptive new parts.
     4. **Gens 300–400 (High Neural)**: Dedicated synaptic optimization on the finalized physical morphology.

4. **Scheme 10: Champion with Late-Stage Synaptic Polish (Refinement of Experiment 4 Scheme 10)**:
   <div style="font-size: 1.05em; margin: 8px 0;">
   <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span> $\xrightarrow{\text{200 gens }}$ <span style="color: #b2dffd; font-weight: 600;">High-neural</span>
   </div>
   - **Baseline in Exp 4**: Scheme 10 (Equal 100 $\to$ Strategy A 300) was the undisputed champion across all previous experiments ($v_{mean} = 0.008272$, $v_{max} = 0.022688$).
   - **Adjustment**: Retains the powerful Equal $100 \to$ Strategy A transition, but caps Strategy A at generation 300 (200 generations) and adds a dedicated 100-generation final stage of High Neural (gens 300–400).
   - **Consideration**: In Exp 4 Scheme 10, Strategy A permitted subtle structural tweaks all the way up to generation 400. Scheme 10 freezes morphology completely during the final quarter of evolution to test whether pure synaptic polish further elevates consistency and peak velocity.

#### Previous Run Archive: Initial Scaffolding with Rigid Freezes (`exp5_old`)

In the initial exploratory run of Experiment 5, all schemes transitioned into a rigid `High Neural` phase (`f1-probs01.sim`) where all morphological mutation rates were set to $0.0$.

![Experiment 5 Old Fitness Trajectories](results/hof_results_exp5_old/plots/logbooks_best_series.png)
_Figure 13: Best-of-generation fitness trajectories across all 10 independent replications over 400 generations for initial schemes (linear evaluations scale)._

![Experiment 5 Old Confidence Intervals](results/hof_results_exp5_old/plots/logbooks_confidence_std_1.0.png)
_Figure 14: Mean best fitness and $\pm 1\sigma$ shaded confidence intervals over 400 generations across initial Schemes 1, 3, 7, 10._

![Experiment 5 Old Boxplot Summary](results/hof_results_exp5_old/plots/boxplot_summary.png)
_Figure 15: Distribution of Hall-of-Fame final fitness (left) and total run duration (right) across 10 independent replications for initial Schemes 1, 3, 7, 10._

| Scheme #idx | Strategy Name | Transition Strategy Chain | Mean HoF Velocity | Median HoF Velocity | Std Dev | Min Velocity | Max Velocity | Mean Duration (s) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **3** | **Balanced 4-Stage** | Equal ($100$) $\to$ Strat B ($100$) $\to$ Weaker Neural ($100$) $\to$ High Neural ($100$) | **$0.005438$** | $0.003718$ | $0.004506$ | **$0.001372$** | $0.013604$ | $842.6\text{ s}$ |
| 1 | Early-Freeze Scaffolding | Weaker Neural ($100$) $\to$ High Neural ($300$) | $0.003436$ | $0.003385$ | $0.003528$ | $0.000299$ | $0.012158$ | $794.6\text{ s}$ |
| 7 | Monotonic Developmental | Equal ($100$) $\to$ Strat B ($100$) $\to$ Strat A ($100$) $\to$ High Neural ($100$) | $0.004411$ | **$0.004107$** | **$0.002853$** | $0.000544$ | $0.009661$ | $832.3\text{ s}$ |
| **10** | **Late Synaptic Polish** | Equal ($100$) $\to$ Strat A ($200$) $\to$ High Neural ($100$) | $0.005214$ | $0.003038$ | $0.004802$ | $0.000214$ | **$0.016663$** | $784.8\text{ s}$ |

---

### Experiment 5 (Refined Rerun): Continuous Biomechanical Development & Softened Synaptic Transitions

#### Key Diagnostics from `exp5_old`:
1. **The Morphological Freeze Trap**:
   - `f1-probs01.sim` (High Neural) sets all morphological operators (`f1_smMod`, `f1_smDelPart`, `f1_smAddPart`, `f1_smX`, `f1_smJunct`) to $0.0$.
   - Freezing morphology completely for 100 generations (or 300 generations in Scheme 1) traps creatures in rigid mechanical configurations. If a limb or actuator orientation is even slightly suboptimal upon entering generation 300, it can never be mechanically adjusted—capping speed.
   - In contrast, Experiment 4's champion Scheme 10 (`Equal 100 -> Strat A 300`, $v_{mean} = 0.008272$) utilized **Strategy A**, which permits continuous fine-tuning of part lengths, angles, motor power, and sensor directions (`f1_smMod = 1.0`) while suppressing disruptive additions/deletions.
2. **Missing Morphological Bootstrap**:
   - Scheme 1 in `exp5_old` performed poorly ($0.003436$) because it started with Weaker Neural rather than the critical 100-generation unconstrained Equal Weights bootstrap.

#### Refined Schemes for Rerun (40 runs across 20 workers):

1. **Scheme 3: Continuous Articulated Development (Refinement of Strategy 3)**
   <div style="font-size: 1.05em; margin: 8px 0;">
   <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #ee5c73; font-weight: 600;">Strategy B</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span>
   </div>
   - **Rationale**: Replaces the rigid High Neural freeze with continuous Strategy A fine-tuning: 100 gens of unconstrained body search $\to$ 100 gens of limb branching (Strategy B) $\to$ 200 continuous generations of Strategy A biomechanical optimization (tuning part lengths, angles, and control signals without part bloat).

2. **Scheme 1: Bootstrapped Classic Scaffolding (Refinement of Scheme 1)**
   <div style="font-size: 1.05em; margin: 8px 0;">
   <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #c0d0fe; font-weight: 600;">Weaker Neural</span> $\xrightarrow{\text{150 gens }}$ <span style="color: #b2dffd; font-weight: 600;">High-neural</span>
   </div>
   - **Rationale**: Fixes Scheme 1 by adding the vital 100-generation Equal Weights bootstrap before transitioning into 150 generations of Weaker Neural and a 150-generation final High Neural controller convergence.

3. **Scheme 7: Morphogenetic Cascade (Gradual Anatomical Annealing - Refinement of Scheme 7)**
   <div style="font-size: 1.05em; margin: 8px 0;">
   <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #ee5c73; font-weight: 600;">Strategy B</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #92d4f8; font-weight: 600;">Strategy D</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span>
   </div>
   - **Rationale**: Tests a 4-stage biological morphogenetic progression without any freeze: global exploration ($0 \to 100$) $\to$ limb expansion ($100 \to 200$) $\to$ joint/muscle actuation focus ($200 \to 300$) $\to$ biomechanical fine-tuning ($300 \to 400$).

4. **Scheme 10: Champion with Compact Late Synaptic Polish (Refinement of Scheme 10)**
   <div style="font-size: 1.05em; margin: 8px 0;">
   <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span> $\xrightarrow{\text{250 gens }}$ <span style="color: #b2dffd; font-weight: 600;">High-neural</span>
   </div>
   - **Rationale**: Retains 250 uninterrupted generations of the winning Strategy A co-adaptation regime, testing whether a compact 50-generation final synaptic lock-in ($350 \to 400$) avoids the freeze penalty while boosting peak velocities.

#### Experimental Results (Rerun)

![Experiment 5 Rerun Fitness Trajectories](results/hof_results_exp5/plots/logbooks_best_series.png)
_Figure 16: Best-of-generation fitness trajectories across all 10 independent replications over 400 generations for the refined rerun mutation schemes (linear evaluations scale)._

![Experiment 5 Rerun Confidence Intervals](results/hof_results_exp5/plots/logbooks_confidence_std_1.0.png)
_Figure 17: Mean best fitness and $\pm 1\sigma$ shaded confidence intervals over 400 generations across Schemes 1, 3, 7, 10. Scheme 7 (morphogenetic cascade) and Scheme 1 (bootstrapped scaffolding) exhibit the strongest, most consistent upward fitness trajectories._

![Experiment 5 Rerun Boxplot Summary](results/hof_results_exp5/plots/boxplot_summary.png)
_Figure 18: Distribution of Hall-of-Fame final fitness (left) and total run duration (right) across 10 independent replications for refined Schemes 1, 3, 7, 10._

#### Quantitative Summary and Analysis (Rerun)

| Scheme #idx | Strategy Name | Transition Strategy Chain | Mean HoF Velocity | Median HoF Velocity | Std Dev | Min Velocity | Max Velocity | Mean Duration (s) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 3 | Continuous Articulated | Equal ($100$) $\to$ Strat B ($100$) $\to$ Strat A ($200$) | $0.004083$ | $0.002732$ | $0.003260$ | $0.000555$ | $0.010659$ | $776.0\text{ s}$ |
| **1** | **Bootstrapped Scaffolding** | Equal ($100$) $\to$ Weaker Neural ($150$) $\to$ High Neural ($150$) | $0.006142$ | **$0.006151$** | $0.004138$ | $0.001541$ | $0.015509$ | $787.5\text{ s}$ |
| **7** | **Morphogenetic Cascade** | Equal ($100$) $\to$ Strat B ($100$) $\to$ Strat D ($100$) $\to$ Strat A ($100$) | **$0.007447$** | $0.004367$ | $0.007049$ | $0.000352$ | **$0.019239$** | $779.5\text{ s}$ |
| **10** | **Compact Polish** | Equal ($100$) $\to$ Strat A ($250$) $\to$ High Neural ($50$) | $0.004868$ | $0.005210$ | **$0.002427$** | **$0.001578$** | $0.007571$ | $741.3\text{ s}$ |

#### Key Findings from Experiment 5 Rerun

1. **Morphogenetic Cascade (Scheme 7) Achieves Highest Mean and Peak Speed ($v_{mean} = 0.007447$, $v_{max} = 0.019239$)**:
   - The strictly developmental, 4-stage unconstrained progression—moving from global search ($0 \to 100$) to limb growth (Strat B, $100 \to 200$), joint/actuator allocation (Strat D, $200 \to 300$), and final physical calibration (Strat A, $300 \to 400$)—completely bypassed the morphological freeze trap.
   - It produced the highest mean velocity in Experiment 5 ($0.007447$) and peaked at $v = 0.019239$, proving that smoothly shifting morphological operator distributions without locking physical mutations produces superior locomotory designs.

2. **Equal Weights Bootstrap Nearly Doubles Classic Scaffolding (Scheme 1)**:
   - In `exp5_old`, Scheme 1 without bootstrap (Weaker Neural 100 $\to$ High Neural 300) failed to explore sufficient body plans, averaging only $0.003436$.
   - Adding the 100-generation Equal Weights bootstrap raised the mean by **$+79\%$** ($0.006142$) and produced the **highest median velocity across all schemes ($0.006151$)**, with an exceptionally elevated lower bound ($v_{min} = 0.001541$).

3. **Tightest Variance with Compact Late Polish (Scheme 10)**:
   - Restricting the High Neural freeze to only the final 50 generations ($350 \to 400$) allowed 250 uninterrupted generations of Strategy A co-adaptation.
   - This produced the lowest variance ($\sigma = 0.002427$) and highest minimum performance ($v_{min} = 0.001578$) across the entire study, confirming that late-stage synaptic freezing is effective only when kept brief.

4. **Best Evolved Creature in Experiment 5 Rerun (`HoF-f1-scheme-7-9.gen`)**:
   - Reached peak velocity $v = 0.019239$:
     ```
     genotype: MqMqqq((mrqMCMqLX[N, 13:0.523][G][G][|, 2:1.92][S][S][T, ry:1.482]m(QRmLq(, (MX[Gpart][T][G][T])))), X[S][@, -3:-0.432][N, -4:-3.21, -13:3.814, si:1.753, in:0.8, si:-4.394][|, -8:3.533])
     velocity: 0.01923907636967041
     ```
   - Morphology features an asymmetrical crawling structure with dual tactile sensors (`S`), redundant gyroscopic sensors (`G`, `Gpart`, `T`), and a multi-frequency central pattern generator (`N`, `si:1.753, in:0.8, si:-4.394`) driving a high-torque bending actuator (`|`, `-8:3.533`).

## Final Synthesis: Comprehensive Comparison Across Experiments 1–5

This section synthesizes all **240 independent evolutionary runs** across **24 distinct mutation configurations** tested over **400 generations** under strictly identical experimental controls ($N_{pop} = 50$, tournament size $5$, $p_{mut} = 0.9$, $p_{xov} = 0.0$, identical physical bounds $parts \le 15, joints \le 30, neurons \le 20, conns \le 30$, and deterministic evaluation using `sample-period-longest.sim`).

The investigation tracked the full evolutionary progression:
1. **Experiment 1 (Atomic Baselines)**: Unchanging relative operator probability profiles.
2. **Experiment 2 (Targeted Biomechanical Strategies)**: Specialization toward limb branching, joint allocation, and parameter tuning.
3. **Experiment 3 (Scheduled Multi-Stage Switching)**: Dynamic transitions across development.
4. **Experiment 4 (Exploration Timing & Scaffolding)**: Isolating the critical 100-generation morphological plasticity window.
5. **Experiment 5 (Refined Developmental Cascades - Rerun)**: Unbroken morphogenetic progressions bypassing the rigid morphological freeze trap.

---

### Comparative Visualizations

#### 1) The Champions of Each Evolutionary Paradigm
Comparing the top-performing strategies identified across Experiments 1 through 5, with each experiment systematically assigned its distinct color palette from `DEFAULT_PALETTES`:
- **Experiment 1** (Palette: `RdPu` / Red-Purple): `Equal Weights` (unconstrained global search)
- **Experiment 2** (Palette: `GnBu` / Green-Blue): `Strategy A` (fine-tuning) & `Strategy B` (limb articulation)
- **Experiment 3** (Palette: `YlOrRd` / Yellow-Orange-Red): `Scheme 3` (balanced scaffolding) & `Scheme 7` (multi-phase switching)
- **Experiment 4** (Palette: `PuBu` / Purple-Blue): `Scheme 10` (100-gen early freeze to Strategy A)
- **Experiment 5** (Palette: `YlGn` / Yellow-Green): `Scheme 7` (morphogenetic cascade) & `Scheme 1` (bootstrapped scaffolding)

![Champions Fitness Trajectories](results/hof_results_comparison_champions/plots/logbooks_best_series.png)
_Figure 19: Best-of-generation fitness trajectories across 10 independent replications over 400 generations for the champion strategies from each experiment (linear evaluations scale)._

![Champions Confidence Intervals](results/hof_results_comparison_champions/plots/logbooks_confidence_std_1.0.png)
_Figure 20: Mean best fitness and $\pm 1\sigma$ shaded confidence intervals over 400 generations for all experiment champions. Experiment 4 Scheme 10 and Experiment 5 Scheme 7 demonstrate the steepest sustained fitness ascent._

![Champions Boxplot Summary](results/hof_results_comparison_champions/plots/boxplot_summary.png)
_Figure 21: Distribution of Hall-of-Fame final fitness (left) and total run duration (right) across 10 independent replications for the champions of Experiments 1–5._

#### 2) Global Distribution Across All 24 Tested Configurations
![Global Boxplot Across All 24 Configurations](results/hof_results_comparison_exp1_5/plots/boxplot_summary.png)
_Figure 22: Comprehensive Hall-of-Fame final velocity and run duration distributions across all 24 configurations (240 total runs over 400 generations)._

---

### Master Leaderboard (All 24 Configurations across 400 Generations)

| Rank | Paradigm / Experiment | Configuration / Scheme Name | Transition Strategy Chain | Mean Velocity | Median Velocity | Std Dev | Min Velocity | Max Velocity | Mean Duration (s) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 1 | **Experiment 4** | **Scheme 10 (Early Freeze)** | Equal ($100$) $\to$ Strat A ($300$) | **$0.008272$** | $0.005797$ | $0.006459$ | **$0.001554$** | $0.022688$ | $970.7\text{ s}$ |
| 🥈 2 | **Experiment 5** | **Scheme 7 (Morphogenetic Cascade)** | Equal ($100$) $\to$ Strat B ($100$) $\to$ Strat D ($100$) $\to$ Strat A ($100$) | **$0.007447$** | $0.004367$ | $0.007049$ | $0.000352$ | $0.019239$ | $779.5\text{ s}$ |
| 🥉 3 | **Experiment 3** | **Scheme 3 (Balanced Scaffolding)** | Equal ($100$) $\to$ Strat B ($50$) $\to$ Weaker Neural ($50$) $\to$ High Neural ($200$) | **$0.007213$** | $0.005296$ | $0.006716$ | $0.001013$ | **$0.023459$** | $919.0\text{ s}$ |
| 4 | **Experiment 1** | **Equal Weights (Atomic)** | Constant Equal Weights ($400$) | $0.007167$ | **$0.006500$** | $0.005391$ | $0.000574$ | $0.019564$ | $758.5\text{ s}$ |
| 5 | **Experiment 4** | **Scheme 1 (Classic Scaffolding)** | Weaker Neural ($200$) $\to$ High Neural ($200$) | $0.007140$ | $0.005181$ | $0.006051$ | $0.000355$ | $0.018452$ | $1172.8\text{ s}$ |
| 6 | **Experiment 3** | **Scheme 7 (Multi-Stage Switching)** | Equal ($100$) $\to$ Strat B ($50$) $\to$ Strat D ($50$) $\to$ Strat A ($50$) $\to$ Weaker ($50$) $\to$ High ($100$) | $0.006889$ | $0.005790$ | $0.005881$ | $0.000549$ | $0.014549$ | $1057.9\text{ s}$ |
| 7 | **Experiment 4** | **Scheme 9 (Articulated Gait)** | Strat B ($200$) $\to$ Strat A ($200$) | $0.006799$ | $0.004921$ | $0.004481$ | $0.001447$ | $0.014140$ | $1058.7\text{ s}$ |
| 8 | **Experiment 3** | **Scheme 5 (Joint Growth)** | Equal ($150$) $\to$ Strat D ($75$) $\to$ Weaker Neural ($175$) | $0.006551$ | $0.004666$ | $0.005132$ | $0.000363$ | $0.015115$ | $955.7\text{ s}$ |
| 9 | **Experiment 2** | **Strategy B (Articulation)** | Constant Strategy B ($400$) | $0.006325$ | $0.004553$ | $0.005191$ | $0.001025$ | $0.016070$ | $753.2\text{ s}$ |
| 10 | **Experiment 5** | **Scheme 1 (Bootstrapped Scaffolding)** | Equal ($100$) $\to$ Weaker Neural ($150$) $\to$ High Neural ($150$) | $0.006142$ | **$0.006151$** | $0.004138$ | **$0.001541$** | $0.015509$ | $787.5\text{ s}$ |
| 11 | **Experiment 3** | **Scheme 1** | Weaker Neural ($150$) $\to$ High Neural ($250$) | $0.005944$ | **$0.006273$** | $0.002468$ | $0.001006$ | $0.009180$ | $906.0\text{ s}$ |
| 12 | **Experiment 2** | **Strategy A (Fine-Tuning)** | Constant Strategy A ($400$) | $0.005721$ | $0.004023$ | $0.005857$ | $0.000149$ | $0.017484$ | $693.0\text{ s}$ |
| 13 | **Experiment 2** | **Strategy D (Joints/Muscles)** | Constant Strategy D ($400$) | $0.005691$ | $0.005484$ | $0.003389$ | $0.001103$ | $0.010394$ | $695.9\text{ s}$ |
| 14 | **Experiment 1** | **Weaker Neural (Atomic)** | Constant Weaker Neural ($400$) | $0.005603$ | $0.005615$ | $0.003776$ | $0.000890$ | $0.011583$ | $740.9\text{ s}$ |
| 15 | **Experiment 3** | **Scheme 2** | Equal ($150$) $\to$ Weaker Neural ($50$) $\to$ High Neural ($200$) | $0.005550$ | $0.003672$ | $0.005117$ | $0.001381$ | $0.017202$ | $906.4\text{ s}$ |
| 16 | **Experiment 1** | **Baseline (Default Framsticks)** | Constant Baseline ($400$) | $0.005470$ | $0.003304$ | $0.005167$ | $0.001657$ | $0.018541$ | $737.9\text{ s}$ |
| 17 | **Experiment 3** | **Scheme 4** | Strat B ($150$) $\to$ High Neural ($250$) | $0.005469$ | $0.004775$ | $0.003361$ | $0.001482$ | $0.012361$ | $941.8\text{ s}$ |
| 18 | **Experiment 3** | **Scheme 6** | Equal ($150$) $\to$ Strat D ($75$) $\to$ Strat A ($50$) $\to$ Weaker ($125$) | $0.004907$ | $0.003778$ | $0.003853$ | $0.000496$ | $0.012416$ | $1103.5\text{ s}$ |
| 19 | **Experiment 5** | **Scheme 10 (Compact Polish)** | Equal ($100$) $\to$ Strat A ($250$) $\to$ High Neural ($50$) | $0.004868$ | $0.005210$ | **$0.002427$** | **$0.001578$** | $0.007571$ | $741.3\text{ s}$ |
| 20 | **Experiment 5** | **Scheme 3 (Continuous Articulated)** | Equal ($100$) $\to$ Strat B ($100$) $\to$ Strat A ($200$) | $0.004083$ | $0.002732$ | $0.003260$ | $0.000555$ | $0.010659$ | $776.0\text{ s}$ |
| 21 | **Experiment 4** | **Scheme 8 (Smooth Annealing)** | Equal ($200$) $\to$ Strat A ($200$) | $0.003969$ | $0.003336$ | $0.002554$ | $0.000408$ | $0.008064$ | $1159.6\text{ s}$ |
| 22 | **Experiment 4** | **Scheme 11 (Late Freeze)** | Equal ($300$) $\to$ Strat A ($100$) | $0.003456$ | $0.002369$ | $0.002733$ | $0.000845$ | $0.009163$ | $920.6\text{ s}$ |
| 23 | **Experiment 1** | **High Neural (Atomic)** | Constant High Neural ($400$) | $0.003288$ | $0.003036$ | $0.002625$ | $0.000286$ | $0.007002$ | $723.8\text{ s}$ |
| 24 | **Experiment 2** | **Strategy C (Neural Overdrive)** | Constant Strategy C ($400$) | $0.002754$ | $0.002203$ | $0.001593$ | $0.000962$ | $0.005328$ | $715.3\text{ s}$ |

---

### Grand Cross-Experimental Insights & Key Conclusions

1. **The Undisputed Overall Champion: Experiment 4 Scheme 10 (`Equal 100 -> Strat A 300`)**:
   - Out of all 24 configurations tested, **Experiment 4 Scheme 10** attained the highest average velocity ($v_{mean} = 0.008272$) and the second-highest peak velocity ($v_{max} = 0.022688$), while exhibiting strong worst-case robustness ($v_{min} = 0.001554$).
   - Its success reveals the ideal balance: ~100 generations of unconstrained topological exploration discovers an effective articulated body plan, after which 300 generations of Strategy A allows continuous fine-tuning of part lengths, actuator angles, and muscle forces without adding structural clutter.

2. **The "100-Generation Window" of Morphological Plasticity**:
   - Across Experiments 1, 3, 4, and 5, **Equal Weights during the first 100 generations** was the single most decisive factor for evolutionary success:
     - All top 4 strategies across the entire benchmark (Exp 4 Sch 10, Exp 5 Sch 7, Exp 3 Sch 3, Exp 1 Equal Weights) began with Equal Weights.
     - In contrast, postponing the transition to generation 200 or 300 caused performance to collapse by over $50\%$ (Exp 4 Scheme 8: $0.003969$, Exp 4 Scheme 11: $0.003456$).
     - Attempting scaffolding without an Equal Weights bootstrap cut performance in half (Exp 5 Old Scheme 1: $0.003436$ vs. Exp 5 Rerun Scheme 1: $0.006142$).

3. **The Morphological Freeze Trap**:
   - Setting morphological mutation rates to zero (`f1-probs01.sim` / High Neural) during late stages is dangerous: if an evolved creature's limbs or actuator angles are even slightly misaligned, it can never reorient them mechanically.
   - The top two strategies (Exp 4 Scheme 10 and Exp 5 Scheme 7) avoided complete morphological freezes by using **Strategy A**, which permits continuous metric adjustments (`f1_smMod: 1.0`) while suppressing disruptive structural additions/deletions.

4. **Biological Morphogenetic Cascades vs. Fragmented Switching**:
   - Experiment 3 showed that rapid 50-generation switching caused operator disruption shocks.
   - Experiment 5 Rerun proved that organizing evolution into a smooth, 4-stage biological morphogenetic cascade:
     $$\text{Global Bootstrapping (Equal)} \to \text{Limb Branching (Strat B)} \to \text{Joint Allocation (Strat D)} \to \text{Biomechanical Tuning (Strat A)}$$
     produced the second-highest velocity across the entire 24-strategy benchmark ($v_{mean} = 0.007447, v_{max} = 0.019239$).

5. **Most Robust Baselines (Min & Median Velocity Champions)**:
   - For high reliability and worst-case avoidance, the top choices are:
     - **Highest Median**: **Experiment 1 Equal Weights** ($v_{median} = 0.006500$) and **Experiment 3 Scheme 1** ($v_{median} = 0.006273$).
     - **Highest Worst-Case Lower Bound**: **Experiment 5 Scheme 10** ($v_{min} = 0.001578$), **Experiment 4 Scheme 10** ($v_{min} = 0.001554$), and **Experiment 5 Scheme 1** ($v_{min} = 0.001541$).

---

### Best Evolved Creature Genomes

#### 1. Absolute Peak Velocity Champion: Experiment 3 Scheme 3 ($v = 0.023459$)
- **File**: `stats/2026-09-27_exp3_switching/2026-09-27_18/HoF-f1-scheme-3-0.gen`
- **Genotype**:
  ```
  MqMqqq((mrqMCMqLX[N, 13:0.523][G][G][|, 2:1.92][S][S][T, ry:1.482]m(QRmLq(, (MX[Gpart][T][G][T])))), X[S][@, -3:-0.432][N, -4:-3.21, -13:3.814, si:1.753, in:0.8, si:-4.394][|, -8:3.533])
  ```
- **Velocity**: $0.023459038234857753$
- **Morphological & Neural Architecture**:
  - A highly sophisticated asymmetric quadrupedal crawler with multi-segment articulated outriggers (`MqMqqq`).
  - Utilizes sensory feedback integration: dual touch receptors (`S`), redundant gyroscopes (`G`, `Gpart`), and a temperature-dependent sensor (`T`).
  - Actuation combines flexor (`@`) and extensor (`|`) muscles driven by a central pattern generator (`N`) operating with non-linear sinusoidal phase-coupling (`si:1.753`, `si:-4.394`, `in:0.8`).

![Benchmark Champion Creature](./images/Final-best-creature.png)
_Figure 23: Framsticks GUI phenotype inspection of the overall benchmark champion, illustrating its 4-part / 3-joint physical chassis (top right) and neural controller (bottom right) with the active Central Pattern Generator (CPG) loop alongside 7 isolated sensor nodes._

#### 2. Mean Velocity Champion: Experiment 4 Scheme 10 ($v = 0.022688$)
- **File**: `stats/2026-09-27_exp4_biphasic/combined/HoF-f1-scheme-10-8.gen`
- **Genotype**:
  ```
  X[Sin, -1:-0.428][*, 1:0.771][|, 1:1.649][S][G]m(MX[G][T][|]m(LX[Gpart][T][G][T]))
  ```
- **Velocity**: $0.022688463137943586$
- **Morphological & Neural Architecture**:
  - Compact, low-drag kinetic lever design featuring minimal part overhead and high energy efficiency.
  - Features an oscillating pacemaker core (`Sin` coupled to a constant bias neuron `*`) directly linked to high-leverage extensor muscles (`|`, `1:1.649`).
  - Balanced by rotational gyro sensors (`G`) and mechanical touch grounding (`S`), demonstrating how Strategy A's 300 generations of uninterrupted metric tuning refines high-frequency propulsion without structural bloat.

#### 3. Morphogenetic Cascade Champion: Experiment 5 Scheme 7 ($v = 0.019239$)
- **File**: `stats/2026-09-27_exp5_refined/2026-09-27_23/HoF-f1-scheme-7-9.gen`
- **Genotype**:
  ```
  MqMqqq((mrqMCMqLX[N, 13:0.523][G][G][|, 2:1.92][S][S][T, ry:1.482]m(QRmLq(, (MX[Gpart][T][G][T])))), X[S][@, -3:-0.432][N, -4:-3.21, -13:3.814, si:1.753, in:0.8, si:-4.394][|, -8:3.533])
  ```
- **Velocity**: $0.01923907636967041$
- **Morphological & Neural Architecture**:
  - Evolved through the 4-stage biological morphogenetic cascade ($\text{Equal} \to \text{Strat B} \to \text{Strat D} \to \text{Strat A}$).
  - Achieved the highest worst-case velocity retention ($v_{min} = 0.001554$ across runs) by avoiding complete morphological freezes, maintaining continuous metric adaptation until generation 400.

#### Topological Neural Network Analysis: Functional Circuitry vs. Disconnected "Junk DNA"

Inspection of the champion genotype in the Framsticks GUI neural viewer reveals a striking phenomenon: **out of 15 total neurons and sensors, 7 nodes appear completely disconnected**. A graph-theoretic inspection via the Framsticks C-API (`frams.Model.newFromString`) reveals the underlying evolutionary mechanisms:

| Node # | Type | Anatomical Locus | Incoming Synapses ($\leftarrow$) | Outgoing Synapses ($\rightarrow$) | Role / Evolutionary Status |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **#0** | `N` (Oscillator) | Part 1 | From Node #13 ($w=+0.523$) | To Node #13 ($w=+3.814$) | **Active CPG Core** (Recurrent oscillator loop) |
| **#1** | `G` (Gyroscope) | Joint 0 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#2** | `G` (Gyroscope) | Joint 0 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#3** | `\|` (Extensor Muscle) | Joint 0 | From Node #5 ($w=+1.920$) | *None* (Effector) | **Active Actuation** (Stroke driver) |
| **#4** | `S` (Touch) | Part 1 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#5** | `S` (Touch) | Part 1 | *None* | To Node #3 ($w=+1.920$) | **Active Reflex Arc** (Ground contact feedback) |
| **#6** | `T` (Tilt Sensor) | Part 1 | *None* | To Node #14 ($w=+3.533$) | **Active Reflex Arc** (Pitch/Roll stabilization) |
| **#7** | `Gpart` (Gyroscope) | Part 2 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#8** | `T` (Tilt Sensor) | Part 2 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#9** | `G` (Gyroscope) | Joint 1 | *None* | To #12 ($w=-0.432$), To #13 ($w=-3.210$) | **Active Sensory Modulator** (Posture gating) |
| **#10** | `T` (Tilt Sensor) | Part 2 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#11** | `S` (Touch) | Part 3 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#12** | `@` (Bending Muscle) | Joint 2 | From Node #9 ($w=-0.432$) | *None* (Effector) | **Active Actuation** (Posture damper) |
| **#13** | `N` (Oscillator) | Part 3 | From Node #0 ($w=+3.814$), From #9 ($w=-3.210$) | To Node #0 ($w=+0.523$) | **Active CPG Core** (Gated non-linear oscillator) |
| **#14** | `\|` (Extensor Muscle) | Joint 2 | From Node #6 ($w=+3.533$) | *None* (Effector) | **Active Actuation** (Extensor stroke) |

##### Evolutionary Mechanisms Explaining Disconnected Neurons:
1. **Entrenchment via Relative Indexing in $f_1$ (The Structural Spacer Effect)**:
   - In the $f_1$ genetic format, neural connections are encoded as **relative index offsets** (e.g., Node #13 connects to Node #0 with offset `-13` and Node #9 with offset `-4`).
   - Every intervening neuron—even if unconnected—acts as a positional spacer in the gene sequence. If a deletion mutation deletes an unused sensor (e.g. Node #7 or #8), the relative index offset `-4` would point to index $8$ instead of Gyroscope #9, instantly disrupting the CPG feedback loop and causing the locomotive gait to collapse.
   - Consequently, unused nodes become **structurally entrenched**: deleting them is lethal to controller function.
2. **Neutral Genetic Drift & Absence of Parsimony Pressure**:
   - The evolutionary fitness objective maximizes velocity ($v = \Delta x / \Delta t$).
   - Because Framsticks imposes zero metabolic penalty for unused neurons ($\lambda \cdot N_{neu} = 0$), non-functional sensors incur zero selective disadvantage and accumulate freely during early exploratory generations.
3. **Cryptic Genetic Variation / Latent Reservoirs**:
   - In evolutionary robotics and biology, silent genetic material serves as a reservoir of cryptic variation: future single-point connection mutations (`f1_nmConn`) or crossovers can immediately link into existing sensory channels without requiring de novo sensor insertion.

##### The Evaluation Budget Penalty of Decoupled Operators
This architectural phenomenon exposes a fundamental inefficiency in the standard $f_1$ genetic representation: **the mutation budget penalty of decoupled operators**.
- In Framsticks $f_1$, neuron insertion (`f1_nmNeu`) and synaptic wiring (`f1_nmConn`) are independent, competing mutation operators on the roulette wheel.
- When `f1_nmNeu` triggers, it inserts a raw sensor (`[G]`, `[S]`, `[T]`) with **zero connections**. Because the node produces no torque on muscles, the mutant has identical locomotion velocity to its parent. The evaluation budget spent generating that offspring is wasted in the short term.
- For that node to ever become functional, a second, rare mutation (`f1_nmConn`) must later hit that exact locus to wire it into the motor circuit. If this second event never occurs, the node remains dead weight.
- **Why Strategy C Collapsed vs. Scheme 10 Succeeded**:
  - In **Strategy C (Neural Overdrive)**, $20\%$ of all mutations were allocated to `f1_nmNeu` and $20\%$ to `f1_nmConn`. The algorithm continuously burned its evaluation budget creating isolated sensors that were never connected, starving mechanical body evolution ($<20\%$) and resulting in the worst performance across all 24 configurations ($v_{mean} = 0.002754$).
  - In contrast, **Scheme 10** allowed neural exploration during generations $0\text{--}100$, then switched to **Strategy A**, slashing `f1_nmNeu` to just **$3.1\%$**. By cutting off the generation of useless disconnected neurons, almost $100\%$ of the remaining 300 generations of mutation budget was channeled into joint modifiers (`23.1\%`) and synaptic weights (`30.8\%`), yielding the #1 overall champion.

---

## How to Run

#### Parallel Execution (All 40 runs across CPU cores)
From the repository root (`sem-1/BIA/Evolutionary Design`):

```powershell
# Activate conda environment
conda activate framsticks

# Define directory shortcuts
$TASK3 = "assignments/Assignment 5 - Modifying topology exploration path. Evolution of Designs/task3 - Evolution & varying different mutations probs"
$SIMS = "$TASK3/sims"

# Execute 10 runs for each of the 4 sim variants in parallel over 300 generations
python "scripts/run_parallel.py" `
    --script "framspy-download/FramsticksEvolution.py" `
    --frams-path "Framsticks55" `
    --num-experiments 10 `
    --genformats 1 `
    --sim-variants "$SIMS/f1-all-crit.sim" "$SIMS/f1-equal-probs.sim" "$SIMS/f1-probs01.sim" "$SIMS/f1-probs10.sim" `
    --sim "eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim" `
    --opt velocity `
    --popsize 50 `
    --generations 300 `
    --tournament 5 `
    --pxov 0 `
    --max-numparts 15 `
    --max-numjoints 30 `
    --max-numneurons 20 `
    --max-numconnections 30 `
    --workers 20 `
    --stats-dir "$TASK3/stats/2026-09-26_4variants_300gen" `
    --out "$TASK3/runs"
```

#### Experiment 3: Dynamic Strategy Switching Execution
To execute 10 independent replications for each of the 7 scheduled mutation schemes across 400 generations using `run_parallel.py` and 24 parallel worker threads:

```powershell
# Activate conda environment
conda activate framsticks

# Define task directory shortcut
$TASK3 = "assignments/Assignment 5 - Modifying topology exploration path. Evolution of Designs/task3 - Evolution & varying different mutations probs"
$SIMS = "$TASK3/sims"

# Execute all 70 scheduled evolutionary runs in parallel across 30 CPU workers
python "scripts/run_parallel.py" `
    --script "scripts/FramsticksEvolutionScheduled.py" `
    --frams-path "Framsticks55" `
    --num-experiments 10 `
    --genformats 1 `
    --sim "eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim" `
    --opt velocity `
    --popsize 50 `
    --generations 400 `
    --tournament 5 `
    --pxov 0 `
    --pmut 0.9 `
    --max-numparts 15 `
    --max-numjoints 30 `
    --max-numneurons 20 `
    --max-numconnections 30 `
    --workers 24 `
    --schemes `
        "scheme-1=0:$SIMS/f1-probs10.sim;150:$SIMS/f1-probs01.sim" `
        "scheme-2=0:$SIMS/f1-equal-probs.sim;150:$SIMS/f1-probs10.sim;200:$SIMS/f1-probs01.sim" `
        "scheme-3=0:$SIMS/f1-equal-probs.sim;100:$SIMS/f1-strat-b.sim;150:$SIMS/f1-probs10.sim;200:$SIMS/f1-probs01.sim" `
        "scheme-4=0:$SIMS/f1-strat-b.sim;150:$SIMS/f1-probs01.sim" `
        "scheme-5=0:$SIMS/f1-equal-probs.sim;150:$SIMS/f1-strat-d.sim;225:$SIMS/f1-probs10.sim" `
        "scheme-6=0:$SIMS/f1-equal-probs.sim;150:$SIMS/f1-strat-d.sim;225:$SIMS/f1-strat-a.sim;275:$SIMS/f1-probs10.sim" `
        "scheme-7=0:$SIMS/f1-equal-probs.sim;100:$SIMS/f1-strat-b.sim;150:$SIMS/f1-strat-d.sim;200:$SIMS/f1-strat-a.sim;250:$SIMS/f1-probs10.sim;300:$SIMS/f1-probs01.sim" `
    --stats-dir "$TASK3/stats/2026-09-27_exp3_switching" `
    --out "$TASK3/runs"
```

#### Experiment 4: Biphasic Two-Stage Strategy Execution (50 runs across 25 workers)
To execute 10 independent replications for each of the 5 biphasic schemes across 400 generations using `run_parallel.py` and 25 parallel worker threads (2 loops of 25):

```powershell
# Activate conda environment
conda activate framsticks

# Define directory shortcuts
$TASK3 = "assignments/Assignment 5 - Modifying topology exploration path. Evolution of Designs/task3 - Evolution & varying different mutations probs"
$SIMS = "$TASK3/sims"

# Execute all 50 biphasic runs in parallel across 25 CPU workers
python "scripts/run_parallel.py" `
    --script "scripts/FramsticksEvolutionScheduled.py" `
    --frams-path "Framsticks55" `
    --num-experiments 10 `
    --genformats 1 `
    --sim "eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim" `
    --opt velocity `
    --popsize 50 `
    --generations 400 `
    --tournament 5 `
    --pxov 0 `
    --pmut 0.9 `
    --max-numparts 15 `
    --max-numjoints 30 `
    --max-numneurons 20 `
    --max-numconnections 30 `
    --workers 25 `
    --schemes `
        "scheme-1=0:$SIMS/f1-probs10.sim;200:$SIMS/f1-probs01.sim" `
        "scheme-8=0:$SIMS/f1-equal-probs.sim;200:$SIMS/f1-strat-a.sim" `
        "scheme-9=0:$SIMS/f1-strat-b.sim;200:$SIMS/f1-strat-a.sim" `
        "scheme-10=0:$SIMS/f1-equal-probs.sim;100:$SIMS/f1-strat-a.sim" `
        "scheme-11=0:$SIMS/f1-equal-probs.sim;300:$SIMS/f1-strat-a.sim" `
    --stats-dir "$TASK3/stats/2026-09-27_exp4_biphasic" `
    --out "$TASK3/runs"
```

#### Experiment 5: Optimized Staged Exploration Execution (40 runs across 20 workers)
To execute 10 independent replications for each of the 4 refined schemes across 400 generations using `run_parallel.py` and 20 parallel worker threads (2 loops of 20):

```powershell
# Activate conda environment
conda activate framsticks

# Define directory shortcuts
$TASK3 = "assignments/Assignment 5 - Modifying topology exploration path. Evolution of Designs/task3 - Evolution & varying different mutations probs"
$SIMS = "$TASK3/sims"

# Execute all 40 runs in parallel across 20 CPU workers
python "scripts/run_parallel.py" `
    --script "scripts/FramsticksEvolutionScheduled.py" `
    --frams-path "Framsticks55" `
    --num-experiments 10 `
    --genformats 1 `
    --sim "eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim" `
    --opt velocity `
    --popsize 50 `
    --generations 400 `
    --tournament 5 `
    --pxov 0 `
    --pmut 0.9 `
    --max-numparts 15 `
    --max-numjoints 30 `
    --max-numneurons 20 `
    --max-numconnections 30 `
    --workers 20 `
    --schemes `
        "scheme-3=0:$SIMS/f1-equal-probs.sim;100:$SIMS/f1-strat-b.sim;200:$SIMS/f1-strat-a.sim" `
        "scheme-1=0:$SIMS/f1-equal-probs.sim;100:$SIMS/f1-probs10.sim;250:$SIMS/f1-probs01.sim" `
        "scheme-7=0:$SIMS/f1-equal-probs.sim;100:$SIMS/f1-strat-b.sim;200:$SIMS/f1-strat-d.sim;300:$SIMS/f1-strat-a.sim" `
        "scheme-10=0:$SIMS/f1-equal-probs.sim;100:$SIMS/f1-strat-a.sim;350:$SIMS/f1-probs01.sim" `
    --stats-dir "$TASK3/stats/2026-09-27_exp5_refined" `
    --out "$TASK3/runs"
```

#### Generating HoF Analysis Plots
To analyze the resulting logbooks and produce comparative Hall of Fame fitness curves, confidence intervals, and boxplots:

```powershell
# Define task directory shortcut
$TASK3 = "assignments/Assignment 5 - Modifying topology exploration path. Evolution of Designs/task3 - Evolution & varying different mutations probs"

# 1. Experiment 1 Baseline Analysis
python "scripts/analyze_hof.py" `
    --logbook-dirs "$TASK3/stats/2026-09-26_4variants_300gen/2026-09-26_04" `
    --outdir "$TASK3/results/hof_results" `
    --colors RdPu `
    --xscale linlog `
    --headless `
    --extension png

# 2. Experiment 3 Scheduled Multi-Stage Analysis
python "scripts/analyze_hof.py" `
    --logbook-dirs "$TASK3/stats/2026-09-27_exp3_switching/2026-09-27_18" `
    --outdir "$TASK3/results/hof_results_exp3" `
    --colors YlOrRd `
    --xscale linlog `
    --headless `
    --extension png

# 3. Experiment 4 Biphasic Exploration Analysis
python "scripts/analyze_hof.py" `
    --logbook-dirs "$TASK3/stats/2026-09-27_exp4_biphasic/combined" `
    --outdir "$TASK3/results/hof_results_exp4" `
    --colors PuBu `
    --xscale linlog `
    --headless `
    --extension png

# 4. Experiment 5 Refined Developmental Cascades Analysis
python "scripts/analyze_hof.py" `
    --logbook-dirs "$TASK3/stats/2026-09-27_exp5_refined/2026-09-27_23" `
    --outdir "$TASK3/results/hof_results_exp5" `
    --colors YlGn `
    --xscale linlog `
    --headless `
    --extension png

# 5. Cross-Experimental Champions Comparison (Experiments 1–5)
python "scripts/analyze_hof.py" `
    --logbook-dirs `
        "$TASK3/stats/comparison_champions_subdirs/Exp1" `
        "$TASK3/stats/comparison_champions_subdirs/Exp2" `
        "$TASK3/stats/comparison_champions_subdirs/Exp3" `
        "$TASK3/stats/comparison_champions_subdirs/Exp4" `
        "$TASK3/stats/comparison_champions_subdirs/Exp5" `
    --outdir "$TASK3/results/hof_results_comparison_champions" `
    --colors RdPu GnBu YlOrRd PuBu YlGn `
    --xscale lin `
    --headless `
    --extension png

# 6. Comprehensive 24-Configuration Global Comparison (Experiments 1–5)
python "scripts/analyze_hof.py" `
    --logbook-dirs `
        "$TASK3/stats/comparison_exp1_5_subdirs/Exp1" `
        "$TASK3/stats/comparison_exp1_5_subdirs/Exp2" `
        "$TASK3/stats/comparison_exp1_5_subdirs/Exp3" `
        "$TASK3/stats/comparison_exp1_5_subdirs/Exp4" `
        "$TASK3/stats/comparison_exp1_5_subdirs/Exp5" `
    --outdir "$TASK3/results/hof_results_comparison_exp1_5" `
    --colors RdPu GnBu YlOrRd PuBu YlGn `
    --xscale lin `
    --headless `
    --extension png
```