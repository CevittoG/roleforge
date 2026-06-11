import { Download } from 'lucide-react';
import { downloadUrl } from '@/lib/api';
import { DOWNLOAD_LABELS, type DownloadKey } from '@/lib/types';
import { cn } from '@/lib/cn';

// Interview prep is generated on demand (see InterviewPrepButton), so it's not
// in the always-available set.
const ORDER: DownloadKey[] = ['resume', 'cover_letter', 'job_description'];

export function DownloadButtons({ folderId, className }: { folderId: string; className?: string }) {
  return (
    <div className={cn('grid grid-cols-1 gap-2 sm:grid-cols-2', className)}>
      {ORDER.map((key) => (
        <a
          key={key}
          href={downloadUrl(folderId, key)}
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
