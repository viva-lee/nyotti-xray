// A WebGL point field that morphs between layouts. Every point keeps a "from" and a "to" state on the GPU;
// a morph uploads the new targets once and the vertex shader interpolates them, each point starting after its own
// delay. The CPU only re-derives the in-flight state when a new morph interrupts an old one.
(function (root) {
  'use strict';

  const VS = `
attribute vec2 aFrom;
attribute vec2 aTo;
attribute vec4 aColFrom;
attribute vec4 aColTo;
attribute vec2 aSize;
attribute float aDelay;
uniform float uT;
uniform float uDur;
uniform vec2 uView;
uniform float uDpr;
uniform float uReveal;
varying vec4 vCol;
varying float vPx;
float ease(float t) { return t < 0.5 ? 4.0 * t * t * t : 1.0 - pow(-2.0 * t + 2.0, 3.0) / 2.0; }
void main() {
  float p = ease(clamp((uT - aDelay) / uDur, 0.0, 1.0));
  vec2 pos = mix(aFrom, aTo, p);
  vec4 col = mix(aColFrom, aColTo, p);
  float size = mix(aSize.x, aSize.y, p);
  if (uReveal > 0.5) {
    // Developing film: invisible until the scan beam passes, then a short flash that settles.
    float since = uT - aDelay;
    float shown = step(0.0, since);
    float flash = shown * exp(-max(since, 0.0) * 4.5);
    col = vec4(mix(col.rgb, vec3(1.0), flash * 0.85), col.a * shown);
    size *= 1.0 + 1.6 * flash;
  }
  vCol = col;
  vPx = max(1.0, size * uDpr);
  // The quad is larger than the dot so the fragment shader can draw a faint phosphor halo around it.
  gl_PointSize = vPx * 2.2;
  vec2 clip = pos / uView * 2.0 - 1.0;
  gl_Position = vec4(clip.x, -clip.y, 0.0, 1.0);
}`;

  const FS = `
precision mediump float;
varying vec4 vCol;
varying float vPx;
uniform float uGlow;
void main() {
  // r = 1 at the dot's edge; the quad reaches r = 2.2.
  float r = length(gl_PointCoord * 2.0 - 1.0) * 2.2;
  float soft = 1.6 / vPx;
  float core = 1.0 - smoothstep(1.0 - soft * 2.0, 1.0, r);
  float halo = pow(max(0.0, 1.0 - r / 2.2), 2.0) * uGlow;
  float a = vCol.a * min(1.0, core + halo);
  if (a <= 0.003) discard;
  vec3 rgb = mix(vCol.rgb, vec3(0.75, 0.88, 1.0), (1.0 - core) * 0.35);
  gl_FragColor = vec4(rgb * a, a);
}`;

  function compile(gl, type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }

  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

  function create(canvas, N) {
    const gl = canvas.getContext('webgl', { antialias: false, alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: false });
    if (!gl) return null;
    const prog = gl.createProgram();
    gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VS));
    gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
    gl.useProgram(prog);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

    // CPU copies of everything on the GPU.
    const from = new Float32Array(N * 2), to = new Float32Array(N * 2);
    const colFrom = new Float32Array(N * 4), colTo = new Float32Array(N * 4);
    const size = new Float32Array(N * 2), delay = new Float32Array(N);
    const attrs = {};
    [['aFrom', from, 2], ['aTo', to, 2], ['aColFrom', colFrom, 4], ['aColTo', colTo, 4], ['aSize', size, 2], ['aDelay', delay, 1]]
      .forEach(([name, arr, n]) => {
        const buf = gl.createBuffer();
        const loc = gl.getAttribLocation(prog, name);
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, arr, gl.DYNAMIC_DRAW);
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, n, gl.FLOAT, false, 0, 0);
        attrs[name] = { buf, arr };
      });
    const U = {};
    ['uT', 'uDur', 'uView', 'uDpr', 'uReveal', 'uGlow'].forEach((n) => { U[n] = gl.getUniformLocation(prog, n); });
    let glow = 0.22;

    let W = 1, H = 1, dpr = 1, t0 = 0, dur = 1, span = 0, reveal = 0, raf = 0, onFrame = null;
    const now = () => performance.now() / 1000;

    function upload() {
      Object.values(attrs).forEach(({ buf, arr }) => {
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, arr);
      });
    }

    // Bake the state at time t into the "from" side, so a new morph starts exactly where the old one is.
    function settle(t) {
      const el = t - t0;
      for (let i = 0; i < N; i++) {
        const p = ease(Math.min(1, Math.max(0, (el - delay[i]) / dur)));
        if (p === 0 && reveal) { colFrom[i * 4 + 3] = 0; }
        from[i * 2] += (to[i * 2] - from[i * 2]) * p;
        from[i * 2 + 1] += (to[i * 2 + 1] - from[i * 2 + 1]) * p;
        for (let k = 0; k < 4; k++) colFrom[i * 4 + k] += (colTo[i * 4 + k] - colFrom[i * 4 + k]) * p;
        size[i * 2] += (size[i * 2 + 1] - size[i * 2]) * p;
      }
    }

    function draw() {
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform1f(U.uT, now() - t0);
      gl.uniform1f(U.uDur, dur);
      gl.uniform2f(U.uView, W, H);
      gl.uniform1f(U.uDpr, dpr);
      gl.uniform1f(U.uReveal, reveal);
      gl.uniform1f(U.uGlow, glow);
      gl.drawArrays(gl.POINTS, 0, N);
    }

    function loop() {
      draw();
      const el = now() - t0;
      if (onFrame) onFrame(Math.min(1, el / (dur + span)), el);
      if (el < dur + span + 0.05) raf = requestAnimationFrame(loop);
      else raf = 0;
    }

    return {
      N,
      resize(w, h, ratio) {
        W = w; H = h; dpr = ratio;
        canvas.width = Math.round(w * ratio);
        canvas.height = Math.round(h * ratio);
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
        draw();
      },
      // target: {x, y, s, rgba} with x/y/s Float32Array(N) and rgba Float32Array(N*4).
      // opts: {duration, delays: Float32Array(N) | null, reveal: bool, onFrame(progress, elapsed)}
      morph(target, opts = {}) {
        const t = now();
        settle(t);
        if (opts.reveal) {
          // Reveal keeps the points in place: from = to, and the shader handles the flash.
          for (let i = 0; i < N; i++) {
            from[i * 2] = target.x[i]; from[i * 2 + 1] = target.y[i];
            size[i * 2] = target.s[i];
            for (let k = 0; k < 4; k++) colFrom[i * 4 + k] = target.rgba[i * 4 + k];
          }
        }
        for (let i = 0; i < N; i++) {
          to[i * 2] = target.x[i]; to[i * 2 + 1] = target.y[i];
          size[i * 2 + 1] = target.s[i];
          for (let k = 0; k < 4; k++) colTo[i * 4 + k] = target.rgba[i * 4 + k];
          delay[i] = opts.delays ? opts.delays[i] : 0;
        }
        span = 0;
        for (let i = 0; i < N; i++) if (delay[i] > span) span = delay[i];
        dur = Math.max(0.001, opts.duration ?? 1.1);
        reveal = opts.reveal ? 1 : 0;
        if (opts.glow != null) glow = opts.glow;
        onFrame = opts.onFrame || null;
        upload();
        t0 = t;
        if (!raf) raf = requestAnimationFrame(loop);
      },
      redraw: draw,
      busy: () => raf !== 0,
    };
  }

  root.XAtlasGL = { create };
})(window);
