import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const API_TOKEN = import.meta.env.VITE_API_TOKEN || "local-dev-token";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

client.interceptors.request.use((config) => {
  config.headers.Authorization = `Bearer ${API_TOKEN}`;
  return config;
});

export async function createJob(payload) {
  const response = await client.post("/jobs", payload);
  return response.data;
}

export async function listJobs(limit = 20) {
  const response = await client.get("/jobs", { params: { limit } });
  return response.data.items;
}

export async function fetchJob(jobId) {
  const response = await client.get(`/jobs/${jobId}`);
  return response.data;
}

export async function updateJob(jobId, payload) {
  const response = await client.patch(`/jobs/${jobId}`, payload);
  return response.data;
}

export async function rerenderJob(jobId) {
  const response = await client.post(`/jobs/${jobId}/rerender`);
  return response.data;
}

export async function fetchArtifact(jobId, type) {
  const response = await client.get(
    `/jobs/${jobId}/artifact/${type}`,
    type === "frames"
      ? {}
      : {
          responseType: type === "script" ? "text" : "blob",
        },
  );

  if (type === "script") {
    return response.data;
  }

  if (type === "frames") {
    return response.data;
  }

  const blob = response.data;
  const url = URL.createObjectURL(blob);
  return url;
}

export async function requestAudio(jobId, voice) {
  const response = await client.post(
    `/jobs/${jobId}/audio`,
    null,
    voice ? { params: { voice } } : undefined,
  );
  return response.data;
}

export async function requestVideo(jobId) {
  const response = await client.post(`/jobs/${jobId}/video`);
  return response.data;
}
