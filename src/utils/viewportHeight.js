// Set a custom property with the actual viewport height
// This is used as a fallback for browsers that don't support dvh units

export function setViewportHeight() {
  document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
}

export function initViewportHeight() {
  // Set the initial value
  setViewportHeight();

  // Update on resize and orientation change
  window.addEventListener('resize', setViewportHeight);
  window.addEventListener('orientationchange', setViewportHeight);
}