// localStorage-backed draft persistence for the Generate form. Defensive
// against quota errors and SSR-time access (storage is not available in
// Node during static export).
const DRAFT_KEY = 'roleforge.generate.draft.v1';
const ACTIVE_JOB_KEY = 'roleforge.generate.active_job.v1';
const ACTIVE_JOB_MAX_AGE_MS = 60 * 60 * 1000; // 1h — matches backend job TTL.

export type Draft = {
  jd_text: string;
};

export type ActiveJob = {
  job_id: string;
  created_at: number; // epoch ms
};

const EMPTY: Draft = { jd_text: '' };

export function loadDraft(): Draft {
  if (typeof window === 'undefined') return EMPTY;
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    if (!raw) return EMPTY;
    // Tolerant of old shape (mode/jd_url) — those keys are silently ignored.
    const parsed = JSON.parse(raw) as Partial<Draft>;
    return {
      jd_text: typeof parsed.jd_text === 'string' ? parsed.jd_text : '',
    };
  } catch {
    return EMPTY;
  }
}

export function saveDraft(draft: Draft): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // Quota exceeded or storage disabled — silent best-effort.
  }
}

export function clearDraft(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(DRAFT_KEY);
  } catch {
    // ignore
  }
}

export function loadActiveJob(): ActiveJob | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(ACTIVE_JOB_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ActiveJob>;
    if (typeof parsed.job_id !== 'string' || typeof parsed.created_at !== 'number') return null;
    if (Date.now() - parsed.created_at > ACTIVE_JOB_MAX_AGE_MS) {
      window.localStorage.removeItem(ACTIVE_JOB_KEY);
      return null;
    }
    return { job_id: parsed.job_id, created_at: parsed.created_at };
  } catch {
    return null;
  }
}

export function saveActiveJob(job: ActiveJob): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(ACTIVE_JOB_KEY, JSON.stringify(job));
  } catch {
    // ignore
  }
}

export function clearActiveJob(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(ACTIVE_JOB_KEY);
  } catch {
    // ignore
  }
}
