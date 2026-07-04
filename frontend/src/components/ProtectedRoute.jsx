import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Spin } from "antd";

export default function ProtectedRoute({ children }) {
  const { hydrated, isAuthenticated, isGuest } = useAuth();
  const location = useLocation();

  if (!hydrated) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--ln-ground)",
      }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!isAuthenticated && !isGuest) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return children;
}
