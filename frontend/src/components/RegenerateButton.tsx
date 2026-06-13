import * as React from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ProviderToggle } from '@/components/ProviderToggle';
import { ApiError, regenerateApplication } from '@/lib/api';
import { useLlmConfig, useProviderSelection } from '@/lib/config';
import { useJobPoll } from '@/lib/useJobPoll';

/**
 * One-click re-generate for a failed application. Enqueues a full generate job
 * (reusing the saved JD + questions) and polls it; on success the parent
 * re-fetches so the now-"Generated" record replaces the error state.
 */
export function RegenerateButton({
  folderId,
  onRegenerated,
}: {
  folderId: string;
  onRegenerated: () => void;
}) {
  const [jobId, setJobId] = React.useState<string | null>(null);
  const [enqueuing, setEnqueuing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const { providers, defaultProvider } = useLlmConfig();
  const [provider, setProvider] = useProviderSelection(providers, defaultProvider);

  // Reset when the modal switches to a different record.
  React.useEffect(() => {
    setJobId(null);
    setEnqueuing(false);
    setError(null);
  }, [folderId]);

  useJobPoll(jobId, {
    onDone: () => {
      setJobId(null);
      onRegenerated();
    },
    onError: (message) => {
      setJobId(null);
      setError(message);
    },
  });

  async function run() {
    setEnqueuing(true);
    setError(null);
    try {
      const res = await regenerateApplication(folderId, { provider });
      setJobId(res.job_id);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not start re-generation. Try again.',
      );
    } finally {
      setEnqueuing(false);
    }
  }

  const working = enqueuing || jobId != null;

  return (
    <div className="flex flex-col gap-1.5">
      {providers.length > 1 ? (
        <ProviderToggle
          providers={providers}
          value={provider}
          onChange={setProvider}
          disabled={working}
        />
      ) : null}
      <Button className="w-full justify-center" disabled={working} onClick={() => void run()}>
        {working ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Re-generating… (~30–90s)
          </>
        ) : (
          <>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Re-generate
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
