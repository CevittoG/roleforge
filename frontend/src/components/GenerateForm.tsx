import * as React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import type { Draft } from '@/lib/storage';

export type SubmitPayload = { jd_text?: string; jd_url?: string };

const URL_RE = /^https?:\/\/\S+$/i;
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

  function setMode(mode: 'text' | 'url') {
    onDraftChange({ ...draft, mode });
    setSubmitError(null);
  }

  function setText(jd_text: string) {
    onDraftChange({ ...draft, jd_text });
  }

  function setUrl(jd_url: string) {
    onDraftChange({ ...draft, jd_url });
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (draft.mode === 'text') {
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
      onSubmit({ jd_text: text });
      return;
    }
    const url = draft.jd_url.trim();
    if (!URL_RE.test(url)) {
      setSubmitError('Enter a valid http(s) URL.');
      return;
    }
    setSubmitError(null);
    onSubmit({ jd_url: url });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <Tabs value={draft.mode} onValueChange={(v) => setMode(v as 'text' | 'url')}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="text">Paste JD</TabsTrigger>
          <TabsTrigger value="url">From URL</TabsTrigger>
        </TabsList>
        <TabsContent value="text" className="space-y-2">
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
        </TabsContent>
        <TabsContent value="url" className="space-y-2">
          <Label htmlFor="jd_url">Job posting URL</Label>
          <Input
            id="jd_url"
            type="url"
            value={draft.jd_url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://…"
            disabled={disabled}
            inputMode="url"
            autoCapitalize="off"
            autoCorrect="off"
            spellCheck={false}
          />
          <p className="text-xs text-muted-foreground">
            We&apos;ll fetch the page server-side. Some sites (LinkedIn, Workday) need paste mode.
          </p>
        </TabsContent>
      </Tabs>

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
