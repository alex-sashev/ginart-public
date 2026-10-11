// Mobile menu
const burger = document.querySelector(".burger"), nav = document.getElementById("nav");
burger.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  burger.setAttribute("aria-expanded", open);
});

// Article category filter ("За пациентите")
document.querySelectorAll(".chip").forEach(chip => chip.addEventListener("click", () => {
  const cat = chip.dataset.filter;
  document.querySelectorAll(".chip").forEach(c => c.setAttribute("aria-pressed", c === chip));
  document.querySelectorAll(".art-list .art-card").forEach(card => {
    card.hidden = cat && card.dataset.category !== cat;
  });
}));
