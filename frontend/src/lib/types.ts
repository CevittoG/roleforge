// Mirrors app/web/schemas.py. Keep in sync by hand — the surface is tiny.
export type ApplicationSummary = {
  date: string;
  company: string;
  role: string;
  status: string;
  seniority: string;
  fit_score: number | null;
  work_mode: string;
  location: string | null;
  pay: string | null;
  benefits: string | null;
  key_requirements: string[];
  tech_stack: string[];
  matched_experience: string[];
  missing_experience: string[];
  concerns: string | null;
  jd_source_url: string | null;
  folder_url: string;
  folder_id: string;
};

// Which LLM produces the application. Mirrors app/web/schemas.py::LlmProvider.
export type LlmProvider = 'anthropic' | 'gemini';

export const PROVIDER_LABELS: Record<LlmProvider, string> = {
  anthropic: 'Claude',
  gemini: 'Gemini',
};

export type GenerateRequest = {
  jd_text: string;
  confirm_overwrite?: boolean;
  provider?: LlmProvider;
};

// Mirrors app/domain/models.py::ApplicationStatus. Keep in sync by hand.
export const APPLICATION_STATUSES = [
  'Generated',
  'Applied',
  'Interview',
  'Offer',
  'Rejected',
  'Withdrawn',
  'Ghosted',
  'On hold',
] as const;
export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number];

export type JobStatus = 'queued' | 'running' | 'done' | 'duplicate' | 'error';

// Returned by POST /api/generate. The work hasn't started yet — poll
// /api/jobs/{job_id} to watch it run.
export type GenerateResponse = { job_id: string; status: JobStatus };

export type JobResponse = {
  job_id: string;
  status: JobStatus;
  application: ApplicationSummary | null;
  existing: ApplicationSummary | null;
  error: string | null;
  started_at: number | null;
  finished_at: number | null;
};

export type AppConfig = {
  insights_url: string | null;
  llm_providers: LlmProvider[];
  default_llm_provider: LlmProvider;
};

export type DownloadKey = 'resume' | 'cover_letter' | 'job_description' | 'interview_prep';

export const DOWNLOAD_LABELS: Record<DownloadKey, string> = {
  // The resume lives in Drive as an editable Google Doc; this download exports
  // a fresh PDF. Edit the Doc itself via "Open in Drive".
  resume: 'Resume (PDF)',
  cover_letter: 'Cover Letter (TXT)',
  job_description: 'Job Description (MD)',
  interview_prep: 'Interview Prep (MD)',
};
