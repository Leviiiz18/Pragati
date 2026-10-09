/**
 * SpecularButton Component (React Bits Vanilla WebGL2 Port)
 * Dynamic SDF Specular Light Shader for CTA Buttons
 */

(function () {
  const PAD = 20;

  const VERT = `#version 300 es
  in vec2 position;
  void main() {
    gl_Position = vec4(position, 0.0, 1.0);
  }
  `;

  const FRAG = `#version 300 es
  precision highp float;

  uniform vec2 uCenter;
  uniform vec2 uHalfSize;
  uniform float uRadius;
  uniform float uAngle;
  uniform float uPx;
  uniform vec3 uLineColor;
  uniform vec3 uBaseColor;
  uniform float uIntensity;
  uniform float uShineSize;
  uniform float uShineFade;
  uniform float uThickness;
  uniform float uBaseWidth;

  out vec4 fragColor;

  float sdRoundedRect(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
  }

  float shapeSDF(vec2 p) { return sdRoundedRect(p, uHalfSize, uRadius); }

  float gaussianLine(float d, float sigma) {
    float x = d / (sigma + 1e-6);
    float k = mix(1.0, 1.6, smoothstep(0.0, 1.5, x));
    return exp(-k * x * x);
  }

  void main() {
    vec2 p = gl_FragCoord.xy - uCenter;
    float d = shapeSDF(p);
    vec2 L = vec2(cos(uAngle), sin(uAngle));

    // Dark base stroke hugging the edge for a sense of thickness
    float base = (1.0 - smoothstep(0.0, uBaseWidth, abs(d))) * 0.45;

    // Symmetric specular: the edges facing toward/away from the light both
    // catch a streak. The angular window (size + fade) is measured with an
    // elliptical normal so it varies continuously along straight edges.
    vec2 nEll = normalize(p / (uHalfSize * uHalfSize) + 1e-6);
    float phi = acos(clamp(abs(dot(nEll, L)), 0.0, 1.0));
    float rim = 1.0 - smoothstep(uShineSize - uShineFade, uShineSize + uShineFade + 1e-4, phi);
    float line = gaussianLine(d, uThickness);
    float edgeClamp = 1.0 - smoothstep(0.5 * uPx, 3.0 * uPx, abs(d));
    float hi = line * rim * edgeClamp * uIntensity;

    vec3 col = uBaseColor * base + uLineColor * hi;
    float a = clamp(base + hi, 0.0, 1.0);
    fragColor = vec4(col, a);
  }
  `;

  function parseColor(hex) {
    if (!hex || typeof hex !== 'string') return [1, 1, 1];
    let h = hex.trim().replace(/^#/, '');
    if (h.length === 3) {
      h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    }
    if (h.length === 6) {
      const num = parseInt(h, 16);
      if (!isNaN(num)) {
        return [
          ((num >> 16) & 255) / 255,
          ((num >> 8) & 255) / 255,
          (num & 255) / 255
        ];
      }
    }
    return [1, 1, 1];
  }

  function initSpecularButton(btn) {
    if (btn._specularInitialized) return;
    btn._specularInitialized = true;

    let fx = btn.querySelector('.specular-button__fx');
    if (!fx) {
      fx = document.createElement('span');
      fx.className = 'specular-button__fx';
      fx.setAttribute('aria-hidden', 'true');
      btn.insertBefore(fx, btn.firstChild);
    }

    const ds = btn.dataset;
    const props = {
      radius: ds.radius !== undefined ? parseFloat(ds.radius) : 18,
      lineColor: ds.lineColor || '#ffffff',
      baseColor: ds.baseColor || '#525252',
      intensity: ds.intensity !== undefined ? parseFloat(ds.intensity) : 1,
      shineSize: ds.shineSize !== undefined ? parseFloat(ds.shineSize) : 10,
      shineFade: ds.shineFade !== undefined ? parseFloat(ds.shineFade) : 40,
      thickness: ds.thickness !== undefined ? parseFloat(ds.thickness) : 1,
      speed: ds.speed !== undefined ? parseFloat(ds.speed) : 0.35,
      followMouse: ds.followMouse !== undefined ? ds.followMouse !== 'false' : true,
      proximity: ds.proximity !== undefined ? parseFloat(ds.proximity) : 250,
      autoAnimate: ds.autoAnimate !== undefined ? ds.autoAnimate === 'true' : false
    };

    const canvas = document.createElement('canvas');
    fx.appendChild(canvas);

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const gl = canvas.getContext('webgl2', {
      alpha: true,
      premultipliedAlpha: true,
      antialias: true
    });

    if (!gl) {
      return;
    }

    gl.clearColor(0, 0, 0, 0);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

    // Vertex shader
    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, VERT);
    gl.compileShader(vs);

    // Fragment shader
    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, FRAG);
    gl.compileShader(fs);

    // Program
    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);

    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.warn('Specular program error:', gl.getProgramInfoLog(prog));
      return;
    }

    gl.useProgram(prog);

    // Geometry - Full screen triangle
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const vbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 3, -1, -1, 3]),
      gl.STATIC_DRAW
    );
    const posLoc = gl.getAttribLocation(prog, 'position');
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

    // Uniforms
    const uCenter = gl.getUniformLocation(prog, 'uCenter');
    const uHalfSize = gl.getUniformLocation(prog, 'uHalfSize');
    const uRadius = gl.getUniformLocation(prog, 'uRadius');
    const uAngle = gl.getUniformLocation(prog, 'uAngle');
    const uPx = gl.getUniformLocation(prog, 'uPx');
    const uLineColor = gl.getUniformLocation(prog, 'uLineColor');
    const uBaseColor = gl.getUniformLocation(prog, 'uBaseColor');
    const uIntensity = gl.getUniformLocation(prog, 'uIntensity');
    const uShineSize = gl.getUniformLocation(prog, 'uShineSize');
    const uShineFade = gl.getUniformLocation(prog, 'uShineFade');
    const uThickness = gl.getUniformLocation(prog, 'uThickness');
    const uBaseWidth = gl.getUniformLocation(prog, 'uBaseWidth');

    gl.uniform1f(uPx, dpr);
    gl.uniform1f(uBaseWidth, dpr);

    const sizeRef = { w: 1, h: 1 };
    const resize = () => {
      const rect = btn.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      if (w === 0 || h === 0) return;
      sizeRef.w = w;
      sizeRef.h = h;
      const pixelW = Math.round((w + PAD * 2) * dpr);
      const pixelH = Math.round((h + PAD * 2) * dpr);
      if (canvas.width !== pixelW || canvas.height !== pixelH) {
        canvas.width = pixelW;
        canvas.height = pixelH;
      }
      gl.viewport(0, 0, pixelW, pixelH);
      gl.useProgram(prog);
      gl.uniform2f(uCenter, (PAD + w / 2) * dpr, (PAD + h / 2) * dpr);
      gl.uniform2f(uHalfSize, (w / 2) * dpr, (h / 2) * dpr);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(btn);
    resize();

    let pointerAngle = null;
    let proximityT = 0;
    const onPointerMove = (e) => {
      const rect = btn.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = Math.max(rect.left - e.clientX, 0, e.clientX - rect.right);
      const dy = Math.max(rect.top - e.clientY, 0, e.clientY - rect.bottom);
      const dist = Math.hypot(dx, dy);

      if (dist === 0) {
        const nx = (e.clientX - cx) / (rect.width / 2);
        const ny = (cy - e.clientY) / (rect.height / 2);
        pointerAngle = Math.atan2(2 / rect.height, -2 / rect.width) + nx * 0.3 + ny * 0.15;
      } else {
        pointerAngle = Math.atan2(cy - e.clientY, e.clientX - cx);
      }
      const t = Math.max(0, 1 - dist / Math.max(props.proximity, 1));
      proximityT = t * t * (3 - 2 * t);
    };
    window.addEventListener('pointermove', onPointerMove, { passive: true });

    let angle = 2.4;
    let idleAngle = 2.4;
    let bright = 0;
    let last = performance.now();
    let raf = 0;

    const lineC = parseColor(props.lineColor);
    const baseC = parseColor(props.baseColor);

    const update = (now) => {
      raf = requestAnimationFrame(update);
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      idleAngle += props.speed * dt;
      const steer = props.followMouse && pointerAngle != null && (!props.autoAnimate || proximityT > 0);
      const target = steer ? pointerAngle : idleAngle;
      const diff = ((target - angle + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
      angle += diff * (1 - Math.exp(-dt * 7));

      const brightTarget = props.autoAnimate ? 1 : proximityT;
      bright += (brightTarget - bright) * (1 - Math.exp(-dt * 8));

      gl.useProgram(prog);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform1f(uAngle, angle);
      gl.uniform1f(uRadius, Math.min(props.radius, Math.min(sizeRef.w, sizeRef.h) / 2) * dpr);
      gl.uniform3f(uLineColor, lineC[0], lineC[1], lineC[2]);
      gl.uniform3f(uBaseColor, baseC[0], baseC[1], baseC[2]);
      gl.uniform1f(uIntensity, props.intensity * bright);
      gl.uniform1f(uShineSize, (props.shineSize * Math.PI) / 180);
      gl.uniform1f(uShineFade, (props.shineFade * Math.PI) / 180);
      gl.uniform1f(uThickness, props.thickness * dpr);

      gl.bindVertexArray(vao);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    raf = requestAnimationFrame(update);
  }

  function initAllSpecularButtons() {
    const buttons = document.querySelectorAll('.specular-button');
    buttons.forEach(initSpecularButton);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllSpecularButtons);
  } else {
    initAllSpecularButtons();
  }

  window.initSpecularButtons = initAllSpecularButtons;
  window.initSpecularButton = initSpecularButton;
})();
