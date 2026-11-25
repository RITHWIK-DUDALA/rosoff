# PROJECT W.A.L.L. — Mathematical Foundations
## Kinematics, Dynamics, and Tension Optimization

### 1. Analytical Inverse Kinematics
Given the end-effector center coordinate $\mathbf{P} = (x, y)^T$ and local platform eyelet vectors $\mathbf{b}_i$, the global position of cable attachment point $i$ is:
$$\mathbf{P}_i = \mathbf{P} + \mathbf{b}_i$$

The geometric length of cable $i$ connecting anchor $\mathbf{A}_i = (A_{ix}, A_{iy})^T$ to eyelet $\mathbf{P}_i$ is:
$$L_i = \|\mathbf{P}_i - \mathbf{A}_i\| = \sqrt{(P_{ix} - A_{ix})^2 + (P_{iy} - A_{iy})^2}$$

### 2. Cable Jacobian Matrix
The time derivative of cable lengths relates to end-effector velocity $\mathbf{v} = (\dot{x}, \dot{y})^T$:
$$\dot{\mathbf{L}} = \mathbf{J} \mathbf{v}$$
where the $i$-th row of the $4 \times 2$ Jacobian matrix is the unit vector pointing from anchor $\mathbf{A}_i$ toward attachment $\mathbf{P}_i$:
$$\mathbf{J}_{i,:} = \frac{\mathbf{P}_i - \mathbf{A}_i}{\|\mathbf{P}_i - \mathbf{A}_i\|}$$

### 3. Static Equilibrium and Bounded Quadratic Programming
The structure matrix $\mathbf{A}_{struct}$ is formed by the unit pull vectors $\mathbf{u}_i = \frac{\mathbf{A}_i - \mathbf{P}_i}{L_i}$:
$$\mathbf{A}_{struct} = [\mathbf{u}_1, \mathbf{u}_2, \mathbf{u}_3, \mathbf{u}_4] \in \mathbb{R}^{2 \times 4}$$

For static equilibrium under external forces $\mathbf{F}_{ext}$ and gravitational force $\mathbf{F}_g = (0, -m \cdot g)^T$:
$$\mathbf{A}_{struct} \mathbf{T} + \mathbf{F}_{ext} + \mathbf{F}_g = \mathbf{0}$$
$$\mathbf{A}_{struct} \mathbf{T} = -\mathbf{F}_{resultant}$$

Subject to physical Dyneema cable limits:
$$T_{min} \le T_i \le T_{max} \quad (2.0\text{ N} \le T_i \le 50.0\text{ N})$$

The tension allocation solver minimizes:
$$\min_{\mathbf{T}} \|\mathbf{A}_{struct} \mathbf{T} - \mathbf{b}\|^2 + \alpha \|\mathbf{T} - \mathbf{T}_{mid}\|^2$$
using Bounded Variable Least Squares (`scipy.optimize.lsq_linear`).

### 4. Dyneema Cable Linear Elasticity
Cable stretch under tension $T$ is modeled via Hooke's Law:
$$\Delta L_i = \frac{T_i L_i}{E \cdot A_{cross}}$$
where:
- $E = 100\text{ GPa} = 100{,}000\text{ N/mm}^2$
- $d = 1.0\text{ mm} \implies A_{cross} = \frac{\pi (1.0)^2}{4} \approx 0.7854\text{ mm}^2$

### 5. Multilayer Winch Drum Winding
As cable wraps around the drum core ($r_0 = 10\text{ mm}$), the effective radius increases:
$$r_{eff} = r_0 + n_{layer} \cdot d_{cable} \cdot \frac{\sqrt{3}}{2}$$
Motor angular displacement $\Delta \theta$ relates to payed-out cable length:
$$\Delta L = r_{eff} \cdot \Delta \theta$$

