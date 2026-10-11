# MATHEMATICAL AND PHYSICAL MODEL SPECIFICATION (MODEL.md)

## 1. Coordinate Frames and Geometry

The planar Cable-Driven Parallel Robot (CDPR) operates in a horizontal plane with 2 translational degrees of freedom (X and Y).

- **Global Origin**: Located at the geometric centre of the frame.
- **X Axis**: Horizontal, pointing positive to the right.
- **Y Axis**: Vertical on the screen / planar layout, pointing positive upward.
- **Z Axis**: Normal to the motion plane.
- **Platform Coordinates**: $q = [x, y]^T \in \mathbb{R}^2$ represents the position of the platform centre.
- **Rotational Degree of Freedom**: Mechanical anti-rotation guide rods constrain all three angular degrees of freedom ($\theta_x = \theta_y = \theta_z = 0$) and normal translation ($z = 0$).

### Anchor and Attachment Coordinates
In frame coordinates (meters):
- $A_1 = [-0.250, +0.200]^T$ (Top-Left)
- $A_2 = [+0.250, +0.200]^T$ (Top-Right)
- $A_3 = [+0.250, -0.200]^T$ (Bottom-Right)
- $A_4 = [-0.250, -0.200]^T$ (Bottom-Left)

Platform attachment coordinates in local platform frame (meters):
- $b_1 = [-0.050, +0.040]^T$
- $b_2 = [+0.050, +0.040]^T$
- $b_3 = [+0.050, -0.040]^T$
- $b_4 = [-0.050, -0.040]^T$

World position of attachment point $i$:
$$P_i(q) = q + b_i = \begin{bmatrix} x + b_{ix} \\ y + b_{iy} \end{bmatrix}$$

Vector from platform attachment to frame anchor:
$$v_i(q) = A_i - P_i(q)$$

Cable Euclidean length:
$$L_i(q) = \|v_i(q)\| = \sqrt{(A_{ix} - x - b_{ix})^2 + (A_{iy} - y - b_{iy})^2}$$

---

## 2. Kinematics and Jacobian

### Analytical Cable-Length Jacobian
The cable-length Jacobian $J_L(q) \in \mathbb{R}^{4 \times 2}$ maps platform planar velocity $\dot{q}$ to cable length rates $\dot{L}$:
$$\dot{L} = J_L(q) \dot{q}$$
where:
$$J_{L, i} = \frac{\partial L_i}{\partial q} = \begin{bmatrix} \frac{x + b_{ix} - A_{ix}}{L_i} & \frac{y + b_{iy} - A_{iy}}{L_i} \end{bmatrix} = - u_i^T$$
$u_i = \frac{A_i - P_i}{L_i}$ is the unit vector pointing along the $i$-th cable from platform attachment towards the frame anchor.

### Differential Actuator Kinematics
For drum radius $r = 0.010\text{ m}$:
$$\omega_i = \frac{\dot{L}_i}{r}$$
$$\text{RPM}_i = \frac{60}{2\pi} \omega_i = \frac{60}{2\pi r} \dot{L}_i$$

**Sign Convention**:
- Payout ($\dot{L}_i > 0$): Positive angular velocity $\omega_i > 0$.
- Retraction ($\dot{L}_i < 0$): Negative angular velocity $\omega_i < 0$.

### Forward Kinematics Formulation
Given 4 redundant measured cable lengths $L_{meas} \in \mathbb{R}^4$, the estimated position $\hat{q}$ minimizes the non-linear least squares residual:
$$\min_q \sum_{i=1}^4 w_i \left(L_i(q) - L_{meas, i}\right)^2$$
Solved via damped Gauss-Newton (Levenberg-Marquardt):
$$\left(J_L^T W J_L + \mu I\right) \Delta q = - J_L^T W (L(q) - L_{meas})$$

---

## 3. Static Force Allocation and Dynamics

### Principle of Virtual Work and Equilibrium
The cable tension force vector acting on the platform is:
$$F_{cable} = - J_L(q)^T T$$
where $T = [T_1, T_2, T_3, T_4]^T \ge 0$ is the non-negative cable tension vector.

Planar equations of motion for mass $m = 0.5\text{ kg}$:
$$M \ddot{q} = F_{cable} + F_{ext} - F_{fric}$$
$$M \ddot{q} = - J_L(q)^T T + F_{ext} - \mu m g \frac{\dot{q}}{\|\dot{q}\|}$$

To maintain reference acceleration $\ddot{q}$, the required wrench is:
$$J_L(q)^T T = - \left(M \ddot{q} - F_{ext} + F_{fric}\right)$$

### Constrained Tension Allocation
Because $J_L^T \in \mathbb{R}^{2 \times 4}$, the tension solution has a 2-dimensional internal tension nullspace. We solve:
$$\min_T \frac{1}{2} \|T - T_{ref}\|^2$$
subject to:
$$J_L(q)^T T = F_{demand}$$
$$T_{min} \le T_i \le T_{max}$$
where $T_{min} = 2.0\text{ N}$ and $T_{max} = \min(300\text{ N}, \frac{\tau_{max} \eta}{r}) = 36.0\text{ N}$.

Solved using bounded least-squares active-set solver (`scipy.optimize.lsq_linear`).

---

## 4. Servo Actuator Model

- **Speed saturation**: $\text{RPM}_{actual} = \text{clip}(\text{RPM}_{demand}, -300, 300)$.
- **Output torque**:
  $$\tau_i = \frac{T_i r}{\eta} + J_{drum} \alpha_i$$
  Hard limit: $\tau_i \le 0.40\text{ Nm}$.
- **Sat Flagging**: When commanded trajectory demands torque $> 0.4\text{ Nm}$ or speed $> 300\text{ RPM}$, saturation flags and safety alerts are raised.
