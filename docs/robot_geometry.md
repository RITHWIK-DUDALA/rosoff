# ROBOT GEOMETRY SPECIFICATION (robot_geometry.md)
## Planar 2-DOF Cable-Driven Parallel Robot (CDPR)

---

## 1. Canonical Coordinate System

The robot operates with 2 translational degrees of freedom in a horizontal plane constrained against out-of-plane translation and rotation by a precision dual-rod anti-rotation linear guide:

- **Origin $(0, 0, 0)$:** The geometric centre of the outer structural frame.
- **X Axis:** Horizontal, pointing positive to the right.
- **Y Axis:** Vertical across the motion plane, pointing positive upwards.
- **Z Axis:** Normal to the motion plane, pointing upwards (gravity acts along $-Z$, reaction force carried by guide shafts).
- **Controlled State:** $q = [x, y]^T \in \mathbb{R}^2$.
- **Orientation:** Mechanically constrained by dual guide shafts ($\theta_x = \theta_y = \theta_z = 0$).

---

## 2. Frame Geometry and Cable Anchors

The rigid outer frame is constructed from 2020/2040 clear-anodized aluminum extrusions:

| Dimension | Millimetres | Metres (SI Internal) | Notes |
|---|---:|---:|---|
| Frame Width ($W_f$) | 500.0 mm | 0.500 m | Inner bounding frame |
| Frame Height ($H_f$) | 400.0 mm | 0.400 m | Inner bounding frame |
| Frame Depth ($D_f$) | 120.0 mm | 0.120 m | Structural envelope |

### Frame Anchor Points ($A_i$)
The cable anchors / pulley exit points are positioned at the four frame corners:

| Cable Anchor | Corner | X (mm) | Y (mm) | X (m) | Y (m) | Z (m) |
|---|---|---:|---:|---:|---:|---:|
| **$A_1$ (C1)** | Top-Left | -250.0 | +200.0 | -0.250 | +0.200 | 0.000 |
| **$A_2$ (C2)** | Top-Right | +250.0 | +200.0 | +0.250 | +0.200 | 0.000 |
| **$A_3$ (C3)** | Bottom-Right | +250.0 | -200.0 | +0.250 | -0.200 | 0.000 |
| **$A_4$ (C4)** | Bottom-Left | -250.0 | -200.0 | -0.250 | -0.200 | 0.000 |

---

## 3. Moving Platform and Cable Attachments

The moving end-effector platform is a precision-machined 6061-T6 aluminum or carbon-reinforced composite plate:

| Property | Millimetres / Grams | SI Internal Units | Status |
|---|---:|---:|---|
| Platform Width ($W_p$) | 100.0 mm | 0.100 m | Design Input |
| Platform Height ($H_p$) | 80.0 mm | 0.080 m | Design Input |
| Platform Thickness ($T_p$) | 6.0 mm | 0.006 m | Design Input |
| Platform Mass ($m$) | 500 g | 0.500 kg | Provisional |
| Rotational Inertia ($I_{zz}$) | - | $0.0006833\text{ kg}\cdot\text{m}^2$ | $\frac{1}{12}m(W_p^2 + H_p^2)$ |

### Platform Attachment Points ($B_i$)
Attachment eyelet centres in local platform coordinates (relative to platform centre):

| Attachment | Corner | Local X (mm) | Local Y (mm) | Local X (m) | Local Y (m) | Local Z (m) |
|---|---|---:|---:|---:|---:|---:|
| **$B_1$ (C1)** | Top-Left | -50.0 | +40.0 | -0.050 | +0.040 | 0.000 |
| **$B_2$ (C2)** | Top-Right | +50.0 | +40.0 | +0.050 | +0.040 | 0.000 |
| **$B_3$ (C3)** | Bottom-Right | +50.0 | -40.0 | +0.050 | -0.040 | 0.000 |
| **$B_4$ (C4)** | Bottom-Left | -50.0 | -40.0 | -0.050 | -0.040 | 0.000 |

### World Attachment Position ($P_i$)
Given platform position $q = [x, y]^T$:
$$P_i(q) = q + B_i = \begin{bmatrix} x + B_{ix} \\ y + B_{iy} \end{bmatrix}$$

---

## 4. Spool Drums and Actuator Geometry

Each corner winch incorporates a precision constant-pitch grooved spool drum:

- **Nominal Spool Pitch Radius ($r$):** $10.0\text{ mm}$ ($0.010\text{ m}$, provisional).
- **Spool Circumference:** $C = 2\pi r \approx 62.83\text{ mm/rev}$.
- **Spool Inertia ($J_{drum}$):** $1.0 \times 10^{-5}\text{ kg}\cdot\text{m}^2$ (provisional).
- **Provisional Motor Speed Limit:** $300\text{ RPM}$ ($31.416\text{ rad/s} \rightarrow 314.16\text{ mm/s}$ maximum linear cable rate).
- **Provisional Motor Torque Limit:** $0.40\text{ Nm}$ (sustains up to $36.0\text{ N}$ cable tension at $\eta = 0.90$).

---

## 5. Permissible Workspace Limits

To prevent mechanical collision between the moving platform perimeter and the outer frame rails, a conservative safety margin of $20.0\text{ mm}$ ($0.020\text{ m}$) is enforced:

$$X_{travel} = \pm \left(\frac{W_f}{2} - \frac{W_p}{2} - \text{margin}\right) = \pm (250 - 50 - 20) = \pm 180.0\text{ mm} = \pm 0.180\text{ m}$$

$$Y_{travel} = \pm \left(\frac{H_f}{2} - \frac{H_p}{2} - \text{margin}\right) = \pm (200 - 40 - 20) = \pm 140.0\text{ mm} = \pm 0.140\text{ m}$$

- **Allowable X Range:** $[-180.0\text{ mm}, +180.0\text{ mm}]$ ($[-0.180\text{ m}, +0.180\text{ m}]$)
- **Allowable Y Range:** $[-140.0\text{ mm}, +140.0\text{ mm}]$ ($[-0.140\text{ m}, +0.140\text{ m}]$)

---

## 6. Cable Length at Home Position ($q = [0, 0]$)

At origin $q = [0, 0]^T$:
$$\Delta x_i = |A_{ix} - B_{ix}| = 0.250 - 0.050 = 0.200\text{ m}$$
$$\Delta y_i = |A_{iy} - B_{iy}| = 0.200 - 0.040 = 0.160\text{ m}$$
$$L_{home} = \sqrt{0.200^2 + 0.160^2} = \sqrt{0.0400 + 0.0256} = \sqrt{0.0656} \approx 0.256125\text{ m} \quad (256.12\text{ mm})$$

By quadrant symmetry, all four cables have identical geometric lengths at home:
$$L_1 = L_2 = L_3 = L_4 = 256.125\text{ mm}$$
