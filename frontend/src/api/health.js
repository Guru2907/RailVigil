import axiosClient from "./axiosClient.js";

export const getHealth = () => axiosClient.get("/health", { timeout: 4000 });
