import { useEffect, useState } from "react";

export default function EditModal({
  open,
  script,
  transcript,
  imagePrompts,
  onClose,
  onSave,
  saving,
}) {
  const [localScript, setLocalScript] = useState(script ?? "");
  const [localTranscript, setLocalTranscript] = useState(transcript ?? "");
  const [localPrompts, setLocalPrompts] = useState(
    JSON.stringify(imagePrompts ?? {}, null, 2),
  );
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setLocalScript(script ?? "");
      setLocalTranscript(transcript ?? "");
      setLocalPrompts(JSON.stringify(imagePrompts ?? {}, null, 2));
      setError("");
    }
  }, [open, script, transcript, imagePrompts]);

  if (!open) {
    return null;
  }

  const handleSave = () => {
    try {
      const parsedPrompts = JSON.parse(localPrompts);
      onSave({
        script: localScript,
        transcript: localTranscript,
        image_prompts: parsedPrompts,
      });
    } catch (err) {
      setError("Invalid JSON for image prompts.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
      <div className="glass w-full max-w-5xl max-h-[90vh] overflow-y-auto p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-white">
              Edit script & prompts
            </h3>
            <p className="text-sm text-slate-400">
              Update the narration or the image prompts, then trigger a
              rerender.
            </p>
          </div>
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="flex flex-col space-y-2">
            <label className="text-sm font-semibold text-slate-200">
              Script
            </label>
            <textarea
              className="min-h-[320px] w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-primary focus:outline-none"
              value={localScript}
              onChange={(event) => setLocalScript(event.target.value)}
            />
          </div>
          <div className="flex flex-col space-y-2">
            <label className="text-sm font-semibold text-slate-200">
              Transcript (verbatim narration)
            </label>
            <textarea
              className="min-h-[320px] w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-primary focus:outline-none"
              value={localTranscript}
              onChange={(event) => setLocalTranscript(event.target.value)}
            />
          </div>
        </div>

        <div className="mt-6 flex flex-col space-y-2">
          <label className="text-sm font-semibold text-slate-200">
            Image prompts (JSON)
          </label>
          <textarea
            className="min-h-[320px] w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-primary focus:outline-none"
            value={localPrompts}
            onChange={(event) => setLocalPrompts(event.target.value)}
          />
        </div>

        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}

        <div className="mt-6 flex justify-end gap-3">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save & Re-render"}
          </button>
        </div>
      </div>
    </div>
  );
}
