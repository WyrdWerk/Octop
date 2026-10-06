import { useEffect, useState } from "react";
import { octopSettingsApi } from "../../../api/modules/settings";

/**
 * Channel kinds the deployment offers (``OCTOP_CHANNEL_ALLOWLIST`` on the
 * server). ``undefined`` until loaded (callers fall back to the global
 * default set), ``null`` when every kind is allowed.
 */
export function useAllowedChannelKinds(): string[] | null | undefined {
  const [allowed, setAllowed] = useState<string[] | null | undefined>(
    undefined,
  );

  useEffect(() => {
    let cancelled = false;
    octopSettingsApi
      .capabilities()
      .then((data) => {
        if (cancelled) return;
        setAllowed(
          data.channel_kinds === undefined ? undefined : data.channel_kinds,
        );
      })
      .catch(() => {
        // Keep the built-in global default on failure.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return allowed;
}
