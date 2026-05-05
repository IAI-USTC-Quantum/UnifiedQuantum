/* ───────────────────────────────────────────
   UnifiedQuantum Landing — Script
   Particle animation, copy, scroll reveal, mobile nav
   ─────────────────────────────────────────── */

(function () {
  'use strict';

  /* ─── Quantum Particle Canvas ─── */
  const canvas = document.getElementById('particles');
  const ctx = canvas.getContext('2d');
  let particles = [];
  let width, height;
  let animId;

  const isMobile = window.innerWidth < 640;
  const PARTICLE_COUNT = isMobile ? 40 : 90;
  const MAX_DIST = isMobile ? 100 : 140;
  const SPEED = 0.15;

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  }

  function createParticle() {
    const colors = [
      'rgba(124, 58, 237,',  // accent purple
      'rgba(6, 182, 212,',   // cyan
      'rgba(167, 139, 250,', // light purple
    ];
    return {
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * SPEED,
      vy: (Math.random() - 0.5) * SPEED,
      r: Math.random() * 1.5 + 0.5,
      color: colors[Math.floor(Math.random() * colors.length)],
      alpha: Math.random() * 0.5 + 0.2,
    };
  }

  function initParticles() {
    particles = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push(createParticle());
    }
  }

  function drawParticles() {
    ctx.clearRect(0, 0, width, height);

    // Draw connecting lines
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < MAX_DIST) {
          const opacity = (1 - dist / MAX_DIST) * 0.12;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(124, 58, 237, ${opacity})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }

    // Draw particles
    for (const p of particles) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `${p.color} ${p.alpha})`;
      ctx.fill();
    }
  }

  function updateParticles() {
    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;

      // Wrap around edges with margin
      if (p.x < -10) p.x = width + 10;
      if (p.x > width + 10) p.x = -10;
      if (p.y < -10) p.y = height + 10;
      if (p.y > height + 10) p.y = -10;
    }
  }

  function animate() {
    updateParticles();
    drawParticles();
    animId = requestAnimationFrame(animate);
  }

  resize();
  initParticles();
  animate();

  let resizeTimeout;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function () {
      resize();
      initParticles();
    }, 200);
  });

  /* ─── Copy to Clipboard ─── */
  function copyText(text, btn) {
    navigator.clipboard.writeText(text).then(function () {
      btn.classList.add('copied');
      const originalHTML = btn.innerHTML;
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 8l3 3 7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      setTimeout(function () {
        btn.classList.remove('copied');
        btn.innerHTML = originalHTML;
      }, 1500);
    });
  }

  document.querySelectorAll('.copy-btn, .copy-btn-sm').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const cmd = this.getAttribute('data-cmd');
      if (cmd) copyText(cmd, this);
    });
  });

  /* ─── Skills Tab Switching ─── */
  var skillTabs = document.querySelectorAll('.skills-tab');
  skillTabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      skillTabs.forEach(function (t) { t.classList.remove('active'); });
      this.classList.add('active');
      var target = this.getAttribute('data-tab');
      var claudeTab = document.getElementById('tab-claude');
      var codexTab = document.getElementById('tab-codex');
      if (claudeTab) claudeTab.style.display = target === 'claude' ? 'flex' : 'none';
      if (codexTab) codexTab.style.display = target === 'codex' ? 'flex' : 'none';
    });
  });

  /* ─── Scroll Reveal ─── */
  const reveals = document.querySelectorAll('.reveal');

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    reveals.forEach(function (el) {
      observer.observe(el);
    });
  } else {
    reveals.forEach(function (el) {
      el.classList.add('visible');
    });
  }

  /* ─── Mobile Nav ─── */
  const hamburger = document.getElementById('hamburger');
  const mobileMenu = document.getElementById('mobileMenu');

  hamburger.addEventListener('click', function () {
    mobileMenu.classList.toggle('open');
    const spans = hamburger.querySelectorAll('span');
    if (mobileMenu.classList.contains('open')) {
      spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
      spans[1].style.opacity = '0';
      spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
      document.body.style.overflow = 'hidden';
    } else {
      spans[0].style.transform = '';
      spans[1].style.opacity = '';
      spans[2].style.transform = '';
      document.body.style.overflow = '';
    }
  });

  // Close mobile menu on link click
  mobileMenu.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', function () {
      mobileMenu.classList.remove('open');
      const spans = hamburger.querySelectorAll('span');
      spans[0].style.transform = '';
      spans[1].style.opacity = '';
      spans[2].style.transform = '';
      document.body.style.overflow = '';
    });
  });

})();
