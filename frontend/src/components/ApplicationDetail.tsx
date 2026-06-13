import * as React from 'react';
import { ExternalLink } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/select';
import { SkillBadges } from '@/components/SkillBadges';
import { DownloadButtons } from '@/components/DownloadButtons';
import { InterviewPrepButton } from '@/components/InterviewPrepButton';
import { ApplicationQuestionsPanel } from '@/components/ApplicationQuestionsPanel';
import { ApiError, updateApplicationStatus } from '@/lib/api';
import { fitScoreTone, formatDate } from '@/lib/format';
import {
  APPLICATION_STATUSES,
  type ApplicationStatus,
  type ApplicationSummary,
} from '@/lib/types';

export function ApplicationDetail({
  application,
  open,
  onOpenChange,
  onStatusChange,
}: {
  application: ApplicationSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onStatusChange: (folderId: string, status: ApplicationStatus) => void;
}) {
  const [saving, setSaving] = React.useState(false);
  const [statusError, setStatusError] = React.useState<string | null>(null);

  // Clear transient feedback whenever the modal opens on a different record.
  React.useEffect(() => {
    setStatusError(null);
    setSaving(false);
  }, [application?.folder_id]);

  if (!application) return null;
  const tone = fitScoreTone(application.fit_score);

  async function handleStatusChange(next: string) {
    if (!application) return;
    if (!isApplicationStatus(next) || next === application.status) return;
    const previous = application.status as ApplicationStatus;
    onStatusChange(application.folder_id, next);
    setSaving(true);
    setStatusError(null);
    try {
      await updateApplicationStatus(application.folder_id, next);
    } catch (err) {
      onStatusChange(application.folder_id, previous);
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Could not update status.';
      setStatusError(message);
    } finally {
      setSaving(false);
    }
  }

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
          <Badge tone="outline">{application.work_mode}</Badge>
        </div>
        <div className="space-y-1">
          <label
            htmlFor="status-select"
            className="text-xs uppercase tracking-wide text-muted-foreground"
          >
            Status
          </label>
          <Select
            id="status-select"
            value={application.status}
            disabled={saving}
            onChange={(e) => void handleStatusChange(e.target.value)}
          >
            {/* Surface any legacy/unknown value so it's not silently lost. */}
            {!isKnownStatus(application.status) ? (
              <option value={application.status}>{application.status}</option>
            ) : null}
            {APPLICATION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
          {statusError ? (
            <p className="text-xs text-destructive" role="alert">
              {statusError}
            </p>
          ) : null}
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
          <DownloadButtons
            folderId={application.folder_id}
            role={application.role}
            date={application.date}
          />
          <div className="mt-2">
            <InterviewPrepButton
              folderId={application.folder_id}
              role={application.role}
              date={application.date}
            />
          </div>
        </Section>
        <Section title="Application questions">
          <ApplicationQuestionsPanel
            folderId={application.folder_id}
            role={application.role}
            date={application.date}
          />
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

function isApplicationStatus(value: string): value is ApplicationStatus {
  return (APPLICATION_STATUSES as readonly string[]).includes(value);
}

function isKnownStatus(value: string): boolean {
  return (APPLICATION_STATUSES as readonly string[]).includes(value);
}
