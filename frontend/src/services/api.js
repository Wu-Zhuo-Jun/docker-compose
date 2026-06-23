import axios from "axios";

const API_BASE_URL = "/api";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

export const uploadDocument = async (file, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post("/documents/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });

  return response.data;
};

export const searchDocuments = async (query, topK = 10) => {
  const response = await apiClient.post("/documents/search", {
    query,
    top_k: topK,
  });
  return response.data;
};

export const qaSearch = async (query, topK = 10) => {
  const response = await apiClient.post("/documents/qa", {
    query,
    top_k: topK,
  });
  return response.data;
};

export const listDocuments = async () => {
  const response = await apiClient.get("/documents/list");
  return response.data;
};

export const deleteDocument = async (docId) => {
  const response = await apiClient.delete(`/documents/${docId}`);
  return response.data;
};

export default apiClient;
