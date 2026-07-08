import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme as antdTheme, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import { antdTheme as lnTokens, linear } from "@/styles/tokens";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppShell from "@/components/AppShell";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import HomePage from "@/pages/HomePage";
import UploadPage from "@/pages/UploadPage";
import SearchPage from "@/pages/SearchPage";
import DocumentListPage from "@/pages/DocumentListPage";
import RecentPage from "@/pages/RecentPage";
import KnowledgePage from "@/pages/KnowledgePage";
import ChatPage from "@/pages/ChatPage";
import AdminReviewPage from "@/pages/AdminReviewPage";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        ...lnTokens("dark"),
        algorithm: antdTheme.darkAlgorithm,
      }}
    >
      <AntApp>
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/app"
                element={
                  <ProtectedRoute>
                    <AppShell />
                  </ProtectedRoute>
                }
              >
                <Route index element={<HomePage />} />
                <Route path="upload" element={<UploadPage />} />
                <Route path="search" element={<SearchPage />} />
                <Route path="list" element={<DocumentListPage />} />
                <Route path="recent" element={<RecentPage />} />
                <Route path="knowledge" element={<KnowledgePage />} />
                <Route path="chat" element={<ChatPage />} />
                <Route path="review" element={<AdminReviewPage />} />
              </Route>
              <Route path="/" element={<Navigate to="/app" replace />} />
              <Route path="*" element={<Navigate to="/app" replace />} />
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>
);
