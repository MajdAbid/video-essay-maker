import { useEffect, useMemo, useState } from "react";
import {
  createJob,
  fetchJob,
  listJobs,
  rerenderJob,
  updateJob,
  requestAudio,
  requestVideo,
} from "./api.js";
import EditModal from "./components/EditModal.jsx";
import JobDetails from "./components/JobDetails.jsx";
import JobForm from "./components/JobForm.jsx";
import JobList from "./components/JobList.jsx";

const processingStates = new Set(["processing", "rerendering"]);
const pendingStates = new Set(["queued"]);

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [audioLoading, setAudioLoading] = useState(false);
  const [videoLoading, setVideoLoading] = useState(false);

  const activeJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );

  useEffect(() => {
    refreshJobs();
  }, []);

  useEffect(() => {
    if (!selectedJobId) return;

    fetchJob(selectedJobId)
      .then(setSelectedJob)
      .catch((error) => {
        console.error(error);
        setFeedback("Failed to fetch job details.");
      });
  }, [selectedJobId]);

  // Poll details when any stage is still in progress or queued.
  useEffect(() => {
    if (!selectedJob) return;

    const shouldPoll =
      processingStates.has(selectedJob.status) ||
      processingStates.has(selectedJob.script_status) ||
      processingStates.has(selectedJob.audio_status) ||
      processingStates.has(selectedJob.video_status) ||
      pendingStates.has(selectedJob.script_status) ||
      pendingStates.has(selectedJob.audio_status) ||
      pendingStates.has(selectedJob.video_status);

    if (!shouldPoll) return;

    const interval = setInterval(() => {
      fetchJob(selectedJob.id)
        .then((data) => {
          setSelectedJob(data);
          refreshJobs(false);
        })
        .catch((error) => {
          console.error(error);
        });
    }, 5000);
    return () => clearInterval(interval);
  }, [selectedJob]);

  const refreshJobs = async (resetSelection = true) => {
    try {
      const items = await listJobs();
      setJobs(items);
      if (resetSelection && items.length > 0) {
        setSelectedJobId(items[0].id);
      }
    } catch (error) {
      console.error(error);
      setFeedback("Unable to load jobs from the API.");
    }
  };

  const handleCreateJob = async (payload) => {
    try {
      setLoading(true);
      const job = await createJob(payload);
      setFeedback("Job created. Script generation started.");
      await refreshJobs(false);
      setSelectedJobId(job.id);
      setSelectedJob(job);
    } catch (error) {
      console.error(error);
      setFeedback("Failed to create job. Check API logs.");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveEdits = async (payload) => {
    if (!selectedJobId) return;
    try {
      setSavingEdit(true);
      await updateJob(selectedJobId, payload);
      await rerenderJob(selectedJobId);
      setFeedback("Edits saved. Rerender triggered.");
      setShowModal(false);
      const updated = await fetchJob(selectedJobId);
      setSelectedJob(updated);
      await refreshJobs(false);
    } catch (error) {
      console.error(error);
      setFeedback("Failed to save edits.");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleRefresh = async () => {
    if (!selectedJobId) return;
    try {
      setRefreshing(true);
      const updated = await fetchJob(selectedJobId);
      setSelectedJob(updated);
      await refreshJobs(false);
    } catch (error) {
      console.error(error);
      setFeedback("Failed to refresh job.");
    } finally {
      setRefreshing(false);
    }
  };

  const handleRequestAudio = async (voice) => {
    if (!selectedJobId) return;
    try {
      setAudioLoading(true);
      await requestAudio(selectedJobId, voice);
      const updated = await fetchJob(selectedJobId);
      setSelectedJob(updated);
      await refreshJobs(false);
      setFeedback("Audio generation requested.");
    } catch (error) {
      console.error(error);
      setFeedback("Failed to request audio. Check API logs.");
    } finally {
      setAudioLoading(false);
    }
  };

  const handleRequestVideo = async () => {
    if (!selectedJobId) return;
    try {
      setVideoLoading(true);
      await requestVideo(selectedJobId);
      const updated = await fetchJob(selectedJobId);
      setSelectedJob(updated);
      await refreshJobs(false);
      setFeedback("Video generation requested.");
    } catch (error) {
      console.error(error);
      setFeedback("Failed to request video. Check API logs.");
    } finally {
      setVideoLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-4 py-8 sm:px-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold text-white">Video Essay Maker</h1>
        <p className="text-sm text-slate-400">
          Submit topics, monitor the async pipeline, edit artifacts, and
          rerender final videos with full observability.
        </p>
      </header>

      {feedback && (
        <div className="glass border-l-4 border-primary px-4 py-3 text-sm text-slate-100">
          {feedback}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        <div className="space-y-6">
          <JobForm onCreate={handleCreateJob} loading={loading} />
          <JobList
            jobs={jobs}
            selectedJobId={selectedJobId}
            onSelect={setSelectedJobId}
          />
        </div>
        <JobDetails
          job={selectedJob}
          onEdit={() => setShowModal(true)}
          onRefresh={handleRefresh}
          refreshing={refreshing}
          onRequestAudio={handleRequestAudio}
          onRequestVideo={handleRequestVideo}
          audioLoading={audioLoading}
          videoLoading={videoLoading}
        />
      </div>

      <EditModal
        open={showModal}
        script={selectedJob?.script}
        transcript={selectedJob?.transcript}
        imagePrompts={selectedJob?.image_prompts}
        onClose={() => setShowModal(false)}
        onSave={handleSaveEdits}
        saving={savingEdit}
      />
    </div>
  );
}
