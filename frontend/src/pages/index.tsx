import * as React from 'react';
import Head from 'next/head';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { GenerateForm, type SubmitPayload } from '@/components/GenerateForm';
import { ProgressPanel } from '@/components/ProgressPanel';
import { ResultPanel } from '@/components/ResultPanel';
import { DuplicateDialog } from '@/components/DuplicateDialog';
import { ApiError, DuplicateError, generate } from '@/lib/api';
import { clearDraft, loadDraft, saveDraft, type Draft } from '@/lib/storage';
import type { ApplicationSummary } from '@/lib/types';

const EMPTY_DRAFT: Draft = { mode: 'text', jd_text: '', jd_url: '' };

type Phase =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'duplicate'; existing: ApplicationSummary; payload: SubmitPayload }
  | { kind: 'overwriting'; existing: ApplicationSummary; payload: SubmitPayload }
  | { kind: 'done'; application: ApplicationSummary };

export default function GeneratePage() {
  const [draft, setDraft] = React.useState<Draft>(EMPTY_DRAFT);
  const [phase, setPhase] = React.useState<Phase>({ kind: 'idle' });
  const [error, setError] = React.useState<string | null>(null);

  // Hydrate draft from localStorage on mount (avoids SSR/CSR mismatch by not
  // touching window during render).
  React.useEffect(() => {
    setDraft(loadDraft());
  }, []);

  // Persist on every change once hydrated.
  React.useEffect(() => {
    if (phase.kind !== 'done') saveDraft(draft);
  }, [draft, phase.kind]);

  async function runGenerate(payload: SubmitPayload, confirmOverwrite: boolean) {
    setError(null);
    try {
      const application = await generate({ ...payload, confirm_overwrite: confirmOverwrite });
      clearDraft();
      setPhase({ kind: 'done', application });
    } catch (err) {
      if (err instanceof DuplicateError) {
        setPhase({ kind: 'duplicate', existing: err.existing, payload });
        return;
      }
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Generation failed. Please try again.');
      }
      setPhase({ kind: 'idle' });
    }
  }

  function handleSubmit(payload: SubmitPayload) {
    setPhase({ kind: 'submitting' });
    void runGenerate(payload, false);
  }

  function handleConfirmOverwrite() {
    if (phase.kind !== 'duplicate') return;
    const { existing, payload } = phase;
    setPhase({ kind: 'overwriting', existing, payload });
    void runGenerate(payload, true);
  }

  function handleReset() {
    setError(null);
    setDraft(EMPTY_DRAFT);
    clearDraft();
    setPhase({ kind: 'idle' });
  }

  const inFlight = phase.kind === 'submitting' || phase.kind === 'overwriting';
  const existing =
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
          existing={existing}
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
