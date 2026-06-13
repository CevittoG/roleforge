import * as React from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { ExternalLink } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select } from '@/components/ui/select';
import { ApplicationCard } from '@/components/ApplicationCard';
import { ApplicationDetail } from '@/components/ApplicationDetail';
import { ApiError, getConfig, listApplications } from '@/lib/api';
import { STATUS_FILTER_OPTIONS, type ApplicationSummary } from '@/lib/types';

type LoadError = { message: string; transient: boolean };

type SortKey = 'date' | 'fit';

const ALL_STATUSES = 'All';

function sortApps(apps: ApplicationSummary[], key: SortKey): ApplicationSummary[] {
  const copy = apps.slice();
  if (key === 'fit') {
    copy.sort((a, b) => (b.fit_score ?? -1) - (a.fit_score ?? -1));
  } else {
    copy.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  }
  return copy;
}

export default function HistoryPage() {
  const router = useRouter();
  const [apps, setApps] = React.useState<ApplicationSummary[] | null>(null);
  const [error, setError] = React.useState<LoadError | null>(null);
  const [sort, setSort] = React.useState<SortKey>('date');
  const [statusFilter, setStatusFilter] = React.useState<string>(ALL_STATUSES);
  const [insightsUrl, setInsightsUrl] = React.useState<string | null>(null);
  const [reloadKey, setReloadKey] = React.useState(0);

  React.useEffect(() => {
    const controller = new AbortController();
    setError(null);
    setApps(null);
    listApplications(controller.signal)
      .then((data) => setApps(data))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(classifyError(err));
        setApps([]);
      });
    getConfig(controller.signal)
      .then((cfg) => setInsightsUrl(cfg.insights_url))
      .catch(() => {
        // Best-effort; missing config just hides the link.
      });
    return () => controller.abort();
  }, [reloadKey]);

  const sorted = React.useMemo(() => (apps ? sortApps(apps, sort) : []), [apps, sort]);
  const visible = React.useMemo(
    () =>
      statusFilter === ALL_STATUSES
        ? sorted
        : sorted.filter((a) => a.status === statusFilter),
    [sorted, statusFilter],
  );

  const selectedId = typeof router.query.app === 'string' ? router.query.app : null;
  const selected = selectedId ? sorted.find((a) => a.folder_id === selectedId) ?? null : null;

  function closeDetail() {
    const { app: _omit, ...rest } = router.query;
    void router.replace({ pathname: '/history', query: rest }, undefined, { shallow: true });
  }

  function handleStatusChange(folderId: string, status: string) {
    setApps((current) =>
      current
        ? current.map((a) => (a.folder_id === folderId ? { ...a, status } : a))
        : current,
    );
  }

  return (
    <>
      <Head>
        <title>History · Roleforge</title>
      </Head>
      <div className="space-y-4">
        <div className="flex items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">History</h1>
            <p className="text-sm text-muted-foreground">
              Every application you&apos;ve generated, sortable by date or fit.
            </p>
          </div>
        </div>

        {error ? (
          <Alert tone="destructive">
            <AlertTitle>Couldn&apos;t load history</AlertTitle>
            <AlertDescription className="space-y-3">
              <p>{error.message}</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setReloadKey((n) => n + 1)}
              >
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        ) : null}

        {apps == null ? (
          <SkeletonList />
        ) : apps.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <Tabs value={sort} onValueChange={(v) => setSort(v as SortKey)}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="date">Recent</TabsTrigger>
                <TabsTrigger value="fit">Best fit</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="space-y-1">
              <label
                htmlFor="status-filter"
                className="text-xs uppercase tracking-wide text-muted-foreground"
              >
                Filter by status
              </label>
              <Select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value={ALL_STATUSES}>All statuses</option>
                {STATUS_FILTER_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </div>
            {visible.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
                No applications with status &ldquo;{statusFilter}&rdquo;.
              </p>
            ) : (
              <ul className="space-y-3">
                {visible.map((app) => (
                  <li key={app.folder_id}>
                    <ApplicationCard app={app} />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}

        {insightsUrl ? (
          <div className="pt-2">
            <a
              href={insightsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
            >
              Open Insights in Sheets
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          </div>
        ) : null}

        <ApplicationDetail
          application={selected}
          open={selected != null}
          onOpenChange={(open) => {
            if (!open) closeDetail();
          }}
          onStatusChange={handleStatusChange}
          onRegenerated={() => setReloadKey((n) => n + 1)}
        />
      </div>
    </>
  );
}

function classifyError(err: unknown): LoadError {
  if (err instanceof ApiError) {
    if (err.status >= 500) {
      return {
        message: 'The backend is waking up — give it ~30 seconds and try again.',
        transient: true,
      };
    }
    if (err.status === 401 || err.status === 403) {
      return {
        message: 'Your session expired. Refresh the page to sign back in.',
        transient: false,
      };
    }
    return { message: err.message, transient: false };
  }
  // Network errors throw plain Error / TypeError; treat as transient.
  if (err instanceof Error) {
    return { message: `Network error: ${err.message}`, transient: true };
  }
  return { message: 'Failed to load applications.', transient: true };
}

function SkeletonList() {
  return (
    <ul className="space-y-3" aria-busy="true" aria-label="Loading applications">
      {Array.from({ length: 3 }).map((_, i) => (
        <li
          key={i}
          className="h-24 animate-pulse rounded-lg border border-border bg-muted/40"
        />
      ))}
    </ul>
  );
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center">
      <p className="text-sm font-medium">No applications yet.</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Generate your first one to populate history.
      </p>
      <Link
        href="/"
        className="mt-4 inline-flex h-11 min-h-touch items-center justify-center rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        Go to Generate
      </Link>
    </div>
  );
}
