import * as React from 'react';
import { CheckCircle2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/cn';

// Phased pseudo-progress. The backend runs these steps in this order. Timings
// are rough medians (seconds) and the last phase intentionally lingers, since
// it's the most variable and the label ("Saving to Drive…") is plausible for
// any tail of the request.
const PHASES = [
  { label: 'Reading job description…', durationMs: 3_000 },
  { label: 'Calling Claude…', durationMs: 35_000 },
  { label: 'Rendering PDFs…', durationMs: 6_000 },
  { label: 'Saving to Drive…', durationMs: 20_000 },
] as const;

export function ProgressPanel() {
  const [phase, setPhase] = React.useState(0);
  const [elapsed, setElapsed] = React.useState(0);

  React.useEffect(() => {
    const start = performance.now();
    const tick = () => {
      const ms = performance.now() - start;
      setElapsed(ms);
      let acc = 0;
      let next = PHASES.length - 1;
      for (let i = 0; i < PHASES.length; i += 1) {
        acc += PHASES[i].durationMs;
        if (ms < acc) {
          next = i;
          break;
        }
      }
      setPhase(next);
    };
    const id = window.setInterval(tick, 250);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="rounded-lg border border-border bg-muted/40 p-5">
      <div className="mb-4 flex items-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium">Generating your application</p>
          <p className="text-xs text-muted-foreground">
            This usually takes 30–90 seconds. Keep this tab open.
          </p>
        </div>
      </div>
      <ol className="space-y-2" aria-live="polite">
        {PHASES.map((p, i) => {
          const done = i < phase;
          const active = i === phase;
          return (
            <li key={p.label} className="flex items-center gap-2 text-sm">
              {done ? (
                <CheckCircle2
                  className="h-4 w-4 text-success"
                  aria-label="completed"
                  aria-hidden="false"
                />
              ) : active ? (
                <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
              ) : (
                <span className="inline-block h-4 w-4 rounded-full border border-border" />
              )}
              <span
                className={cn(
                  done && 'text-muted-foreground line-through decoration-1',
                  active && 'font-medium',
                  !done && !active && 'text-muted-foreground',
                )}
              >
                {p.label}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="mt-4 text-xs text-muted-foreground">
        Elapsed: {Math.round(elapsed / 1000)}s
      </p>
    </div>
  );
}
