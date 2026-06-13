import * as React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { ProviderToggle } from '@/components/ProviderToggle';
import { useLlmConfig, useProviderSelection } from '@/lib/config';
import type { Draft } from '@/lib/storage';
import type { LlmProvider } from '@/lib/types';

export type SubmitPayload = {
  jd_text: string;
  provider: LlmProvider;
  application_questions: string;
};

const MAX_JD_CHARS = 250_000;
const MAX_QUESTIONS_CHARS = 10_000;

export function GenerateForm({
  draft,
  onDraftChange,
  onSubmit,
  disabled,
}: {
  draft: Draft;
  onDraftChange: (draft: Draft) => void;
  onSubmit: (payload: SubmitPayload) => void;
  disabled: boolean;
}) {
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  // Open the optional section if a restored draft already has questions.
  const [showQuestions, setShowQuestions] = React.useState(
    () => draft.application_questions.trim().length > 0,
  );
  const { providers, defaultProvider } = useLlmConfig();
  const [provider, setProvider] = useProviderSelection(providers, defaultProvider);

  function setText(jd_text: string) {
    onDraftChange({ ...draft, jd_text });
  }

  function setQuestions(application_questions: string) {
    onDraftChange({ ...draft, application_questions });
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const text = draft.jd_text.trim();
    if (!text) {
      setSubmitError('Paste the job description before generating.');
      return;
    }
    if (text.length > MAX_JD_CHARS) {
      setSubmitError(`Job description is too long (${text.length.toLocaleString()} chars).`);
      return;
    }
    const questions = draft.application_questions.trim();
    if (questions.length > MAX_QUESTIONS_CHARS) {
      setSubmitError(`Application questions are too long (${questions.length.toLocaleString()} chars).`);
      return;
    }
    setSubmitError(null);
    onSubmit({ jd_text: text, provider, application_questions: questions });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <div className="space-y-2">
        <Label htmlFor="jd_text">Job description</Label>
        <Textarea
          id="jd_text"
          value={draft.jd_text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste the full job description here…"
          rows={12}
          disabled={disabled}
          spellCheck={false}
          autoComplete="off"
        />
        <p className="text-xs text-muted-foreground">
          {draft.jd_text.length.toLocaleString()} / {MAX_JD_CHARS.toLocaleString()} chars
        </p>
      </div>

      <div className="space-y-2">
        <button
          type="button"
          onClick={() => setShowQuestions((v) => !v)}
          aria-expanded={showQuestions}
          aria-controls="application_questions"
          disabled={disabled}
          className="inline-flex min-h-touch items-center gap-1.5 text-sm font-medium text-foreground hover:text-primary disabled:opacity-50"
        >
          {showQuestions ? (
            <ChevronDown className="h-4 w-4" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          )}
          Application questions
          <span className="font-normal text-muted-foreground">(optional)</span>
        </button>
        {showQuestions ? (
          <div className="space-y-1.5">
            <Textarea
              id="application_questions"
              value={draft.application_questions}
              onChange={(e) => setQuestions(e.target.value)}
              placeholder="Paste any follow-up questions from the application form, one per line. Include word limits (e.g. 'max 150 words') and they'll be respected."
              rows={5}
              disabled={disabled}
              spellCheck={false}
              autoComplete="off"
            />
            <p className="text-xs text-muted-foreground">
              Answered in the same run, grounded in your experience docs — no extra wait.
            </p>
          </div>
        ) : null}
      </div>

      {providers.length > 1 ? (
        <div className="space-y-2">
          <Label htmlFor="provider-toggle">Model</Label>
          <ProviderToggle
            providers={providers}
            value={provider}
            onChange={setProvider}
            disabled={disabled}
          />
        </div>
      ) : null}

      {submitError ? (
        <p className="text-sm text-destructive" role="alert">
          {submitError}
        </p>
      ) : null}

      <Button type="submit" size="lg" className="w-full" disabled={disabled}>
        Generate application
      </Button>
    </form>
  );
}
