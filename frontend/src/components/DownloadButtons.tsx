import { Download } from 'lucide-react';
import { downloadUrl } from '@/lib/api';
import { DOWNLOAD_LABELS, type DownloadKey } from '@/lib/types';
import { cn } from '@/lib/cn';

// Interview prep and application questions are generated on demand (separate
// buttons), so they're not in the always-available set.
export const DEFAULT_DOWNLOAD_KEYS: DownloadKey[] = [
  'resume',
  'cover_letter',
  'match_report',
  'job_description',
];

export function DownloadButtons({
  folderId,
  role,
  date,
  keys = DEFAULT_DOWNLOAD_KEYS,
  className,
}: {
  folderId: string;
  role?: string;
  date?: string;
  keys?: DownloadKey[];
  className?: string;
}) {
  return (
    <div className={cn('grid grid-cols-1 gap-2 sm:grid-cols-2', className)}>
      {keys.map((key) => (
        <a
          key={key}
          href={downloadUrl(folderId, key, role, date)}
          className={
            'inline-flex min-h-touch items-center justify-between gap-3 rounded-md border border-border ' +
            'bg-background px-4 py-2 text-sm font-medium shadow-sm transition hover:bg-muted active:bg-muted/70 ' +
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
          }
        >
          <span>{DOWNLOAD_LABELS[key]}</span>
          <Download className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </a>
      ))}
    </div>
  );
}
