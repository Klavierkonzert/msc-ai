# Evolutionary Design #2
## Different Encodings. Modification of Fitness Landscape, Smoothness and Gradient

This assignment (4) is slightly more complicated than the previous  [`Assignment 3`](../Assignment%203%20-%20Mutation%20Intensity%20in%20Evolutionary%20Algorithms/README.md). 
Here we compare 4 genome representations - f0, f1, f4, f9. Also - in contrast to the previous assignment - we start with no initial genome (`--initialgenome`), which slightly complicates further evolution. Additionally, 2 new simulation files (`only-body.sim` and [`uneven-ground.sim`](https://www.cs.put.poznan.pl/mkomosinski/uneven-ground.sim)) were included to introduce some perturbations to a physical landscape, so slightly negative values of mass center vertical position are possible (around $-0.01$).

The description of genformats can be found here: https://www.framsticks.com/a/al_genotype.html, list and corresponding links to these genotypes can be found there at the bottom.
Brief description of genformats:
- [f0](https://www.framsticks.com/a/al_geno_f0.html): Parts (_p_), Joints (_j_) [and Neurons (_n_)] with reference numbers to attach to, positions in 3D (not mutated), 3D rotation arguments, part shapes. This is the most low-level encoding. All genotypes in all genetic representations in Framsticks must be translatable to f0, so that their phenotypes can be simulated.
- [f1](https://www.framsticks.com/a/al_geno_f1.html): easy recursive language which tree-structure semantics, e.g. `X(X,X)` - there will be 2 parts growing in opposite directions from the first one (letter "Y"), with length, rotation, curvedness and some other modifiers
- [f4](http://www.framsticks.com/a/al_geno_f4.html): similar to f1, but  encodes the process of development of a phenotype - composed of instructions to cells, e.g. `/*4*/<X>X` will signal: cell division (`<`), the first cell performs the next instruction (`X` - turn into a stick) + the other cell also executes `X` and turns into a stick, stop division of the first cell (`>`), the second cell stops development. f4 has binary-tree semantics, and string genome representation - its pre-order traversal. Allows to specify branching angle, etc. Additionally, the # gene enables repeated interpretation of a given genotype (`/*4*/...#10,<repeated 10 times genotype>...`)
- f9: all the letters (6 letters) encode 3 pairs of perpendicular directions in 3D, in which sticks will grow. Does not have all the nice properties as above.


The **goal** is the same - maximise vertical position of the mass center of creature - `vertpos`. As before, max num of "limbs"/parts of a creature is limited by 30.

In the experiments mutation intensity is set to 0 (previous experiment in the `Assignment 3` revealed that this is the optimal value). As before, population size is set to 100, tournament size is 10, number of generations is 300. All the experiments were run in parallel on 20 cores.

Example of modeling creatures with *f1* genformat:
- square: `/*1*/X(X(X(X,,),,),,)`
- spiky structure: `/*1*/X(X,X,RRX(X,RRX(X,RRX(X,X,X),X),X))`

## How to run

### Prerequisites
Ensure `only-body.sim` and `uneven-ground.sim` are present in the latest Framsticks [`data`](../../Framsticks55/data/) folder:
```bash
# Copy only-body.sim to Framsticks data folder
$ cp framspy-download/only-body.sim $(ls -d Framsticks*/data | sort -V | tail -n 1)

# Download uneven-ground.sim to Framsticks data folder
$ curl -s -o $(ls -d Framsticks*/data | sort -V | tail -n 1)/uneven-ground.sim https://www.cs.put.poznan.pl/mkomosinski/uneven-ground.sim
```

### Fitness Function Modification in `FramsticksEvolution.py`
In [`framspy-download/FramsticksEvolution.py` (inside `frams_evaluate()`)](../../framspy-download/FramsticksEvolution.py#L55), the default line:
```python
fitness = [default_evaluation_data[crit] for crit in OPTIMIZATION_CRITERIA]
```
is replaced with modified fitness (according to the formula below):
```python
max_parts = parsed_args.max_numparts if parsed_args.max_numparts else 30
fitness = [default_evaluation_data[crit] if (crit != 'vertpos' or default_evaluation_data[crit] > 0) else -0.01 * (1.0 - (default_evaluation_data['numparts'] - 1.0) / max_parts) for crit in OPTIMIZATION_CRITERIA]
```

### Running Evolution
Use the following command to run everything on one CPU:
```powershell
cd "sem-1/BIA/Evolutionary Design"
$F_values = 0, 1, 4, 9
$N_values = 1..10
$framsPath = (Get-ChildItem -Directory Framsticks* | Sort-Object Name -Descending | Select-Object -First 1).FullName

foreach ($F in $F_values) {
    foreach ($N in $N_values) {
        python framspy-download\FramsticksEvolution.py `
            -path $framsPath `
            -sim "eval-allcriteria.sim;deterministic.sim;sample-period-2.sim;only-body.sim;uneven-ground.sim" `
            -opt vertpos `
            -max_numparts 30 `
            -genformat $F `
            -popsize 50 `
            -generations 50 `
            -hof_size 1 `
            -hof_savefile "HoF-f$F-$N.gen"
    }
}
```

For parallel execution:
```bash
$ cd "sem-1/BIA/Evolutionary Design"
$ conda activate framsticks
$ python "scripts/run_parallel.py" --script framspy-download/FramsticksEvolution.py --frams-path "Framsticks55"  --num-experiments 10 --stats-dir stats --out runs --workers 20 --popsize 100 --generations 300 --tournament 10 --genformats 0 1 4 9 --sim "eval-allcriteria.sim;deterministic.sim;sample-period-2.sim;only-body.sim;uneven-ground.sim"        
```
Or `--stats-dir "assignments\Assignment 4 - EA with different genome encodings\stats"`.

To build plots of several experiments (make sure these folders exist. In these example the experiment results should be located in folders `stats\fitness = vertpos\`, etc):

```bash
python scripts/analyze_hof.py --logbook-dirs "stats\fitness = vertpos" "stats\fitness = vertpos + 0.00003 numparts"   "stats\fitness = vertpos + 0.0003 numparts" "stats\2026-09-07_22" --outdir "assignments\Assignment 4 - EA with different genome encodings"
# or python scripts/analyze_hof.py --logbook-dirs "assignments\Assignment 4 - EA with different genome encodings\stats\fitness = vertpos" "assignments\Assignment 4 - EA with different genome encodings\stats\fitness = vertpos or 0.0003 numparts" --outdir "assignments\Assignment 4 - EA with different genome encodings\stats" 
```

Pay attention that this time no characters limit is imposed on a genotype (since f0 is much more verbose, in contrast to [`Assignment 3`](../Assignment%203%20-%20Mutation%20Intensity%20in%20Evolutionary%20Algorithms/README.md))
## Objectives (Task 2):
- **Modify the fitness formula by introducing a gradient**, so that fitness landscape is changed in the smallest possible area, guiding evolution out of plateau.
- Why (with evolution using the unmodified objective function) the population for some representations left the plateau earlier, and for others it required more generations?
- Justify modification of fitness function
- Interpret the results
- Other methods that can be used to help evolution escape the plateau (e.g. starting far away from plateau like in the [`Assignment 3`](../Assignment%203%20-%20Mutation%20Intensity%20in%20Evolutionary%20Algorithms/README.md))

## Examination of plateau and modification of fitness function

Upon examination of "flat" individuals (whose `vertpos` is slightly below zero), it was found that vertical position has some small fluctuations ("tiny bumps"). For instance,
|`genformat`| example of negative `vertpos` value| abs difference|
|-----------|------------------------------------|-----------|
|f0|  -0.00999999805645396| 
|f0|  -0.01025336017022685|~0.00025
|f1|  -0.010233344531400231|
|f1|  -0.010159999425665912|~0.00007
|f4|  -0.010052799622804176|
|f4|  -0.010070608383014887|~0.00002
|f9|  -0.010494672413986115|
|f9|  -0.01055063527872108|~0.00006
|||max=0.00025 ~ 0.0003

The tiny differences in landscape observed above are caused by the microscopically uneven heightfield configured in `uneven-ground.sim`. In Framsticks, flat creatures lying on the floor have resting center-of-mass heights fluctuating around $vertpos \approx -0.010 \pm 0.0005$ purely due to this terrain noise. Furthermore, physical testing reveals a settling effect: as flat creatures add more parts along the floor, they distribute contact points across terrain micro-depressions and settle slightly deeper (e.g., $vertpos$ drops from $-0.01016$ for 2 parts down to $-0.01040$ for 12 parts). Consequently, under the unmodified objective function, adding body parts while remaining flat actually *decreases* raw $vertpos$, creating a deceptive anti-gradient that actively discourages structural growth.

To guide evolution out of this plateau, any intervention should be minimal, mathematically sound, and well-justified according to four explicit requirements:
1. **Affecting only the plateau area** and just enough to guide evolution out of the plateau as quickly as possible with the aid of the gradient.
2. **Never modifying the fitness of solutions from the plateau to exceed the raw positive `vertpos` of solutions outside the plateau** (avoiding anti-gradients and ensuring upright solutions are always favored).
3. **Not using randomly noisy quantities**, which cause uncontrolled rippling of the landscape and form false local optima.
4. **Preferably not affecting the characteristics of the results compared to no intervention** (preserving natural convergence and morphological properties outside the plateau).

In any case, we can use these observed plateau values as a guidance for how much perturbation to introduce when modifying the fitness function. Following the hypothesis outlined in the previous assignment that [ "building blocks" drive evolution](../Assignment%203%20-%20Mutation%20Intensity%20in%20Evolutionary%20Algorithms/README.md#L87), the number of parts (up to 30) has potential to improve the behavior of the algorithm. Guided by these requirements, the modified fitness function is formulated as a concise one-liner:

\[fitness' := vertpos \cdot \mathbb{I}[vertpos > 0] - 0.01 \cdot \left(1 - \frac{numparts - 1}{max\_numparts}\right) \cdot \mathbb{I}[vertpos \le 0]\]

*(where $max\_numparts = 30$, and on the plateau $fitness'(plateau) \subseteq [-0.01, -0.000333]$)*

### Justification of the formula

- **Eliminating Random Noise on the Plateau:** On the plateau ($vertpos \le 0$), raw $vertpos$ reflects only microscopic terrain fluctuations ($\pm 0.0003$) and ground settling (where flat structures with more parts settle slightly deeper into depressions, e.g. from $-0.01016$ to $-0.01040$). If $vertpos$ were retained on the plateau (such as in a naive $vertpos + c \cdot numparts$), the terrain noise would drown out small part bonuses and create false local optima. Completely removing $vertpos$ from the plateau term ensures a 100% deterministic, smooth, monotonic gradient: every added part provides a constant step $\Delta f' = \frac{0.01}{30} \approx +0.000333$.
- **Preventing Anti-Gradients and Exceeding Positive Solutions:** Plateau fitness is strictly negative for all $numparts \in [1, 30]$ (capped at $-0.000333 < 0$). If an additive bonus reached positive values on the plateau (e.g. $-0.0095 + 0.01 = +0.0005$), flat carpets would score higher than genuine upright mutants ($vertpos = +0.0002$), creating an anti-gradient cliff at $vertpos = 0$ that penalizes creatures for standing up. Under this formula, any upright creature ($vertpos > 0$) unconditionally beats every plateau individual.
- **Enabling $f_0$ to Escape the Plateau:** The initial $f_0$ genotype has 2 parts (`//0\np:\np:1\nj:0,1`), which physically cannot stand upright. In $f_0$, mutations directly add parts and joints in 3D Euclidean space. With a noise-free monotonic gradient on `numparts`, selection pressure greedily accumulates parts, assembling 3D tripods and multi-joint support frames that mechanically prop the structure up, escaping the plateau in just 2 generations ($vertpos = 0.18$ at gen 2).
- **Preserving Original Behavior Outside the Plateau:** When $vertpos > 0$, the plateau indicator $\mathbb{I}[vertpos \le 0]$ zeroes out the bonus, returning raw $vertpos$. This ensures upright creatures evolve purely for vertical height without artificial part bloat.

For comparison, original fitness function is:

\[ fitness = vertpos\]
*Note: The other components of `default_evaluation_data` were examined for a potential in improving behaviour of evolution - increasing speed of escaping plateau, but they introduced no interest since they either reflect noise or have constant values. `numjoints` is expected to strongly correlate with `numparts` ($numjoints = numparts - 1$ in simple trees), so using `numparts` directly is sufficient and cleaner.*

### Components of `default_evaluation_data` dictionary

The other components of the `default_evaluation_data` dictionary are:
- `'fit_stdev'`
- `'vertvel'`: 8.621866190577921e-11, vertical velocity of the creature, which is a noise as in case of `velocity` (being its vertical projcection)
- `'numjoints'`: (e.g. 1 in the beginning) - this quantity is expected to correlate with `numparts`
- `'fit'`: 3.7197517326808554e-07,
- `'lifespan'`: 10000.0 - const
- `'instances'`: 1 
- `'numparts'`: 2 - this variable shows most variability across different genformats, generations and runs, and thus it's at least good candidate for investigation
- `'numneurons'`: 0 - constant value
- `'time'`: 0.012157201766967773
- `'vertpos'`: **objective function**
- `'velocity'`: (e.g. $3.7e-07$) is equal roughly dist/time. Since time also have some immanent random properties, this quantity is highly unstable and should not be used in the fitness function expression.
- `'distance'`: (e.g. $0.0037$), which is random noise
- `'numconnections'`: 0,
- `'numgenocharacters'`: 29


## Experiment results

The experiments compare 4 genetic representations ($f_0, f_1, f_4, f_9$) across 10 independent random seeds under three experimental conditions (120 evolutionary runs in total):
1. **Unmodified Fitness**: $fitness = vertpos$
2. **Primary Modified Fitness**: $\Delta \approx 0.0003 \cdot numparts$ on the plateau ([main run](./runs/2026-09-07_213255/))
3. **Auxiliary Modified Fitness**: $\Delta \approx 0.00003 \cdot numparts$ (10 times decreased perturbation, [auxiliary run](./runs/2026-09-07_224747/))

### Quantitative Comparison Across All Conditions

| Condition | Encoding | Mean Escape Generation | Mean Final Fitness | Max Final Fitness |
| :--- | :---: | :---: | :---: | :---: | 
| **Unmodified**<br>($fitness = vertpos$) | $f_0$<br>$f_1$<br>$f_4$<br>$f_9$ | **Never (trapped)**<br>9.9 (7 – 13)<br>21.3 (12 – 36)<br>4.6 (2 – 8) | $-0.0100$<br>$1.7025$<br>$1.5090$<br>$0.9430$ | $-0.0100$<br>$2.1664$<br>$1.7782$<br>$1.0586$ |
| **Modified (Actual Run)**<br>($\Delta \approx 0.0003 \cdot numparts$) | $f_0$<br>$f_1$<br>$f_4$<br>$f_9$ | **2.1 (2 – 3)**<br>6.9 (4 – 11)<br>5.0 (4 – 7)<br>2.0 (2 – 2) | **$1.4476$**<br>$1.6208$<br>**$1.8635$**<br>$0.9416$ | **$2.2241$**<br>$2.0855$<br>**$2.4444$**<br>$1.0716$ |

_Note: $f_0$ genomes with unmodified fitness function never escape plateau, while in all the other cases escape rate was 100%._


The following plots demonstrate the experimental data for unmodified and modified fitness. Boxplots additionally include data for the decreased scale factor:

*Note: The first and second plots utilize a symlog horizontal axis to take a closer look at the initial generations of evolution, while the rest of the evolutionary trajectory is shown on a logarithmic scale.*

<div style="width:90%; margin: auto;">

![alt text](image.png)
_Figure 1: Fitness progression across generations (symlog scale)._

![alt text](image-1.png)
_Figure 2: Evolution of creature size (number of parts) across generations._

![alt text](image-2.png)
_Figure 3: Distribution of plateau escape generations and final fitness values across conditions._
</div>

Since 4 genetic representations were tested, it is important to note that the embryogeny (the mapping from genotype to phenotype) directly determines the smoothness or ruggedness of the resulting landscape, which influences how fast evolution escapes the plateau.
For example, creatures encoded in **f9** escape the plateau almost immediately, in a few generations, while **f1** or **f4** representations eventually form either spiral or "irregular" antennae-like structures, which are remarkably stable, but take longer to emerge:

<div align="center">
<img src="Screenshot 2026-06-08 025349- series of f1 well performing creatures.png" alt="Responsive Image" style="width:50%; height:auto;">

*Series of mutations had no effect on this creature.*

<img src="image-6.png" alt="Responsive Image" style="width:50%; height:auto;">

<img src="image-7.png" alt="Responsive Image" style="width:50%; height:auto;">
</div>

The following reasons explain the differences between **f9** and **f1/f4** genetic representations:
- **Epistasis**: If a representation has high epistasis (where one needs two specific genes to change simultaneously to gain height), it will stay stuck on the plateau much longer.
- **Locality**: Representations where a single mutation is likely to result in a "Part" being added or a "Joint" rotating vertically will leave the plateau faster.

In particular:
* **$f_9$ representation** uses a direct, sequential encoding with a low number of degrees of freedom (6 orthogonal directions in 3D space).
  - **High locality**: A small change in genotype typically leads to a predictable change in phenotype (e.g. substituting letter "D" with "U" immediately increases `vertpos`).
  - **Low epistasis**: Achieving higher `vertpos` requires minimal cooperation between distant genes.
  - **Stability issues**: Sequential instruction growth often forms linear, fragile sticks that struggle to develop wide stability bases.
* **$f_1$ / $f_4$ representations**:
  - **Higher epistasis**: Branching and developmental instructions mean a single gene change (such as joint rotation or cell division branching) radically alters downstream interpretation. Finding the initial upright configuration requires coordinated mutations.
  - **Larger neutrality**: Complex grammars produce many distinct genotypes mapping to the same "flat" creature, requiring a neutral random walk.
  - **Higher quality limit**: The building blocks they discover (spirals, cross-braced towers) are fundamentally more stable, achieving peak heights ($> 2.4$) far beyond $f_9$ ($\approx 1.05$).
  - **Acceleration of $f_4$**: The modified fitness function accelerates $f_4$'s escape by $>4\times$ (from generation 21.3 down to 5.0), enabling it to reach the highest overall fitness in the experiment ($1.86$ mean, $2.44$ max).

To summarize, $f_9$ favours **intensification** (rapid exploitation of simple local gradients), while $f_1$ and $f_4$ favour **exploration** (discovering globally superior architectures).


### Analysis of $f_0$ and Plateau Escape

Under the unmodified fitness function (`fitness = vertpos`), $f_0$ remained completely trapped on the plateau across all 10 runs for 300 generations (0% escape rate, final fitness locked at $-0.0100$). The explanation lies in its physical and genetic characteristics:
1. **Mechanical constraint:** The minimal initial genotype in $f_0$ consists of 2 parts connected by 1 joint (`//0\np:\np:1\nj:0,1`). In static physical simulation without active neural control, a 2-part stick cannot stand upright; gravity forces it flat against the ground.
2. **Deceptive raw landscape:** When mutations added parts in $f_0$, new parts initially lay on the ground. Flat multi-part structures settle deeper into terrain micro-depressions (raw $vertpos$ drops from $-0.01016$ to $-0.01040$). Consequently, unmodified evolution actively penalized individuals that added parts while flat, locking $f_0$ at 2 parts indefinitely.

**Why $f_0$ is the easiest representation to assist with an auxiliary gradient on `numparts`:**
Unlike $f_1$ and $f_4$ (where developmental grammar and high epistasis mean adding a symbol can drastically alter all downstream branches) or $f_9$ (where sticks are confined to 6 orthogonal directions), $f_0$ is an unconstrained, direct representation: mutations directly append parts and joints with 3D coordinate offsets.
With our justified, noise-free monotonic gradient on $numparts$:
- Selection pressure effortlessly and deterministically drives $f_0$ to accumulate parts.
- As $f_0$ structures reach 4–8 parts connected in 3D Euclidean space, random joint angle mutations assemble non-coplanar polygonal bases (tripods).
- These 3D frames mechanically prop parts above the ground, lifting the center of mass above zero ($vertpos > 0$).
- The instant $vertpos > 0$, the individual leaves the plateau, and the evolutionary algorithm seamlessly transitions to optimizing raw vertical height.
  
<div align="center">

![Tall stable f0 creature](image-5.png)
_Figure 7: Example of a tall, stable $f_0$ creature evolved after escaping the plateau._
</div>

**Empirical Result**: The building-block gradient transformed $f_0$ from the most stubborn representation into one of the fastest to escape (**100% escape rate in an average of 2.1 generations**), reaching an average final fitness of **1.45** (max **2.22**).

---

### Auxiliary Test: Effect of Gradient Magnitude ($\Delta \approx 0.00003 \cdot numparts$)

In the [auxiliary run](./runs/2026-09-07_224747/), the scaling factor was reduced by 10:
- **100% of runs still escaped the plateau**, demonstrating that even a minimal gradient on structural complexity is sufficient to break the plateau trap.
- However, $f_0$ and $f_1$ achieved slightly lower average final fitness.
- This confirms that our primary calibration of $\Delta = \frac{0.01}{30} \approx 3.33 \times 10^{-4}$ per part represents the optimal balance: it comfortably exceeds terrain noise ($\sim 0.00025$) while preserving smooth handover to raw vertical height optimization.



## Other methods to escape plateau

1. **Adjusting selection pressure**:
   - **Tournament size tuning**: Reducing tournament size (e.g. from 10 to 5) softens selection pressure, allowing the population to perform a broader neutral random walk across the plateau rather than prematurely converging on slight micro-crevice variations.
   - **Fitness truncation / sharing**: Penalizing individuals with identical fitness or structures prevents early "lucky" candidates from dominating the population before genuine height-increasing mutations emerge.
2. **Meta-schemes for neutral landscapes**:
   - **Island model**: Splitting the population into isolated sub-populations with low-frequency migration ensures diverse exploration paths across the neutral plateau, preventing global stagnation in a single terrain trap.
   - **Niching and crowding**: Incorporating phenotypic distance into selection penalizes structural clustering, actively forcing the search to explore structurally distinct configurations (e.g. branched vs linear vs closed-loop geometries).
3. **Seeding with structural precursors**:
   - Initializing the population with minimal 3D seeds (such as a 3-part non-collinear tripod) rather than a degenerate 2-part linear stick immediately bypasses the zero-dimensional flat boundary.
