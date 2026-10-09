/**
 * PatternWaves Component (React Bits Vanilla WebGL2 Engine)
 * Dynamic Procedural Fabric & Interactive Cursor Ripple Wave Surface Renderer
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
      shine: 0.8,
      contrast: 1.2,
      speed: 0.35,
      scale: 1,
      direction: 20
    },
    ocean: {
      pattern: 'dot',
      wave: 'swell',
      spacing: 10,
      markSize: 0.9,
      depth: 0.42,
      light: 0,
      shine: 1,
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
      shine: 0.6,
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
      markSize: 0.8,
      depth: 0.95,
      light: 0,
      shine: 1,
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
  const INTRO_SECONDS = 2;
  const RIPPLE_CELL = 8;

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

  const passVertex = `#version 300 es
  in vec2 position;
  void main() {
    gl_Position = vec4(position, 0.0, 1.0);
  }
  `;

  // Ripple simulation fragment shader (Wave Equation Ping-Pong)
  const rippleFragment = `#version 300 es
  precision highp float;
  precision highp int;

  uniform sampler2D tRipple;
  uniform vec2 uResolution;
  uniform vec2 uPointer;
  uniform float uImpulse;
  uniform float uRadius;
  uniform float uDamping;

  out vec4 fragColor;

  void main() {
    vec2 uv = gl_FragCoord.xy / uResolution;
    vec2 step = 1.0 / uResolution;

    float p10 = texture(tRipple, uv + vec2(step.x, 0.0)).r;
    float p_10 = texture(tRipple, uv - vec2(step.x, 0.0)).r;
    float p01 = texture(tRipple, uv + vec2(0.0, step.y)).r;
    float p0_1 = texture(tRipple, uv - vec2(0.0, step.y)).r;

    vec4 cur = texture(tRipple, uv);
    float next = ((p10 + p_10 + p01 + p0_1) * 0.5 - cur.g) * uDamping;

    if (uImpulse > 0.0001) {
      vec2 diff = (uv - uPointer) * uResolution;
      float dist = length(diff);
      if (dist < uRadius) {
        float impact = smoothstep(uRadius, 0.0, dist) * uImpulse;
        next += impact;
      }
    }

    fragColor = vec4(next, cur.r, 0.0, 1.0);
  }
  `;

  // Procedural 3D surface generator with wave dynamics + cursor ripple injection
  const fieldFragment = `#version 300 es
  precision highp float;
  precision highp int;
  uniform vec2 uSize;
  uniform float uDpr;
  uniform vec2 uOrigin;
  uniform vec2 uPitch;
  uniform int uWave;
  uniform float uTime;
  uniform float uUnit;
  uniform vec2 uHeading;
  uniform float uAmp;
  uniform float uDepth;
  uniform vec3 uLight;
  uniform float uShine;
  uniform float uContrast;
  uniform float uInk;
  uniform float uOpacity;
  uniform int uFade;
  uniform float uFadeSize;
  uniform float uAppear;
  uniform sampler2D tRipple;
  uniform float uRipple;
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
    if (uRipple > 0.0001) {
      vec2 ripUv = clamp(css / uSize, 0.0, 1.0);
      float rip = texture(tRipple, ripUv).r;
      h += rip * uRipple;
    }
    return h;
  }

  void main() {
    vec2 cell = floor(gl_FragCoord.xy);
    vec2 center = uOrigin + (cell + 0.5) * uPitch;
    vec2 css = center / uDpr;
    vec2 uv = css / uSize;
    float e = max(uPitch.y / uDpr, 4.0);
    float h = heightAt(css);
    float hx = (heightAt(css + vec2(e, 0.0)) - heightAt(css - vec2(e, 0.0))) / (2.0 * e);
    float hy = (heightAt(css + vec2(0.0, e)) - heightAt(css - vec2(0.0, e))) / (2.0 * e);
    vec2 grad = vec2(hx, hy) * uUnit * uDepth * 0.4;
    vec3 n = normalize(vec3(-grad, 1.0));

    float diffuse = clamp(dot(n, uLight), 0.0, 1.0);
    vec3 halfway = normalize(uLight + vec3(0.0, 0.0, 1.0));
    float spec = pow(clamp(dot(n, halfway), 0.0, 1.0), 160.0) * uShine * 1.15;
    float hollow = 0.7 + 0.3 * clamp(h * 0.5 + 0.5, 0.0, 1.0);
    float tone = clamp(diffuse * hollow * 0.78 + spec, 0.0, 1.0);
    tone = clamp((tone - 0.42) * uContrast + 0.42, 0.0, 1.0);

    float level = uInk > 0.5 ? pow(clamp(1.0 - tone / 0.46, 0.0, 1.0), 2.4) * 0.72 : pow(tone, 2.2);
    float emphasis = uInk > 0.5 ? smoothstep(0.55, 0.95, level) : clamp(spec * 1.6, 0.0, 1.0);

    float fade = 1.0;
    vec2 c = uv * 2.0 - 1.0;
    if (uFade == 1) {
      fade = 1.0 - smoothstep(1.0 - uFadeSize, 1.18, length(c));
    } else if (uFade == 2) {
      fade = mix(0.05, 1.0, smoothstep(0.08, 0.08 + uFadeSize, length(c * vec2(1.0, 1.35))));
    } else if (uFade == 3) {
      fade = smoothstep(0.0, uFadeSize, uv.y);
    } else if (uFade == 4) {
      fade = smoothstep(0.0, uFadeSize, 1.0 - uv.y);
    }

    float reach = length(css - 0.5 * uSize) / max(0.5 * length(uSize), 1.0);
    float appear = smoothstep(reach - 0.05, reach + 0.3, uAppear * 1.35);

    float alpha = uOpacity * fade * appear * (0.22 + 0.78 * level);
    float lift = clamp(h * uDepth * 0.42, -0.48, 0.48);
    fragColor = vec4(level, alpha, emphasis, lift + 0.5);
  }
  `;

  // Pattern Mark Rendering
  const markFragment = `#version 300 es
  precision highp float;
  precision highp int;
  uniform sampler2D tField;
  uniform vec2 uOrigin;
  uniform vec2 uPitch;
  uniform vec2 uGrid;
  uniform int uPattern;
  uniform float uMarkSize;
  uniform float uStroke;
  uniform vec3 uColor;
  uniform vec3 uAccent;
  uniform vec4 uBackground;
  out vec4 fragColor;

  float box(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
  }

  float coverage(vec2 local, float level) {
    float span = uPitch.y * uMarkSize;
    float area = max(sqrt(level), 0.14);
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

  vec4 lineInk(vec2 rel) {
    float fx = rel.x / uPitch.x - 0.5;
    float c0 = clamp(floor(fx), 0.0, uGrid.x - 1.0);
    float c1 = min(c0 + 1.0, uGrid.x - 1.0);
    float t = clamp(fx - c0, 0.0, 1.0);
    float row = floor(rel.y / uPitch.y);
    vec4 ink = vec4(0.0);
    for (int k = -1; k <= 1; k++) {
      float cy = row + float(k);
      if (cy < 0.0 || cy >= uGrid.y) continue;
      vec4 a = texelFetch(tField, ivec2(int(c0), int(cy)), 0);
      vec4 b = texelFetch(tField, ivec2(int(c1), int(cy)), 0);
      vec4 f = mix(a, b, t);
      if (f.g < 0.002) continue;
      float y = (cy + 0.5 + f.a - 0.5) * uPitch.y;
      float slope = (b.a - a.a) * uPitch.y / uPitch.x;
      float thickness = max(uStroke, uPitch.y * uMarkSize * f.r);
      float d = abs(rel.y - y) / sqrt(1.0 + slope * slope) - 0.5 * thickness;
      float alpha = clamp(0.5 - d, 0.0, 1.0) * f.g;
      if (alpha > ink.a) ink = vec4(mix(uColor, uAccent, f.b) * alpha, alpha);
    }
    return ink;
  }

  void main() {
    vec2 rel = gl_FragCoord.xy - uOrigin;
    vec4 background = vec4(uBackground.rgb * uBackground.a, uBackground.a);
    vec4 ink = vec4(0.0);
    if (uPattern == 3) {
      ink = lineInk(rel);
    } else {
      float cx = floor(rel.x / uPitch.x);
      float row = floor(rel.y / uPitch.y);
      if (cx >= 0.0 && cx < uGrid.x) {
        for (int k = -1; k <= 1; k++) {
          float cy = row + float(k);
          if (cy < 0.0 || cy >= uGrid.y) continue;
          vec4 f = texelFetch(tField, ivec2(int(cx), int(cy)), 0);
          if (f.g < 0.002) continue;
          vec2 center = (vec2(cx, cy) + 0.5) * uPitch + vec2(0.0, (f.a - 0.5) * uPitch.y);
          float alpha = coverage(rel - center, f.r) * f.g;
          if (alpha > ink.a) ink = vec4(mix(uColor, uAccent, f.b) * alpha, alpha);
        }
      }
    }
    fragColor = ink + background * (1.0 - ink.a);
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
    const colorStr = ds.color || '#2687E8';
    const bgStr = ds.backgroundColor || '#0A0C10';
    const opacity = ds.opacity ? parseFloat(ds.opacity) : 1;
    const fade = ds.fade || 'bottom';
    const fadeSize = ds.fadeSize ? parseFloat(ds.fadeSize) : 0.6;
    const intro = ds.intro !== 'false';
    const isInteractive = ds.interactive !== 'false';
    const cursorSize = ds.cursorSize ? parseFloat(ds.cursorSize) : 48;
    const cursorStrength = ds.cursorStrength ? parseFloat(ds.cursorStrength) : 0.65;

    const color = parseColor(colorStr, [0.15, 0.53, 0.91, 1]);
    const background = parseColor(bgStr, [0.04, 0.05, 0.06, 1]);

    const canvas = document.createElement('canvas');
    canvas.style.display = 'block';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    container.appendChild(canvas);

    const gl = canvas.getContext('webgl2', {
      alpha: true,
      premultipliedAlpha: true,
      antialias: false,
      depth: false
    });

    if (!gl) {
      console.warn('WebGL2 not supported for PatternWaves');
      return;
    }

    const extFloat = gl.getExtension('EXT_color_buffer_float');

    // Helper to create shader program
    function createProg(vsSrc, fsSrc) {
      const vs = gl.createShader(gl.VERTEX_SHADER);
      gl.shaderSource(vs, vsSrc);
      gl.compileShader(vs);
      if (!gl.getShaderParameter(vs, gl.COMPILE_STATUS)) {
        console.error('VS Error:', gl.getShaderInfoLog(vs));
      }

      const fs = gl.createShader(gl.FRAGMENT_SHADER);
      gl.shaderSource(fs, fsSrc);
      gl.compileShader(fs);
      if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {
        console.error('FS Error:', gl.getShaderInfoLog(fs));
      }

      const prog = gl.createProgram();
      gl.attachShader(prog, vs);
      gl.attachShader(prog, fs);
      gl.linkProgram(prog);
      return prog;
    }

    const rippleProg = createProg(passVertex, rippleFragment);
    const fieldProg = createProg(passVertex, fieldFragment);
    const markProg = createProg(passVertex, markFragment);

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
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    // Ripple Ping-Pong Textures & FBOs
    let ripWidth = 0;
    let ripHeight = 0;
    const ripTexA = gl.createTexture();
    const ripTexB = gl.createTexture();
    const ripFboA = gl.createFramebuffer();
    const ripFboB = gl.createFramebuffer();
    const ripTexs = [ripTexA, ripTexB];
    const ripFbos = [ripFboA, ripFboB];
    let ripReadIdx = 0;
    let ripWriteIdx = 1;

    function setupRippleTextures(w, h) {
      if (ripWidth === w && ripHeight === h) return;
      ripWidth = w;
      ripHeight = h;

      for (let i = 0; i < 2; i++) {
        gl.bindTexture(gl.TEXTURE_2D, ripTexs[i]);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

        if (extFloat) {
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, w, h, 0, gl.RGBA, gl.HALF_FLOAT, null);
        } else {
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
        }

        gl.bindFramebuffer(gl.FRAMEBUFFER, ripFbos[i]);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, ripTexs[i], 0);
        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
      }
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    }

    // Ripple uniforms
    const uRippleUni = {
      tRipple: gl.getUniformLocation(rippleProg, 'tRipple'),
      uResolution: gl.getUniformLocation(rippleProg, 'uResolution'),
      uPointer: gl.getUniformLocation(rippleProg, 'uPointer'),
      uImpulse: gl.getUniformLocation(rippleProg, 'uImpulse'),
      uRadius: gl.getUniformLocation(rippleProg, 'uRadius'),
      uDamping: gl.getUniformLocation(rippleProg, 'uDamping')
    };

    // Field Target FBO
    let fboWidth = 1;
    let fboHeight = 1;
    const fieldTex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, fieldTex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, fieldTex, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    // Field uniforms
    const uField = {
      uSize: gl.getUniformLocation(fieldProg, 'uSize'),
      uDpr: gl.getUniformLocation(fieldProg, 'uDpr'),
      uOrigin: gl.getUniformLocation(fieldProg, 'uOrigin'),
      uPitch: gl.getUniformLocation(fieldProg, 'uPitch'),
      uWave: gl.getUniformLocation(fieldProg, 'uWave'),
      uTime: gl.getUniformLocation(fieldProg, 'uTime'),
      uUnit: gl.getUniformLocation(fieldProg, 'uUnit'),
      uHeading: gl.getUniformLocation(fieldProg, 'uHeading'),
      uAmp: gl.getUniformLocation(fieldProg, 'uAmp'),
      uDepth: gl.getUniformLocation(fieldProg, 'uDepth'),
      uLight: gl.getUniformLocation(fieldProg, 'uLight'),
      uShine: gl.getUniformLocation(fieldProg, 'uShine'),
      uContrast: gl.getUniformLocation(fieldProg, 'uContrast'),
      uInk: gl.getUniformLocation(fieldProg, 'uInk'),
      uOpacity: gl.getUniformLocation(fieldProg, 'uOpacity'),
      uFade: gl.getUniformLocation(fieldProg, 'uFade'),
      uFadeSize: gl.getUniformLocation(fieldProg, 'uFadeSize'),
      uAppear: gl.getUniformLocation(fieldProg, 'uAppear'),
      tRipple: gl.getUniformLocation(fieldProg, 'tRipple'),
      uRipple: gl.getUniformLocation(fieldProg, 'uRipple')
    };

    // Mark uniforms
    const uMark = {
      tField: gl.getUniformLocation(markProg, 'tField'),
      uOrigin: gl.getUniformLocation(markProg, 'uOrigin'),
      uPitch: gl.getUniformLocation(markProg, 'uPitch'),
      uGrid: gl.getUniformLocation(markProg, 'uGrid'),
      uPattern: gl.getUniformLocation(markProg, 'uPattern'),
      uMarkSize: gl.getUniformLocation(markProg, 'uMarkSize'),
      uStroke: gl.getUniformLocation(markProg, 'uStroke'),
      uColor: gl.getUniformLocation(markProg, 'uColor'),
      uAccent: gl.getUniformLocation(markProg, 'uAccent'),
      uBackground: gl.getUniformLocation(markProg, 'uBackground')
    };

    let width = 1;
    let height = 1;
    let time = 0;
    let introClock = 0;
    let last = performance.now();

    // Cursor tracking state
    let pointerX = -1000;
    let pointerY = -1000;
    let lastPointerX = -1000;
    let lastPointerY = -1000;
    let isPointerInside = false;
    let impulse = 0;
    let isMouseDown = false;

    if (isInteractive) {
      const onPointerMove = (e) => {
        const rect = container.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (x >= -60 && x <= rect.width + 60 && y >= -60 && y <= rect.height + 60) {
          isPointerInside = true;
          const clampedX = clamp(x, 0, rect.width);
          const clampedY = clamp(y, 0, rect.height);

          if (lastPointerX < 0) {
            lastPointerX = clampedX;
            lastPointerY = clampedY;
          }

          const dist = Math.hypot(clampedX - lastPointerX, clampedY - lastPointerY);
          lastPointerX = clampedX;
          lastPointerY = clampedY;
          pointerX = clampedX;
          pointerY = clampedY;

          impulse += Math.min(dist / 6.0, 1.8) * 0.55 * cursorStrength;
          if (isMouseDown) impulse += 0.45 * cursorStrength;
        } else {
          isPointerInside = false;
        }
      };

      const onPointerDown = (e) => {
        isMouseDown = true;
        const rect = container.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
          pointerX = x;
          pointerY = y;
          lastPointerX = x;
          lastPointerY = y;
          impulse += 1.4 * cursorStrength;
        }
      };

      const onPointerUp = () => {
        isMouseDown = false;
      };

      window.addEventListener('pointermove', onPointerMove, { passive: true });
      window.addEventListener('pointerdown', onPointerDown, { passive: true });
      window.addEventListener('pointerup', onPointerUp, { passive: true });
    }

    const resize = () => {
      width = Math.max(1, container.clientWidth);
      height = Math.max(1, container.clientHeight);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);

      const rw = Math.max(16, Math.floor(width / RIPPLE_CELL));
      const rh = Math.max(16, Math.floor(height / RIPPLE_CELL));
      setupRippleTextures(rw, rh);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(container);
    resize();

    const patternIndex = PATTERNS[pattern] ?? 0;
    const waveIndex = WAVES[wave] ?? 0;
    const fadeIndex = FADES[fade] ?? 3;
    const heading = (direction * Math.PI) / 180;
    const lightAngle = ((direction + 180 + clamp(light, -90, 90)) * Math.PI) / 180;
    const ink = background[3] > 0.02 ? luminance(color) < luminance(background) : luminance(color) < 0.5;

    const loop = (now) => {
      requestAnimationFrame(loop);
      const dt = Math.min(0.05, Math.max(1 / 240, (now - last) / 1000));
      last = now;

      time += dt * speed;
      introClock = intro ? Math.min(1, introClock + dt / INTRO_SECONDS) : 1;
      const appear = 1 - Math.pow(1 - clamp(introClock / 0.75, 0, 1), 3);
      const rise = clamp((introClock - 0.1) / 0.9, 0, 1);
      const amp = rise * rise * (3 - 2 * rise);

      // Add ambient gentle movement under pointer if resting
      if (isPointerInside) {
        impulse += 0.025 * cursorStrength;
      }

      // PASS 0: Interactive Ripple Simulation Pass (Ping-Pong FBO)
      let currentRippleTex = null;
      if (isInteractive && ripWidth > 0 && ripHeight > 0) {
        gl.bindFramebuffer(gl.FRAMEBUFFER, ripFbos[ripWriteIdx]);
        gl.viewport(0, 0, ripWidth, ripHeight);
        gl.useProgram(rippleProg);

        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, ripTexs[ripReadIdx]);
        gl.uniform1i(uRippleUni.tRipple, 0);

        gl.uniform2f(uRippleUni.uResolution, ripWidth, ripHeight);
        
        const pxUv = clamp(pointerX / width, 0, 1);
        const pyUv = clamp((height - pointerY) / height, 0, 1);
        gl.uniform2f(uRippleUni.uPointer, pxUv, pyUv);

        gl.uniform1f(uRippleUni.uImpulse, impulse);
        gl.uniform1f(uRippleUni.uRadius, Math.max(3.0, cursorSize / RIPPLE_CELL));
        gl.uniform1f(uRippleUni.uDamping, 0.985);

        gl.bindVertexArray(vao);
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        impulse = Math.max(0, impulse * 0.65);

        currentRippleTex = ripTexs[ripWriteIdx];

        // Swap ping-pong indices
        const temp = ripReadIdx;
        ripReadIdx = ripWriteIdx;
        ripWriteIdx = temp;
      }

      const canvasW = canvas.width;
      const canvasH = canvas.height;
      const dpr = canvasW / width;
      const pitchY = Math.max(4, Math.round(clamp(spacing, 4, 120) * dpr));
      const pitchX = patternIndex === 3 ? Math.max(2, Math.round(pitchY / 4)) : pitchY;
      const cols = Math.min(4096, Math.ceil(canvasW / pitchX) + 1);
      const rows = Math.min(4096, Math.ceil(canvasH / pitchY) + 2);
      const origin = [Math.floor((canvasW - cols * pitchX) / 2), Math.floor((canvasH - rows * pitchY) / 2)];

      if (fboWidth !== cols || fboHeight !== rows) {
        fboWidth = cols;
        fboHeight = rows;
        gl.bindTexture(gl.TEXTURE_2D, fieldTex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, cols, rows, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      }

      // PASS 1: Render 3D Surface Field to FBO
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.viewport(0, 0, cols, rows);
      gl.useProgram(fieldProg);

      gl.uniform2f(uField.uSize, width, height);
      gl.uniform1f(uField.uDpr, dpr);
      gl.uniform2f(uField.uOrigin, origin[0], origin[1]);
      gl.uniform2f(uField.uPitch, pitchX, pitchY);
      gl.uniform1i(uField.uWave, waveIndex);
      gl.uniform1f(uField.uTime, time);
      gl.uniform1f(uField.uUnit, WAVE_UNIT * clamp(scale, 0.2, 5));
      gl.uniform2f(uField.uHeading, Math.cos(heading), Math.sin(heading));
      gl.uniform1f(uField.uAmp, amp);
      gl.uniform1f(uField.uDepth, clamp(depth, 0, 1.5));
      gl.uniform3f(uField.uLight, Math.cos(lightAngle) * 0.78, Math.sin(lightAngle) * 0.78, 0.62);
      gl.uniform1f(uField.uShine, clamp(shine, 0, 2));
      gl.uniform1f(uField.uContrast, clamp(contrast, 0.3, 3));
      gl.uniform1f(uField.uInk, ink ? 1 : 0);
      gl.uniform1f(uField.uOpacity, clamp(opacity, 0, 1));
      gl.uniform1i(uField.uFade, fadeIndex);
      gl.uniform1f(uField.uFadeSize, clamp(fadeSize, 0.05, 1));
      gl.uniform1f(uField.uAppear, appear);

      if (currentRippleTex) {
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, currentRippleTex);
        gl.uniform1i(uField.tRipple, 1);
        gl.uniform1f(uField.uRipple, 0.48 * cursorStrength);
      } else {
        gl.uniform1f(uField.uRipple, 0.0);
      }

      gl.bindVertexArray(vao);
      gl.drawArrays(gl.TRIANGLES, 0, 3);

      // PASS 2: Render Pattern Marks to Screen Canvas
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.viewport(0, 0, canvasW, canvasH);
      gl.useProgram(markProg);

      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, fieldTex);
      gl.uniform1i(uMark.tField, 0);

      gl.uniform2f(uMark.uOrigin, origin[0], origin[1]);
      gl.uniform2f(uMark.uPitch, pitchX, pitchY);
      gl.uniform2f(uMark.uGrid, cols, rows);
      gl.uniform1i(uMark.uPattern, patternIndex);
      gl.uniform1f(uMark.uMarkSize, clamp(markSize, 0.05, 1));
      gl.uniform1f(uMark.uStroke, patternIndex === 3 ? 0.9 * dpr : Math.max(1.1 * dpr, pitchY * 0.08));

      const tint = ink ? 0 : 1;
      const blend = ink ? 0.35 : 0.55;
      const accent = color.slice(0, 3).map((c) => c + (tint - c) * blend);

      gl.uniform3f(uMark.uColor, color[0], color[1], color[2]);
      gl.uniform3f(uMark.uAccent, accent[0], accent[1], accent[2]);
      gl.uniform4f(uMark.uBackground, background[0], background[1], background[2], background[3]);

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

