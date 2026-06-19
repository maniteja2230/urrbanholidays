/**
 * Urban Holidays – Main JavaScript
 * Navbar scroll effects, animations, utilities
 */

document.addEventListener('DOMContentLoaded', function () {

  // ─── Navbar Scroll Effect ────────────────────────────────────────────
  const navbar = document.getElementById('mainNavbar');
  if (navbar) {
    const onScroll = () => {
      if (window.scrollY > 60) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll(); // Initial check
  }

  // ─── Counter Animations ──────────────────────────────────────────────
  const counterElements = document.querySelectorAll('[data-counter]');
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const target = parseInt(el.getAttribute('data-counter'), 10);
        let count = 0;
        const duration = 2000;
        const step = target / (duration / 16);
        const update = () => {
          count = Math.min(count + step, target);
          el.textContent = Math.floor(count).toLocaleString('en-IN');
          if (count < target) requestAnimationFrame(update);
        };
        requestAnimationFrame(update);
        counterObserver.unobserve(el);
      }
    });
  }, { threshold: 0.5 });
  counterElements.forEach(el => counterObserver.observe(el));

  // ─── Package Card Hover Enhancement ──────────────────────────────────
  document.querySelectorAll('.package-card').forEach(card => {
    card.addEventListener('mouseenter', function () {
      this.style.zIndex = '10';
    });
    card.addEventListener('mouseleave', function () {
      this.style.zIndex = '';
    });
  });

  // ─── Auto-close mobile navbar on link click ───────────────────────────
  const navLinks = document.querySelectorAll('.navbar-collapse .nav-link, .navbar-collapse .btn');
  const navCollapse = document.getElementById('navbarMain');
  if (navCollapse) {
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        const bsCollapse = bootstrap.Collapse.getInstance(navCollapse);
        if (bsCollapse) bsCollapse.hide();
      });
    });
  }

  // ─── Smooth Scroll for Anchor Links ──────────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ─── Form Validation Enhancement ─────────────────────────────────────
  const forms = document.querySelectorAll('form[novalidate]');
  forms.forEach(form => {
    form.addEventListener('submit', function (e) {
      const requiredFields = form.querySelectorAll('[required]');
      let valid = true;
      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          field.classList.add('is-invalid');
          valid = false;
        } else {
          field.classList.remove('is-invalid');
          field.classList.add('is-valid');
        }
      });
    });
  });

  // ─── Copy to Clipboard Utility ────────────────────────────────────────
  window.copyToClipboard = function (text, label) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(`${label || 'Text'} copied!`, 'success');
    }).catch(() => {
      showToast('Copy failed. Please try manually.', 'error');
    });
  };

  // ─── Toast Notification ───────────────────────────────────────────────
  window.showToast = function (message, type = 'success') {
    const toastId = 'toast_' + Date.now();
    const bgClass = type === 'success' ? 'text-bg-success' : type === 'error' ? 'text-bg-danger' : 'text-bg-info';
    const toast = document.createElement('div');
    toast.innerHTML = `
      <div id="${toastId}" class="toast align-items-center ${bgClass} border-0 shadow-lg" role="alert" style="min-width:280px;">
        <div class="d-flex">
          <div class="toast-body fw-semibold">${message}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      </div>
    `;
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'position-fixed bottom-0 end-0 p-3';
      container.style.zIndex = '9999';
      document.body.appendChild(container);
    }
    container.appendChild(toast.firstElementChild);
    const bsToast = new bootstrap.Toast(document.getElementById(toastId), { delay: 3500 });
    bsToast.show();
    document.getElementById(toastId).addEventListener('hidden.bs.toast', () => {
      document.getElementById(toastId)?.remove();
    });
  };

  // ─── Lazy Load Images ─────────────────────────────────────────────────
  if ('IntersectionObserver' in window) {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    const imgObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            imgObserver.unobserve(img);
          }
        }
      });
    });
    lazyImages.forEach(img => imgObserver.observe(img));
  }

  // ─── Initialize Tooltips ─────────────────────────────────────────────
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(el => new bootstrap.Tooltip(el));

  // ─── Phone Number Formatting ──────────────────────────────────────────
  document.querySelectorAll('input[type="tel"]').forEach(input => {
    input.addEventListener('input', function () {
      this.value = this.value.replace(/[^\d]/g, '').slice(0, 10);
    });
  });

  // ─── Loading Button State ─────────────────────────────────────────────
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function () {
      const submitBtn = form.querySelector('[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        setTimeout(() => {
          submitBtn.disabled = true;
          const original = submitBtn.innerHTML;
          submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
          // Re-enable after 10s as fallback
          setTimeout(() => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = original;
          }, 10000);
        }, 100);
      }
    });
  });

});
