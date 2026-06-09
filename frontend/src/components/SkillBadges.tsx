import { Badge } from '@/components/ui/badge';

export function SkillBadges({
  skills,
  tone,
  emptyLabel,
  limit,
}: {
  skills: string[];
  tone: 'success' | 'destructive' | 'muted' | 'outline';
  emptyLabel?: string;
  limit?: number;
}) {
  if (!skills.length) {
    return emptyLabel ? (
      <p className="text-xs text-muted-foreground">{emptyLabel}</p>
    ) : null;
  }
  const shown = limit ? skills.slice(0, limit) : skills;
  const overflow = limit ? skills.length - shown.length : 0;
  return (
    <ul className="flex flex-wrap gap-1.5">
      {shown.map((s) => (
        <li key={s}>
          <Badge tone={tone}>{s}</Badge>
        </li>
      ))}
      {overflow > 0 ? (
        <li>
          <Badge tone="outline">+{overflow}</Badge>
        </li>
      ) : null}
    </ul>
  );
}
