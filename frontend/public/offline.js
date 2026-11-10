/* global document, window */
document.getElementById("retry-btn")?.addEventListener("click", (event) => {
  event.preventDefault();
  window.location.reload();
});
