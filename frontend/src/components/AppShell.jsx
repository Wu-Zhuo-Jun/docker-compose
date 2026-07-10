import { useState, useMemo } from "react";
import { Layout, Menu, Dropdown, Avatar, Tag, Tooltip, App as AntApp } from "antd";
import {
  UploadOutlined,
  SearchOutlined,
  FileTextOutlined,
  UserOutlined,
  LogoutOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  BookOutlined,
  MessageOutlined,
  AuditOutlined,
} from "@ant-design/icons";
import { Outlet, useLocation, useNavigate, NavLink } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { linear } from "@/styles/tokens";

const { Header, Content, Sider } = Layout;

const navItems = [
  { key: "/app/chat", icon: <MessageOutlined />, label: "智能对话", shortcut: "C" },
  { key: "/app/search", icon: <SearchOutlined />, label: "智能检索", shortcut: "S" },
  { key: "/app/upload", icon: <UploadOutlined />, label: "上传文档", shortcut: "U" },
  { key: "/app/list", icon: <FileTextOutlined />, label: "文档列表", shortcut: "L" },
];

const secondaryItems = [
  { key: "/app/recent", icon: <ClockCircleOutlined />, label: "最近访问" },
  { key: "/app/knowledge", icon: <BookOutlined />, label: "知识库" },
  { key: "/app/review", icon: <AuditOutlined />, label: "文档审核" },
];

export default function AppShell() {
  const { user, isGuest, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { modal } = AntApp.useApp();
  const [collapsed, setCollapsed] = useState(false);

  const selectedKey = useMemo(() => {
    const m = navItems.find((n) => location.pathname.startsWith(n.key));
    if (m) return m.key;
    const sec = secondaryItems.find((n) => location.pathname.startsWith(n.key));
    return sec ? sec.key : "/app/chat";
  }, [location.pathname]);

  const handleLogout = () => {
    modal.confirm({
      title: "退出登录?",
      content: "退出后需要重新登录才能使用完整功能。",
      okText: "退出",
      cancelText: "取消",
      onOk: () => {
        logout();
        navigate("/login", { replace: true });
      },
    });
  };

  const userMenu = {
    items: [
      {
        key: "email",
        label: user ? user.username : "访客模式",
        icon: <UserOutlined />,
        disabled: true,
      },
      { type: "divider" },
      {
        key: "logout",
        label: "退出登录",
        icon: <LogoutOutlined />,
        danger: true,
        onClick: handleLogout,
      },
    ],
  };

  return (
    <>
      {/* Purple-black ambient layers — static, behind everything in /app */}
      <div className="app-mesh-top" />
      <div className="app-mesh-corner-tl" />
      <div className="app-mesh-corner-br" />
      <div className="app-grid" />
      <div className="app-grain" />
      <Layout style={{ minHeight: "100vh", background: "transparent", position: "relative", zIndex: 1 }}>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          width={232}
          collapsedWidth={64}
          theme="dark"
          style={{
            background: "var(--ln-ground)",
            borderRight: "1px solid var(--ln-hairline)",
          }}>
          <BrandMark collapsed={collapsed} />
          <div style={{ padding: "8px 12px 0" }}>
            <SectionLabel>工作区</SectionLabel>
            <Menu
              theme="dark"
              mode="inline"
              selectedKeys={[selectedKey]}
              onClick={({ key }) => navigate(key)}
              items={navItems.map((i) => ({
                key: i.key,
                icon: i.icon,
                label: <NavItemLabel label={i.label} shortcut={i.shortcut} />,
              }))}
              style={{ background: "transparent", border: "none" }}
            />
          </div>

          <div style={{ padding: "16px 12px 0" }}>
            <SectionLabel>浏览</SectionLabel>
            <Menu
              theme="dark"
              mode="inline"
              items={secondaryItems.map((i) => ({
                key: i.key,
                icon: i.icon,
                label: i.label,
              }))}
              onClick={({ key }) => navigate(key)}
              selectedKeys={[selectedKey]}
              style={{ background: "transparent", border: "none" }}
            />
          </div>

          <div style={styles.siderFooter(collapsed)}>
            <GuestBadge visible={isGuest} />
          </div>
        </Sider>

        <Layout style={{ background: "transparent" }}>
          <Header style={styles.header}>
            <BreadcrumbLite pathname={location.pathname} />
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Tooltip title="按 ⌘K 打开命令面板 (即将推出)">
                <div style={styles.searchChip}>
                  <SearchOutlined style={{ color: linear.textDim, fontSize: 13 }} />
                  <span style={{ marginLeft: 8, color: linear.textMuted, fontSize: 13 }}>搜索</span>
                  <span style={{ marginLeft: 16, display: "flex", gap: 4 }}>
                    <span className="ln-kbd">⌘</span>
                    <span className="ln-kbd">K</span>
                  </span>
                </div>
              </Tooltip>
              <Dropdown menu={userMenu} trigger={["click"]} placement="bottomRight">
                <div style={styles.userChip}>
                  <Avatar
                    size={28}
                    style={{
                      background: isGuest ? linear.surface2 : linear.accentSurface,
                      color: isGuest ? linear.textMuted : linear.accent,
                      fontSize: 12,
                      fontWeight: 600,
                    }}>
                    {user ? user.username[0].toUpperCase() : <ThunderboltOutlined />}
                  </Avatar>
                  <span style={styles.userName}>{user ? user.username : "访客"}</span>
                </div>
              </Dropdown>
            </div>
          </Header>

          <Content style={styles.content}>
            <div style={styles.contentInner}>
              <Outlet />
            </div>
          </Content>
        </Layout>
      </Layout>
    </>
  );
}

function BrandMark({ collapsed }) {
  return (
    <div style={styles.brand(collapsed)}>
      <div style={styles.brandMark}>
        <div style={{ ...styles.brandMarkDot, background: linear.accent }} />
      </div>
      {!collapsed && (
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.2 }}>
          <span className="ln-display" style={{ fontSize: 14, fontWeight: 600 }}>
            恒华客流
          </span>
          {/* <span style={{ fontSize: 10, color: linear.textDim, letterSpacing: "0.04em", textTransform: "uppercase" }}>
            Documents · v1
          </span> */}
        </div>
      )}
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div
      style={{
        fontSize: 10,
        color: linear.textDim,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        padding: "12px 12px 8px",
        fontWeight: 500,
      }}>
      {children}
    </div>
  );
}

function NavItemLabel({ label, shortcut }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span>{label}</span>
      {shortcut && <span className="ln-kbd">{shortcut}</span>}
    </div>
  );
}

function GuestBadge({ visible }) {
  if (!visible) return null;
  return (
    <Tag style={styles.guestBadge}>
      <ThunderboltOutlined style={{ marginRight: 4 }} />
      访客模式
    </Tag>
  );
}

function BreadcrumbLite({ pathname }) {
  const segs = pathname.split("/").filter(Boolean);
  const label = segs[segs.length - 1] || "chat";
  const map = {
    upload: "上传文档",
    search: "智能检索",
    list: "文档列表",
    app: "工作台",
    chat: "智能对话",
    review: "文档审核",
  };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, color: linear.textMuted, fontSize: 13 }}>
      <NavLink to="/app" style={{ color: linear.textDim, textDecoration: "none" }}>
        工作台
      </NavLink>
      <span style={{ color: linear.textDim }}>/</span>
      <span style={{ color: linear.text }}>{map[label] || label}</span>
    </div>
  );
}

const styles = {
  header: {
    height: 56,
    padding: "0 24px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "rgba(8, 9, 10, 0.7)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
    borderBottom: "1px solid var(--ln-hairline)",
    position: "sticky",
    top: 0,
    zIndex: 10,
  },
  content: {
    padding: 0,
  },
  contentInner: {
    padding: "32px 40px",
    maxWidth: 1280,
    margin: "0 auto",
  },
  brand: (collapsed) => ({
    height: 56,
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: collapsed ? "0 20px" : "0 16px",
    borderBottom: "1px solid var(--ln-hairline)",
    justifyContent: collapsed ? "center" : "flex-start",
  }),
  brandMark: {
    width: 26,
    height: 26,
    borderRadius: 6,
    background: "var(--ln-surface-2)",
    border: "1px solid var(--ln-hairline-strong)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  brandMarkDot: { width: 12, height: 12, borderRadius: 4 },
  searchChip: {
    display: "flex",
    alignItems: "center",
    height: 32,
    padding: "0 10px",
    background: "var(--ln-surface-2)",
    border: "1px solid var(--ln-hairline-strong)",
    borderRadius: 6,
    minWidth: 240,
    cursor: "pointer",
  },
  userChip: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "4px 10px 4px 4px",
    height: 36,
    background: "var(--ln-surface-2)",
    border: "1px solid var(--ln-hairline-strong)",
    borderRadius: 6,
    cursor: "pointer",
  },
  userName: {
    color: linear.text,
    fontSize: 13,
    fontWeight: 500,
    maxWidth: 140,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  guestBadge: {
    background: linear.accentSurface,
    color: linear.accent,
    border: "1px solid rgba(94,106,210,0.25)",
    fontSize: 11,
    margin: 0,
  },
  siderFooter: (collapsed) => ({
    position: "absolute",
    bottom: 16,
    left: collapsed ? 0 : 16,
    right: collapsed ? 0 : 16,
    display: "flex",
    justifyContent: collapsed ? "center" : "flex-start",
  }),
};
