import axios, { AxiosInstance } from "axios";
import { useAuthStore } from "../store/useAuthStore";
import { getConfig } from "./config";

const config = getConfig();

interface ExtendedAxiosInstance extends AxiosInstance {
  get_all_pages: (path: string, pageSize: number) => Promise<any[]>;
}

const api: ExtendedAxiosInstance = axios.create({
  baseURL: config.apiUrl, // Set your API base URL here
});

api.interceptors.request.use((config) => {
  const state = useAuthStore.getState();
  if (state.token) {
    config.headers.Authorization = `Bearer ${state.token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      useAuthStore.getState().logout();
      // Redirect to login or show message
    }
    return Promise.reject(error);
  },
);

api.get_all_pages = async (path: string, pageSize: number) => {
  try {
    // Fetch the first page to get total page count
    const initialResponse = await api.get(`${path}?page=1&size=${pageSize}`);
    const totalPages = initialResponse.data.pages;

    // Fetch all pages concurrently
    const pagePromises = [];
    for (let page = 1; page <= totalPages; page++) {
      pagePromises.push(api.get(`${path}?page=${page}&size=${pageSize}`));
    }

    const pageResponses = await Promise.all(pagePromises);
    return pageResponses.flatMap((response) => response.data.items);
  } catch (error) {
    console.error("Error fetching pages:", error);
    return [];
  }
};

export default api;
