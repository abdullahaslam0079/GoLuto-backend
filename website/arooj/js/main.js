const photos = [
  {
    src: "photos/01-nikah.png",
    caption: "Our Nikah",
    title: "The beginning",
    story: "The day we started this life. White, gold, and your hand in mine.",
    featured: true,
  },
  {
    src: "photos/02-before-nikah.png",
    caption: "Before the ceremony",
    title: "Understanding",
    story: "We sat down before our Nikah — to know each other, to take this to the next level, to choose with open eyes.",
    featured: true,
  },
  {
    src: "photos/03-barat.png",
    caption: "Barat",
    title: "A new chapter",
    story: "The day our new life began — you in red and gold, me beside you, a whole world opening.",
    featured: true,
  },
  {
    src: "photos/04-walima.png",
    caption: "Walima",
    title: "The celebration",
    story: "Our Walima — the day we stood in front of everyone as husband and wife, and the joy finally had a room of its own.",
    featured: true,
  },
  {
    caption: "Honeymoon",
    title: "The best time of our life",
    story: "Just us, and mountains wide enough to hold it. I still go back there in my mind.",
    featured: true,
    gallery: [
      { src: "photos/05-honeymoon-1.png", caption: "The mountains" },
      { src: "photos/05-honeymoon-2.png", caption: "Beside you" },
      { src: "photos/05-honeymoon-3.png", caption: "A day I keep" },
    ],
  },
  {
    src: "photos/06-first-eid.png",
    caption: "Our first Eid",
    title: "Together",
    story: "The first Eid we spent as us. A blessing I had only imagined before — and then it had your smile in it.",
    featured: true,
  },
];

const film = document.getElementById("film");
const curtain = document.getElementById("curtain");
const beginBtn = document.getElementById("begin");
const hint = document.getElementById("scroll-hint");
const muteBtn = document.getElementById("mute");
const score = document.getElementById("score");
const stillsScene = document.getElementById("stills-scene");
const stills = document.getElementById("stills");
const moments = document.getElementById("moments");
const countdown = document.getElementById("countdown");
const progress = document.getElementById("progress");
const reel = document.getElementById("reel");
const lightbox = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const lightboxCap = document.getElementById("lightbox-cap");
const dust = document.getElementById("dust");
const chapters = document.getElementById("chapters");
const prevBtn = document.getElementById("prev");
const nextBtn = document.getElementById("next");

let sceneIndex = 0;

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function preloadImages() {
  photos.forEach((photo) => {
    if (photo.src) new Image().src = photo.src;
    (photo.gallery || []).forEach((item) => {
      new Image().src = item.src;
    });
  });
}

function frameMarkup(src, caption) {
  return `
    <figure class="moment-frame" data-full="${src}" data-cap="${caption}">
      <img src="${src}" alt="${caption}" />
      <figcaption>${caption}</figcaption>
    </figure>`;
}

function renderPhotos() {
  const featured = photos.filter((photo) => photo.featured);
  const rest = photos.filter((photo) => !photo.featured);

  moments.innerHTML = featured
    .map((photo) => {
      if (photo.gallery) {
        const frames = photo.gallery
          .map((item, i) =>
            frameMarkup(item.src, item.caption || photo.caption).replace(
              "moment-frame",
              `moment-frame${i === 0 ? " gallery-hero" : ""}`
            )
          )
          .join("");
        return `
          <section class="scene scene-moment scene-gallery" data-reel="${photo.caption}">
            <p class="eyebrow">${photo.caption}</p>
            <div class="moment-gallery">${frames}</div>
            <h2>${photo.title}</h2>
            <p class="whisper">${photo.story}</p>
          </section>`;
      }

      return `
        <section class="scene scene-moment" data-reel="${photo.caption}">
          <p class="eyebrow">${photo.caption}</p>
          ${frameMarkup(photo.src, photo.caption)}
          <h2>${photo.title}</h2>
          <p class="whisper">${photo.story}</p>
        </section>`;
    })
    .join("");

  if (!rest.length) {
    stillsScene.hidden = true;
    return;
  }

  stillsScene.hidden = false;
  stills.innerHTML = rest
    .map(
      (photo) => `
      <figure class="still">
        <img src="${photo.src}" alt="${photo.caption || "A still from our life"}" />
        ${photo.caption ? `<figcaption>${photo.caption}</figcaption>` : ""}
      </figure>`
    )
    .join("");
}

function sceneList() {
  return [...document.querySelectorAll(".scene")].filter(
    (scene) => !scene.hidden && scene.offsetParent !== null
  );
}

function goToScene(index) {
  const scenes = sceneList();
  if (!scenes.length) return;
  sceneIndex = Math.max(0, Math.min(index, scenes.length - 1));
  scenes[sceneIndex].scrollIntoView({ behavior: "smooth", block: "start" });
  updateChapters();
}

function renderChapters() {
  const scenes = sceneList();
  chapters.innerHTML = scenes
    .map(
      (scene, index) =>
        `<button type="button" class="chapter" data-index="${index}" aria-label="${scene.dataset.reel || "Scene"}"></button>`
    )
    .join("");
}

function updateChapters() {
  chapters.querySelectorAll(".chapter").forEach((dot, index) => {
    dot.classList.toggle("is-active", index === sceneIndex);
  });
}

function observeScenes() {
  const scenes = sceneList();
  renderChapters();

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        entry.target.classList.toggle("is-in", entry.isIntersecting);
        if (entry.isIntersecting) {
          if (entry.target.dataset.reel) reel.textContent = entry.target.dataset.reel;
          sceneIndex = scenes.indexOf(entry.target);
          updateChapters();
        }
      });
    },
    { threshold: 0.45 }
  );
  scenes.forEach((scene) => io.observe(scene));
}

function startDust() {
  const ctx = dust.getContext("2d");
  const dots = [];

  function resize() {
    dust.width = window.innerWidth;
    dust.height = window.innerHeight;
  }

  resize();
  window.addEventListener("resize", resize);

  for (let i = 0; i < 36; i += 1) {
    dots.push({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      r: Math.random() * 1.4 + 0.3,
      s: Math.random() * 0.28 + 0.06,
      a: Math.random() * 0.35 + 0.08,
    });
  }

  function tick() {
    ctx.clearRect(0, 0, dust.width, dust.height);
    dots.forEach((dot) => {
      ctx.beginPath();
      ctx.fillStyle = `rgba(201, 166, 107, ${dot.a})`;
      ctx.arc(dot.x, dot.y, dot.r, 0, Math.PI * 2);
      ctx.fill();
      dot.y -= dot.s;
      dot.x += Math.sin(dot.y / 40) * 0.15;
      if (dot.y < -4) {
        dot.y = dust.height + 4;
        dot.x = Math.random() * dust.width;
      }
    });
    requestAnimationFrame(tick);
  }

  tick();
}

function fadeInAudio() {
  score.volume = 0;
  const target = 0.32;
  const step = () => {
    if (score.volume < target - 0.01) {
      score.volume = Math.min(target, score.volume + 0.02);
      requestAnimationFrame(step);
    }
  };
  requestAnimationFrame(step);
}

async function startScore() {
  try {
    score.currentTime = 0;
    await score.play();
    fadeInAudio();
    score.muted = false;
    muteBtn.hidden = false;
    muteBtn.classList.remove("is-off");
    muteBtn.textContent = "♪";
  } catch {
    muteBtn.hidden = true;
  }
}

const quiz = document.getElementById("quiz");
const quizReact = document.getElementById("quiz-react");
const quizStamp = document.getElementById("quiz-stamp");
let wrongGuesses = 0;

function stamp(src) {
  quizStamp.src = src;
  quizStamp.hidden = false;
  quizStamp.classList.remove("is-on");
  void quizStamp.offsetWidth;
  quizStamp.classList.add("is-on");
}

function funnyWrong(button, message) {
  wrongGuesses += 1;
  const extra =
    wrongGuesses >= 2 ? " I can sit here all day. You KNOW this." : " Try again!";
  button.classList.remove("is-wrong");
  void button.offsetWidth;
  button.classList.add("is-wrong");
  setTimeout(() => button.classList.remove("is-wrong"), 600);
  stamp("assets/cartoon-nope.png");
  quizReact.hidden = false;
  quizReact.className = "quiz-react is-funny";
  quizReact.textContent = message + extra;
}

async function sweetRight(button, message) {
  button.classList.add("is-right");
  quiz.classList.add("is-sweet");
  stamp("assets/cartoon-yay.png");
  quizReact.hidden = false;
  quizReact.className = "quiz-react is-sweet";
  quizReact.textContent = message;
  await wait(3400);
  quiz.classList.add("is-leaving");
  await wait(600);
  quiz.hidden = true;
  document.body.classList.remove("is-cartoon");
  curtain.hidden = false;
  void curtain.offsetWidth;
  curtain.classList.add("is-ready");
}

quiz.addEventListener("click", (event) => {
  const button = event.target.closest(".choice");
  if (!button || quiz.classList.contains("is-sweet")) return;
  if (button.dataset.ok === "true") {
    sweetRight(button, button.dataset.msg);
  } else {
    funnyWrong(button, button.dataset.msg);
  }
});

async function startFilm() {
  startScore();
  curtain.classList.add("is-gone");
  countdown.hidden = false;

  for (const beat of ["3", "2", "1"]) {
    countdown.textContent = beat;
    countdown.classList.remove("pop");
    void countdown.offsetWidth;
    countdown.classList.add("pop");
    await wait(480);
  }

  countdown.hidden = true;
  document.documentElement.classList.add("is-playing");
  document.body.classList.add("is-playing");
  film.hidden = false;
  hint.hidden = false;
  prevBtn.hidden = false;
  nextBtn.hidden = false;
  observeScenes();
  document.querySelector(".scene")?.classList.add("is-in");
}

beginBtn.addEventListener("click", () => {
  beginBtn.disabled = true;
  startFilm();
});

muteBtn.addEventListener("click", async () => {
  if (score.paused) {
    await startScore();
    return;
  }
  score.muted = !score.muted;
  muteBtn.classList.toggle("is-off", score.muted);
  muteBtn.textContent = score.muted ? "♫" : "♪";
});

prevBtn.addEventListener("click", () => goToScene(sceneIndex - 1));
nextBtn.addEventListener("click", () => goToScene(sceneIndex + 1));

chapters.addEventListener("click", (event) => {
  const dot = event.target.closest(".chapter");
  if (!dot) return;
  goToScene(Number(dot.dataset.index));
});

window.addEventListener(
  "scroll",
  () => {
    if (window.scrollY > 80) hint.classList.add("is-hidden");
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const pct = max > 0 ? (window.scrollY / max) * 100 : 0;
    progress.style.width = `${pct}%`;
  },
  { passive: true }
);

moments.addEventListener("click", (event) => {
  const frame = event.target.closest(".moment-frame");
  if (!frame) return;
  lightboxImg.src = frame.dataset.full;
  lightboxCap.textContent = frame.dataset.cap || "";
  lightbox.hidden = false;
});

lightbox.addEventListener("click", () => {
  lightbox.hidden = true;
  lightboxImg.src = "";
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    lightbox.hidden = true;
    lightboxImg.src = "";
    return;
  }
  if (!document.body.classList.contains("is-playing") || !lightbox.hidden) return;
  if (event.key === "ArrowRight" || event.key === " ") {
    event.preventDefault();
    goToScene(sceneIndex + 1);
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    goToScene(sceneIndex - 1);
  }
});

renderPhotos();
preloadImages();
startDust();
