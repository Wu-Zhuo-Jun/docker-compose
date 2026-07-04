import { linear } from "@/styles/tokens";

export default function KnowledgePage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h1 className="ln-display" style={{ fontSize: 24 }}>知识库</h1>
      <div style={{
        padding: 40,
        background: linear.surface1,
        border: "1px solid var(--ln-hairline)",
        borderRadius: 12,
        textAlign: "center",
        color: linear.textMuted,
      }}>
        <p style={{ margin: 0 }}>按主题组织的知识库视图即将上线。</p>
        <p style={{ marginTop: 8, color: linear.textDim, fontSize: 12 }}>
          Curated collections, pinned docs, and shared spaces.
        </p>
      </div>
    </div>
  );
}
