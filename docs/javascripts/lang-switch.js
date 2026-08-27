/**
 * Selettore lingua: mantiene la pagina corrente quando si passa it ↔ en.
 *
 * Zensical non supporta (ancora) la mappatura pagina→traduzione di
 * mkdocs-static-i18n: i link di extra.alternate puntano alle radici
 * (/service-app/ e /service-app/en/). Questo script riscrive gli href con il
 * percorso della pagina corrente, sfruttando la struttura speculare
 * docs/ ↔ docs/en/.
 *
 * La riscrittura avviene al click (delegazione in cattura su document) e non
 * al load: il tema naviga client-side (document$), quindi gli href nel DOM
 * possono essere stanchi, ma il click viene sempre risolto con l'URL attuale.
 *
 * Da rimuovere quando Zensical implementerà l'i18n nativo
 * (https://github.com/zensical/backlog/issues/1).
 */
(function () {
  "use strict";

  var BASE = "/service-app/";
  var EN_PREFIX = BASE + "en/";

  function relPath() {
    var path = window.location.pathname;
    var isEn = path.indexOf(EN_PREFIX) === 0;
    // Percorso della pagina senza la parte di lingua ("" per la home).
    var rel = isEn ? path.slice(EN_PREFIX.length) : path.slice(BASE.length);
    return rel.replace(/(^|\/)index\.html$/, "$1");
  }

  function switchHref(lang) {
    return (lang === "en" ? EN_PREFIX : BASE) + relPath();
  }

  // Click sul selettore: riscrivi la destinazione usando l'URL corrente.
  document.addEventListener(
    "click",
    function (ev) {
      var el = ev.target && ev.target.closest
        ? ev.target.closest("a.md-select__link[hreflang]")
        : null;
      if (!el) return;
      var lang = el.getAttribute("hreflang");
      if (lang !== "it" && lang !== "en") return;
      var href = switchHref(lang);
      ev.preventDefault();
      window.location.href = href;
    },
    true
  );

  // <link rel="alternate"> nel <head> (SEO): allineali al load iniziale e a
  // ogni navigazione client-side, se l'observable document$ è disponibile.
  function rewriteHead() {
    document
      .querySelectorAll("link[rel='alternate'][hreflang]")
      .forEach(function (el) {
        var lang = el.getAttribute("hreflang");
        if (lang === "it" || lang === "en") {
          el.setAttribute("href", switchHref(lang));
        }
      });
  }
  rewriteHead();
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(rewriteHead);
  }
})();