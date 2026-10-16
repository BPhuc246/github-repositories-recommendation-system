import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import InteractionBar from "../components/InteractionBar";
import { card, errorBox } from "../components/ui";
import { api } from "../services/api";
import type { RepoDetail } from "../types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-4 py-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-0.5 font-medium text-slate-800">{value}</div>
    </div>
  );
}

export default function RepoDetailPage() {
  const { id } = useParams();
  const repoId = Number(id);
  const [repo, setRepo] = useState<RepoDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setRepo(null);
    setError("");
    api
      .getRepo(repoId)
      .then(setRepo)
      .catch((e) => setError((e as Error).message));
  }, [repoId]);

  if (error) return <p className={errorBox}>{error}</p>;
  if (!repo)
    return (
      <p className="py-20 text-center text-sm text-slate-400">Đang tải...</p>
    );

  return (
    <div className="space-y-6">
      <Link to="/" className="text-sm text-slate-400 hover:text-slate-700">
        ← Quay lại tìm kiếm
      </Link>

      <section className={card}>
        <a
          href={repo.url ?? "#"}
          target="_blank"
          rel="noreferrer"
          className="break-all text-lg font-semibold text-slate-800 hover:text-brand"
        >
          {repo.full_name}
        </a>
        <p className="mt-2 text-sm text-slate-500">
          {repo.description ?? "Chưa có mô tả"}
        </p>

        {repo.topics && repo.topics.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {repo.topics.map((t) => (
              <span
                key={t}
                className="rounded-full bg-teal-50 px-2.5 py-0.5 text-xs text-teal-700"
              >
                {t}
              </span>
            ))}
          </div>
        )}

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Ngôn ngữ" value={repo.language ?? "—"} />
          <Stat label="Sao" value={repo.stars.toLocaleString("vi-VN")} />
          <Stat label="Fork" value={repo.forks.toLocaleString("vi-VN")} />
          <Stat
            label={`Đánh giá (${repo.rating_count})`}
            value={repo.avg_rating ? `${repo.avg_rating} / 5` : "Chưa có"}
          />
        </div>

        <div className="mt-6 border-t border-slate-100 pt-6">
          <InteractionBar repoId={repo.repo_id} />
        </div>
      </section>

      <section className={card}>
        <h2 className="mb-3 font-medium text-slate-800">README</h2>
        <div className="max-h-120 overflow-auto rounded-lg bg-slate-50 p-4">
          <pre className="whitespace-pre-wrap text-sm leading-relaxed text-slate-600">
            {repo.readme_text ?? "Không có README."}
          </pre>
        </div>
      </section>
    </div>
  );
}
