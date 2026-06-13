import * as React from 'react';
import { ApiError, getJob } from '@/lib/api';
import type { ApplicationSummary, JobResponse } from '@/lib/types';

const POLL_INTERVAL_MS = 2000;

export type JobPollHandlers = {
  onDone: (application: ApplicationSummary, job: JobResponse) => void;
  onError: (message: string, job: JobResponse | null) => void;
  // Only generate produces 'duplicate'; if omitted it's surfaced via onError.
  onDuplicate?: (existing: ApplicationSummary, job: JobResponse) => void;
};

/**
 * Poll GET /api/jobs/{id} every 2s until it terminates, then invoke the matching
 * handler exactly once. Transient network blips retry silently; a 404 (job
 * evicted / server restart) ends polling via onError. Pass jobId=null to idle.
 *
 * Handlers are read through a ref, so passing fresh closures each render is
 * fine — the effect only re-subscribes when jobId changes.
 */
export function useJobPoll(jobId: string | null, handlers: JobPollHandlers): void {
  const handlersRef = React.useRef(handlers);
  handlersRef.current = handlers;

  React.useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    let timeout: number | null = null;

    async function tick() {
      try {
        const job = await getJob(jobId!);
        if (cancelled) return;
        const h = handlersRef.current;
        if (job.status === 'done' && job.application) {
          h.onDone(job.application, job);
          return;
        }
        if (job.status === 'duplicate' && job.existing) {
          if (h.onDuplicate) h.onDuplicate(job.existing, job);
          else h.onError('A matching application already exists.', job);
          return;
        }
        if (job.status === 'error') {
          h.onError(job.error ?? 'Generation failed.', job);
          return;
        }
        // queued or running — keep polling.
        timeout = window.setTimeout(tick, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          handlersRef.current.onError(
            'We lost track of the running job — please try again.',
            null,
          );
          return;
        }
        // Transient network blip — retry on the next tick.
        timeout = window.setTimeout(tick, POLL_INTERVAL_MS);
      }
    }

    void tick();
    return () => {
      cancelled = true;
      if (timeout !== null) window.clearTimeout(timeout);
    };
  }, [jobId]);
}
