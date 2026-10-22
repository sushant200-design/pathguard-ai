const menuToggle = document.getElementById("menuToggle");
const mainNav = document.getElementById("mainNav");
if (menuToggle && mainNav) menuToggle.addEventListener("click", () => mainNav.classList.toggle("nav-open"));
document.querySelectorAll(".flash").forEach((el) => {
  window.setTimeout(() => { if (el.isConnected) el.classList.add("flash-fade"); }, 6000);
});
