/**
 * Barabanki Connect — Client JavaScript Utilities
 * Handles theme toggling, mobile navigation, toast alerts, and CSRF helpers.
 */

document.addEventListener("DOMContentLoaded", () => {
  initThemeToggle();
  initMobileNav();
  initAlertDismissals();
});

/**
 * Theme Management (Auto / Light / Dark) with LocalStorage Persistence
 */
function initThemeToggle() {
  const toggleBtn = document.getElementById("theme-toggle-btn");
  if (!toggleBtn) return;

  const currentTheme = localStorage.getItem("bbk_theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

  document.documentElement.setAttribute("data-theme", currentTheme);
  updateThemeIcon(toggleBtn, currentTheme);

  toggleBtn.addEventListener("click", () => {
    const activeTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", activeTheme);
    localStorage.setItem("bbk_theme", activeTheme);
    updateThemeIcon(toggleBtn, activeTheme);
  });
}

function updateThemeIcon(btn, theme) {
  if (theme === "dark") {
    btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
    btn.setAttribute("title", "Switch to Light Mode");
    btn.setAttribute("aria-label", "Switch to Light Mode");
  } else {
    btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
    btn.setAttribute("title", "Switch to Dark Mode");
    btn.setAttribute("aria-label", "Switch to Dark Mode");
  }
}

/**
 * Mobile Navigation Drawer
 */
function initMobileNav() {
  const toggleBtn = document.getElementById("mobile-menu-toggle");
  const drawer = document.getElementById("mobile-drawer");

  if (!toggleBtn || !drawer) return;

  toggleBtn.addEventListener("click", () => {
    const isOpen = drawer.classList.contains("open");
    if (isOpen) {
      drawer.classList.remove("open");
      toggleBtn.setAttribute("aria-expanded", "false");
    } else {
      drawer.classList.add("open");
      toggleBtn.setAttribute("aria-expanded", "true");
    }
  });

  // Close when clicking outside
  document.addEventListener("click", (e) => {
    if (drawer.classList.contains("open") && !drawer.contains(e.target) && !toggleBtn.contains(e.target)) {
      drawer.classList.remove("open");
      toggleBtn.setAttribute("aria-expanded", "false");
    }
  });
}

/**
 * Flash Alert Dismissal
 */
function initAlertDismissals() {
  document.querySelectorAll(".alert-close").forEach((btn) => {
    btn.addEventListener("click", () => {
      const alert = btn.closest(".alert");
      if (alert) {
        alert.style.opacity = "0";
        setTimeout(() => alert.remove(), 200);
      }
    });
  });
}

/**
 * Toast Notification System
 * Call: window.showToast("Message", "success" | "danger" | "info" | "warning")
 */
window.showToast = function (message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div style="flex: 1; font-size: 0.9rem;">${message}</div>
    <button type="button" style="background:none;border:none;cursor:pointer;color:inherit;font-weight:bold;">&times;</button>
  `;

  toast.querySelector("button").addEventListener("click", () => toast.remove());
  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }
  }, 4000);
};

/**
 * Helper to get cookie by name
 */
window.getCookie = function (name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
};
