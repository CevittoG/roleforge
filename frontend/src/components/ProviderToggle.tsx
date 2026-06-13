import { cn } from '@/lib/cn';
import { PROVIDER_LABELS, type LlmProvider } from '@/lib/types';

/**
 * Segmented control for picking the LLM provider. Two options, both visible,
 * one tap — better than a dropdown on a phone. Renders nothing when there's
 * only one provider configured (the selector would be meaningless).
 */
export function ProviderToggle({
  providers,
  value,
  onChange,
  disabled,
}: {
  providers: LlmProvider[];
  value: LlmProvider;
  onChange: (provider: LlmProvider) => void;
  disabled?: boolean;
}) {
  if (providers.length < 2) return null;
  return (
    <div
      role="radiogroup"
      aria-label="LLM provider"
      className="inline-flex rounded-md border border-border bg-background p-0.5"
    >
      {providers.map((provider) => {
        const selected = provider === value;
        return (
          <button
            key={provider}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={() => onChange(provider)}
            className={cn(
              'min-h-touch rounded px-4 py-2 text-sm font-medium transition',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              'disabled:opacity-50 disabled:pointer-events-none',
              selected
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:bg-muted',
            )}
          >
            {PROVIDER_LABELS[provider]}
          </button>
        );
      })}
    </div>
  );
}
