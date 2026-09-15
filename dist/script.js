const header = document.querySelector("#site-header");
const menuButton = document.querySelector(".menu-toggle");
const nav = document.querySelector("#primary-nav");
const menuBackground = document.querySelectorAll("main, body > footer");

const updateHeader = () => {
  header?.classList.toggle("is-scrolled", window.scrollY > 32);
};

const closeMenu = () => {
  menuButton?.setAttribute("aria-expanded", "false");
  nav?.classList.remove("is-open");
  header?.classList.remove("menu-active");
  document.body.classList.remove("menu-open");
  menuBackground.forEach((element) => { element.inert = false; });
};

updateHeader();
window.addEventListener("scroll", updateHeader, { passive: true });

menuButton?.addEventListener("click", () => {
  const isOpen = menuButton.getAttribute("aria-expanded") === "true";
  menuButton.setAttribute("aria-expanded", String(!isOpen));
  nav?.classList.toggle("is-open", !isOpen);
  header?.classList.toggle("menu-active", !isOpen);
  document.body.classList.toggle("menu-open", !isOpen);
  menuBackground.forEach((element) => { element.inert = !isOpen; });
});

nav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
window.addEventListener("keydown", (event) => {
  if (menuButton?.getAttribute("aria-expanded") !== "true") return;
  if (event.key === "Escape") {
    closeMenu();
    menuButton.focus();
  }
  if (event.key === "Tab") {
    const controls = [menuButton, ...nav.querySelectorAll("a")];
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
});
window.matchMedia("(min-width: 1021px)").addEventListener("change", closeMenu);

const classTabs = [...document.querySelectorAll(".class-tabs [role=tab]")];
classTabs.forEach((tab, index) => {
  const selectTab = () => {
    classTabs.forEach((item) => {
      const selected = item === tab;
      item.setAttribute("aria-selected", String(selected));
      item.tabIndex = selected ? 0 : -1;
      const panel = document.getElementById(item.getAttribute("aria-controls"));
      if (panel) panel.hidden = !selected;
    });
  };
  tab.addEventListener("click", selectTab);
  tab.addEventListener("keydown", (event) => {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % classTabs.length;
    else if (event.key === "ArrowLeft") next = (index + classTabs.length - 1) % classTabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = classTabs.length - 1;
    else return;
    event.preventDefault();
    classTabs[next].focus();
    classTabs[next].click();
  });
});

const disciplines = {
  striking: {
    image: "./assets/archive-sparring-two.webp",
    alt: "Strange Wolves members working striking and takedown range",
    kicker: "Distance is never neutral",
    name: "Strike with the takedown in mind.",
    text: "Footwork, hands and kicks taught in the reality of MMA—where the level change, clinch and cage are always part of the exchange.",
  },
  wrestling: {
    image: "./assets/grappling-showcase.webp",
    alt: "A Strange Wolves grappling and takedown demonstration",
    kicker: "Own the collision",
    name: "Turn contact into control.",
    text: "Entries, clinch work, takedowns and defence. Wrestling is the engine room that decides where the fight happens.",
  },
  ground: {
    image: "./assets/cage-corner.webp",
    alt: "Strange Wolves coaching and competing beside the cage",
    kicker: "Position before the finish",
    name: "Stay dangerous on the floor.",
    text: "Control, escapes and submissions with the reminder that strikes change every position. Ground work stays connected to the whole fight.",
  },
};

const disciplineStage = document.querySelector(".discipline-stage");
const disciplineImage = document.querySelector("#discipline-image");
const disciplineKicker = document.querySelector("#discipline-kicker");
const disciplineName = document.querySelector("#discipline-name");
const disciplineText = document.querySelector("#discipline-text");

const disciplineButtons = [...document.querySelectorAll("[data-discipline]")];
if (disciplineStage) disciplineStage.id = "discipline-panel";
disciplineButtons.forEach((button, index) => {
  button.id = "tab-" + button.dataset.discipline;
  button.setAttribute("aria-controls", "discipline-panel");
  button.tabIndex = index === 0 ? 0 : -1;
  if (index === 0) disciplineStage?.setAttribute("aria-labelledby", button.id);
  button.addEventListener("keydown", (event) => {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % disciplineButtons.length;
    else if (event.key === "ArrowLeft") next = (index + disciplineButtons.length - 1) % disciplineButtons.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = disciplineButtons.length - 1;
    else return;
    event.preventDefault();
    disciplineButtons[next].focus();
    disciplineButtons[next].click();
  });
  button.addEventListener("click", () => {
    const choice = disciplines[button.dataset.discipline];
    if (!choice || button.getAttribute("aria-selected") === "true") return;

    document.querySelectorAll("[data-discipline]").forEach((item) => {
      item.setAttribute("aria-selected", String(item === button));
      item.tabIndex = item === button ? 0 : -1;
    });
    disciplineStage?.setAttribute("aria-labelledby", button.id);
      if (disciplineImage) {
        disciplineImage.src = choice.image;
        disciplineImage.alt = choice.alt;
        disciplineImage.removeAttribute("height");
      }
      if (disciplineKicker) disciplineKicker.textContent = choice.kicker;
      if (disciplineName) disciplineName.textContent = choice.name;
      if (disciplineText) disciplineText.textContent = choice.text;
  });
});

const galleryDialog = document.querySelector("#gallery-dialog");
const dialogImage = document.querySelector("#dialog-image");
const dialogCaption = document.querySelector("#dialog-caption");

document.querySelectorAll("[data-gallery-src]").forEach((button) => {
  button.addEventListener("click", () => {
    if (!galleryDialog || !dialogImage || !dialogCaption) return;
    dialogImage.src = button.dataset.gallerySrc;
    dialogImage.alt = button.dataset.galleryAlt || "Strange Wolves club photograph";
    dialogCaption.textContent = button.querySelector("span")?.textContent || "Strange Wolves MMA";
    galleryDialog.showModal();
  });
});

document.querySelector(".dialog-close")?.addEventListener("click", () => galleryDialog?.close());
galleryDialog?.addEventListener("click", (event) => {
  if (event.target === galleryDialog) galleryDialog.close();
});

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const revealItems = document.querySelectorAll(".reveal");

if (reducedMotion || !("IntersectionObserver" in window)) {
  revealItems.forEach((item) => item.classList.add("in-view"));
} else {
  const observer = new IntersectionObserver(
    (entries, activeObserver) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          activeObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08, rootMargin: "0px 0px -4%" },
  );
  revealItems.forEach((item) => observer.observe(item));
}

const year = document.querySelector("#year");
if (year) year.textContent = String(new Date().getFullYear());

// Keep links useful when their destination is inside a tab or closed panel.
const revealDestination = (hash, scroll = false) => {
  if (!hash || hash === "#") return;
  let target;
  try { target = document.getElementById(decodeURIComponent(hash.slice(1))); }
  catch { return; }
  if (!target) return;
  const panel = target.closest(".class-panel");
  if (panel?.hidden) {
    classTabs.find((tab) => tab.getAttribute("aria-controls") === panel.id)?.click();
  }
  for (let parent = target.parentElement; parent; parent = parent.parentElement) {
    if (parent.tagName === "DETAILS") parent.open = true;
  }
  if (scroll) requestAnimationFrame(() => target.scrollIntoView({ block: "start" }));
};
document.addEventListener("click", (event) => {
  const link = event.target.closest?.('a[href^="#"]');
  if (link) revealDestination(link.hash);
});
window.addEventListener("hashchange", () => revealDestination(location.hash, true));
revealDestination(location.hash, true);
