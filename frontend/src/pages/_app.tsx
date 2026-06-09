import * as React from 'react';
import type { AppProps } from 'next/app';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { FileText, History } from 'lucide-react';
import { warmPing } from '@/lib/api';
import { cn } from '@/lib/cn';
import '@/styles/globals.css';

function useWarmPing() {
  React.useEffect(() => {
    const controller = new AbortController();
    void warmPing(controller.signal);

    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        void warmPing();
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      controller.abort();
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);
}

function NavLink({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: typeof FileText;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        'flex min-h-touch flex-1 flex-col items-center justify-center gap-0.5 py-2 text-xs font-medium transition-colors',
        active ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
      )}
      aria-current={active ? 'page' : undefined}
    >
      <Icon className="h-5 w-5" aria-hidden="true" />
      {label}
    </Link>
  );
}

export default function App({ Component, pageProps }: AppProps) {
  useWarmPing();
  const router = useRouter();
  const path = router.pathname;

  return (
    <>
      <Head>
        <title>Roleforge</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#ffffff" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <div className="flex min-h-full flex-col bg-background">
        <header className="border-b border-border bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <div className="mx-auto flex max-w-2xl items-center justify-between">
            <Link href="/" className="text-base font-semibold tracking-tight">
              Roleforge
            </Link>
          </div>
        </header>
        <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-4 pb-24">
          <Component {...pageProps} />
        </main>
        <nav
          className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur supports-[backdrop-filter]:bg-background/80"
          aria-label="Primary"
        >
          <div className="mx-auto flex max-w-2xl">
            <NavLink href="/" label="Generate" icon={FileText} active={path === '/'} />
            <NavLink
              href="/history"
              label="History"
              icon={History}
              active={path.startsWith('/history')}
            />
          </div>
        </nav>
      </div>
    </>
  );
}
