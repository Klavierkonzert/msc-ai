# Quantum Computing: Fundamentals

> *Notes translated from my 2020 bachelor term paper, cleaned up and corrected.*

## Scope (1-3)
0. [Physical Foundations](./00-preliminaries.md)
1. **[Principle of Computation](#1-principle-of-computation)**
2. **[Notes on Quantum Logic](#2-notes-on-quantum-logic)**
3. **[Qubit Operations & Gates](#3-operations-on-qubits)**
    1. Single-Qubit Gates
    2. Two-Qubit Gates
    3. Three-Qubit Gates
4. [Universal Gate Synthesis](./02-universal-gates.md) (mathematically heavy and can be skipped)
5. [Circuits & Measurement](./03-quantum-circuits.md)
6. ...

## 1. Principle of Computation

Classical computers operate on discrete bits taking values in _{0, 1}_. The quantum analog is the **qubit** (quantum bit), which can exist in an arbitrary linear superposition of _computational basis states_. In standard Dirac notation, state vectors are called _kets_ and represented as column vectors:

$$\displaystyle|\psi\rangle = \alpha|0\rangle + \beta|1\rangle \equiv \begin{bmatrix} \alpha \\ 
                                                                          \beta \end{bmatrix}\in \mathbb{C}^2$$

where $\alpha, \beta \in \mathbb{C}$ are probability amplitudes constrained by the normalization condition:

$$|\alpha|^2 + |\beta|^2 = 1$$

Corresponding conjugate linear operators are denoted as _bra_ vectors $\langle\psi| \equiv |\psi\rangle^\dagger$ (Hermitian conjugate), represented by row vectors.

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
State evolution is continuous and unitary, while final readout is probabilistic. Hence the whole quantum computation should be repeated multiple times to obtain the final distribution of solutions, which allows one to obtain not only the best answer but also several good ones.


## 2. Notes on Quantum Logic

Standard computation relies on Boolean propositional calculus $(0, 1, \wedge, \vee, \neg)$.
In standard quantum logic (originating with Birkhoff and von Neumann), propositions correspond to closed linear subspaces (projection operators) of a complex Hilbert space $\mathcal{H}$, breaking several properties of classical propositional logic:

* **Failure of Distributivity:** Because non-commuting observables cannot be resolved simultaneously, quantum propositions do not satisfy classical distributivity:

   <div align="center" style="font-size: 110%;"> $A \wedge (B \vee C) \neq (A \wedge B) \vee (A \wedge C)$</div>

   The proposition structure forms an **orthomodular lattice** (Birkhoff–von Neumann logic) rather than a Boolean algebra.

* **The Implication Problem:** There is no canonical conditional connective $\to$ satisfying the classical deduction theorem ($A \vdash B \iff \vdash A \to B$). Logical implication is evaluated via subspace inclusion $P_A \le P_B$.

These non-classical properties mirror foundational physical phenomena such as wave interference and diffraction. 

### Computational Quantum Logic 
Cattaneo, Dalla Chiara, and Giuntini (2003) formulated *fuzzy quantum logic based on quantum computation*:
* Atomic propositions are mapped to state vectors $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$ in $\mathcal{H}_2 \cong \mathbb{C}^2$.
* Composite formulas correspond to unit vectors in tensor product spaces

$$\displaystyle\mathcal{H}_{2^n}=\bigotimes_{i=1}^n \mathcal{H}_2$$

* Logical connectives are realized as **unitary operators** of dimension $2^n$ rather than static truth tables, directly recovering the standard circuit model of quantum computing.

However, in contradistinction to Birkhoff-von Neumann logic, **the law of the excluded middle** is broken in this formulation (e.g. for a superposition state like $\frac{\vert{}0\rangle + \vert{}1\rangle}{\sqrt{2}}$).






## 3. Operations on Qubits

> see https://en.wikipedia.org/wiki/Quantum_logic_gate for more details

A quantum gate is a unitary transformation acting on a qubit register. Unlike classical irreversible logic, all quantum operations on closed systems are strictly reversible and trace-preserving. The result of the applying a gate operator $U$ on a qubit register is denoted as $U\vert{}\psi\rangle$.

A single-qubit gate is represented by a $2 \times 2$ unitary matrix satisfying:

$$U U^\dagger = U^\dagger U = I$$

where $U^\dagger = (U^*)^T$ is the Hermitian conjugate. An $n$-qubit gate corresponds to a $2^n \times 2^n$ unitary matrix.

_Computational basis states_ in standard column vector form:

$$|0\rangle = \begin{bmatrix} 1 \\ 
                              0 \end{bmatrix}, 
    |1\rangle = \begin{bmatrix} 0 \\ 
                                      1 \end{bmatrix}$$


Composite registers are constructed via the _tensor product_:

$$|ab\rangle = |a\rangle \otimes |b\rangle \equiv \begin{bmatrix} a_0 b_0 \\ 
                                                                  a_0 b_1 \\ 
                                                                  a_1 b_0 \\ 
                                                                  a_1 b_1 \end{bmatrix}   \equiv   v_{00}|00\rangle + v_{01}|01\rangle + v_{10}|10\rangle + v_{11}|11\rangle
                                                             \text{, \ \ where}\sum_{i,j} |v_{ij}|^2 = 1$$

### Elementary Single-Qubit Gates
Given a single qubit $|\psi\rangle=\alpha|0\rangle + \beta|1\rangle$, the following ounitary operations can be performed:
* **Identity Gate ($I$ or $\sigma_0$):**

$$I = \begin{bmatrix} 1 & 0 \\ 
                      0 & 1 \end{bmatrix}, 
        \quad I|\psi\rangle = |\psi\rangle $$

* **Pauli-X Gate ($X$ or $\sigma_x$)** is the quantum NOT gate; corresponds to a $\pi$ rotation about the X-axis of the Bloch sphere:

$$X = \begin{bmatrix} 0 & 1 \\ 
                      1 & 0 \end{bmatrix}, 
       \quad X|\psi\rangle = \beta|0\rangle + \alpha|1\rangle$$

* **Pauli-Z Gate ($Z$ or $\sigma_z$)** flips the relative phase; corresponds to a $\pi$ rotation about the Z-axis of the Bloch sphere:

$$Z = \begin{bmatrix} 1 & 0 \\ 
                      0 & -1 \end{bmatrix},
    \quad Z|\psi\rangle = \alpha|0\rangle - \beta|1\rangle$$


* **Pauli-Y Gate ($Y$ or $\sigma_y$)** corresponds to a $\pi$ rotation about the Y-axis of the Bloch sphere:

$$Y = \begin{bmatrix} 0 & -i \\
                      i & 0 \end{bmatrix},
   \quad Y|\psi\rangle = -i\beta|0\rangle + i\alpha|1\rangle$$
  

The Pauli matrices are Hermitian and involutory:

$$I^2 = X^2 = Y^2 = Z^2 = -iXYZ = I$$



* **Hadamard Gate ($H$)** generates equal superpositions; corresponds to a rotation of $\pi$ radians about the diagonal axis $(\hat{x} + \hat{z})/\sqrt{2}$ on the Bloch sphere. Satisfies $H = H^\dagger$ and $H^2 = I$:

$$H = \frac{1}{\sqrt{2}}\begin{bmatrix} 1 & 1 \\
                                          1 & -1 \end{bmatrix}$$
                                          
$$H|0\rangle = \frac{|0\rangle + |1\rangle}{\sqrt{2}} = |+\rangle, \quad H|1\rangle = \frac{|0\rangle - |1\rangle}{\sqrt{2}} = |-\rangle$$
  

* **Square Root of NOT ($\sqrt{X}$ or $\sqrt{\text{NOT}}$):**

$$\sqrt{X} = \frac{1}{2}\begin{bmatrix} 1+i & 1-i \\
                                          1-i & 1+i \end{bmatrix}, \quad \sqrt{X}^2 = X$$



* **Phase Shift Gate ($R_\phi$)** rotates a vector within $xy$ plane on a given angle $\phi$; leaves computational basis measurement probabilities unchanged while shifting relative phase. 

$$R_\phi = \begin{bmatrix} 1 & 0 \\ 
                           0 & e^{i\phi} \end{bmatrix}$$

Two particular cases of the Shift Gate are of interest:
- **S gate** ($R_{\pi/2}$):

$$S = \begin{bmatrix} 1 & 0 \\
                      0 & i \end{bmatrix}$$
    
- **T gate** ($R_{\pi/4}$):

$$T = \begin{bmatrix} 1 & 0 \\
                      0 & e^{i\pi/4} \end{bmatrix} \implies T^2 = S$$


### Two-Qubit Gates

* **SWAP Gate** exchanges two states:
 
$$\text{SWAP} = \begin{bmatrix} 1 & 0 & 0 & 0 \\ 
                                0 & 0 & 1 & 0 \\ 
                                0 & 1 & 0 & 0 \\ 
                                0 & 0 & 0 & 1 \end{bmatrix}$$

$$\text{SWAP} \begin{bmatrix} v_{00} & v_{01} & v_{10} & v_{11} \end{bmatrix}^T \equiv v_{00} |00\rangle + v_{10}|01\rangle + v_{01}|10\rangle + v_{11} |11\rangle $$

* **$\sqrt{\text{SWAP}}$ Gate** is a universal in combination with single-qubit rotations gate, which performs an entangling half-swap:

$$\sqrt{\text{SWAP}} = \begin{bmatrix} 1 & 0 & 0 & 0 \\
                                       0 & \frac{1+i}{2} & \frac{1-i}{2} & 0 \\ 
                                       0 & \frac{1-i}{2} & \frac{1+i}{2} & 0 \\ 
                                       0 & 0 & 0 & 1 \end{bmatrix}$$


#### Controlled Gates

Controlled gates  ($C(U)$ ) apply operation $U$ to the target qubit if the control qubit is $|1\rangle$, leaving it unchanged otherwise:

* **Controlled-NOT (CNOT / $cX$):**

$$\text{CNOT}|a, b\rangle = |a, a \oplus b\rangle$$

$$\text{CNOT} = \begin{bmatrix} 1 & 0 & 0 & 0 \\ 
                                0 & 1 & 0 & 0 \\ 
                                0 & 0 & 0 & 1 \\ 
                                0 & 0 & 1 & 0 \end{bmatrix}$$
  
* **General Controlled-U**:

$$C(U) = \begin{bmatrix} 1 & 0 & 0 & 0 \\
                        0 & 1 & 0 & 0 \\
                        0 & 0 & u_{00} & u_{01} \\
                        0 & 0 & u_{10} & u_{11} \end{bmatrix}$$


### Three-Qubit Gates

* **Toffoli Gate (CCNOT, $D_{\pi/2}$)** is an _involutory_ and _classically universal_ gate which returns $NOT|c\rangle$ iff $a=b=1$: 

$$\text{CCNOT}|a, b, c\rangle = |a, b, c \oplus (a \wedge b)\rangle$$

* **Fredkin Gate (CSWAP)** is a _involutory_ controlled swap gate preserving total Hamming weight:

$$\text{CSWAP}:=\begin{bmatrix} I_{4\times 4} & 0_{4 \times 4} \\
                        0_{4\times 4} & \text{SWAP} \end{bmatrix}$$
                        
$$\implies \text{CSWAP}|1, b, c\rangle = |1, c, b\rangle, \quad \text{CSWAP}|0, b, c\rangle = |0, b, c\rangle$$


* **Deutsch Gate ($D_\theta$)** is a _quantum-universal_ (if $\frac{\theta}{\pi} \notin\mathbb{Q}$) gate which performs a controlled single-qubit unitary rotation $U_{\theta}$ iff the first two qubits are in state $|1\rangle$:

$$U_\theta:=\begin{bmatrix} i\cos\theta & \sin\theta \\
                            \sin \theta & i\cos\theta \end{bmatrix}$$
                        
$$\implies D_\theta|a, b, c\rangle := \begin{cases}
  i\cos\theta|a, b, c\rangle + \sin\theta|a, b, 1-c\rangle & \text{if } a = b = 1 \\
  |a, b, c\rangle & \text{otherwise}
  \end{cases}$$

