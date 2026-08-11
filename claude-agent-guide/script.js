const lessonCheckboxes = [...document.querySelectorAll("[data-complete]")];
const lessonSections = [...document.querySelectorAll("[data-lesson]")];
const navLinks = [...document.querySelectorAll("#lesson-nav a")];
const progressStorageKey = "claude-agent-guide-progress-v1";

function loadProgress() {
  try {
    return new Set(JSON.parse(localStorage.getItem(progressStorageKey) || "[]"));
  } catch {
    return new Set();
  }
}

let completedLessons = loadProgress();

function saveProgress() {
  localStorage.setItem(progressStorageKey, JSON.stringify([...completedLessons]));
}

function renderLessonProgress() {
  lessonCheckboxes.forEach((checkbox) => {
    checkbox.checked = completedLessons.has(checkbox.dataset.complete);
  });

  const completed = completedLessons.size;
  const total = lessonCheckboxes.length;
  const percent = total ? Math.round((completed / total) * 100) : 0;

  document.querySelector("#lesson-count").textContent = `${completed} of ${total} lessons complete`;
  document.querySelector("#sidebar-progress-value").textContent = `${percent}%`;
  document.querySelector("#sidebar-progress-bar").style.transform = `scaleX(${percent / 100})`;
}

lessonCheckboxes.forEach((checkbox) => {
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) {
      completedLessons.add(checkbox.dataset.complete);
    } else {
      completedLessons.delete(checkbox.dataset.complete);
    }
    saveProgress();
    renderLessonProgress();
  });
});

document.querySelector("#reset-progress").addEventListener("click", () => {
  completedLessons = new Set();
  saveProgress();
  renderLessonProgress();
});

function updateReadingProgress() {
  const scrollable = document.documentElement.scrollHeight - window.innerHeight;
  const percent = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
  document.querySelector("#reading-progress-bar").style.transform =
    `scaleX(${Math.min(percent, 100) / 100})`;
}

let scrollQueued = false;
window.addEventListener(
  "scroll",
  () => {
    if (scrollQueued) return;
    scrollQueued = true;
    requestAnimationFrame(() => {
      updateReadingProgress();
      scrollQueued = false;
    });
  },
  { passive: true },
);

const lessonObserver = new IntersectionObserver(
  (entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

    if (!visible) return;
    navLinks.forEach((link) => {
      const isActive = link.getAttribute("href") === `#${visible.target.id}`;
      link.classList.toggle("active", isActive);
      if (isActive) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
  },
  { rootMargin: "-20% 0px -58% 0px", threshold: [0.05, 0.25, 0.5] },
);

lessonSections.forEach((section) => lessonObserver.observe(section));

document.querySelector("#copy-prompt").addEventListener("click", async () => {
  const status = document.querySelector("#copy-status");
  const button = document.querySelector("#copy-prompt");

  try {
    await navigator.clipboard.writeText(document.querySelector("#prompt-text").innerText);
    status.textContent = "Prompt copied to your clipboard.";
    button.textContent = "Copied";
    setTimeout(() => {
      button.textContent = "Copy prompt";
      status.textContent = "";
    }, 2200);
  } catch {
    status.textContent = "Copy was blocked. Select the prompt text and copy it manually.";
  }
});

document.querySelector("#print-guide").addEventListener("click", () => window.print());

document.querySelector("#check-all").addEventListener("click", (event) => {
  const boxes = [...document.querySelectorAll("#preflight-checklist input")];
  const shouldCheck = boxes.some((box) => !box.checked);
  boxes.forEach((box) => {
    box.checked = shouldCheck;
  });
  event.currentTarget.textContent = shouldCheck ? "Clear all" : "Check all";
});

renderLessonProgress();
updateReadingProgress();
