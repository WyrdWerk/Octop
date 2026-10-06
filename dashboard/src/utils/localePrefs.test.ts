import { afterEach, describe, expect, it, vi } from "vitest";
import {
  detectBrowserLocale,
  normalizeUiLocale,
  readStoredUiLocale,
  resolveInitialLocale,
  resolveUserLocale,
  speechLocaleFromUi,
  storeUiLocale,
  UI_LOCALE_STORAGE_KEY,
} from "./localePrefs";

describe("localePrefs", () => {
  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("detectBrowserLocale prefers zh when browser lists Chinese first", () => {
    vi.stubGlobal("navigator", {
      language: "en-US",
      languages: ["zh-CN", "en-US"],
    });
    expect(detectBrowserLocale()).toBe("zh");
  });

  it("detectBrowserLocale prefers en when browser lists English first", () => {
    vi.stubGlobal("navigator", {
      language: "zh-CN",
      languages: ["en-US", "zh-CN"],
    });
    expect(detectBrowserLocale()).toBe("en");
  });

  it("detectBrowserLocale defaults to en for other languages", () => {
    vi.stubGlobal("navigator", {
      language: "fr-FR",
      languages: ["fr-FR", "de-DE"],
    });
    expect(detectBrowserLocale()).toBe("en");
  });

  it("normalizeUiLocale falls back to en", () => {
    expect(normalizeUiLocale(null)).toBe("en");
    expect(normalizeUiLocale(undefined)).toBe("en");
    expect(normalizeUiLocale("")).toBe("en");
    expect(normalizeUiLocale("fr")).toBe("en");
    expect(normalizeUiLocale("zh-CN")).toBe("zh");
  });

  it("resolveInitialLocale ignores a non-explicit stored locale", () => {
    vi.stubGlobal("navigator", {
      language: "en-US",
      languages: ["en-US"],
    });
    storeUiLocale("zh");
    expect(readStoredUiLocale()).toBe("zh");
    expect(resolveInitialLocale()).toBe("en");
  });

  it("resolveInitialLocale uses explicit preference over browser", () => {
    vi.stubGlobal("navigator", {
      language: "en-US",
      languages: ["en-US"],
    });
    storeUiLocale("zh", { explicit: true });
    expect(resolveInitialLocale()).toBe("zh");
    expect(readStoredUiLocale()).toBe("zh");
    localStorage.removeItem(UI_LOCALE_STORAGE_KEY);
    expect(resolveInitialLocale()).toBe("en");
  });

  it("speechLocaleFromUi maps UI locale to STT BCP-47 tags", () => {
    expect(speechLocaleFromUi("zh")).toBe("zh-CN");
    expect(speechLocaleFromUi("zh-CN")).toBe("zh-CN");
    expect(speechLocaleFromUi("en")).toBe("en-US");
    expect(speechLocaleFromUi("en-US")).toBe("en-US");
    expect(speechLocaleFromUi(null)).toBe("en-US");
  });

  it("resolveUserLocale does not let the server zh default force Chinese", () => {
    vi.stubGlobal("navigator", {
      language: "en-US",
      languages: ["en-US"],
    });
    expect(resolveUserLocale("zh")).toBe("en");
    expect(resolveUserLocale(null)).toBe("en");
    expect(resolveUserLocale("en")).toBe("en");
  });

  it("resolveUserLocale honors server zh for Chinese browsers", () => {
    vi.stubGlobal("navigator", {
      language: "zh-CN",
      languages: ["zh-CN"],
    });
    expect(resolveUserLocale("zh")).toBe("zh");
    expect(resolveUserLocale("en")).toBe("en");
  });

  it("resolveUserLocale honors an explicit zh pick", () => {
    vi.stubGlobal("navigator", {
      language: "en-US",
      languages: ["en-US"],
    });
    storeUiLocale("zh", { explicit: true });
    expect(resolveUserLocale("zh")).toBe("zh");
  });
});
