import { describe, expect, it } from "vitest";

import {
  groupPresets,
  isOverseasPreset,
  partitionCloudPresets,
} from "./presetUtils";
import type { ProviderPreset } from "./useProviders";

function preset(
  id: string,
  extra: Partial<ProviderPreset> = {},
): ProviderPreset {
  return {
    id,
    name: id,
    base_url: "",
    protocol: "openai",
    api_key_prefix: "",
    models: [],
    ...extra,
  };
}

describe("provider preset ordering", () => {
  it("lists OpenAI, Anthropic, OpenRouter and Gemini first", () => {
    const { ungrouped } = groupPresets([
      preset("deepseek"),
      preset("gemini"),
      preset("anthropic"),
      preset("mimo"),
      preset("openrouter"),
      preset("openai"),
    ]);
    expect(ungrouped.map((p) => p.id)).toEqual([
      "openai",
      "anthropic",
      "openrouter",
      "gemini",
      "deepseek",
      "mimo",
    ]);
  });

  it("features global presets and collapses China-region clouds", () => {
    expect(isOverseasPreset(preset("openai"))).toBe(false);
    expect(isOverseasPreset(preset("deepseek"))).toBe(true);
    const { featured, more } = partitionCloudPresets(
      [
        preset("openai"),
        preset("kimi-cn", { provider_group: "kimi" }),
        preset("kimi-intl", { provider_group: "kimi" }),
        preset("deepseek"),
      ],
      [],
    );
    expect(featured.ungrouped.map((p) => p.id)).toEqual(["openai"]);
    expect(more.grouped.map((g) => g.groupKey)).toEqual(["kimi"]);
    expect(more.ungrouped.map((p) => p.id)).toEqual(["deepseek"]);
  });

  it("keeps an already-configured China provider visible", () => {
    const { featured } = partitionCloudPresets(
      [preset("openai"), preset("deepseek", { name: "DeepSeek" })],
      [{ name: "DeepSeek" } as never],
    );
    expect(featured.ungrouped.map((p) => p.id)).toEqual(["openai", "deepseek"]);
  });
});
