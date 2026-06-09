import * as React from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ApplicationCard } from '@/components/ApplicationCard';
import { ApplicationDetail } from '@/components/ApplicationDetail';
import { listApplications } from '@/lib/api';
import type { ApplicationSummary } from '@/lib/types';

type SortKey = 'date' | 'fit';

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
  const [error, setError] = React.useState<string | null>(null);
  const [sort, setSort] = React.useState<SortKey>('date');

  React.useEffect(() => {
    const controller = new AbortController();
    listApplications(controller.signal)
      .then((data) => setApps(data))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const message = err instanceof Error ? err.message : 'Failed to load applications.';
        setError(message);
        setApps([]);
      });
    return () => controller.abort();
  }, []);

  const sorted = React.useMemo(() => (apps ? sortApps(apps, sort) : []), [apps, sort]);

  const selectedId = typeof router.query.app === 'string' ? router.query.app : null;
  const selected = selectedId ? sorted.find((a) => a.folder_id === selectedId) ?? null : null;

  function closeDetail() {
    const { app: _omit, ...rest } = router.query;
    void router.replace({ pathname: '/history', query: rest }, undefined, { shallow: true });
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
            <AlertDescription>{error}</AlertDescription>
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
            <ul className="space-y-3">
              {sorted.map((app) => (
                <li key={app.folder_id}>
                  <ApplicationCard app={app} />
                </li>
              ))}
            </ul>
          </>
        )}

        <ApplicationDetail
          application={selected}
          open={selected != null}
          onOpenChange={(open) => {
            if (!open) closeDetail();
          }}
        />
      </div>
    </>
  );
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
