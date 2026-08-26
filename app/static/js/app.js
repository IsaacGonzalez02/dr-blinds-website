document.addEventListener("DOMContentLoaded", function () {
  var siteHeader = document.querySelector(".site-header");
  if (siteHeader) {
    var updateHeaderScrolled = function () {
      siteHeader.classList.toggle("scrolled", window.scrollY > 40);
    };
    updateHeaderScrolled();
    window.addEventListener("scroll", updateHeaderScrolled, { passive: true });
  }

  var toggle = document.getElementById("nav-toggle");
  var menu = document.getElementById("mobile-nav");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var isOpen = menu.classList.toggle("open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  }

  var windowReveal = document.getElementById("window-reveal");
  if (windowReveal && "IntersectionObserver" in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            windowReveal.classList.add("in-view");
            observer.unobserve(windowReveal);
          }
        });
      },
      { threshold: 0.35 }
    );
    observer.observe(windowReveal);
  } else if (windowReveal) {
    windowReveal.classList.add("in-view");
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
