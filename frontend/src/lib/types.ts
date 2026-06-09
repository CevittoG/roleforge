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

export type GenerateRequest = {
  jd_text?: string;
  jd_url?: string;
  confirm_overwrite?: boolean;
};

export type GenerateResponse = { application: ApplicationSummary };

export type DuplicateResponse = { detail: string; existing: ApplicationSummary };

export type DownloadKey = 'resume' | 'cover_letter' | 'job_description' | 'interview_prep';

export const DOWNLOAD_LABELS: Record<DownloadKey, string> = {
  resume: 'Resume (PDF)',
  cover_letter: 'Cover Letter (PDF)',
  job_description: 'Job Description (MD)',
  interview_prep: 'Interview Prep (MD)',
};
