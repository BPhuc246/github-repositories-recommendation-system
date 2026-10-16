import { Link } from 'react-router-dom';
import type { Repo } from '../types';

export default function RepoCard({ repo }: { repo: Repo }) {
  return (
    <Link
      to={`/repos/${repo.repo_id}`}
      className="block rounded-xl border border-slate-200 bg-white p-5 transition hover:border-teal-200 hover:shadow-sm"
    >
      <h3 className="break-all font-medium text-slate-800">{repo.full_name}</h3>
      <p className="mt-1 line-clamp-2 text-sm text-slate-500">
        {repo.description ?? 'Chưa có mô tả'}
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-400">
        {repo.language && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">{repo.language}</span>
        )}
        <span>★ {repo.stars.toLocaleString('vi-VN')}</span>
        <span>⑂ {repo.forks.toLocaleString('vi-VN')}</span>
      </div>
    </Link>
  );
}
