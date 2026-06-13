import * as React from 'react';
import { Download, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ProviderToggle } from '@/components/ProviderToggle';
import { ApiError, downloadUrl, generateInterviewPrep } from '@/lib/api';
import { useLlmConfig, useProviderSelection } from '@/lib/config';
import { DOWNLOAD_LABELS } from '@/lib/types';

const linkClasses =
  'inline-flex min-h-touch items-center justify-between gap-3 rounded-md border border-border ' +
  'bg-background px-4 py-2 text-sm font-medium shadow-sm transition hover:bg-muted active:bg-muted/70 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

type State = 'idle' | 'working' | 'ready';

/**
 * Generates Interview_Prep.md on demand (it's kept out of the main generate run
 * to save tokens), then swaps to a download link. We can't know from the list
 * whether prep already exists, so we always start with the generate action;
 * regenerating is idempotent.
 */
export function InterviewPrepButton({ folderId }: { folderId: string }) {
  const [state, setState] = React.useState<State>('idle');
  const [error, setError] = React.useState<string | null>(null);
  const { providers, defaultProvider } = useLlmConfig();
  const [provider, setProvider] = useProviderSelection(providers, defaultProvider);

  React.useEffect(() => {
    setState('idle');
    setError(null);
  }, [folderId]);

  async function run() {
    setState('working');
    setError(null);
    try {
      await generateInterviewPrep(folderId, provider);
      setState('ready');
    } catch (err) {
      setState('idle');
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not generate interview prep. Try again.',
      );
    }
  }

  const toggle =
    providers.length > 1 ? (
      <ProviderToggle
        providers={providers}
        value={provider}
        onChange={setProvider}
        disabled={state === 'working'}
      />
    ) : null;

  if (state === 'ready') {
    return (
      <div className="flex flex-col gap-1.5">
        {toggle}
        <a href={downloadUrl(folderId, 'interview_prep')} className={linkClasses}>
          <span>{DOWNLOAD_LABELS.interview_prep}</span>
          <Download className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </a>
        <button
          type="button"
          onClick={() => void run()}
          className="self-start text-xs text-muted-foreground hover:underline"
        >
          Regenerate
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      {toggle}
      <Button
        variant="outline"
        className="w-full justify-center"
        disabled={state === 'working'}
        onClick={() => void run()}
      >
        {state === 'working' ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Generating… (~30s)
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            Generate Interview Prep
          </>
        )}
      </Button>
      {error ? (
        <p className="text-xs text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
