import { ExternalLink } from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SkillBadges } from '@/components/SkillBadges';
import { DownloadButtons } from '@/components/DownloadButtons';
import { InterviewPrepButton } from '@/components/InterviewPrepButton';
import { fitScoreTone } from '@/lib/format';
import type { ApplicationSummary } from '@/lib/types';

export function ResultPanel({
  application,
  onReset,
}: {
  application: ApplicationSummary;
  onReset: () => void;
}) {
  const tone = fitScoreTone(application.fit_score);
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle className="truncate">{application.company}</CardTitle>
              <CardDescription className="truncate">
                {application.role} · {application.seniority}
              </CardDescription>
            </div>
            {application.fit_score != null ? (
              <Badge tone={tone}>{application.fit_score}% fit</Badge>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
            <Meta label="Work mode" value={application.work_mode} />
            <Meta label="Location" value={application.location ?? '—'} />
            <Meta label="Pay" value={application.pay ?? '—'} />
            <Meta label="Benefits" value={application.benefits ?? '—'} />
          </div>

          <Section title="Matched experience">
            <SkillBadges
              skills={application.matched_experience}
              tone="success"
              emptyLabel="No matches recorded."
            />
          </Section>

          <Section title="Missing experience">
            <SkillBadges
              skills={application.missing_experience}
              tone="destructive"
              emptyLabel="No gaps recorded."
            />
          </Section>

          {application.concerns ? (
            <Section title="Concerns">
              <p className="whitespace-pre-wrap text-sm text-foreground">
                {application.concerns}
              </p>
            </Section>
          ) : null}

          <a
            href={application.folder_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
          >
            Open in Drive <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Downloads</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <DownloadButtons folderId={application.folder_id} />
          <InterviewPrepButton folderId={application.folder_id} />
        </CardContent>
      </Card>

      <Button variant="outline" size="lg" className="w-full" onClick={onReset}>
        Generate another
      </Button>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="truncate text-sm">{value}</dd>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="mb-1.5 text-xs uppercase tracking-wide text-muted-foreground">{title}</h4>
      {children}
    </div>
  );
}
