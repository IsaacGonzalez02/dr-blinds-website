document.addEventListener("DOMContentLoaded", function () {
  var siteHeader = document.querySelector(".site-header");
  if (siteHeader) {
    var updateHeaderScrolled = function () {
      siteHeader.classList.toggle("scrolled", window.scrollY > 40);
    };
    updateHeaderScrolled();
    window.addEventListener("scroll", updateHeaderScrolled, { passive: true });
  }

  document.querySelectorAll(".btn").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      var rect = btn.getBoundingClientRect();
      var size = Math.max(rect.width, rect.height);
      var ripple = document.createElement("span");
      ripple.className = "btn-ripple";
      ripple.style.width = ripple.style.height = size + "px";
      ripple.style.left = (e.clientX - rect.left - size / 2) + "px";
      ripple.style.top = (e.clientY - rect.top - size / 2) + "px";
      btn.appendChild(ripple);
      ripple.addEventListener("animationend", function () { ripple.remove(); });
    });
  });

  var toggle = document.getElementById("nav-toggle");
  var menu = document.getElementById("mobile-nav");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var isOpen = menu.classList.toggle("open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  }

  var windowReveal = document.getElementById("window-reveal");
  var bwSlats = windowReveal ? windowReveal.querySelectorAll(".bw-slat") : [];
  var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (windowReveal && bwSlats.length && !reducedMotion) {
    var updateBwSlats = function () {
      var rect = windowReveal.getBoundingClientRect();
      var vh = window.innerHeight;
      var raw = (vh - rect.top) / (vh + rect.height * 0.35);
      var progress = Math.max(0, Math.min(1, raw));
      bwSlats.forEach(function (slat, i) {
        var start = i * 0.07;
        var span = 0.55;
        var local = Math.max(0, Math.min(1, (progress - start) / span));
        var eased = 1 - Math.pow(1 - local, 3);
        var rise = parseFloat(slat.getAttribute("data-rise")) || 0;
        var scaleY = 1 - eased * 0.88;
        slat.style.transform = "translateY(" + (-eased * rise) + "px) scaleY(" + scaleY + ")";
      });
    };

    var bwTicking = false;
    var onBwScroll = function () {
      if (!bwTicking) {
        window.requestAnimationFrame(function () {
          updateBwSlats();
          bwTicking = false;
        });
        bwTicking = true;
      }
    };

    updateBwSlats();
    window.addEventListener("scroll", onBwScroll, { passive: true });
    window.addEventListener("resize", onBwScroll);
  }

  var revealTargets = document.querySelectorAll(".card, .section-heading");
  if (revealTargets.length && "IntersectionObserver" in window) {
    var revealObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    revealTargets.forEach(function (el) { revealObserver.observe(el); });
  }

  var countUpTargets = document.querySelectorAll(".count-up");
  var prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (countUpTargets.length) {
    var animateCountUp = function (el) {
      var target = parseInt(el.getAttribute("data-count"), 10) || 0;
      if (prefersReducedMotion) {
        el.textContent = target;
        return;
      }
      var duration = 1200;
      var start = null;
      var step = function (timestamp) {
        if (!start) start = timestamp;
        var progress = Math.min((timestamp - start) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * target);
        if (progress < 1) {
          window.requestAnimationFrame(step);
        } else {
          el.textContent = target;
        }
      };
      window.requestAnimationFrame(step);
    };

    if ("IntersectionObserver" in window) {
      var countUpObserver = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              animateCountUp(entry.target);
              countUpObserver.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.5 }
      );
      countUpTargets.forEach(function (el) { countUpObserver.observe(el); });
    } else {
      countUpTargets.forEach(function (el) { el.textContent = el.getAttribute("data-count"); });
    }
  }

  var lightbox = document.getElementById("lightbox");
  var lightboxBody = document.getElementById("lightbox-body");
  var lightboxClose = document.getElementById("lightbox-close");
  var galleryItems = document.querySelectorAll(".gallery-item");

  function openLightbox(src, type, title) {
    if (!lightbox || !lightboxBody) return;
    lightboxBody.innerHTML = "";
    var el;
    if (type === "video") {
      el = document.createElement("video");
      el.src = src;
      el.controls = true;
      el.autoplay = true;
      el.playsInline = true;
    } else {
      el = document.createElement("img");
      el.src = src;
      el.alt = title || "";
    }
    lightboxBody.appendChild(el);
    lightbox.classList.add("open");
    lightbox.setAttribute("aria-hidden", "false");
  }

  function closeLightbox() {
    if (!lightbox || !lightboxBody) return;
    lightbox.classList.remove("open");
    lightbox.setAttribute("aria-hidden", "true");
    lightboxBody.innerHTML = "";
  }

  galleryItems.forEach(function (item) {
    item.addEventListener("click", function () {
      openLightbox(item.getAttribute("data-src"), item.getAttribute("data-type"), item.getAttribute("data-title"));
    });
  });

  if (lightboxClose) lightboxClose.addEventListener("click", closeLightbox);
  if (lightbox) {
    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox) closeLightbox();
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeLightbox();
  });

  var filterButtons = document.querySelectorAll(".gallery-filter");
  if (filterButtons.length) {
    filterButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var filter = btn.getAttribute("data-filter");
        filterButtons.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        galleryItems.forEach(function (item) {
          var matches = filter === "all" || item.getAttribute("data-type") === filter;
          item.classList.remove("gallery-item-enter");
          if (matches) {
            item.classList.remove("gallery-item-hidden");
            void item.offsetWidth;
            item.classList.add("gallery-item-enter");
          } else {
            item.classList.add("gallery-item-hidden");
          }
        });
      });
    });
  }
});
