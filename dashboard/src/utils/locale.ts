import i18n, { ensureLocaleBundle } from "../i18n";
import {
  normalizeUiLocale,
  resolveInitialLocale,
  resolveUserLocale,
  storeUiLocale,
  syncDocumentLang,
  type UiLocale,
} from "./localePrefs";

export type { UiLocale };
export {
  detectBrowserLocale,
  normalizeUiLocale,
  readExplicitUiLocale,
  readStoredUiLocale,
  resolveInitialLocale,
  resolveUserLocale,
  storeUiLocale,
  syncDocumentLang,
  UI_LOCALE_EXPLICIT_KEY,
  UI_LOCALE_STORAGE_KEY,
} from "./localePrefs";

/**
 * Apply the server-stored user locale to the dashboard i18n instance.
 *
 * ``explicit: true`` means the user just picked this language (switcher /
 * settings), so it is applied verbatim and remembered. Otherwise (login /
 * session restore) the server value goes through ``resolveUserLocale`` so the
 * server's ``zh`` default does not force Chinese on English-speaking users.
 */
export async function applyUserLocale(
  raw: string | null | undefined,
  opts?: { explicit?: boolean },
): Promise<UiLocale> {
  const lang = opts?.explicit ? normalizeUiLocale(raw) : resolveUserLocale(raw);
  storeUiLocale(lang, { explicit: opts?.explicit });
  await ensureLocaleBundle(lang);
  if (i18n.language !== lang) {
    await i18n.changeLanguage(lang);
  }
  syncDocumentLang(lang);
  return lang;
}

/** Guest surfaces (login / post-logout): stored preference or browser locale. */
export async function applyGuestLocale(): Promise<UiLocale> {
  const lang = resolveInitialLocale();
  storeUiLocale(lang);
  await ensureLocaleBundle(lang);
  if (i18n.language !== lang) {
    await i18n.changeLanguage(lang);
  }
  syncDocumentLang(lang);
  return lang;
}
