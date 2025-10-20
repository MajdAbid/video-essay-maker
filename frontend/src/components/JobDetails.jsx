import { useEffect, useMemo, useState } from "react";
import MetricCard from "./MetricCard.jsx";
import { fetchArtifact } from "../api.js";

function formatSeconds(seconds) {
  if (!seconds && seconds !== 0) return "—";
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  if (minutes === 0) {
    return `${seconds.toFixed(1)}s`;
  }
  return `${minutes}m ${remaining}s`;
}

const backendHost =
  import.meta.env.VITE_BACKEND_HOST || window.location.origin;

const statusClasses = {
  queued: "bg-slate-800 text-slate-200",
  processing: "bg-blue-500/10 text-blue-300",
  completed: "bg-emerald-500/10 text-emerald-300",
  failed: "bg-rose-500/10 text-rose-300",
  rerendering: "bg-purple-500/10 text-purple-300",
  not_requested: "bg-slate-800 text-slate-400",
};

function StageBadge({ label, value }) {
  const cls = statusClasses[value] || "bg-slate-700 text-slate-300";
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-slate-400">{label}</span>
      <span
        className={`inline-flex h-7 items-center justify-center rounded-md px-3 text-xs font-semibold capitalize ${cls}`}
      >
        {value || "unknown"}
      </span>
    </div>
  );
}

export default function JobDetails({
  job,
  onEdit,
  onRefresh,
  refreshing,
  onRequestAudio,
  onRequestVideo,
  audioLoading,
  videoLoading,
}) {
  const videoDownloadUrl = useMemo(() => {
    if (!job?.video_url) return null;
    if (job.video_url.startsWith("http")) return job.video_url;
    return `${backendHost}${job.video_url}`;
  }, [job]);

  const [audioUrl, setAudioUrl] = useState(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState(null);
  const videoFeatureEnabled =
    (import.meta.env.VITE_ENABLE_IMAGE_GENERATION ?? "true") !== "false";
  useEffect(() => {
    let objectUrl;
    if (job?.audio_status === "completed") {
      fetchArtifact(job.id, "audio")
        .then((url) => {
          objectUrl = url;
          setAudioUrl(url);
        })
        .catch(() => setAudioUrl(null));
    } else {
      setAudioUrl(null);
    }
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [job?.id, job?.audio_status]);

  useEffect(() => {
    let objectUrl;
    if (job?.video_status === "completed") {
      fetchArtifact(job.id, "video")
        .then((url) => {
          objectUrl = url;
          setVideoPreviewUrl(url);
        })
        .catch(() => setVideoPreviewUrl(null));
    } else {
      setVideoPreviewUrl(null);
    }

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [job?.id, job?.video_status]);

  if (!job) {
    return (
      <div className="glass flex flex-1 items-center justify-center p-12 text-slate-400">
        Select a job to see details.
      </div>
    );
  }

  const audioDisabled =
    job.script_status !== "completed" ||
    job.audio_status === "processing" ||
    audioLoading;
  const videoDisabled =
    !videoFeatureEnabled ||
    job.audio_status !== "completed" ||
    job.video_status === "processing" ||
    videoLoading;

  return (
    <div className="glass flex-1 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-white">{job.topic}</h2>
          <p className="text-sm text-slate-400">
            {job.style} • {job.length}s target length
          </p>
        </div>
        <div className="flex gap-3">
          <button className="btn-secondary" onClick={onRefresh} disabled={refreshing}>
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
          <button className="btn-primary" onClick={onEdit}>
            Edit & rerender
          </button>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricCard
          label="Generation time"
          value={job.generation_time ? formatSeconds(job.generation_time) : "Pending"}
          hint="From pipeline start to final artifacts."
        />
        <MetricCard
          label="Review score"
          value={
            job.review_score !== null && job.review_score !== undefined
              ? `${job.review_score}/100`
              : "Pending"
          }
          hint="LLM evaluator quality score."
        />
        <MetricCard
          label="Last updated"
          value={job.updated_at ? new Date(job.updated_at).toLocaleString() : "—"}
          hint="UTC timestamp"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StageBadge label="Script" value={job.script_status} />
        <StageBadge label="Audio" value={job.audio_status} />
        <StageBadge label="Video" value={job.video_status} />
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          className="btn-primary"
          onClick={() => onRequestAudio()}
          disabled={audioDisabled}
        >
          {audioLoading
            ? "Requesting audio..."
            : job.audio_status === "completed"
            ? "Regenerate audio"
            : "Generate audio"}
        </button>
        <button
          className="btn-secondary"
          onClick={onRequestVideo}
          disabled={videoDisabled}
        >
          {videoFeatureEnabled
            ? videoLoading
              ? "Requesting video..."
              : job.video_status === "completed"
              ? "Regenerate video"
              : "Generate video"
            : "Video disabled"}
        </button>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
            Script
          </h3>
          <pre className="mt-2 max-h-72 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-100">
            {job.script || "Script not available yet."}
          </pre>
        </div>

        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
              Transcript
            </h3>
            <pre className="mt-2 max-h-60 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-100">
              {job.transcript || "Transcript not available yet."}
            </pre>
          </div>

          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
              Audio preview
            </h3>
            {job.audio_status === "completed" && audioUrl ? (
              <audio
                controls
                className="mt-2 w-full rounded-lg border border-slate-800 bg-slate-950"
                src={audioUrl}
              />
            ) : (
              <div className="mt-2 flex h-16 items-center justify-center rounded-lg border border-dashed border-slate-700 text-sm text-slate-500">
                {job.audio_status === "failed"
                  ? "Audio generation failed."
                  : "Audio not available yet."}
              </div>
            )}
          </div>

          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
              Video preview
            </h3>
            {videoPreviewUrl ? (
              <video
                key={videoPreviewUrl}
                controls
                className="mt-2 aspect-video w-full rounded-lg border border-slate-800 bg-black"
                src={videoPreviewUrl}
              />
            ) : (
              <div className="mt-2 flex h-48 items-center justify-center rounded-lg border border-dashed border-slate-700 text-sm text-slate-500">
                {job.video_status === "failed"
                  ? "Video generation failed."
                  : "Final MP4 not ready yet."}
              </div>
            )}
            <div className="mt-3 flex gap-3">
              {job.video_url && (
                <a
                  className="btn-secondary"
                  href={videoDownloadUrl ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download MP4
                </a>
              )}
              <a
                className="btn-secondary"
                href={import.meta.env.VITE_GRAFANA_URL || "http://localhost:3001"}
                target="_blank"
                rel="noreferrer"
              >
                Open dashboard
              </a>
            </div>
          </div>
        </div>
      </div>

      {job.youtube_context?.results?.length ? (
        <div className="mt-6">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
            YouTube research
          </h3>
          <div className="mt-2 rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-200">
            {job.youtube_context.summary ? (
              <pre className="whitespace-pre-wrap text-xs text-slate-300">
                {job.youtube_context.summary}
              </pre>
            ) : (
              <p className="text-sm text-slate-400">No summary available.</p>
            )}

            <div className="mt-4 space-y-3">
              {job.youtube_context.transcripts?.slice(0, 3).map((entry) => (
                <div key={entry.video_id} className="rounded-md border border-slate-800 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <a
                      href={entry.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm font-semibold text-primary hover:underline"
                    >
                      {entry.title}
                    </a>
                    <span className="text-xs text-slate-500">{entry.channel}</span>
                  </div>
                  {entry.transcript ? (
                    <p className="mt-2 text-xs text-slate-400">
                      {entry.transcript.length > 320
                        ? `${entry.transcript.slice(0, 320)}…`
                        : entry.transcript}
                    </p>
                  ) : (
                    <p className="mt-2 text-xs text-slate-500">Transcript unavailable.</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
