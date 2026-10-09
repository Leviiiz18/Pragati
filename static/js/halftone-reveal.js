/**
 * HalftoneReveal Component (Vanilla WebGL2 Engine from KalpKrafts)
 * Interactive CMYK Halftone Screen Shader with Cursor Reveal Lens
 */

(function () {
  const hexToRgb = (hex) => {
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex || '');
    return m ? [parseInt(m[1], 16) / 255, parseInt(m[2], 16) / 255, parseInt(m[3], 16) / 255] : [0, 0, 0];
  };

  const MODES = { mono: 0, duotone: 1, color: 2 };
  const SHAPES = { circle: 0, square: 1, diamond: 2, line: 3 };
  const TRIGGERS = { off: 0, hover: 1, always: 2 };

  const VERT = `#version 300 es
  in vec2 position;
  out vec2 vUv;
  void main() {
    vUv = position * 0.5 + 0.5;
    gl_Position = vec4(position, 0.0, 1.0);
  }
  `;

  const FRAG = `#version 300 es
  precision highp float;

  uniform sampler2D tMap;
  uniform vec2 iResolution;
  uniform vec2 uImageSize;
  uniform vec2 uMouse;
  uniform float uActivity;

  uniform float uDotSize;
  uniform float uDensity;
  uniform float uAngle;
  uniform int uShape;
  uniform vec3 uInk;
  uniform vec3 uPaper;
  uniform int uMode;
  uniform float uContrast;
  uniform float uInvert;

  uniform float uRevealRadius;
  uniform float uEdge;
  uniform float uIdleReveal;
  uniform int uTrigger;

  in vec2 vUv;
  out vec4 fragColor;

  vec2 uAspect() {
    return vec2(iResolution.x / max(iResolution.y, 1.0), 1.0);
  }

  vec2 coverUv(vec2 uv) {
    float ia = uImageSize.x / max(uImageSize.y, 1.0);
    float pa = iResolution.x / max(iResolution.y, 1.0);
    vec2 s = pa > ia ? vec2(1.0, ia / pa) : vec2(pa / ia, 1.0);
    return (uv - 0.5) * s + 0.5;
  }

  vec3 gradeRGB(vec3 c) {
    c = clamp((c - 0.5) * uContrast + 0.5, 0.0, 1.0);
    return mix(c, 1.0 - c, uInvert);
  }

  float shapeDist(vec2 f) {
    if (uShape == 1) return max(abs(f.x), abs(f.y));
    if (uShape == 2) return abs(f.x) + abs(f.y);
    if (uShape == 3) return abs(f.y);
    return length(f);
  }

  mat2 rot(float a) {
    float c = cos(a);
    float s = sin(a);
    return mat2(c, -s, s, c);
  }

  vec4 sampleCell(vec2 st, float dens, float ang) {
    vec2 rp = rot(ang) * st * dens;
    vec2 center = floor(rp) + 0.5;
    vec2 stC = rot(-ang) * (center / dens);
    vec2 uvC = stC / uAspect();
    return texture(tMap, clamp(coverUv(uvC), 0.0, 1.0));
  }

  float coverage(vec2 st, float dens, float ang, float ink, float rscale) {
    vec2 rp = rot(ang) * st * dens;
    vec2 f = fract(rp) - 0.5;
    float d = shapeDist(f);
    float r = sqrt(clamp(ink, 0.0, 1.0)) * 0.72 * rscale * uDotSize;
    float w = length(fwidth(rp)) * 0.6 + 1e-4;
    return smoothstep(r + w, r - w, d);
  }

  void main() {
    vec2 aspect = uAspect();
    vec2 st = vUv * aspect;
    float ang = radians(uAngle);

    vec2 duv = (vUv - uMouse) * aspect;
    float dist = length(duv);

    float act = uTrigger == 2 ? 1.0 : (uTrigger == 0 ? 0.0 : uActivity);
    float radius = max(uRevealRadius, 1e-4) * mix(0.4, 1.0, act);

    float px = 1.4 / max(iResolution.y, 1.0);
    float band = max(px, radius * (1.0 - clamp(uEdge, 0.0, 1.0)) * 0.45);
    float loupe = 1.0 - smoothstep(radius - band, radius + band, dist);
    float focus = clamp(max(loupe * act, uIdleReveal), 0.0, 1.0);

    float dens = uDensity;

    vec3 print;
    if (uMode == 2) {
      vec3 gc = gradeRGB(sampleCell(st, dens, ang + radians(15.0)).rgb);
      vec3 gm = gradeRGB(sampleCell(st, dens, ang + radians(75.0)).rgb);
      vec3 gy = gradeRGB(sampleCell(st, dens, ang).rgb);
      vec3 gk = gradeRGB(sampleCell(st, dens, ang + radians(45.0)).rgb);
      float c = 1.0 - gc.r;
      float m = 1.0 - gm.g;
      float y = 1.0 - gy.b;
      float k = 1.0 - dot(gk, vec3(0.299, 0.587, 0.114));
      float gcr = min(min(c, m), y) * 0.5;
      c = clamp(c - gcr, 0.0, 1.0);
      m = clamp(m - gcr, 0.0, 1.0);
      y = clamp(y - gcr, 0.0, 1.0);
      k = clamp(max(gcr, k * k * 0.9), 0.0, 1.0);
      float covC = coverage(st, dens, ang + radians(15.0), c, 0.82);
      float covM = coverage(st, dens, ang + radians(75.0), m, 0.82);
      float covY = coverage(st, dens, ang, y, 0.82);
      float covK = coverage(st, dens, ang + radians(45.0), k, 0.78);
      print = uPaper;
      print = mix(print, print * vec3(0.10, 0.72, 0.90), covC);
      print = mix(print, print * vec3(0.92, 0.10, 0.52), covM);
      print = mix(print, print * vec3(0.98, 0.86, 0.10), covY);
      print = mix(print, print * vec3(0.08), covK);
    } else if (uMode == 1) {
      vec3 ink2 = mix(uInk.gbr, vec3(0.90, 0.24, 0.30), 0.7);
      float lumA = dot(gradeRGB(sampleCell(st, dens, ang).rgb), vec3(0.299, 0.587, 0.114));
      float lumB = dot(gradeRGB(sampleCell(st, dens, ang + radians(38.0)).rgb), vec3(0.299, 0.587, 0.114));
      float covA = coverage(st, dens, ang, 1.0 - lumA, 1.0);
      float covB = coverage(st, dens, ang + radians(38.0), pow(1.0 - lumB, 1.4), 0.92);
      print = uPaper;
      print = mix(print, ink2, covB * 0.85);
      print = mix(print, uInk, covA);
    } else {
      float lum = dot(gradeRGB(sampleCell(st, dens, ang).rgb), vec3(0.299, 0.587, 0.114));
      float cov = coverage(st, dens, ang, 1.0 - lum, 1.0);
      print = mix(uPaper, uInk, cov);
    }

    float t = clamp(dist / radius, 0.0, 1.0);
    float bend = t * t * t * t;
    vec2 dir = dist > 1e-5 ? duv / dist : vec2(0.0);
    vec2 off = dir * bend * radius * 0.22 / aspect;
    vec2 ca = dir * bend * 0.0045 / aspect;
    vec3 sharp = gradeRGB(vec3(
      texture(tMap, clamp(coverUv(vUv - off - ca), 0.0, 1.0)).r,
      texture(tMap, clamp(coverUv(vUv - off), 0.0, 1.0)).g,
      texture(tMap, clamp(coverUv(vUv - off + ca), 0.0, 1.0)).b
    ));

    vec3 col = mix(print, sharp, focus);
    fragColor = vec4(col, 1.0);
  }
  `;

  function initHalftoneReveal(container) {
    if (container._halftoneInitialized) return;
    container._halftoneInitialized = true;

    const ds = container.dataset;
    const src = ds.src || '/static/images/college_life.png';
    const inkColor = ds.inkColor || '#1D222D';
    const paperColor = ds.paperColor || '#F5FBFD';
    const mode = ds.mode || 'color';
    const dotSize = ds.dotSize !== undefined ? parseFloat(ds.dotSize) : 1;
    const dotDensity = ds.dotDensity !== undefined ? parseFloat(ds.dotDensity) : 150;
    const angle = ds.angle !== undefined ? parseFloat(ds.angle) : 45;
    const shape = ds.shape || 'circle';
    const contrast = ds.contrast !== undefined ? parseFloat(ds.contrast) : 1.15;
    const invert = ds.invert === 'true';
    const revealRadius = ds.revealRadius !== undefined ? parseFloat(ds.revealRadius) : 0.32;
    const edge = ds.edge !== undefined ? parseFloat(ds.edge) : 0.8;
    const follow = ds.follow !== undefined ? parseFloat(ds.follow) : 0.37;
    const idleReveal = ds.idleReveal !== undefined ? parseFloat(ds.idleReveal) : 0;
    const trigger = ds.trigger || 'hover';

    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const gl = canvas.getContext('webgl2', {
      alpha: false,
      antialias: true
    });

    if (!gl) {
      console.warn('WebGL2 not supported for HalftoneReveal');
      return;
    }

    gl.clearColor(0, 0, 0, 1);

    // Shaders
    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, VERT);
    gl.compileShader(vs);

    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, FRAG);
    gl.compileShader(fs);

    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);

    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.warn('Halftone shader error:', gl.getProgramInfoLog(prog));
      return;
    }

    gl.useProgram(prog);

    // Quad geometry
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

    // Texture
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

    // 1x1 placeholder
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGBA,
      1,
      1,
      0,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      new Uint8Array([240, 240, 240, 255])
    );

    // Uniform locations
    const uLocs = {
      tMap: gl.getUniformLocation(prog, 'tMap'),
      iResolution: gl.getUniformLocation(prog, 'iResolution'),
      uImageSize: gl.getUniformLocation(prog, 'uImageSize'),
      uMouse: gl.getUniformLocation(prog, 'uMouse'),
      uActivity: gl.getUniformLocation(prog, 'uActivity'),
      uDotSize: gl.getUniformLocation(prog, 'uDotSize'),
      uDensity: gl.getUniformLocation(prog, 'uDensity'),
      uAngle: gl.getUniformLocation(prog, 'uAngle'),
      uShape: gl.getUniformLocation(prog, 'uShape'),
      uInk: gl.getUniformLocation(prog, 'uInk'),
      uPaper: gl.getUniformLocation(prog, 'uPaper'),
      uMode: gl.getUniformLocation(prog, 'uMode'),
      uContrast: gl.getUniformLocation(prog, 'uContrast'),
      uInvert: gl.getUniformLocation(prog, 'uInvert'),
      uRevealRadius: gl.getUniformLocation(prog, 'uRevealRadius'),
      uEdge: gl.getUniformLocation(prog, 'uEdge'),
      uIdleReveal: gl.getUniformLocation(prog, 'uIdleReveal'),
      uTrigger: gl.getUniformLocation(prog, 'uTrigger')
    };

    const inkRGB = hexToRgb(inkColor);
    const paperRGB = hexToRgb(paperColor);

    gl.uniform1i(uLocs.tMap, 0);
    gl.uniform1f(uLocs.uDotSize, dotSize);
    gl.uniform1f(uLocs.uDensity, dotDensity);
    gl.uniform1f(uLocs.uAngle, angle);
    gl.uniform1i(uLocs.uShape, SHAPES[shape] ?? 0);
    gl.uniform3f(uLocs.uInk, inkRGB[0], inkRGB[1], inkRGB[2]);
    gl.uniform3f(uLocs.uPaper, paperRGB[0], paperRGB[1], paperRGB[2]);
    gl.uniform1i(uLocs.uMode, MODES[mode] ?? 2);
    gl.uniform1f(uLocs.uContrast, contrast);
    gl.uniform1f(uLocs.uInvert, invert ? 1 : 0);
    gl.uniform1f(uLocs.uRevealRadius, revealRadius);
    gl.uniform1f(uLocs.uEdge, edge);
    gl.uniform1f(uLocs.uIdleReveal, idleReveal);
    gl.uniform1i(uLocs.uTrigger, TRIGGERS[trigger] ?? 1);

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = src;
    img.onload = () => {
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      gl.useProgram(prog);
      gl.uniform2f(uLocs.uImageSize, img.naturalWidth || 1, img.naturalHeight || 1);
    };

    const resize = () => {
      const w = container.clientWidth || 1;
      const h = container.clientHeight || 1;
      const pixelW = Math.round(w * dpr);
      const pixelH = Math.round(h * dpr);
      if (canvas.width !== pixelW || canvas.height !== pixelH) {
        canvas.width = pixelW;
        canvas.height = pixelH;
      }
      gl.viewport(0, 0, pixelW, pixelH);
      gl.useProgram(prog);
      gl.uniform2f(uLocs.iResolution, pixelW, pixelH);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(container);
    resize();

    const mouse = { x: 0.5, y: 0.5, sx: 0.5, sy: 0.5, active: 0, target: 0 };
    const onMove = (e) => {
      const rect = container.getBoundingClientRect();
      const withinX = e.clientX >= rect.left && e.clientX <= rect.right;
      const withinY = e.clientY >= rect.top && e.clientY <= rect.bottom;
      if (withinX && withinY) {
        mouse.x = (e.clientX - rect.left) / rect.width;
        mouse.y = 1 - (e.clientY - rect.top) / rect.height;
        mouse.target = 1;
      } else {
        mouse.target = 0;
      }
    };

    window.addEventListener('pointermove', onMove, { passive: true });

    let prev = performance.now();
    let raf = 0;

    const loop = (now) => {
      raf = requestAnimationFrame(loop);
      const dt = Math.min(0.05, Math.max(0.001, (now - prev) / 1000));
      prev = now;

      const a = 1 - Math.exp(-dt / Math.max(0.001, follow));
      mouse.sx += (mouse.x - mouse.sx) * a;
      mouse.sy += (mouse.y - mouse.sy) * a;

      const ba = 1 - Math.exp(-dt / 0.18);
      mouse.active += (mouse.target - mouse.active) * ba;

      gl.useProgram(prog);
      gl.uniform2f(uLocs.uMouse, mouse.sx, mouse.sy);
      gl.uniform1f(uLocs.uActivity, mouse.active);

      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, texture);

      gl.bindVertexArray(vao);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    raf = requestAnimationFrame(loop);
  }

  function initAllHalftones() {
    const containers = document.querySelectorAll('.halftone-reveal');
    containers.forEach(initHalftoneReveal);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllHalftones);
  } else {
    initAllHalftones();
  }

  window.initHalftones = initAllHalftones;
  window.initHalftoneReveal = initHalftoneReveal;
})();
