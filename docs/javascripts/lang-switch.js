/**
 * Selettore lingua: mantiene la pagina corrente quando si passa it ↔ en.
 *
 * Zensical non supporta (ancora) la mappatura pagina→traduzione di
 * mkdocs-static-i18n: i link di extra.alternate puntano alle radici
 * (/service-app/ e /service-app/en/). Questo script riscrive gli href del
 * selettore e dei <link rel="alternate"> con il percorso della pagina
 * corrente, sfruttando la struttura speculare docs/ ↔ docs/en/.
 *
 * Da rimuovere quando Zensical implementerà l'i18n nativo
 * (https://github.com/zensical/backlog/issues/1).
 */
(function () {
  "use strict";

  var BASE = "/service-app/";
  var EN_PREFIX = BASE + "en/";

  var path = window.location.pathname;
  var isEn = path.indexOf(EN_PREFIX) === 0;
  // Percorso della pagina senza la parte di lingua ("" per la home).
  var rel = isEn ? path.slice(EN_PREFIX.length) : path.slice(BASE.length);
  // Rimuovi eventuale "index.html" finale.
  rel = rel.replace(/(^|\/)index\.html$/, "$1");

  function switchHref(lang) {
    return (lang === "en" ? EN_PREFIX : BASE) + rel;
  }

  // Link del selettore nel header + <link rel="alternate"> nel <head>.
  document.querySelectorAll("a.md-select__link[hreflang], link[rel='alternate'][hreflang]").forEach(function (el) {
    var lang = el.getAttribute("hreflang");
    if (lang === "it" || lang === "en") {
      el.setAttribute("href", switchHref(lang));
    }
  });
})();