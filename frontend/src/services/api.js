import axios from "axios";

const API_BASE_URL = "/api";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

// ============================================================================
// 文档相关 API
// ============================================================================

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

// 上传到待审核列表（普通用户）
export const uploadPendingDocument = async (file, uploaderId, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post(
    `/documents/upload-pending?uploader_id=${uploaderId}`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    }
  );

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

// ============================================================================
// 会话管理 API
// ============================================================================

export const listSessions = async (userId, limit = 50) => {
  const response = await apiClient.get(
    `/chat/sessions?user_id=${userId}&limit=${limit}`
  );
  return response.data;
};

export const createSession = async (userId, title = "新对话") => {
  const response = await apiClient.post(
    `/chat/sessions?user_id=${userId}`,
    { title }
  );
  return response.data;
};

export const getSession = async (sessionId, userId) => {
  const response = await apiClient.get(
    `/chat/sessions/${sessionId}?user_id=${userId}`
  );
  return response.data;
};

export const deleteSession = async (sessionId, userId) => {
  const response = await apiClient.delete(
    `/chat/sessions/${sessionId}?user_id=${userId}`
  );
  return response.data;
};

export const multiTurnQA = async (userId, query, sessionId = null, topK = 10) => {
  const response = await apiClient.post(
    `/chat/qa?user_id=${userId}`,
    {
      query,
      session_id: sessionId,
      top_k: topK,
    }
  );
  return response.data;
};

/**
 * 流式多轮问答 (SSE)
 *
 * @param userId 用户ID
 * @param query 问题
 * @param sessionId 会话ID（可选）
 * @param topK 检索数量
 * @param handlers 事件回调: { onSession, onChunk, onSources, onDone, onError, onTitle }
 * @returns AbortController,用于中断流
 */
export const multiTurnQAStream = (userId, query, sessionId, topK = 10, handlers = {}) => {
  const controller = new AbortController();
  const params = new URLSearchParams({ user_id: String(userId) });
  const url = `/chat/qa/stream?${params.toString()}`;

  (async () => {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          session_id: sessionId || null,
          top_k: topK,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        let detail = "请求失败";
        try {
          const body = await res.json();
          detail = body.detail || detail;
        } catch {}
        handlers.onError?.(new Error(detail));
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let currentEvent = "message";
      let currentData = "";

      const dispatch = () => {
        if (!currentData) return;
        try {
          const data = JSON.parse(currentData);
          switch (currentEvent) {
            case "session":
              handlers.onSession?.(data);
              break;
            case "chunk":
              handlers.onChunk?.(data);
              break;
            case "sources":
              handlers.onSources?.(data);
              break;
            case "done":
              handlers.onDone?.(data);
              break;
            case "error":
              handlers.onError?.(new Error(data.detail || "流式错误"));
              break;
            default:
              break;
          }
        } catch (e) {
          // 忽略解析错误
        }
        currentEvent = "message";
        currentData = "";
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // 解析 SSE 帧
        let idx;
        while ((idx = buffer.indexOf("\n")) >= 0) {
          const line = buffer.slice(0, idx).replace(/\r$/, "");
          buffer = buffer.slice(idx + 1);
          if (line === "") {
            dispatch();
          } else if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const piece = line.slice(5).trim();
            currentData = currentData ? currentData + "\n" + piece : piece;
          }
        }
      }
      // 收尾
      if (currentData) dispatch();
    } catch (err) {
      if (err.name === "AbortError") {
        return;
      }
      handlers.onError?.(err);
    }
  })();

  return controller;
};

export const updateSession = async (sessionId, userId, payload) => {
  const response = await apiClient.patch(
    `/chat/sessions/${sessionId}?user_id=${userId}`,
    payload
  );
  return response.data;
};

// ============================================================================
// 文档审核 API
// ============================================================================

export const listPendingReviews = async (adminId) => {
  const response = await apiClient.get(
    `/documents/reviews/pending?admin_id=${adminId}`
  );
  return response.data;
};

export const listAllReviews = async (adminId, status = null) => {
  const params = new URLSearchParams({ admin_id: String(adminId) });
  if (status) params.append("status", status);
  const response = await apiClient.get(
    `/documents/reviews/all?${params.toString()}`
  );
  return response.data;
};

export const approveReview = async (reviewId, reviewerId, comment = null) => {
  const response = await apiClient.post(
    `/documents/reviews/${reviewId}/approve`,
    {
      reviewer_id: reviewerId,
      comment,
    }
  );
  return response.data;
};

export const rejectReview = async (reviewId, reviewerId, comment = null) => {
  const response = await apiClient.post(
    `/documents/reviews/${reviewId}/reject`,
    {
      reviewer_id: reviewerId,
      comment,
    }
  );
  return response.data;
};

export default apiClient;
