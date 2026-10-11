/**
 * Three.js scene setup: Camera, Renderer, OrbitControls, Lighting, Coordinate Axes.
 */
class SceneManager {
  constructor(containerElement) {
    this.container = containerElement;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xffffff);

    const width = this.container.clientWidth || 800;
    const height = this.container.clientHeight || 600;

    // Perspective camera positioned above and slightly in front of the horizontal CDPR plane
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 20.0);
    this.camera.position.set(0.0, -0.36, 0.44); // Look down toward horizontal XY plane matching reference photo
    this.camera.up.set(0, 0, 1); // Z is normal to horizontal motion plane

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.container.appendChild(this.renderer.domElement);

    // OrbitControls
    this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.target.set(0, 0, 0);

    this.setupLighting();
    this.setupEnvironment();

    window.addEventListener('resize', () => this.onResize());
  }

  setupLighting() {
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
    this.scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.85);
    dirLight1.position.set(0.5, -0.5, 1.2);
    this.scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x94a3b8, 0.4);
    dirLight2.position.set(-0.5, 0.5, 0.8);
    this.scene.add(dirLight2);
  }

  setupEnvironment() {
    // Ground reference grid (in XY plane, slightly below robot at z = -0.07 m)
    const grid = new THREE.GridHelper(1.2, 24, 0x94a3b8, 0xe2e8f0);
    grid.rotation.x = Math.PI / 2; // Orient grid in XY plane
    grid.position.z = -0.065;
    this.scene.add(grid);

    // Coordinate axes (RGB = XYZ)
    const axes = new THREE.AxesHelper(0.15); // 150 mm axes
    axes.position.set(0, 0, 0);
    this.scene.add(axes);
  }

  onResize() {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    if (width === 0 || height === 0) return;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  render() {
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}

window.SceneManager = SceneManager;
