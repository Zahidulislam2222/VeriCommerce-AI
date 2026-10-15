import { appConfig } from '../config';
import coreContent from '../data/core.json';
import type { Job } from './types';

export class CoreError extends Error {
  constructor(message: string, public readonly status = 0) { super(message); this.name = 'CoreError'; }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), appConfig.core.requestTimeoutSeconds * 1000);
  try {
    const response = await fetch(`${appConfig.core.base}${path}`, {
      ...options, credentials: 'same-origin', signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
    const data: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : null;
      throw new CoreError(typeof detail === 'string' ? detail : coreContent.errors.request, response.status);
    }
    return data as T;
  } catch (error) {
    if (error instanceof CoreError) throw error;
    throw new CoreError(error instanceof DOMException && error.name === 'AbortError' ? coreContent.errors.timeout : coreContent.errors.connection);
  } finally { window.clearTimeout(timer); }
}

let sessionPromise: Promise<unknown> | undefined;
export function ensureSession(): Promise<unknown> {
  sessionPromise ??= request(appConfig.core.paths.session).catch((error: unknown) => {
    if (error instanceof CoreError && error.status === 401) return request(appConfig.core.paths.session, { method: 'POST', body: '{}' });
    throw error;
  }).finally(() => { sessionPromise = undefined; });
  return sessionPromise;
}

export function post<T>(path: string, data: unknown): Promise<T> {
  return request(path, { method: 'POST', body: JSON.stringify(data) });
}

export async function waitForJob(id: string, onProgress: (job: Job) => void): Promise<Job> {
  const deadline = Date.now() + appConfig.core.jobTimeoutSeconds * 1000;
  while (Date.now() < deadline) {
    const { job } = await request<{ job: Job }>(`${appConfig.core.paths.jobs}/${encodeURIComponent(id)}`);
    onProgress(job);
    if (job.status === 'completed' || job.status === 'succeeded') return job;
    if (job.status === 'failed') throw new CoreError(job.error || coreContent.errors.job);
    await new Promise((resolve) => window.setTimeout(resolve, appConfig.core.pollSeconds * 1000));
  }
  throw new CoreError(coreContent.errors.jobTimeout);
}
