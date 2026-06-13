import * as React from 'react';
import { Download, Loader2, MessageSquareText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { ProviderToggle } from '@/components/ProviderToggle';
import { ApiError, downloadUrl, generateApplicationAnswers } from '@/lib/api';
import { useLlmConfig, useProviderSelection } from '@/lib/config';
import { DOWNLOAD_LABELS } from '@/lib/types';

const linkClasses =
  'inline-flex min-h-touch items-center justify-between gap-3 rounded-md border border-border ' +
  'bg-background px-4 py-2 text-sm font-medium shadow-sm transition hover:bg-muted active:bg-muted/70 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

type State = 'idle' | 'working' | 'ready';

/**
 * On-demand application-question answering for an already-generated application
 * (the case where questions surface after the main run). Paste the questions,
 * generate, then download Application_Questions.docx. Regenerating overwrites.
 */
export function ApplicationQuestionsPanel({
  folderId,
  role,
  date,
}: {
  folderId: string;
  role?: string;
  date?: string;
}) {
  const [questions, setQuestions] = React.useState('');
  const [state, setState] = React.useState<State>('idle');
  const [error, setError] = React.useState<string | null>(null);
  const { providers, defaultProvider } = useLlmConfig();
  const [provider, setProvider] = useProviderSelection(providers, defaultProvider);

  React.useEffect(() => {
    setQuestions('');
    setState('idle');
    setError(null);
  }, [folderId]);

  async function run() {
    const text = questions.trim();
    if (!text) {
      setError('Paste the application questions first.');
      return;
    }
    setState('working');
    setError(null);
    try {
      await generateApplicationAnswers(folderId, text, provider);
      setState('ready');
    } catch (err) {
      setState('idle');
      setError(
        err instanceof ApiError ? err.message : 'Could not generate answers. Try again.',
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

  return (
    <div className="flex flex-col gap-2">
      <div className="space-y-1.5">
        <Label htmlFor={`app-questions-${folderId}`}>Application questions</Label>
        <Textarea
          id={`app-questions-${folderId}`}
          value={questions}
          onChange={(e) => setQuestions(e.target.value)}
          placeholder="Paste the form's questions, one per line. Include any word limits (e.g. 'max 150 words')."
          rows={4}
          disabled={state === 'working'}
          spellCheck={false}
        />
      </div>
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
            <MessageSquareText className="h-4 w-4" aria-hidden="true" />
            {state === 'ready' ? 'Regenerate answers' : 'Generate answers'}
          </>
        )}
      </Button>
      {state === 'ready' ? (
        <a href={downloadUrl(folderId, 'application_questions', role, date)} className={linkClasses}>
          <span>{DOWNLOAD_LABELS.application_questions}</span>
          <Download className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </a>
      ) : null}
      {error ? (
        <p className="text-xs text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
