/**
 * PatternWaves Component (React Bits Vanilla WebGL2 Engine)
 * High-Performance Procedural Silk & Interactive Cursor Ripple Wave Surface Renderer
 */

(function () {
  const SURFACE_PRESETS = {
    silk: {
      pattern: 'dot',
      wave: 'silk',
      spacing: 9,
      markSize: 0.95,
      depth: 0.95,
      light: 0,
      shine: 1.0,
      contrast: 1.25,
      speed: 0.35,
      scale: 1,
      direction: 25
    },
    ocean: {
      pattern: 'dot',
      wave: 'swell',
      spacing: 10,
      markSize: 0.9,
      depth: 0.45,
      light: 0,
      shine: 1.1,
      contrast: 1.2,
      speed: 0.5,
      scale: 1,
      direction: 100
    },
    pond: {
      pattern: 'dot',
      wave: 'ripple',
      spacing: 10,
      markSize: 0.9,
      depth: 0.55,
      light: 0,
      shine: 1.2,
      contrast: 1.2,
      speed: 0.5,
      scale: 1,
      direction: 35
    },
    lines: {
      pattern: 'line',
      wave: 'silk',
      spacing: 12,
      markSize: 0.42,
      depth: 0.9,
      light: 0,
      shine: 0.8,
      contrast: 1.2,
      speed: 0.3,
      scale: 1,
      direction: 20
    },
    terminal: {
      pattern: 'glyph',
      wave: 'ripple',
      spacing: 13,
      markSize: 0.95,
      depth: 0.75,
      light: 0,
      shine: 0.9,
      contrast: 1.4,
      speed: 0.3,
      scale: 1.1,
      direction: 200
    },
    mesh: {
      pattern: 'plus',
      wave: 'silk',
      spacing: 14,
      markSize: 0.85,
      depth: 0.95,
      light: 0,
      shine: 1.1,
      contrast: 1.45,
      speed: 0.4,
      scale: 1.1,
      direction: 325
    }
  };

  const PATTERNS = { dot: 0, square: 1, plus: 2, line: 3, glyph: 4 };
  const WAVES = { silk: 0, swell: 1, ripple: 2 };
  const FADES = { none: 0, edges: 1, center: 2, bottom: 3, top: 4 };
  const WAVE_UNIT = 520;
  const INTRO_SECONDS = 1.5;

  const clamp = (val, min, max) => Math.min(Math.max(val, min), max);
  const luminance = (rgba) => 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2];

  const parseColor = (val, fallback) => {
    try {
      if (!val || typeof val !== 'string') return fallback;
      if (val === 'transparent') return [0, 0, 0, 0];
      const ctx = document.createElement('canvas').getContext('2d');
      if (!ctx) return fallback;
      ctx.fillStyle = val;
      const res = ctx.fillStyle;
      if (res.startsWith('#')) {
        const n = parseInt(res.slice(1), 16);
        return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, 1];
      }
      const parts = res.match(/[\d.]+/g);
      if (!parts || parts.length < 3) return fallback;
      return [Number(parts[0]) / 255, Number(parts[1]) / 255, Number(parts[2]) / 255, parts[3] ? Number(parts[3]) : 1];
    } catch {
      return fallback;
    }
  };

  const vertexShader = `#version 300 es
  in vec2 position;
  void main() {
    gl_Position = vec4(position, 0.0, 1.0);
  }
  `;

  const mainFragmentShader = `#version 300 es
  precision highp float;
  precision highp int;

  uniform vec2 uSize;
  uniform float uDpr;
  uniform vec2 uOrigin;
  uniform vec2 uPitch;
  uniform int uPattern;
  uniform int uWave;
  uniform float uTime;
  uniform float uUnit;
  uniform vec2 uHeading;
  uniform float uAmp;
  uniform float uDepth;
  uniform vec3 uLight;
  uniform float uShine;
  uniform float uContrast;
  uniform float uMarkSize;
  uniform float uStroke;
  uniform vec3 uColor;
  uniform vec3 uAccent;
  uniform vec4 uBackground;
  uniform int uFade;
  uniform float uFadeSize;
  uniform float uAppear;

  // Interactive Cursor Uniforms
  uniform vec2 uPointer;        // In CSS pixels [0..width, 0..height]
  uniform vec2 uPointerVel;     // Cursor velocity vector
  uniform float uCursorActive;  // 0.0 to 1.0 hover strength
  uniform float uCursorRadius;  // Interaction radius in CSS px
  uniform float uCursorStrength;// Interaction wave strength
  uniform vec4 uRipples[4];     // Up to 4 active expanding shockwaves: vec4(x, y, startTime, strength)

  out vec4 fragColor;

  const float FOLDS = 5.5;

  uvec3 scramble(uvec3 v) {
    v = v * 1664525u + 1013904223u;
    v.x += v.y * v.z;
    v.y += v.z * v.x;
    v.z += v.x * v.y;
    v ^= v >> 16u;
    v.x += v.y * v.z;
    v.y += v.z * v.x;
    v.z += v.x * v.y;
    return v;
  }

  vec3 lattice(vec3 corner) {
    uvec3 h = scramble(uvec3(ivec3(corner) + 4096));
    return vec3(h & 65535u) / 32767.5 - 1.0;
  }

  float gradientNoise(vec3 p) {
    vec3 i = floor(p);
    vec3 f = p - i;
    vec3 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
    float n000 = dot(lattice(i), f);
    float n100 = dot(lattice(i + vec3(1.0, 0.0, 0.0)), f - vec3(1.0, 0.0, 0.0));
    float n010 = dot(lattice(i + vec3(0.0, 1.0, 0.0)), f - vec3(0.0, 1.0, 0.0));
    float n110 = dot(lattice(i + vec3(1.0, 1.0, 0.0)), f - vec3(1.0, 1.0, 0.0));
    float n001 = dot(lattice(i + vec3(0.0, 0.0, 1.0)), f - vec3(0.0, 0.0, 1.0));
    float n101 = dot(lattice(i + vec3(1.0, 0.0, 1.0)), f - vec3(1.0, 0.0, 1.0));
    float n011 = dot(lattice(i + vec3(0.0, 1.0, 1.0)), f - vec3(0.0, 1.0, 1.0));
    float n111 = dot(lattice(i + vec3(1.0, 1.0, 1.0)), f - vec3(1.0, 1.0, 1.0));
    return mix(
      mix(mix(n000, n100, u.x), mix(n010, n110, u.x), u.y),
      mix(mix(n001, n101, u.x), mix(n011, n111, u.x), u.y),
      u.z
    );
  }

  float surface(vec2 p, float t) {
    if (uWave == 0) {
      vec2 side = vec2(-uHeading.y, uHeading.x);
      float u = dot(p, uHeading);
      float v = dot(p, side);
      float bend = gradientNoise(vec3(v * 0.85, u * 0.3, t * 0.05)) * 1.7 + 0.4 * sin(v * 1.6 + t * 0.2);
      float phase = u * FOLDS + bend - t * 0.45;
      float swell = 0.6 + 0.4 * gradientNoise(vec3(u * 0.55 + 3.0, v * 0.45, t * 0.04));
      float fold = sin(phase) + 0.32 * sin(2.0 * phase + 1.3);
      float ripple = 0.16 * sin(u * FOLDS * 2.5 + bend * 1.9 - t * 0.9 + 2.1);
      return (fold + ripple) * swell;
    }
    if (uWave == 1) {
      float bend = gradientNoise(vec3(p * 0.6, t * 0.05)) * 0.6;
      float phase = dot(p, uHeading) * 15.0 + bend * 2.2 - t * 1.4;
      float swell = sin(phase) + 0.3 * sin(2.0 * phase - 0.8);
      float roll = 0.75 + 0.25 * gradientNoise(vec3(p * 0.9 + 11.0, t * 0.05));
      return 0.8 * swell * roll;
    }
    float r = length(p + uHeading * 1.2);
    float bend = gradientNoise(vec3(p * 1.2, t * 0.05)) * 0.1;
    return sin((r + bend) * 9.0 - t * 1.8) * (0.45 + 0.55 * exp(-(r - 0.6) * 0.8));
  }

  float heightAt(vec2 css) {
    float h = surface((css - 0.5 * uSize) / uUnit, uTime) * uAmp;

    // Interactive Cursor Wave Dynamics
    if (uCursorActive > 0.001) {
      vec2 diff = css - uPointer;
      float dist = length(diff);

      // 1. Direct 3D cursor elevation crest
      float crest = exp(-dist * dist / (2.0 * uCursorRadius * uCursorRadius)) * uCursorStrength * 1.4;

      // 2. Fluid radiating ripple wave train around cursor
      float ripplePhase = dist / (uCursorRadius * 0.35) - uTime * 6.0;
      float ripple = sin(ripplePhase) * exp(-dist / (uCursorRadius * 2.2)) * uCursorStrength * 0.85;

      // 3. Directional velocity wake
      float velMag = length(uPointerVel);
      if (velMag > 0.1) {
        float wake = dot(normalize(diff + vec2(0.001)), normalize(uPointerVel)) * exp(-dist / (uCursorRadius * 1.6)) * uCursorStrength * 0.6;
        h += wake * uCursorActive;
      }

      h += (crest + ripple) * uCursorActive;
    }

    // Expanding Click / Burst Shockwaves
    for (int i = 0; i < 4; i++) {
      if (uRipples[i].w > 0.01) {
        float age = uTime - uRipples[i].z;
        if (age > 0.0 && age < 3.0) {
          float dist = length(css - uRipples[i].xy);
          float waveFront = age * 320.0;
          float delta = abs(dist - waveFront);
          float ring = sin(delta * 0.08) * exp(-delta * 0.02) * exp(-age * 1.1) * uRipples[i].w;
          h += ring;
        }
      }
    }

    return h;
  }

  float box(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
  }

  float coverage(vec2 local, float level) {
    float span = uPitch.y * uMarkSize;
    float area = max(sqrt(level), 0.16);
    if (uPattern == 0) {
      return clamp(0.5 - (length(local) - 0.5 * span * area), 0.0, 1.0);
    }
    if (uPattern == 1) {
      float extent = 0.5 * span * area;
      return clamp(0.5 - box(local, vec2(extent), extent * 0.3), 0.0, 1.0);
    }
    if (uPattern == 2) {
      float arm = 0.5 * span * mix(0.3, 1.0, level);
      float width = 0.5 * uStroke;
      return clamp(0.5 - min(box(local, vec2(arm, width), width), box(local, vec2(width, arm), width)), 0.0, 1.0);
    }
    return 0.0;
  }

  void main() {
    vec2 rel = gl_FragCoord.xy - uOrigin;
    vec2 cell = floor(rel / uPitch);
    vec2 cellCenter = (cell + 0.5) * uPitch + uOrigin;
    vec2 css = cellCenter / uDpr;
    vec2 uv = css / uSize;

    float e = max(uPitch.y / uDpr, 4.0);
    float h = heightAt(css);
    float hx = (heightAt(css + vec2(e, 0.0)) - heightAt(css - vec2(e, 0.0))) / (2.0 * e);
    float hy = (heightAt(css + vec2(0.0, e)) - heightAt(css - vec2(0.0, e))) / (2.0 * e);
    vec2 grad = vec2(hx, hy) * uUnit * uDepth * 0.45;
    vec3 n = normalize(vec3(-grad, 1.0));

    float diffuse = clamp(dot(n, uLight), 0.0, 1.0);
    vec3 halfway = normalize(uLight + vec3(0.0, 0.0, 1.0));
    float spec = pow(clamp(dot(n, halfway), 0.0, 1.0), 120.0) * uShine * 1.35;
    float tone = clamp(diffuse * 0.75 + spec + 0.15, 0.0, 1.0);
    tone = clamp((tone - 0.38) * uContrast + 0.38, 0.0, 1.0);
    float level = pow(tone, 1.8);

    float fade = 1.0;
    vec2 c = uv * 2.0 - 1.0;
    if (uFade == 1) {
      fade = 1.0 - smoothstep(1.0 - uFadeSize, 1.15, length(c));
    } else if (uFade == 2) {
      fade = mix(0.15, 1.0, smoothstep(0.08, 0.08 + uFadeSize, length(c * vec2(1.0, 1.35))));
    } else if (uFade == 3) {
      fade = smoothstep(0.0, uFadeSize, uv.y);
    } else if (uFade == 4) {
      fade = smoothstep(0.0, uFadeSize, 1.0 - uv.y);
    }

    float appear = uAppear;
    float alpha = fade * appear * (0.3 + 0.7 * level);

    // Render mark at grid cell
    vec2 markCenter = (cell + 0.5) * uPitch + vec2(0.0, h * uDepth * 0.42 * uPitch.y);
    float markCoverage = coverage(rel - markCenter, level);

    vec3 markCol = mix(uColor, uAccent, clamp(spec * 1.8, 0.0, 1.0));
    vec4 markInk = vec4(markCol * (markCoverage * alpha), markCoverage * alpha);

    vec4 bg = vec4(uBackground.rgb * uBackground.a, uBackground.a);
    fragColor = markInk + bg * (1.0 - markInk.a);
  }
  `;

  function initPatternWaves(container) {
    if (container._wavesInitialized) return;
    container._wavesInitialized = true;

    const ds = container.dataset;
    const presetName = ds.preset || 'silk';
    const base = SURFACE_PRESETS[presetName] || SURFACE_PRESETS.silk;

    const pattern = ds.pattern || base.pattern;
    const wave = ds.wave || base.wave;
    const spacing = ds.spacing ? parseFloat(ds.spacing) : base.spacing;
    const markSize = ds.markSize ? parseFloat(ds.markSize) : base.markSize;
    const depth = ds.depth ? parseFloat(ds.depth) : base.depth;
    const light = ds.light ? parseFloat(ds.light) : base.light;
    const shine = ds.shine ? parseFloat(ds.shine) : base.shine;
    const contrast = ds.contrast ? parseFloat(ds.contrast) : base.contrast;
    const speed = ds.speed ? parseFloat(ds.speed) : base.speed;
    const scale = ds.scale ? parseFloat(ds.scale) : base.scale;
    const direction = ds.direction ? parseFloat(ds.direction) : base.direction;
    const colorStr = ds.color || '#38BDF8';
    const bgStr = ds.backgroundColor || '#0A0C10';
    const fade = ds.fade || 'none';
    const fadeSize = ds.fadeSize ? parseFloat(ds.fadeSize) : 0.4;
    const intro = ds.intro !== 'false';
    const isInteractive = ds.interactive !== 'false';
    const cursorRadius = ds.cursorSize ? parseFloat(ds.cursorSize) : 65;
    const cursorStrength = ds.cursorStrength ? parseFloat(ds.cursorStrength) : 0.8;

    const color = parseColor(colorStr, [0.22, 0.74, 0.97, 1]);
    const background = parseColor(bgStr, [0.04, 0.05, 0.06, 1]);

    const canvas = document.createElement('canvas');
    canvas.style.display = 'block';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    container.appendChild(canvas);

    const gl = canvas.getContext('webgl2', {
      alpha: true,
      premultipliedAlpha: true,
      antialias: false,
      depth: false
    });

    if (!gl) {
      console.warn('WebGL2 not supported');
      return;
    }

    function createShader(type, src) {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        console.error('Shader compilation error:', gl.getShaderInfoLog(s));
      }
      return s;
    }

    const vs = createShader(gl.VERTEX_SHADER, vertexShader);
    const fs = createShader(gl.FRAGMENT_SHADER, mainFragmentShader);
    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);

    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.error('Program link error:', gl.getProgramInfoLog(prog));
      return;
    }

    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const vbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 3, -1, -1, 3]),
      gl.STATIC_DRAW
    );
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    const uLocs = {
      uSize: gl.getUniformLocation(prog, 'uSize'),
      uDpr: gl.getUniformLocation(prog, 'uDpr'),
      uOrigin: gl.getUniformLocation(prog, 'uOrigin'),
      uPitch: gl.getUniformLocation(prog, 'uPitch'),
      uPattern: gl.getUniformLocation(prog, 'uPattern'),
      uWave: gl.getUniformLocation(prog, 'uWave'),
      uTime: gl.getUniformLocation(prog, 'uTime'),
      uUnit: gl.getUniformLocation(prog, 'uUnit'),
      uHeading: gl.getUniformLocation(prog, 'uHeading'),
      uAmp: gl.getUniformLocation(prog, 'uAmp'),
      uDepth: gl.getUniformLocation(prog, 'uDepth'),
      uLight: gl.getUniformLocation(prog, 'uLight'),
      uShine: gl.getUniformLocation(prog, 'uShine'),
      uContrast: gl.getUniformLocation(prog, 'uContrast'),
      uMarkSize: gl.getUniformLocation(prog, 'uMarkSize'),
      uStroke: gl.getUniformLocation(prog, 'uStroke'),
      uColor: gl.getUniformLocation(prog, 'uColor'),
      uAccent: gl.getUniformLocation(prog, 'uAccent'),
      uBackground: gl.getUniformLocation(prog, 'uBackground'),
      uFade: gl.getUniformLocation(prog, 'uFade'),
      uFadeSize: gl.getUniformLocation(prog, 'uFadeSize'),
      uAppear: gl.getUniformLocation(prog, 'uAppear'),
      uPointer: gl.getUniformLocation(prog, 'uPointer'),
      uPointerVel: gl.getUniformLocation(prog, 'uPointerVel'),
      uCursorActive: gl.getUniformLocation(prog, 'uCursorActive'),
      uCursorRadius: gl.getUniformLocation(prog, 'uCursorRadius'),
      uCursorStrength: gl.getUniformLocation(prog, 'uCursorStrength')
    };

    const rippleLocs = [];
    for (let i = 0; i < 4; i++) {
      rippleLocs.push(gl.getUniformLocation(prog, `uRipples[${i}]`));
    }

    let width = 1;
    let height = 1;
    let time = 0;
    let introClock = 0;
    let last = performance.now();

    // Cursor and Shockwaves
    let pointerX = -1000;
    let pointerY = -1000;
    let lastPointerX = -1000;
    let lastPointerY = -1000;
    let pointerVelX = 0;
    let pointerVelY = 0;
    let cursorActive = 0;
    const shockwaves = [
      { x: 0, y: 0, time: -100, strength: 0 },
      { x: 0, y: 0, time: -100, strength: 0 },
      { x: 0, y: 0, time: -100, strength: 0 },
      { x: 0, y: 0, time: -100, strength: 0 }
    ];
    let shockwaveIdx = 0;

    function addShockwave(x, y, strength) {
      shockwaves[shockwaveIdx] = { x, y, time, strength };
      shockwaveIdx = (shockwaveIdx + 1) % 4;
    }

    if (isInteractive) {
      const handlePointer = (e) => {
        const rect = container.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (x >= -100 && x <= rect.width + 100 && y >= -100 && y <= rect.height + 100) {
          const clampedX = clamp(x, 0, rect.width);
          const clampedY = clamp(y, 0, rect.height);
          const webglY = rect.height - clampedY; // convert to bottom-left origin

          if (lastPointerX < 0) {
            lastPointerX = clampedX;
            lastPointerY = webglY;
          }

          pointerVelX = clampedX - lastPointerX;
          pointerVelY = webglY - lastPointerY;
          lastPointerX = clampedX;
          lastPointerY = webglY;

          pointerX = clampedX;
          pointerY = webglY;
          cursorActive = Math.min(1.0, cursorActive + 0.15);

          const speed = Math.hypot(pointerVelX, pointerVelY);
          if (speed > 25) {
            addShockwave(pointerX, pointerY, Math.min(speed / 30.0, 1.5) * cursorStrength);
          }
        } else {
          cursorActive = Math.max(0.0, cursorActive - 0.05);
        }
      };

      const handleDown = (e) => {
        const rect = container.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
          const webglY = rect.height - y;
          pointerX = x;
          pointerY = webglY;
          lastPointerX = x;
          lastPointerY = webglY;
          cursorActive = 1.0;
          addShockwave(pointerX, pointerY, 1.5 * cursorStrength);
        }
      };

      window.addEventListener('pointermove', handlePointer, { passive: true });
      window.addEventListener('pointerdown', handleDown, { passive: true });
    }

    const resize = () => {
      width = Math.max(1, container.clientWidth);
      height = Math.max(1, container.clientHeight);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(container);
    resize();

    const patternIndex = PATTERNS[pattern] ?? 0;
    const waveIndex = WAVES[wave] ?? 0;
    const fadeIndex = FADES[fade] ?? 0;
    const heading = (direction * Math.PI) / 180;
    const lightAngle = ((direction + 180 + clamp(light, -90, 90)) * Math.PI) / 180;

    const accent = color.slice(0, 3).map((c) => c + (1.0 - c) * 0.45);

    const loop = (now) => {
      requestAnimationFrame(loop);
      const dt = Math.min(0.05, Math.max(1 / 240, (now - last) / 1000));
      last = now;

      time += dt * speed;
      introClock = intro ? Math.min(1, introClock + dt / INTRO_SECONDS) : 1;
      const appear = 1 - Math.pow(1 - clamp(introClock / 0.75, 0, 1), 3);
      const rise = clamp((introClock - 0.1) / 0.9, 0, 1);
      const amp = rise * rise * (3 - 2 * rise);

      // Smoothly relax velocity and cursor activity
      pointerVelX *= 0.88;
      pointerVelY *= 0.88;

      const canvasW = canvas.width;
      const canvasH = canvas.height;
      const dpr = canvasW / width;
      const pitchY = Math.max(4, Math.round(clamp(spacing, 4, 120) * dpr));
      const pitchX = patternIndex === 3 ? Math.max(2, Math.round(pitchY / 4)) : pitchY;
      const cols = Math.min(4096, Math.ceil(canvasW / pitchX) + 1);
      const rows = Math.min(4096, Math.ceil(canvasH / pitchY) + 2);
      const origin = [Math.floor((canvasW - cols * pitchX) / 2), Math.floor((canvasH - rows * pitchY) / 2)];

      gl.viewport(0, 0, canvasW, canvasH);
      gl.useProgram(prog);

      gl.uniform2f(uLocs.uSize, width, height);
      gl.uniform1f(uLocs.uDpr, dpr);
      gl.uniform2f(uLocs.uOrigin, origin[0], origin[1]);
      gl.uniform2f(uLocs.uPitch, pitchX, pitchY);
      gl.uniform1i(uLocs.uPattern, patternIndex);
      gl.uniform1i(uLocs.uWave, waveIndex);
      gl.uniform1f(uLocs.uTime, time);
      gl.uniform1f(uLocs.uUnit, WAVE_UNIT * clamp(scale, 0.2, 5));
      gl.uniform2f(uLocs.uHeading, Math.cos(heading), Math.sin(heading));
      gl.uniform1f(uLocs.uAmp, amp);
      gl.uniform1f(uLocs.uDepth, clamp(depth, 0, 1.5));
      gl.uniform3f(uLocs.uLight, Math.cos(lightAngle) * 0.78, Math.sin(lightAngle) * 0.78, 0.62);
      gl.uniform1f(uLocs.uShine, clamp(shine, 0, 2));
      gl.uniform1f(uLocs.uContrast, clamp(contrast, 0.3, 3));
      gl.uniform1f(uLocs.uMarkSize, clamp(markSize, 0.05, 1));
      gl.uniform1f(uLocs.uStroke, patternIndex === 3 ? 0.9 * dpr : Math.max(1.1 * dpr, pitchY * 0.08));

      gl.uniform3f(uLocs.uColor, color[0], color[1], color[2]);
      gl.uniform3f(uLocs.uAccent, accent[0], accent[1], accent[2]);
      gl.uniform4f(uLocs.uBackground, background[0], background[1], background[2], background[3]);

      gl.uniform1i(uLocs.uFade, fadeIndex);
      gl.uniform1f(uLocs.uFadeSize, clamp(fadeSize, 0.05, 1));
      gl.uniform1f(uLocs.uAppear, appear);

      // Pass cursor interactive uniforms
      gl.uniform2f(uLocs.uPointer, pointerX, pointerY);
      gl.uniform2f(uLocs.uPointerVel, pointerVelX, pointerVelY);
      gl.uniform1f(uLocs.uCursorActive, cursorActive);
      gl.uniform1f(uLocs.uCursorRadius, cursorRadius);
      gl.uniform1f(uLocs.uCursorStrength, cursorStrength);

      // Pass shockwaves
      for (let i = 0; i < 4; i++) {
        gl.uniform4f(rippleLocs[i], shockwaves[i].x, shockwaves[i].y, shockwaves[i].time, shockwaves[i].strength);
      }

      gl.bindVertexArray(vao);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    requestAnimationFrame(loop);
  }

  function initAllPatternWaves() {
    const containers = document.querySelectorAll('.pattern-waves');
    containers.forEach(initPatternWaves);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllPatternWaves);
  } else {
    initAllPatternWaves();
  }

  window.initPatternWaves = initAllPatternWaves;
})();
