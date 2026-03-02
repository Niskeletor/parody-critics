/**
 * i18n — Parody Critics internationalization
 *
 * Usage:
 *   t('key')              → translated string
 *   t('key', {name: 'X'}) → with interpolation: "Hello {{name}}" → "Hello X"
 *   i18n.setLanguage('en') → switch locale
 *   i18n.current           → active locale code ('es' | 'en')
 *
 * Locales live in /static/locales/{lang}.json
 * Language preference persists in localStorage.
 */

const i18n = (() => {
  const STORAGE_KEY = 'parody_critics_lang';
  const DEFAULT_LANG = 'es';
  const SUPPORTED = ['es', 'en'];

  let strings = {};
  let current = DEFAULT_LANG;

  function _get(key) {
    return key.split('.').reduce((obj, k) => obj?.[k], strings);
  }

  function t(key, vars = {}) {
    let str = _get(key);
    if (str === undefined) {
      console.warn(`[i18n] Missing key: "${key}" (lang: ${current})`);
      return key;
    }
    // Simple {{variable}} interpolation
    return str.replace(/\{\{(\w+)\}\}/g, (_, name) => vars[name] ?? `{{${name}}}`);
  }

  function _applyToDOM() {
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.dataset.i18n;
      const translation = _get(key);
      if (translation !== undefined) {
        el.textContent = translation;
      }
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      const key = el.dataset.i18nPlaceholder;
      const translation = _get(key);
      if (translation !== undefined) {
        el.placeholder = translation;
      }
    });
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      const key = el.dataset.i18nTitle;
      const translation = _get(key);
      if (translation !== undefined) {
        el.title = translation;
      }
    });
  }

  async function setLanguage(lang) {
    if (!SUPPORTED.includes(lang)) {
      console.warn(`[i18n] Unsupported language: "${lang}"`);
      return;
    }
    try {
      const res = await fetch(`/static/locales/${lang}.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      strings = await res.json();
      current = lang;
      localStorage.setItem(STORAGE_KEY, lang);
      document.documentElement.lang = lang;
      _applyToDOM();
    } catch (err) {
      console.error(`[i18n] Failed to load locale "${lang}":`, err);
    }
  }

  async function init() {
    const saved = localStorage.getItem(STORAGE_KEY);
    const lang = SUPPORTED.includes(saved) ? saved : DEFAULT_LANG;
    await setLanguage(lang);
  }

  return {
    t,
    setLanguage,
    init,
    get current() {
      return current;
    },
  };
})();

// Global shortcut
const t = i18n.t.bind(i18n);
