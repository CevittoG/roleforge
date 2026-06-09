import { ExternalLink } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { SkillBadges } from '@/components/SkillBadges';
import { DownloadButtons } from '@/components/DownloadButtons';
import { fitScoreTone, formatDate } from '@/lib/format';
import type { ApplicationSummary } from '@/lib/types';

export function ApplicationDetail({
  application,
  open,
  onOpenChange,
}: {
  application: ApplicationSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!application) return null;
  const tone = fitScoreTone(application.fit_score);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100vh-2rem)] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="truncate">{application.company}</DialogTitle>
          <DialogDescription className="truncate">
            {application.role} · {application.seniority}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-wrap items-center gap-2">
          {application.fit_score != null ? (
            <Badge tone={tone}>{application.fit_score}% fit</Badge>
          ) : null}
          <Badge tone="muted">{application.status}</Badge>
          <Badge tone="outline">{application.work_mode}</Badge>
        </div>
        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
          <Meta label="Generated" value={formatDate(application.date)} />
          <Meta label="Location" value={application.location ?? '—'} />
          <Meta label="Pay" value={application.pay ?? '—'} />
          <Meta label="Benefits" value={application.benefits ?? '—'} />
        </dl>
        <Section title="Key requirements">
          <SkillBadges skills={application.key_requirements} tone="outline" emptyLabel="None." />
        </Section>
        <Section title="Tech stack">
          <SkillBadges skills={application.tech_stack} tone="outline" emptyLabel="None." />
        </Section>
        <Section title="Matched">
          <SkillBadges skills={application.matched_experience} tone="success" emptyLabel="None." />
        </Section>
        <Section title="Missing">
          <SkillBadges
            skills={application.missing_experience}
            tone="destructive"
            emptyLabel="None."
          />
        </Section>
        {application.concerns ? (
          <Section title="Concerns">
            <p className="whitespace-pre-wrap text-sm text-foreground">{application.concerns}</p>
          </Section>
        ) : null}
        <div className="flex flex-col gap-2">
          <a
            href={application.folder_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
          >
            Open in Drive <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
          {application.jd_source_url ? (
            <a
              href={application.jd_source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
            >
              Original job posting <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          ) : null}
        </div>
        <Section title="Downloads">
          <DownloadButtons folderId={application.folder_id} />
        </Section>
      </DialogContent>
    </Dialog>
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
