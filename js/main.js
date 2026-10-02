/**
 * XXIX Ciclo de Estudos Estratégicos
 *
 * Substitui o ScrollReveal (CDN, `reset: true`, delays de até 2s) por um
 * IntersectionObserver que revela cada elemento uma única vez.
 *
 * Opcional por design: as regras de animação em style.css ficam sob `.js`,
 * então sem este arquivo nenhum conteúdo fica invisível.
 */

(() => {
  "use strict";

  const prefersReducedMotion = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : { matches: false, addEventListener: null };

  /* ---- Voltar ao topo: aparece depois de uma certa rolagem ------------ */

  const toTop = document.querySelector("#voltar-para-o-topo");

  if (toTop) {
    let ticking = false;

    function onScroll() {
      toTop.classList.toggle("is-visible", window.scrollY > 600);
    }

    // requestAnimationFrame evita recalcular estilo a cada evento.
    window.addEventListener(
      "scroll",
      () => {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(() => {
          onScroll();
          ticking = false;
        });
      },
      { passive: true }
    );

    onScroll();

    toTop.addEventListener("click", () => {
      window.scrollTo({
        top: 0,
        behavior: prefersReducedMotion.matches ? "auto" : "smooth",
      });
    });
  }

  /* ---- Revelação por rolagem ----------------------------------------- */

  const revealables = document.querySelectorAll("[data-reveal]");

  const showAll = () => {
    revealables.forEach((el) => el.classList.add("is-visible"));
  };

  // Sem IntersectionObserver, ou com movimento reduzido, mostra tudo.
  if (!("IntersectionObserver" in window) || prefersReducedMotion.matches) {
    showAll();
    return;
  }

  const observer = new IntersectionObserver(
    (entries, obs) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        obs.unobserve(entry.target); // uma vez só: não some ao subir a página
      });
    },
    { rootMargin: "0px 0px -10% 0px", threshold: 0.08 }
  );

  revealables.forEach((el) => observer.observe(el));

  // Se a preferência mudar no meio da sessão, revela o que faltou.
  if (prefersReducedMotion.addEventListener) {
    prefersReducedMotion.addEventListener("change", (event) => {
      if (event.matches) showAll();
    });
  }
})();
