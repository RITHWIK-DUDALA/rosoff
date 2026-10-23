# KINEMATICS, JACOBIAN, AND DYNAMICS SPECIFICATION (kinematics.md)
## 2-DOF Planar Cable-Driven Parallel Robot (CDPR)

---

## 1. Inverse Kinematics (IK)

Given the platform Cartesian position $q = [x, y]^T \in \mathbb{R}^2$, inverse kinematics computes the four required geometric cable lengths $L = [L_1, L_2, L_3, L_4]^T$.

### 1.1 Vector Geometry
Let:
- $A_i = [A_{ix}, A_{iy}]^T$ be the fixed coordinates of frame anchor $i$.
- $B_i = [B_{ix}, B_{iy}]^T$ be the coordinates of platform attachment point $i$ in the local platform frame.
- $P_i(q) = q + B_i$ be the world position of attachment point $i$.

The cable vector $v_i(q)$ directed from the platform attachment to the frame anchor is:
$$v_i(q) = A_i - P_i(q) = \begin{bmatrix} A_{ix} - (x + B_{ix}) \\ A_{iy} - (y + B_{iy}) \end{bmatrix}$$

The Euclidean cable length $L_i(q)$ is:
$$L_i(q) = \|v_i(q)\| = \sqrt{(A_{ix} - x - B_{ix})^2 + (A_{iy} - y - B_{iy})^2}$$

---

## 2. Analytical Cable-Length Jacobian

The cable-length Jacobian $J_L(q) \in \mathbb{R}^{4 \times 2}$ relates platform velocity $\dot{q} = [\dot{x}, \dot{y}]^T$ to the cable length rate of change $\dot{L} = [\dot{L}_1, \dot{L}_2, \dot{L}_3, \dot{L}_4]^T$:

$$\dot{L} = J_L(q) \dot{q}$$

### 2.1 Derivation
Differentiating $L_i^2 = (A_i - q - B_i)^T (A_i - q - B_i)$ with respect to time:
$$2 L_i \dot{L}_i = - 2 (A_i - q - B_i)^T \dot{q} = 2 (q + B_i - A_i)^T \dot{q}$$

$$\dot{L}_i = \begin{bmatrix} \frac{x + B_{ix} - A_{ix}}{L_i} & \frac{y + B_{iy} - A_{iy}}{L_i} \end{bmatrix} \dot{q}$$

Let $u_i = \frac{A_i - P_i}{L_i}$ be the unit vector pointing along cable $i$ from attachment point $P_i$ toward anchor $A_i$. Then row $i$ of the Jacobian is:
$$J_{L, i} = - u_i^T = \begin{bmatrix} \frac{x + B_{ix} - A_{ix}}{L_i} & \frac{y + B_{iy} - A_{iy}}{L_i} \end{bmatrix}$$

### 2.2 Jacobian Conditioning and Singularity
The 2-norm condition number of $J_L(q)$ is defined as:
$$\kappa(J_L) = \frac{\sigma_{max}(J_L)}{\sigma_{min}(J_L)}$$
where $\sigma_{max}, \sigma_{min}$ are the singular values of $J_L$.
- At the workspace centre $q = [0, 0]^T$, $\kappa \approx 1.25$ (well-conditioned).
- As the platform approaches singularities or corners where cables become nearly collinear, $\sigma_{min} \rightarrow 0$ and $\kappa \rightarrow \infty$.
- Configurations with $\kappa(J_L) > 25.0$ are flagged as poorly conditioned.

---

## 3. Forward Kinematics (FK)

Given 4 measured cable lengths $L_{meas} \in \mathbb{R}^4$, forward kinematics estimates the platform position $\hat{q} = [\hat{x}, \hat{y}]^T$ that minimizes the non-linear least-squares residual:

$$\min_q f(q) = \frac{1}{2} \sum_{i=1}^4 w_i \left(L_i(q) - L_{meas, i}\right)^2 = \frac{1}{2} r(q)^T W r(q)$$
where $r_i(q) = L_i(q) - L_{meas, i}$ and $W = \text{diag}(w_1, w_2, w_3, w_4)$.

### 3.1 Levenberg-Marquardt Active Solver
The update step $\Delta q$ is obtained by solving the damped normal equations:
$$\left(J_L^T W J_L + \mu I\right) \Delta q = - J_L^T W r(q_k)$$

**Solver Convergence Criteria:**
1. Residual norm $\|r(q_k)\| < 1.0 \times 10^{-7}\text{ m}$.
2. Step magnitude $\|\Delta q\| < 1.0 \times 10^{-7}\text{ m}$.
3. Maximum iterations: $50$.
4. Post-convergence geometric compatibility check: If $\|r(q_{final})\| > 0.020\text{ m}$ ($20\text{ mm}$), the measured lengths are physically incompatible, and convergence is flagged as failed.

---

## 4. Spool Drum and Actuator Model

For an ideal constant-radius spool drum with pitch radius $r = 0.010\text{ m}$:
$$\theta_i = \frac{L_i - L_{ref, i}}{r}$$
$$\omega_i = \frac{\dot{L}_i}{r} \quad (\text{rad/s})$$
$$\text{RPM}_i = \frac{60}{2\pi} \omega_i = \frac{60}{2\pi r} \dot{L}_i$$

### Sign Convention
- **Payout ($\dot{L}_i > 0$):** Positive angular velocity $\omega_i > 0$ (unspooling).
- **Retraction ($\dot{L}_i < 0$):** Negative angular velocity $\omega_i < 0$ (spooling).

### Model Limitations (Rule 0.2 / Section 6.5)
The linear constant-radius relationship $v = \omega r$ assumes:
1. No multi-layer cable build-up on the drum (helical grooved single-layer winding required).
2. Zero cable elasticity, stretch, or sag.
3. Zero spool slip or cord backlash.
These effects represent physical model limitations until experimentally calibrated on the physical testbed.

---

## 5. Tension Allocation and Dynamics

Cables can pull but cannot push (unilateral tension constraint):
$$T_i \ge T_{min} > 0 \quad \forall i \in \{1, 2, 3, 4\}$$

### 5.1 Principle of Virtual Work
The net force exerted by the 4 cables on the platform is:
$$F_{cable} = \sum_{i=1}^4 T_i u_i = - J_L(q)^T T$$

The dynamic equations of motion for mass $m = 0.50\text{ kg}$ are:
$$M \ddot{q} = F_{cable} + F_{ext} - F_{fric}$$
$$- J_L(q)^T T = M \ddot{q} - F_{ext} + \mu m g \frac{\dot{q}}{\|\dot{q}\|}$$

### 5.2 Constrained Tension Optimization
To resolve the 2-DOF cable redundancy ($J_L^T \in \mathbb{R}^{2 \times 4}$), the tension allocation problem is formulated as a bounded quadratic program:
$$\min_T \frac{1}{2} \|T - T_{ref}\|^2$$
subject to:
$$J_L(q)^T T = F_{demand}$$
$$T_{min} \le T_i \le T_{max}$$
where $T_{min} = 2.0\text{ N}$, $T_{max} = 36.0\text{ N}$ (motor torque continuous limit), and $T_{ref} = 10.0\text{ N}$.

Solved via active-set bounded linear least-squares (`scipy.optimize.lsq_linear`). If no solution satisfies $T_i \ge T_{min}$, an `INFEASIBLE_TENSION` fault is flagged.
