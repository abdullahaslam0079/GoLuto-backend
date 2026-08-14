const copy = {
  de: {
    navAbout: "Über uns",
    navApp: "Die App",
    navShops: "Für Händler",
    navCta: "Kontakt",
    kicker: "GoLuto · Deutschland",
    heroA: "Die Stadt wird",
    heroB: "günstiger,",
    heroC: "wenn du sie siehst.",
    lede: "GoLuto ist die App für Angebote um die Ecke und im Netz. Kein Flyer, kein Code zum Vorlesen — du siehst den Deal, gehst hin, löst ein.",
    soonNote: "Download folgt — Buttons sind schon da.",
    iosTop: "Laden im",
    playTop: "Jetzt bei",
    ctaStory: "Was GoLuto ist",
    ctaMail: "hello@goluto.de",
    chip1: "In der Nähe",
    chip2: "Online",
    chip3: "Ein Scan",
    aboutEyebrow: "Die Idee",
    aboutTitle: "Angebote dort, wo du gerade bist.",
    about1:
      "GoLuto verbindet Menschen mit Läden in ihrer Stadt. Du öffnest die App in Berlin oder anderswo in Deutschland und siehst, was in der Nähe und online gerade weniger kostet — Elektronik bei MediaMarkt, ein Hemd bei Zara, Alltag bei Rossmann, das Café um die Ecke.",
    about2:
      "Die Karte zeigt dir, wo der Rabatt wirklich liegt. Die Stores-Ansicht ist der Schaufensterbummel. Zuhause oder unterwegs: ein Scan an der Kasse, und das Angebot ist eingelöst. So einfach soll Sparen sein.",
    about3:
      "Für Händler ist GoLuto die andere Seite derselben Sache: Filiale anlegen, Angebot live stellen, QR an die Tür. Kunden finden euch, ohne dass ihr Flyer drucken müsst.",
    step1t: "Sehen",
    step1: "Deal auf der Karte oder im Feed. Kein Flyer, kein Rätsel.",
    step2t: "Gehen",
    step2: "Zum Laden um die Ecke — oder online, wenn’s passt.",
    step3t: "Einlösen",
    step3: "QR an der Kasse scannen. Das Angebot ist deins.",
    appEyebrow: "So sieht’s aus",
    appTitle: "Drei Blickwinkel. Eine App.",
    cap1t: "Home",
    cap1: "Was sich heute lohnt — in der Nähe und online.",
    cap2t: "Discover",
    cap2: "Die Stadt als Karte. Pins sind Deals, nicht nur Orte.",
    cap3t: "Stores",
    cap3: "Läden wie ein Feed. Tippen, merken, hingehen.",
    youEyebrow: "Für dich",
    youTitle: "Sparen, ohne zu suchen.",
    youBody:
      "Standort, ein Blick auf die Karte, fertig. GoLuto ist kostenlos für alle, die Angebote finden und einlösen wollen. Login mit Telefon, Google oder Apple.",
    shopEyebrow: "Für Händler",
    shopTitle: "Sichtbar werden, wo Kunden schon sind.",
    shopBody:
      "Ihr stellt ein, was gilt. Wir bringen es zu Leuten in der Straße. Filialen, Angebote, QR-Poster, ein Dashboard. Schreib uns, wenn dein Laden dabei sein soll.",
    shopCta: "Als Händler schreiben",
    ctaTitle: "Bald auf iOS und Android.",
    ctaBody: "Sag uns Bescheid. Wir sagen dir, wenn GoLuto live ist.",
    footTag: "Lokale Angebote. Ein Scan.",
    imprint: "Impressum",
    privacy: "Datenschutz",
  },
  en: {
    navAbout: "About",
    navApp: "The app",
    navShops: "For shops",
    navCta: "Contact",
    kicker: "GoLuto · Germany",
    heroA: "The city gets",
    heroB: "cheaper",
    heroC: "when you can see it.",
    lede: "GoLuto is the app for deals around the corner and online. No flyer, no code to read out — see it, go there, redeem.",
    soonNote: "Download coming — buttons are ready.",
    iosTop: "Download on the",
    playTop: "Get it on",
    ctaStory: "What GoLuto is",
    ctaMail: "hello@goluto.de",
    chip1: "Nearby",
    chip2: "Online",
    chip3: "One scan",
    aboutEyebrow: "The idea",
    aboutTitle: "Deals where you actually are.",
    about1:
      "GoLuto connects people with shops in their city. Open the app in Berlin or anywhere in Germany and see what’s cheaper nearby and online — electronics at MediaMarkt, a shirt at Zara, everyday at Rossmann, the café on your street.",
    about2:
      "The map shows where the discount really is. Stores is a window-shopping feed. At home or out: one scan at the till, and the offer is yours. Saving should feel that simple.",
    about3:
      "For merchants, GoLuto is the other half of the same idea: add a branch, publish a deal, QR on the door. Customers find you without a stack of flyers.",
    step1t: "See",
    step1: "The deal on the map or in the feed. No flyer, no puzzle.",
    step2t: "Go",
    step2: "To the shop around the corner — or online, if that fits.",
    step3t: "Redeem",
    step3: "Scan the QR at the till. The offer is yours.",
    appEyebrow: "How it looks",
    appTitle: "Three views. One app.",
    cap1t: "Home",
    cap1: "What’s worth it today — nearby and online.",
    cap2t: "Discover",
    cap2: "The city as a map. Pins are deals, not just places.",
    cap3t: "Stores",
    cap3: "Shops as a feed. Tap, save, go.",
    youEyebrow: "For you",
    youTitle: "Save without hunting.",
    youBody:
      "Location, a look at the map, done. GoLuto is free for anyone who wants to find and redeem offers. Sign in with phone, Google, or Apple.",
    shopEyebrow: "For shops",
    shopTitle: "Show up where customers already are.",
    shopBody:
      "You publish what’s on. We put it in front of people on the street. Branches, offers, QR posters, a dashboard. Write us if your store should be in.",
    shopCta: "Write as a merchant",
    ctaTitle: "Coming soon on iOS and Android.",
    ctaBody: "Tell us you’re in. We’ll tell you when GoLuto is live.",
    footTag: "Local deals. One scan.",
    imprint: "Imprint",
    privacy: "Privacy",
  },
};

function applyLang(lang) {
  const dict = copy[lang] || copy.de;
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) el.textContent = dict[key];
  });
  document.querySelectorAll(".lang button").forEach((btn) => {
    btn.setAttribute("aria-pressed", String(btn.dataset.lang === lang));
  });
  localStorage.setItem("goluto-lang", lang);
}

document.querySelectorAll(".lang button").forEach((btn) => {
  btn.addEventListener("click", () => applyLang(btn.dataset.lang));
});

const menuBtn = document.querySelector(".menu-btn");
menuBtn?.addEventListener("click", () => {
  const open = document.body.classList.toggle("menu-open");
  menuBtn.setAttribute("aria-expanded", String(open));
});

document.querySelectorAll(".nav-panel a").forEach((link) => {
  link.addEventListener("click", () => {
    document.body.classList.remove("menu-open");
    menuBtn?.setAttribute("aria-expanded", "false");
  });
});

const bar = document.querySelector(".progress");
const nav = document.querySelector(".nav");

function onScroll() {
  if (bar) {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = `${max > 0 ? (window.scrollY / max) * 100 : 0}%`;
  }
  nav?.classList.toggle("scrolled", window.scrollY > 16);
}

window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (!reduce) {
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.16, rootMargin: "0px 0px -8% 0px" },
  );
  document.querySelectorAll(".rise").forEach((el, i) => {
    el.style.setProperty("--d", `${(i % 4) * 90}ms`);
    io.observe(el);
  });

  const hero = document.querySelector(".hero");
  const spot = document.getElementById("spot");
  const stack = document.querySelector(".stack");
  const floats = stack ? [...stack.querySelectorAll(".float")] : [];

  let sx = window.innerWidth * 0.7;
  let sy = 180;
  let spx = sx;
  let spy = sy;
  let tx = 0;
  let ty = 0;
  let cx = 0;
  let cy = 0;

  hero?.addEventListener("pointermove", (event) => {
    const r = hero.getBoundingClientRect();
    sx = event.clientX - r.left;
    sy = event.clientY - r.top;
  });

  if (stack) {
    stack.addEventListener("pointermove", (event) => {
      const r = stack.getBoundingClientRect();
      tx = (event.clientX - r.left) / r.width - 0.5;
      ty = (event.clientY - r.top) / r.height - 0.5;
    });
    stack.addEventListener("pointerleave", () => {
      tx = 0;
      ty = 0;
    });
  }

  function tick() {
    spx += (sx - spx) * 0.1;
    spy += (sy - spy) * 0.1;
    cx += (tx - cx) * 0.08;
    cy += (ty - cy) * 0.08;

    if (spot) spot.style.transform = `translate3d(${spx}px, ${spy}px, 0)`;

    floats.forEach((el, i) => {
      const device = el.querySelector(".device");
      if (!device) return;
      const d = (i + 1) * 18;
      device.style.transform = `translate3d(${cx * d}px, ${cy * d}px, 0) rotateX(${-cy * 10}deg) rotateY(${cx * 14}deg)`;
    });

    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  document.querySelectorAll(".tilt").forEach((card) => {
    const device = card.querySelector(".device");
    if (!device) return;
    card.addEventListener("pointermove", (event) => {
      const r = card.getBoundingClientRect();
      const x = (event.clientX - r.left) / r.width - 0.5;
      const y = (event.clientY - r.top) / r.height - 0.5;
      device.style.transform = `translateY(-10px) rotateX(${-y * 12}deg) rotateY(${x * 14}deg)`;
    });
    card.addEventListener("pointerleave", () => {
      device.style.transform = "";
    });
  });

  document.querySelectorAll("[data-magnetic]").forEach((el) => {
    el.addEventListener("pointermove", (event) => {
      const r = el.getBoundingClientRect();
      const x = event.clientX - (r.left + r.width / 2);
      const y = event.clientY - (r.top + r.height / 2);
      el.style.transform = `translate(${x * 0.22}px, ${y * 0.22}px)`;
    });
    el.addEventListener("pointerleave", () => {
      el.style.transform = "";
    });
  });
} else {
  document.querySelectorAll(".rise").forEach((el) => el.classList.add("in"));
}

applyLang(localStorage.getItem("goluto-lang") || "de");

document.querySelectorAll(".store.is-soon").forEach((el) => {
  el.addEventListener("click", (event) => event.preventDefault());
});
