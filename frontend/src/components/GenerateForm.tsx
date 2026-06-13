import * as React from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { ProviderToggle } from '@/components/ProviderToggle';
import { useLlmConfig, useProviderSelection } from '@/lib/config';
import type { Draft } from '@/lib/storage';
import type { LlmProvider } from '@/lib/types';

export type SubmitPayload = { jd_text: string; provider: LlmProvider };

const MAX_JD_CHARS = 250_000;

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
  const { providers, defaultProvider } = useLlmConfig();
  const [provider, setProvider] = useProviderSelection(providers, defaultProvider);

  function setText(jd_text: string) {
    onDraftChange({ ...draft, jd_text });
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
    setSubmitError(null);
    onSubmit({ jd_text: text, provider });
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
