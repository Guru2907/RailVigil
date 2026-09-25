import axiosClient from "./axiosClient.js";

export async function listIncidents(params = {}) {
  const { data } = await axiosClient.get("/incidents", { params });
  return data;
}

export async function getIncident(incidentId) {
  const { data } = await axiosClient.get(`/incidents/${incidentId}`);
  return data;
}