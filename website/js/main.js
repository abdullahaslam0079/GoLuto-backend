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
    aboutEyebrow: "Die Idee",
    aboutTitle: "Angebote dort, wo du gerade bist.",
    about1:
      "GoLuto verbindet Menschen mit Läden in ihrer Stadt. Du öffnest die App in Berlin oder anderswo in Deutschland und siehst, was in der Nähe und online gerade weniger kostet — Elektronik bei MediaMarkt, ein Hemd bei Zara, Alltag bei Rossmann, das Café um die Ecke.",
    about2:
      "Die Karte zeigt dir, wo der Rabatt wirklich liegt. Die Stores-Ansicht ist der Schaufensterbummel. Zuhause oder unterwegs: ein Scan an der Kasse, und das Angebot ist eingelöst. So einfach soll Sparen sein.",
    about3:
      "Für Händler ist GoLuto die andere Seite derselben Sache: Filiale anlegen, Angebot live stellen, QR an die Tür. Kunden finden euch, ohne dass ihr Flyer drucken müsst.",
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
    aboutEyebrow: "The idea",
    aboutTitle: "Deals where you actually are.",
    about1:
      "GoLuto connects people with shops in their city. Open the app in Berlin or anywhere in Germany and see what’s cheaper nearby and online — electronics at MediaMarkt, a shirt at Zara, everyday at Rossmann, the café on your street.",
    about2:
      "The map shows where the discount really is. Stores is a window-shopping feed. At home or out: one scan at the till, and the offer is yours. Saving should feel that simple.",
    about3:
      "For merchants, GoLuto is the other half of the same idea: add a branch, publish a deal, QR on the door. Customers find you without a stack of flyers.",
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

function onScroll() {
  if (!bar) return;
  const max = document.documentElement.scrollHeight - window.innerHeight;
  bar.style.width = `${max > 0 ? (window.scrollY / max) * 100 : 0}%`;
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
    { threshold: 0.15 },
  );
  document.querySelectorAll(".rise").forEach((el) => io.observe(el));

  const stack = document.querySelector(".stack");
  if (stack) {
    stack.addEventListener("pointermove", (event) => {
      const r = stack.getBoundingClientRect();
      const x = (event.clientX - r.left) / r.width - 0.5;
      const y = (event.clientY - r.top) / r.height - 0.5;
      stack.querySelectorAll(".device").forEach((shot, i) => {
        const d = (i + 1) * 8;
        shot.style.translate = `${x * d}px ${y * d - 0}px`;
      });
    });
  }
}

applyLang(localStorage.getItem("goluto-lang") || "de");

document.querySelectorAll(".store.is-soon").forEach((el) => {
  el.addEventListener("click", (event) => event.preventDefault());
});
