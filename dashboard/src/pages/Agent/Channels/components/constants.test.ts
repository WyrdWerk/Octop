import { describe, expect, it } from "vitest";

import {
  applyQqChannelSaveConfig,
  DEFAULT_QQ_GROUP_CONTEXT_CONFIG,
  normalizeQqGroupContextConfig,
  partitionChannelKeys,
  filterAllowedChannelKeys,
  DEFAULT_ALLOWED_CHANNEL_KEYS,
  CHANNEL_KEYS,
  CHANNEL_FIELDS,
  normalizeChannelFieldValue,
} from "./constants";

describe("Discord configuration", () => {
  it("features Discord by default and keeps its credential fields", () => {
    expect(CHANNEL_KEYS).toContain("discord");
    expect(partitionChannelKeys(["discord"], new Set()).featured).toEqual([
      "discord",
    ]);
    expect(
      CHANNEL_FIELDS.discord?.find((f) => f.name === "bot_token"),
    ).toMatchObject({ required: true, type: "password" });
    expect(
      CHANNEL_FIELDS.discord?.find((f) => f.name === "http_proxy_auth"),
    ).toMatchObject({ type: "password" });
  });

  it("preserves snowflake IDs exactly and validates user input", () => {
    expect(
      normalizeChannelFieldValue(
        "allowed_channel_ids",
        "1234567890123456789, 2345678901234567890\n1234567890123456789",
      ),
    ).toEqual(["1234567890123456789", "2345678901234567890"]);
    expect(normalizeChannelFieldValue("allowed_user_ids", "")).toEqual([]);
    expect(normalizeChannelFieldValue("allowed_user_ids", ["123"])).toEqual([
      "123",
    ]);
    expect(() =>
      normalizeChannelFieldValue("allowed_channel_ids", "#general"),
    ).toThrow();
  });
});

describe("partitionChannelKeys", () => {
  it("collapses China-only kinds until expanded unless already configured", () => {
    expect(
      partitionChannelKeys(["weixin", "telegram", "mqtt"], new Set()),
    ).toEqual({
      featured: ["telegram", "mqtt"],
      more: ["weixin"],
    });
    expect(
      partitionChannelKeys(["weixin", "telegram", "mqtt"], new Set(["weixin"])),
    ).toEqual({
      featured: ["weixin", "telegram", "mqtt"],
      more: [],
    });
  });
});

describe("filterAllowedChannelKeys", () => {
  it("defaults to the global channel set", () => {
    expect(filterAllowedChannelKeys(CHANNEL_KEYS, undefined)).toEqual([
      ...DEFAULT_ALLOWED_CHANNEL_KEYS,
    ]);
  });

  it("honours the server allowlist and keeps configured kinds", () => {
    expect(
      filterAllowedChannelKeys(CHANNEL_KEYS, ["telegram"], new Set(["qq"])),
    ).toEqual(["telegram", "qq"]);
    expect(filterAllowedChannelKeys(CHANNEL_KEYS, null)).toEqual(CHANNEL_KEYS);
  });
});

describe("applyQqChannelSaveConfig", () => {
  it("only rewrites QQ delivery keys", () => {
    const weixin = { response_mode: "invoke", show_progress: true };
    applyQqChannelSaveConfig(weixin, "weixin");
    expect(weixin).toEqual({ response_mode: "invoke", show_progress: true });

    const qq = { streaming: false, show_progress: true, token: "t" };
    applyQqChannelSaveConfig(qq, "qq");
    expect(qq).toEqual({ token: "t", c2c_streaming: true });
  });
});

describe("normalizeQqGroupContextConfig", () => {
  it("uses safe QQ group defaults for missing config", () => {
    expect(normalizeQqGroupContextConfig(undefined)).toEqual(
      DEFAULT_QQ_GROUP_CONTEXT_CONFIG,
    );
  });

  it("accepts JSON values left by older channel form drafts", () => {
    expect(
      normalizeQqGroupContextConfig(
        '{"enabled":true,"visibility":"mention_recent","history_limit":20}',
      ),
    ).toMatchObject({
      enabled: true,
      visibility: "mention_recent",
      activation: "mention",
      history: "recent",
      history_limit: 20,
    });
  });

  it("forces mention-only visibility to discard passive history", () => {
    expect(
      normalizeQqGroupContextConfig({
        visibility: "mention_only",
        activation: "always",
        history: "recent",
      }),
    ).toMatchObject({
      visibility: "mention_only",
      activation: "mention",
      history: "none",
    });
  });

  it("keeps active replies and per-group overrides with full visibility", () => {
    const groups = {
      "group-1": { activation: "mention", history_limit: 5 },
    };
    expect(
      normalizeQqGroupContextConfig({
        visibility: "all",
        activation: "always",
        history: "recent",
        history_limit: 25,
        groups,
      }),
    ).toMatchObject({
      visibility: "all",
      activation: "always",
      history_limit: 25,
      groups,
    });
  });
});
