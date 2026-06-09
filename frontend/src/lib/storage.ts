// localStorage-backed draft persistence for the Generate form. Defensive
// against quota errors and SSR-time access (storage is not available in
// Node during static export).
const DRAFT_KEY = 'roleforge.generate.draft.v1';

export type Draft = {
  mode: 'text' | 'url';
  jd_text: string;
  jd_url: string;
};

const EMPTY: Draft = { mode: 'text', jd_text: '', jd_url: '' };

export function loadDraft(): Draft {
  if (typeof window === 'undefined') return EMPTY;
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw) as Partial<Draft>;
    return {
      mode: parsed.mode === 'url' ? 'url' : 'text',
      jd_text: typeof parsed.jd_text === 'string' ? parsed.jd_text : '',
      jd_url: typeof parsed.jd_url === 'string' ? parsed.jd_url : '',
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
