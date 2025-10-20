import { useState } from "react";

const styles = [
  "Educational",
  "Inspirational",
  "Documentary",
  "Storytelling",
  "Explainer",
];

export default function JobForm({ onCreate, loading }) {
  const [topic, setTopic] = useState("");
  const [style, setStyle] = useState(styles[0]);
  const [length, setLength] = useState(180);

  const handleSubmit = (event) => {
    event.preventDefault();
    onCreate({ topic, style, length: Number(length) });
  };

  return (
    <form onSubmit={handleSubmit} className="glass p-6 space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">Generate a new video</h2>
        <p className="text-sm text-slate-400">
          Provide a topic, pick a style, and set the target length in seconds.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          Topic
        </label>
        <input
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 focus:border-primary focus:outline-none"
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
          placeholder="e.g. Rise of generative AI"
          required
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-slate-200 mb-1">
            Style
          </label>
          <select
            className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 focus:border-primary focus:outline-none"
            value={style}
            onChange={(event) => setStyle(event.target.value)}
          >
            {styles.map((option) => (
              <option value={option} key={option}>
                {option}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-200 mb-1">
            Length (seconds)
          </label>
          <input
            className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 focus:border-primary focus:outline-none"
            type="number"
            min={60}
            step={30}
            value={length}
            onChange={(event) => setLength(event.target.value)}
          />
        </div>
      </div>

      <button type="submit" className="btn-primary w-full" disabled={loading}>
        {loading ? "Submitting..." : "Start Generation"}
      </button>
    </form>
  );
}

