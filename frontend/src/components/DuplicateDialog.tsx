import { ExternalLink } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/lib/format';
import type { ApplicationSummary } from '@/lib/types';

export function DuplicateDialog({
  existing,
  open,
  onOpenChange,
  onConfirm,
  pending,
}: {
  existing: ApplicationSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  pending: boolean;
}) {
  if (!existing) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>This role already exists</DialogTitle>
          <DialogDescription>
            You generated an application for <strong>{existing.company}</strong> ·{' '}
            <strong>{existing.role}</strong> on {formatDate(existing.date)}.
          </DialogDescription>
        </DialogHeader>
        <div className="rounded-md border border-border bg-muted/40 p-3 text-sm">
          <p className="mb-2">Overwriting will:</p>
          <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
            <li>Replace the four files in the existing Drive folder.</li>
            <li>Append a new audit row to the Sheet (history is preserved).</li>
          </ul>
        </div>
        <a
          href={existing.folder_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
        >
          Open existing folder <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
        </a>
        <DialogFooter>
          <Button variant="outline" size="md" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button variant="primary" size="md" onClick={onConfirm} disabled={pending}>
            {pending ? 'Overwriting…' : 'Overwrite'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
