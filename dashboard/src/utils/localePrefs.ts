export type UiLocale = "zh" | "en";

export const UI_LOCALE_STORAGE_KEY = "octop:ui-locale";

/** Map browser language tags to a supported dashboard locale. */
export function detectBrowserLocale(): UiLocale {
  if (typeof navigator === "undefined") return "en";

  const candidates =
    navigator.languages?.length > 0
      ? navigator.languages
      : [navigator.language];

  for (const raw of candidates) {
    const lang = raw?.toLowerCase() ?? "";
    if (lang.startsWith("zh")) return "zh";
    if (lang.startsWith("en")) return "en";
  }

  const primary = navigator.language?.toLowerCase() ?? "";
  if (primary.startsWith("zh")) return "zh";
  if (primary.startsWith("en")) return "en";

  return "en";
}

/** Unknown / missing values fall back to English (global default). */
export function normalizeUiLocale(raw: string | null | undefined): UiLocale {
  if (!raw) return "en";
  return raw.toLowerCase().startsWith("zh") ? "zh" : "en";
}

export function readStoredUiLocale(): UiLocale | null {
  try {
    const raw = localStorage.getItem(UI_LOCALE_STORAGE_KEY);
    if (raw === "zh" || raw === "en") return raw;
  } catch {
    // localStorage unavailable
  }
  return null;
}

/** Set to "1" once the user picks a language themselves (switcher / setup). */
export const UI_LOCALE_EXPLICIT_KEY = "octop-ui-locale-explicit";

/**
 * Persist the active UI locale. Pass ``explicit: true`` only when the user
 * chose the language themselves, so later server defaults cannot override it.
 */
export function storeUiLocale(
  locale: UiLocale,
  opts?: { explicit?: boolean },
): void {
  try {
    localStorage.setItem(UI_LOCALE_STORAGE_KEY, locale);
    if (opts?.explicit) localStorage.setItem(UI_LOCALE_EXPLICIT_KEY, "1");
  } catch {
    // quota / disabled
  }
}

/** Stored locale, but only when the user explicitly picked it. */
export function readExplicitUiLocale(): UiLocale | null {
  try {
    if (localStorage.getItem(UI_LOCALE_EXPLICIT_KEY) !== "1") return null;
  } catch {
    return null;
  }
  return readStoredUiLocale();
}

/** Explicit user pick wins; otherwise follow the browser (default English). */
export function resolveInitialLocale(): UiLocale {
  return readExplicitUiLocale() ?? detectBrowserLocale();
}

/**
 * Resolve the UI locale after login from the server-stored user locale.
 *
 * The server defaults new users to ``zh``, so a server ``zh`` is ambiguous
 * (default vs. deliberate). It is honored only when the user explicitly
 * picked Chinese on this device or the browser prefers Chinese; otherwise the
 * explicit/browser preference (default English) wins. A server ``en`` is
 * never a default and is always honored.
 */
export function resolveUserLocale(raw: string | null | undefined): UiLocale {
  const server = normalizeUiLocale(raw);
  if (server === "en") return "en";
  return readExplicitUiLocale() ?? detectBrowserLocale();
}

export function syncDocumentLang(locale: UiLocale): void {
  if (typeof document === "undefined") return;
  document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
}

/** BCP-47 tag for STT / SpeechRecognition from dashboard UI locale. */
export function speechLocaleFromUi(locale: string | null | undefined): string {
  return normalizeUiLocale(locale) === "zh" ? "zh-CN" : "en-US";
}
