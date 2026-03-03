/**
 * Gold dust particles — ambient background decoration for Parody Critics.
 * Tiny diffuse glows drifting downward. Relaxing, unobtrusive.
 */
(function () {
  const canvas = document.getElementById('gold-particles');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  // Gold / bronze palette — [r, g, b] tuples
  const COLORS = [
    [201, 162, 39], // #c9a227 — primary gold
    [212, 174, 60], // lighter gold
    [232, 197, 71], // warm highlight
    [160, 105, 42], // #a0692a — bronze
    [180, 140, 35], // muted gold
  ];

  let W, H, particles, lastTime;

  function rand(a, b) {
    return a + Math.random() * (b - a);
  }

  function newParticle(fromTop) {
    const color = COLORS[Math.floor(Math.random() * COLORS.length)];
    return {
      x: rand(0, W),
      y: fromTop ? rand(-60, -4) : rand(0, H),
      r: rand(1.2, 3.2), // soft glow radius (small = subtle)
      opacity: rand(0.08, 0.28),
      speed: rand(0.3, 0.75), // px per 60fps-normalised frame
      drift: rand(-0.18, 0.18), // horizontal bias
      phase: rand(0, Math.PI * 2), // sine wave offset
      phaseSpeed: rand(0.005, 0.014), // sine oscillation speed
      color,
    };
  }

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function init() {
    resize();
    // ~55 particles — enough to feel lush, few enough to stay invisible
    const count = Math.min(55, Math.floor((W * H) / 22000));
    particles = Array.from({ length: count }, () => newParticle(false));
    lastTime = null;
  }

  function drawParticle(p) {
    const [r, g, b] = p.color;
    // Radial gradient gives a diffuse, glowing-dust look (no hard edges)
    const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 3);
    grad.addColorStop(0, `rgba(${r},${g},${b},${p.opacity})`);
    grad.addColorStop(0.45, `rgba(${r},${g},${b},${p.opacity * 0.35})`);
    grad.addColorStop(1, `rgba(${r},${g},${b},0)`);

    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r * 3, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();
  }

  function tick(timestamp) {
    if (!lastTime) lastTime = timestamp;
    // Normalise delta to 60 fps so speed is monitor-rate-independent
    const dt = Math.min((timestamp - lastTime) / 16.67, 3);
    lastTime = timestamp;

    ctx.clearRect(0, 0, W, H);

    for (const p of particles) {
      p.phase += p.phaseSpeed * dt;
      p.x += (Math.sin(p.phase) * 0.35 + p.drift * 0.4) * dt;
      p.y += p.speed * dt;

      // Wrap: recycle from top when particle leaves bottom
      if (p.y > H + 10) {
        Object.assign(p, newParticle(true));
      }
      // Keep within horizontal bounds with soft wrap
      if (p.x < -10) p.x = W + 5;
      if (p.x > W + 10) p.x = -5;

      drawParticle(p);
    }

    requestAnimationFrame(tick);
  }

  window.addEventListener('resize', () => {
    resize();
    for (const p of particles) {
      if (p.x > W) p.x = Math.random() * W;
    }
  });

  // Start after DOM is ready — canvas is already in the document at this point
  init();
  requestAnimationFrame(tick);
})();
