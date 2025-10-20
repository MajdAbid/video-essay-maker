import clsx from "clsx";
import { DateTime } from "luxon";

const statusColors = {
  queued: "bg-amber-500/10 text-amber-400",
  processing: "bg-sky-500/10 text-sky-400",
  rerendering: "bg-purple-500/10 text-purple-400",
  completed: "bg-emerald-500/10 text-emerald-400",
  failed: "bg-rose-500/10 text-rose-400",
  not_requested: "bg-slate-800 text-slate-400",
};

export default function JobList({ jobs, selectedJobId, onSelect }) {
  return (
    <div className="glass overflow-hidden">
      <div className="border-b border-slate-700/60 px-6 py-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
          Recent jobs
        </h3>
      </div>

      <ul className="divide-y divide-slate-800">
        {jobs.map((job) => (
          <li
            key={job.id}
            className={clsx(
              "cursor-pointer px-6 py-4 transition hover:bg-slate-900/60",
              selectedJobId === job.id && "bg-slate-900/60",
            )}
            onClick={() => onSelect(job.id)}
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-white">{job.topic}</p>
                <p className="text-xs text-slate-400">
                  {DateTime.fromISO(job.created_at).toRelative()}
                </p>
                <div className="mt-2 flex gap-2">
                  {[
                    { label: "S", value: job.script_status },
                    { label: "A", value: job.audio_status },
                    { label: "V", value: job.video_status },
                  ].map(({ label, value }) => (
                    <span
                      key={label}
                      className={clsx(
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                        statusColors[value] ?? "bg-slate-700 text-slate-300",
                      )}
                    >
                      {label}:{" "}
                      <span className="capitalize">{value ?? "n/a"}</span>
                    </span>
                  ))}
                </div>
              </div>
              <span
                className={clsx(
                  "rounded-full px-2.5 py-1 text-xs font-semibold capitalize",
                  statusColors[job.status] ?? "bg-slate-700 text-slate-300",
                )}
              >
                {job.status}
              </span>
            </div>
          </li>
        ))}
        {jobs.length === 0 && (
          <li className="px-6 py-8 text-center text-sm text-slate-500">
            No jobs yet. Submit your first topic.
          </li>
        )}
      </ul>
    </div>
  );
}
