import * as React from 'react';
import Head from 'next/head';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { GenerateForm, type SubmitPayload } from '@/components/GenerateForm';
import { ProgressPanel } from '@/components/ProgressPanel';
import { ResultPanel } from '@/components/ResultPanel';
import { DuplicateDialog } from '@/components/DuplicateDialog';
import { ApiError, getJob, startGenerate } from '@/lib/api';
import {
  clearActiveJob,
  clearDraft,
  loadActiveJob,
  loadDraft,
  saveActiveJob,
  saveDraft,
  type Draft,
} from '@/lib/storage';
import type { ApplicationSummary } from '@/lib/types';

const EMPTY_DRAFT: Draft = { mode: 'text', jd_text: '', jd_url: '' };
const POLL_INTERVAL_MS = 2000;

type Phase =
  | { kind: 'idle' }
  | { kind: 'running'; jobId: string }
  | { kind: 'duplicate'; jobId: string; existing: ApplicationSummary; payload: SubmitPayload | null }
  | {
      kind: 'overwriting';
      jobId: string;
      existing: ApplicationSummary;
      payload: SubmitPayload | null;
    }
  | { kind: 'done'; application: ApplicationSummary };

export default function GeneratePage() {
  const [draft, setDraft] = React.useState<Draft>(EMPTY_DRAFT);
  const [phase, setPhase] = React.useState<Phase>({ kind: 'idle' });
  const [error, setError] = React.useState<string | null>(null);
  // Keep the latest submit payload so confirm-overwrite can re-fire the same JD.
  const lastPayloadRef = React.useRef<SubmitPayload | null>(null);

  // Hydrate draft + resume any active job from localStorage on mount.
  React.useEffect(() => {
    setDraft(loadDraft());
    const active = loadActiveJob();
    if (active) {
      setPhase({ kind: 'running', jobId: active.job_id });
    }
  }, []);

  // Persist draft on every change unless we're showing a result.
  React.useEffect(() => {
    if (phase.kind !== 'done') saveDraft(draft);
  }, [draft, phase.kind]);

  // Poll the active job whenever there's a job in flight.
  const activeJobId =
    phase.kind === 'running' || phase.kind === 'duplicate' || phase.kind === 'overwriting'
      ? phase.jobId
      : null;
  React.useEffect(() => {
    const jobId = activeJobId;
    if (!jobId) return;

    let cancelled = false;
    let timeout: number | null = null;

    async function tick() {
      try {
        const job = await getJob(jobId!);
        if (cancelled) return;
        if (job.status === 'done' && job.application) {
          clearActiveJob();
          clearDraft();
          setPhase({ kind: 'done', application: job.application });
          return;
        }
        if (job.status === 'duplicate' && job.existing) {
          clearActiveJob();
          setPhase({
            kind: 'duplicate',
            jobId: job.job_id,
            existing: job.existing,
            payload: lastPayloadRef.current,
          });
          return;
        }
        if (job.status === 'error') {
          clearActiveJob();
          setError(job.error ?? 'Generation failed.');
          setPhase({ kind: 'idle' });
          return;
        }
        // queued or running — keep polling.
        timeout = window.setTimeout(tick, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          // The job vanished (server restart, TTL eviction). Reset.
          clearActiveJob();
          setError('We lost track of the running job — please try again.');
          setPhase({ kind: 'idle' });
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
  }, [activeJobId]);

  async function startJob(payload: SubmitPayload, confirmOverwrite: boolean): Promise<void> {
    setError(null);
    lastPayloadRef.current = payload;
    try {
      const res = await startGenerate({ ...payload, confirm_overwrite: confirmOverwrite });
      saveActiveJob({ job_id: res.job_id, created_at: Date.now() });
      setPhase({ kind: 'running', jobId: res.job_id });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Could not start generation.';
      setError(message);
      setPhase({ kind: 'idle' });
    }
  }

  function handleSubmit(payload: SubmitPayload) {
    void startJob(payload, false);
  }

  function handleConfirmOverwrite() {
    if (phase.kind !== 'duplicate') return;
    const { existing, payload } = phase;
    if (!payload) {
      setError('Could not resume after refresh — please paste the JD again.');
      setPhase({ kind: 'idle' });
      return;
    }
    setPhase({ kind: 'overwriting', jobId: phase.jobId, existing, payload });
    void startJob(payload, true);
  }

  function handleReset() {
    setError(null);
    setDraft(EMPTY_DRAFT);
    clearDraft();
    clearActiveJob();
    lastPayloadRef.current = null;
    setPhase({ kind: 'idle' });
  }

  const inFlight = phase.kind === 'running' || phase.kind === 'overwriting';
  const dialogExisting =
    phase.kind === 'duplicate' || phase.kind === 'overwriting' ? phase.existing : null;

  return (
    <>
      <Head>
        <title>Generate · Roleforge</title>
      </Head>
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Generate application</h1>
          <p className="text-sm text-muted-foreground">
            Paste a job description or URL. We&apos;ll tailor your resume, cover letter, and
            interview prep, and save them to Drive.
          </p>
        </div>

        {error ? (
          <Alert tone="destructive">
            <AlertTitle>Something went wrong</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {phase.kind === 'done' ? (
          <ResultPanel application={phase.application} onReset={handleReset} />
        ) : (
          <>
            <GenerateForm
              draft={draft}
              onDraftChange={setDraft}
              onSubmit={handleSubmit}
              disabled={inFlight}
            />
            {inFlight ? <ProgressPanel /> : null}
          </>
        )}

        <DuplicateDialog
          existing={dialogExisting}
          open={phase.kind === 'duplicate' || phase.kind === 'overwriting'}
          onOpenChange={(open) => {
            if (!open && phase.kind === 'duplicate') {
              setPhase({ kind: 'idle' });
            }
          }}
          onConfirm={handleConfirmOverwrite}
          pending={phase.kind === 'overwriting'}
        />
      </div>
    </>
  );
}
