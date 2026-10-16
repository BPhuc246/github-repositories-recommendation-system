export interface User {
  user_id: number;
  username: string;
  email: string | null;
  auth_provider: 'local' | 'github';
  github_id: number | null;
  github_login: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface Repo {
  repo_id: number;
  github_repo_id: number;
  full_name: string;
  description: string | null;
  language: string | null;
  topics: string[] | null;
  stars: number;
  forks: number;
  url: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface RepoDetail extends Repo {
  readme_text: string | null;
  avg_rating: number | null;
  rating_count: number;
}

export interface RepoPage {
  items: Repo[];
  total: number;
  page: number;
  page_size: number;
}

export interface RepoState {
  favorite: boolean;
  disliked: boolean;
  rating: number | null;
}

export interface GithubConfig {
  client_id_set: boolean;
  client_secret_set: boolean;
  client_id_preview: string | null;
  redirect_uri: string;
  frontend_url: string;
}
