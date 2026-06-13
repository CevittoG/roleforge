import * as React from 'react';
import Head from 'next/head';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { GenerateForm, type SubmitPayload } from '@/components/GenerateForm';
import { ProgressPanel } from '@/components/ProgressPanel';
import { ResultPanel } from '@/components/ResultPanel';
import { DuplicateDialog } from '@/components/DuplicateDialog';
import { ApiError, startGenerate } from '@/lib/api';
import { useJobPoll } from '@/lib/useJobPoll';
import {
  clearActiveJob,
  clearDraft,
  loadActiveJob,
  loadDraft,
  loadProvider,
  saveActiveJob,
  saveDraft,
  type Draft,
} from '@/lib/storage';
import type { ApplicationSummary } from '@/lib/types';

const EMPTY_DRAFT: Draft = { jd_text: '', application_questions: '' };

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
  | { kind: 'done'; application: ApplicationSummary; hadQuestions: boolean };

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
  useJobPoll(activeJobId, {
    onDone: (application) => {
      // Did this run include application questions? Prefer the in-memory
      // payload; fall back to the persisted flag for jobs resumed after a
      // reload. Read before clearing the active job.
      const hadQuestions = lastPayloadRef.current
        ? lastPayloadRef.current.application_questions.trim().length > 0
        : (loadActiveJob()?.had_questions ?? false);
      clearActiveJob();
      clearDraft();
      setPhase({ kind: 'done', application, hadQuestions });
    },
    onDuplicate: (existing, job) => {
      clearActiveJob();
      setPhase({
        kind: 'duplicate',
        jobId: job.job_id,
        existing,
        payload: lastPayloadRef.current,
      });
    },
    onError: (message, job) => {
      clearActiveJob();
      setError(
        job?.error_record
          ? `Generation failed (${message}). We saved a record to your History — you can re-generate it from there.`
          : message,
      );
      setPhase({ kind: 'idle' });
    },
  });

  async function startJob(payload: SubmitPayload, confirmOverwrite: boolean): Promise<void> {
    setError(null);
    lastPayloadRef.current = payload;
    try {
      const res = await startGenerate({ ...payload, confirm_overwrite: confirmOverwrite });
      saveActiveJob({
        job_id: res.job_id,
        created_at: Date.now(),
        had_questions: payload.application_questions.trim().length > 0,
      });
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
  // The provider for the running job: the one we submitted, or — if the job was
  // resumed from localStorage after a reload — the last persisted choice.
  const inFlightProvider = lastPayloadRef.current?.provider ?? loadProvider('anthropic');
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
            Paste a job description — and any application questions — and we&apos;ll tailor
            your resume, cover letter, and match report, then save them to Drive.
          </p>
        </div>

        {error ? (
          <Alert tone="destructive">
            <AlertTitle>Something went wrong</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {phase.kind === 'done' ? (
          <ResultPanel
            application={phase.application}
            hasApplicationQuestions={phase.hadQuestions}
            onReset={handleReset}
          />
        ) : (
          <>
            <GenerateForm
              draft={draft}
              onDraftChange={setDraft}
              onSubmit={handleSubmit}
              disabled={inFlight}
            />
            {inFlight ? <ProgressPanel provider={inFlightProvider} /> : null}
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
