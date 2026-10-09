# Quantum Computing: Fundamentals

> *Notes translated from my 2020 bachelor term paper, cleaned up and corrected.*

## Scope
0. [Physical Foundations](./00-preliminaries.md)
1. [Principle of Computation](#principle-of-computation)
2. [Notes on Quantum Logic](#notes-on-quantum-logic)
3. Qubit Operations & Gates
    1. Single-Qubit Gates
    2. Two-Qubit Gates
    3. Universal Gate Sets
4. Circuits & Measurement
    1. Circuit Composition
    2. Ancillas & Reversibility
    3. Measurement

## 1. Principle of Computation

Classical computers operate on discrete bits taking values in _{0, 1}_. The quantum analog is the **qubit** (quantum bit), which can exist in an arbitrary linear superposition of computational basis states:

$$|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$$

where $\alpha, \beta \in \mathbb{C}$ are probability amplitudes constrained by the normalization condition:

$$|\alpha|^2 + |\beta|^2 = 1$$

Geometrically, a single-qubit pure state corresponds to a point on the unit **Bloch sphere**:

$$|\psi\rangle = \cos\left(\frac{\theta}{2}\right)|0\rangle + e^{i\phi}\sin\left(\frac{\theta}{2}\right)|1\rangle$$

where $\theta \in [0, \pi]$ is the polar angle and $\phi \in [0, 2\pi)$ is the azimuthal phase.

<div align="center">
<img src="https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f0/Bloch_Sphere_representation.svg/500px-Bloch_Sphere_representation.svg.png?utm_source=en.wikipedia.org&amp;utm_campaign=parser&amp;utm_content=thumbnail" width="30%">
</div>

A single projective measurement yields an eigenvalue corresponding to either $|0\rangle$ or $|1\rangle$, while intermediate states cannot be observed directly. The underlying moduli squared $|\alpha|^2$ and $|\beta|^2$ quantify the probabilities of observing outcome **0** and **1** respectively, and can only be estimated statistically through a series of repeated state preparations and measurements.

A quantum computer consists of multiple (_n_) coupled qubits initialized to an initial state in a specific way corresponding to a problem considered. 
​Under the Everett many-worlds interpretation, it can be conceptually visualized as an ensemble of 2<sup>n</sup> classical computers executing the same algorithm across parallel branches of reality.
Algorithms manipulate the probability amplitudes via unitary quantum gates replacing Boolean logic gates, so that the resulting probability distribution corresponds to the process modeled. Moreover qubits can interfere with each other, which provides the foundation of the computations. Coherent interference across registers is orchestrated in such a way that amplitudes corresponding to correct solutions constructively interfere, while incorrect branches cancel destructively. 
State evolution is continuous and unitary, while final readout is probabilistic. Hence the whole quantum computation should be repeated multiple times to obtain the final distribution of solutions, which allows to obtain not only the best answer but also several good ones.


## 2. Notes on Quantum Logic

Standard computation relies on Boolean propositional calculus $(0, 1, \wedge, \vee, \neg)$.
In standard quantum logic (originating with Birkhoff and von Neumann), propositions correspond to closed linear subspaces (projection operators) of a complex Hilbert space $\mathcal{H}$, breaking several properties of classical propositional logic (such as the law of the excluded middle):

* **Failure of Distributivity:** Because non-commuting observables cannot be resolved simultaneously, quantum propositions do not satisfy classical distributivity:

   <div align="center" style="font-size: 110%;"> $A \wedge (B \vee C) \neq (A \wedge B) \vee (A \wedge C)$</div>

   The proposition structure forms an **orthomodular lattice** (Birkhoff–von Neumann logic) rather than a Boolean algebra.

* **The Implication Problem:** There is no canonical conditional connective $\to$ satisfying the classical deduction theorem ($A \vdash B \iff \vdash A \to B$). Logical implication is evaluated via subspace inclusion $P_A \le P_B$.

These non-classical properties mirror foundational physical phenomena such as wave interference and diffraction. 

### Computational Quantum Logic 
Cattaneo, Dalla Chiara, and Giuntini (2003) formulated *fuzzy quantum logic based on quantum computation*:
* Atomic propositions are mapped to state vectors $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$ in $\mathcal{H}_2 \cong \mathbb{C}^2$.
* Composite formulas correspond to unit vectors in tensor product spaces

$$\displaystyle\mathcal{H_{2^n}}=\bigotimes_{i=1}^n \mathcal{H}_2$$

  * Logical connectives are realized as **unitary operators** of dimension $2^n$ rather than static truth tables, directly recovering the standard circuit model of quantum computing.

