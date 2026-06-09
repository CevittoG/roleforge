import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SkillBadges } from '@/components/SkillBadges';
import { fitScoreTone, formatDate } from '@/lib/format';
import type { ApplicationSummary } from '@/lib/types';

export function ApplicationCard({ app }: { app: ApplicationSummary }) {
  const tone = fitScoreTone(app.fit_score);
  return (
    <Card>
      <Link
        href={{ pathname: '/history', query: { app: app.folder_id } }}
        scroll={false}
        className="flex min-h-touch items-start gap-3 p-4 transition hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-lg"
      >
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-base font-semibold leading-tight">{app.company}</p>
              <p className="truncate text-sm text-muted-foreground">{app.role}</p>
            </div>
            {app.fit_score != null ? (
              <Badge tone={tone}>{app.fit_score}%</Badge>
            ) : (
              <Badge tone="muted">—</Badge>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{formatDate(app.date)}</span>
            <span aria-hidden="true">·</span>
            <span>{app.status}</span>
            <span aria-hidden="true">·</span>
            <span className="truncate">{app.work_mode}</span>
          </div>
          {app.missing_experience.length ? (
            <SkillBadges skills={app.missing_experience} tone="destructive" limit={3} />
          ) : null}
        </div>
        <ChevronRight
          className="mt-1 h-5 w-5 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
      </Link>
    </Card>
  );
}
