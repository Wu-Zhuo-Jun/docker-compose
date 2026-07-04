import { Spin } from "antd";
import { linear } from "@/styles/tokens";

export default function RecentPage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h1 className="ln-display" style={{ fontSize: 24 }}>最近访问</h1>
      <div style={{
        padding: 40,
        background: linear.surface1,
        border: "1px solid var(--ln-hairline)",
        borderRadius: 12,
        textAlign: "center",
        color: linear.textMuted,
      }}>
        <p style={{ margin: 0 }}>正在追踪你的访问轨迹,即将上线。</p>
        <p style={{ marginTop: 8, color: linear.textDim, fontSize: 12 }}>
          This page will list recently touched documents.
        </p>
      </div>
    </div>
  );
}
