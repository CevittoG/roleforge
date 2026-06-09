export function formatDate(iso: string): string {
  // Backend emits ISO with seconds + UTC offset. Render as short local date.
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function fitScoreTone(score: number | null): 'success' | 'warning' | 'destructive' | 'muted' {
  if (score == null) return 'muted';
  if (score >= 75) return 'success';
  if (score >= 50) return 'warning';
  return 'destructive';
}
