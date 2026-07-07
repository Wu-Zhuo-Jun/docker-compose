import { useEffect, useState } from "react";
import { Card, Button, Space, Tag, Skeleton, Empty, Typography } from "antd";
import { ArrowRightOutlined, FileTextOutlined, SearchOutlined, UploadOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import { listDocuments } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { linear } from "@/styles/tokens";

const { Text } = Typography;

export default function HomePage() {
  const { user, isGuest } = useAuth();
  const [stats, setStats] = useState({ total: 0, recent: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await listDocuments();
        if (!alive) return;
        const docs = data?.documents || [];
        setStats({
          total: docs.length,
          recent: docs.slice(0, 4),
        });
      } catch {
        if (alive) setStats({ total: 0, recent: [] });
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const greeting = greetingFor(user, isGuest);

  return (
    <div>
      <header style={{
        marginBottom: 32,
        padding: "8px 4px 8px 16px",
        borderLeft: "2px solid var(--ln-accent)",
      }}>
        <Text style={{
          color: linear.textDim,
          fontSize: 12,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}>
          {todayLabel()}
        </Text>
        <h1 className="ln-display" style={{ fontSize: 32, marginTop: 8 }}>
          {greeting}
        </h1>
        <Text style={{ color: linear.textMuted, fontSize: 15, display: "block", marginTop: 6 }}>
          {isGuest ? "你正在以访客身份使用,数据不会被保存。" : "继续管理你的文档,或开始一次新的检索。"}
        </Text>
      </header>

      <div style={styles.statsRow}>
        <StatCard
          icon={<FileTextOutlined />}
          label="文档总数"
          value={loading ? "—" : stats.total}
          hint="已建立索引的 Word / TXT 文档"
        />
        <StatCard
          icon={<SearchOutlined />}
          label="检索模式"
          value="双引擎"
          hint="向量召回 + 关键词重排"
          accent
        />
        <StatCard
          icon={<ThunderboltOutlined />}
          label="运行状态"
          value="正常"
          hint="ChromaDB · FastAPI · Vite"
          status="ok"
        />
      </div>

      <div style={styles.twoCol}>
        <Card style={styles.card}>
          <CardHeader title="最近文档" hint={`共 ${stats.total} 个`} />
          {loading ? (
            <Skeleton active paragraph={{ rows: 3 }} />
          ) : stats.recent.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={<span style={{ color: linear.textMuted }}>还没有任何文档</span>}
            >
              <Link to="/app/upload">
                <Button type="primary" icon={<UploadOutlined />}>上传第一个文档</Button>
              </Link>
            </Empty>
          ) : (
            <ul style={styles.list}>
              {stats.recent.map((doc) => (
                <li key={doc.doc_id} style={styles.listItem}>
                  <FileTextOutlined style={{ color: linear.textDim, fontSize: 14 }} />
                  <span style={styles.listName}>{doc.source || "未命名文档"}</span>
                  <Tag style={styles.metaTag}>{doc.total_chunks || 0} 块</Tag>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card style={styles.card}>
          <CardHeader title="快速开始" />
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <ActionRow
              to="/app/upload"
              icon={<UploadOutlined />}
              title="上传新文档"
              desc="支持 .docx / .txt,自动分块并建立索引"
            />
            <div style={styles.hairline} />
            <ActionRow
              to="/app/search"
              icon={<SearchOutlined />}
              title="智能检索"
              desc="用自然语言提问,或切换原始检索"
            />
            <div style={styles.hairline} />
            <ActionRow
              to="/app/list"
              icon={<FileTextOutlined />}
              title="管理文档"
              desc="查看、删除已上传的全部文档"
            />
          </Space>
        </Card>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, hint, accent, status }) {
  return (
    <div style={styles.statCard(accent)}>
      <div style={styles.statIcon(accent)}>{icon}</div>
      <div style={{ flex: 1 }}>
        <div style={styles.statLabel}>{label}</div>
        <div className="ln-display" style={styles.statValue(status)}>
          {value}
          {status === "ok" && (
            <span style={{
              display: "inline-block",
              width: 8,
              height: 8,
              borderRadius: 4,
              background: linear.success,
              marginLeft: 10,
              verticalAlign: "middle",
              boxShadow: "0 0 0 3px rgba(52,211,153,0.15)",
            }} />
          )}
        </div>
        <div style={styles.statHint}>{hint}</div>
      </div>
    </div>
  );
}

function CardHeader({ title, hint }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
      <h2 className="ln-display" style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>{title}</h2>
      {hint && <span style={{ fontSize: 12, color: linear.textDim }}>{hint}</span>}
    </div>
  );
}

function ActionRow({ to, icon, title, desc }) {
  return (
    <Link to={to} style={styles.actionRow}>
      <div style={styles.actionIcon}>{icon}</div>
      <div style={{ flex: 1 }}>
        <div style={styles.actionTitle}>{title}</div>
        <div style={styles.actionDesc}>{desc}</div>
      </div>
      <ArrowRightOutlined style={{ color: linear.textDim }} />
    </Link>
  );
}

function greetingFor(user, isGuest) {
  if (isGuest) return "欢迎,访客";
  if (!user) return "欢迎回来";
  const name = user.email.split("@")[0];
  return `欢迎回来,${name}`;
}

function todayLabel() {
  const d = new Date();
  const weekday = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][d.getDay()];
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日 · ${weekday}`;
}

const styles = {
  statsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 12,
    marginBottom: 16,
  },
  statCard: (accent) => ({
    display: "flex",
    gap: 16,
    padding: 20,
    background: "var(--ln-surface-1)",
    border: "1px solid var(--ln-hairline)",
    borderRadius: 12,
    transition: "border-color 200ms var(--ln-ease)",
    ...(accent && { borderColor: "rgba(94,106,210,0.30)" }),
  }),
  statIcon: (accent) => ({
    width: 36,
    height: 36,
    borderRadius: 8,
    background: accent ? "var(--ln-accent-surface)" : "var(--ln-surface-2)",
    color: accent ? linear.accent : linear.textMuted,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 16,
    flexShrink: 0,
  }),
  statLabel: {
    fontSize: 12,
    color: linear.textDim,
    letterSpacing: "0.02em",
  },
  statValue: (status) => ({
    fontSize: 24,
    fontWeight: 600,
    color: status === "ok" ? linear.success : linear.text,
    marginTop: 2,
  }),
  statHint: {
    fontSize: 12,
    color: linear.textDim,
    marginTop: 4,
  },
  twoCol: {
    display: "grid",
    gridTemplateColumns: "1.4fr 1fr",
    gap: 12,
    marginTop: 12,
  },
  card: {
    background: "var(--ln-surface-1)",
    border: "1px solid var(--ln-hairline)",
    borderRadius: 12,
  },
  list: { listStyle: "none", padding: 0, margin: 0 },
  listItem: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "12px 4px",
    borderBottom: "1px solid var(--ln-hairline)",
  },
  listName: {
    flex: 1,
    color: linear.text,
    fontSize: 14,
    fontWeight: 500,
  },
  metaTag: {
    background: "var(--ln-surface-2)",
    color: linear.textMuted,
    border: "1px solid var(--ln-hairline-strong)",
    fontSize: 11,
    margin: 0,
  },
  hairline: { height: 1, background: "var(--ln-hairline)" },
  actionRow: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "4px 0",
    textDecoration: "none",
    color: "inherit",
  },
  actionIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    background: "var(--ln-surface-2)",
    border: "1px solid var(--ln-hairline-strong)",
    color: linear.textMuted,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  actionTitle: { color: linear.text, fontSize: 14, fontWeight: 500 },
  actionDesc: { color: linear.textDim, fontSize: 12, marginTop: 2 },
};
