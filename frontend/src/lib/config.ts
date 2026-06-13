import * as React from 'react';
import { getConfig } from './api';
import { loadProvider, saveProvider } from './storage';
import type { LlmProvider } from './types';

// Runtime config (which LLM providers are available + the default) is the same
// for the whole session, so fetch it once and share the promise across mounts.
let cachedConfig: Promise<{ providers: LlmProvider[]; defaultProvider: LlmProvider }> | null = null;

function fetchLlmConfig(): Promise<{ providers: LlmProvider[]; defaultProvider: LlmProvider }> {
  if (!cachedConfig) {
    cachedConfig = getConfig()
      .then((cfg) => ({
        providers: cfg.llm_providers,
        defaultProvider: cfg.default_llm_provider,
      }))
      .catch((err) => {
        // Don't poison the cache — let a later mount retry.
        cachedConfig = null;
        throw err;
      });
  }
  return cachedConfig;
}

/** Available LLM providers and the server's default. Empty until loaded; the
 * provider selector stays hidden while `providers.length < 2`. */
export function useLlmConfig(): { providers: LlmProvider[]; defaultProvider: LlmProvider } {
  const [providers, setProviders] = React.useState<LlmProvider[]>([]);
  const [defaultProvider, setDefaultProvider] = React.useState<LlmProvider>('anthropic');

  React.useEffect(() => {
    let active = true;
    fetchLlmConfig()
      .then((cfg) => {
        if (!active) return;
        setProviders(cfg.providers);
        setDefaultProvider(cfg.defaultProvider);
      })
      .catch(() => {
        // Best-effort: a failed config fetch just hides the selector.
      });
    return () => {
      active = false;
    };
  }, []);

  return { providers, defaultProvider };
}

/** The selected provider, seeded once from the persisted choice (clamped to
 * what's available) and persisted on change. Used by both the generate form and
 * the interview-prep button so the choice is shared. */
export function useProviderSelection(
  providers: LlmProvider[],
  defaultProvider: LlmProvider,
): [LlmProvider, (provider: LlmProvider) => void] {
  const [provider, setProviderState] = React.useState<LlmProvider>(defaultProvider);
  const seeded = React.useRef(false);

  React.useEffect(() => {
    if (seeded.current || providers.length === 0) return;
    seeded.current = true;
    const stored = loadProvider(defaultProvider);
    setProviderState(providers.includes(stored) ? stored : defaultProvider);
  }, [providers, defaultProvider]);

  const setProvider = React.useCallback((next: LlmProvider) => {
    setProviderState(next);
    saveProvider(next);
  }, []);

  return [provider, setProvider];
}
