import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Result, Button, Spin } from "antd";

export default function ProtectedRoute({ children, requireRole }) {
  const { hydrated, isAuthenticated, isGuest, user } = useAuth();
  console.log(user);
  const location = useLocation();

  if (!hydrated) {
    return (
      <div
        style={{
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

  if (requireRole && isAuthenticated && user?.role !== requireRole) {
    return (
      <div
        style={{
          minHeight: "calc(100vh - 56px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}>
        <Result
          status="403"
          title="无权访问"
          subTitle={`该页面仅 ${requireRole === "admin" ? "管理员" : requireRole} 用户可访问`}
          extra={
            <Button type="primary" onClick={() => window.history.back()}>
              返回
            </Button>
          }
        />
      </div>
    );
  }

  return children;
}
