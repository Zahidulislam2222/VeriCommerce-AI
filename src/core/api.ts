import { appConfig } from '../config';
import coreContent from '../data/core.json';
import phaseContent from '../data/phase-workspace.json';
import type { Job } from './types';

export class CoreError extends Error {
  constructor(message: string, public readonly status = 0) { super(message); this.name = 'CoreError'; }
}
export class CoreRequestStopped extends CoreError {
  constructor() { super(coreContent.assistant.stopped); this.name = 'CoreRequestStopped'; }
}
export class WorkspaceScopeError extends CoreError {
  constructor() { super(phaseContent.common.workspaceChanged, 409); this.name = 'WorkspaceScopeError'; }
}
let workspaceScope: string | undefined;
export function setWorkspaceScope(scope?: string) { workspaceScope = scope; }
export function getWorkspaceScope() { return workspaceScope; }

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const unscoped = path === appConfig.core.paths.session || path === appConfig.core.phasePaths.capabilities ||
    (path.startsWith(`${appConfig.core.phasePaths.auth}/`) && path !== `${appConfig.core.phasePaths.auth}/members`);
  const expectedScope = unscoped ? undefined : workspaceScope;
  const controller = new AbortController();
  const callerSignal = options.signal;
  const stop = () => controller.abort();
  if (callerSignal?.aborted) stop();
  else callerSignal?.addEventListener('abort', stop, { once: true });
  const timer = window.setTimeout(() => controller.abort(), appConfig.core.requestTimeoutSeconds * 1000);
  try {
    const response = await fetch(`${appConfig.core.base}${path}`, {
      ...options, credentials: 'same-origin', signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers, ...(expectedScope ? { 'X-Workspace-ID': expectedScope } : {}) },
    });
    const data: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : null;
      if (detail && typeof detail === 'object' && 'code' in detail && detail.code === 'workspace_changed') throw new WorkspaceScopeError();
      throw new CoreError(typeof detail === 'string' ? detail : coreContent.errors.request, response.status);
    }
    if (callerSignal?.aborted) throw new CoreRequestStopped();
    if (controller.signal.aborted) throw new CoreError(coreContent.errors.timeout);
    if (expectedScope && (workspaceScope !== expectedScope || response.headers.get('X-Workspace-ID') !== expectedScope)) throw new WorkspaceScopeError();
    return data as T;
  } catch (error) {
    if (callerSignal?.aborted) throw new CoreRequestStopped();
    if (error instanceof CoreError) throw error;
    throw new CoreError(error instanceof DOMException && error.name === 'AbortError' ? coreContent.errors.timeout : coreContent.errors.connection);
  } finally { window.clearTimeout(timer); callerSignal?.removeEventListener('abort', stop); }
}

let sessionPromise: Promise<unknown> | undefined;
export function ensureSession(checkCurrent?: () => void): Promise<unknown> {
  const load = () => {
    checkCurrent?.();
    return request(appConfig.core.paths.session).catch((error: unknown) => {
      checkCurrent?.();
      if (error instanceof CoreError && error.status === 401) return request(appConfig.core.paths.session, { method: 'POST', body: '{}' });
      throw error;
    }).then((session) => { checkCurrent?.(); return session; });
  };
  // Guarded snapshots must not inherit a canceled caller's session bootstrap.
  if (checkCurrent) return load();
  sessionPromise ??= load().finally(() => { sessionPromise = undefined; });
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
    if (job.status === 'failed' || job.status === 'dead_letter') throw new CoreError(job.error || coreContent.errors.job);
    await new Promise((resolve) => window.setTimeout(resolve, appConfig.core.pollSeconds * 1000));
  }
  throw new CoreError(coreContent.errors.jobTimeout);
}
