import type { GithubConfig, Repo, RepoDetail, RepoPage, RepoState, User } from '../types';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = typeof body.detail === 'string' ? body.detail : res.statusText;
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

const put = (body: unknown): RequestInit => ({ method: 'PUT', body: JSON.stringify(body) });
const post = (body?: unknown): RequestInit => ({
  method: 'POST',
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  register: (b: { username: string; email?: string; password: string }) =>
    request<User>('/auth/register', post(b)),
  login: (b: { username: string; password: string }) => request<User>('/auth/login', post(b)),
  logout: () => request<{ ok: boolean }>('/auth/logout', post()),
  me: () => request<User>('/auth/me'),

  githubLoginUrl: '/api/auth/github/login',
  githubConfig: () => request<GithubConfig>('/auth/github/config'),

  searchRepos: (params: Record<string, string>) =>
    request<RepoPage>(`/repositories?${new URLSearchParams(params).toString()}`),
  languages: () => request<string[]>('/repositories/languages'),
  getRepo: (id: number) => request<RepoDetail>(`/repositories/${id}`),

  getState: (id: number) => request<RepoState>(`/interactions/repos/${id}`),
  setFavorite: (id: number, on: boolean) =>
    request<RepoState>(`/interactions/repos/${id}/favorite`, put({ on })),
  setDislike: (id: number, on: boolean) =>
    request<RepoState>(`/interactions/repos/${id}/dislike`, put({ on })),
  setRating: (id: number, rating: number | null) =>
    request<RepoState>(`/interactions/repos/${id}/rating`, put({ rating })),
  favorites: () => request<Repo[]>('/interactions/favorites'),

  recommendations: (limit = 6) => request<Repo[]>(`/recommendations?limit=${limit}`),
};
