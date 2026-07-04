import { useState, useEffect } from "react";
import { Form, Input, Button, Checkbox, App as AntApp, Typography, Divider } from "antd";
import { LockOutlined, MailOutlined, ArrowRightOutlined, EyeInvisibleOutlined, EyeTwoTone } from "@ant-design/icons";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { linear } from "@/styles/tokens";

const { Title, Text } = Typography;

export default function LoginPage() {
  const { login, enterAsGuest, logout, isAuthenticated, isGuest, hydrated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { message } = AntApp.useApp();
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  // Dev/debug: ?clear=1 wipes stored auth so the user lands on a fresh login form.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("clear") === "1") {
      logout();
      navigate("/login", { replace: true });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (hydrated && !submitting && (isAuthenticated || isGuest)) {
    const dest = location.state?.from?.pathname || "/app";
    return <Navigate to={dest} replace />;
  }

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      await login(values);
      message.success("登录成功");
      const dest = location.state?.from?.pathname || "/app";
      navigate(dest, { replace: true });
    } catch (err) {
      if (err?.code === "INVALID_CREDENTIALS") {
        form.setFields([{ name: "password", errors: [err.message] }]);
      } else {
        message.error("登录失败,请重试");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleGuest = () => {
    enterAsGuest();
    message.info("已以访客身份进入,部分功能不可用");
    navigate("/app", { replace: true });
  };

  return (
    <div style={styles.page}>
      {/* Ambient motion layer — two slowly drifting orbs + fine grain.
          Kept inside the page container so it never bleeds into the app shell. */}
      <div className="login-aurora" />
      <div className="login-grain" />
      <div style={styles.card}>
        {/* Brand mark — linear.md signature: hairline mark, no logo asset to fake */}
        <div style={styles.brandRow}>
          <BrandMark />
          <span className="ln-mono" style={styles.brandWord}>compose-yml</span>
        </div>

        <div style={{ marginTop: 40 }}>
          <h1 className="ln-display" style={styles.title}>
            登录工作台
          </h1>
          <Text style={styles.subtitle}>
            使用邮箱和密码进入文档管理与检索系统
          </Text>
        </div>

        <Form
          form={form}
          layout="vertical"
          requiredMark={false}
          onFinish={handleSubmit}
          initialValues={{ remember: true }}
          style={{ marginTop: 32 }}
          autoComplete="on"
        >
          <Form.Item
            name="email"
            label={<span style={styles.label}>邮箱</span>}
            rules={[
              { required: true, message: "请输入邮箱" },
              { max: 64, message: "邮箱过长" },
            ]}
          >
            <Input
              size="large"
              prefix={<MailOutlined style={styles.inputIcon} />}
              placeholder="you@company.com"
              autoComplete="username"
              autoFocus
            />
          </Form.Item>

          <Form.Item
            name="password"
            label={<span style={styles.label}>密码</span>}
            rules={[
              { required: true, message: "请输入密码" },
              { min: 6, message: "密码至少 6 位" },
              { max: 64, message: "密码过长" },
            ]}
            style={{ marginTop: 16 }}
          >
            <Input.Password
              size="large"
              prefix={<LockOutlined style={styles.inputIcon} />}
              placeholder="至少 6 位"
              autoComplete="current-password"
              iconRender={(visible) =>
                visible ? <EyeTwoTone twoToneColor={linear.textMuted} /> : <EyeInvisibleOutlined style={styles.inputIcon} />
              }
            />
          </Form.Item>

          <div style={styles.formMeta}>
            <Form.Item name="remember" valuePropName="checked" noStyle>
              <Checkbox>记住我 30 天</Checkbox>
            </Form.Item>
            <Link to="#" style={styles.forgotLink}>忘记密码?</Link>
          </div>

          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            loading={submitting}
            icon={!submitting && <ArrowRightOutlined />}
            iconPosition="end"
            style={{ marginTop: 8, height: 44 }}
          >
            {submitting ? "登录中" : "登录"}
          </Button>
        </Form>

        <Divider plain style={{ margin: "24px 0 16px", color: linear.textDim, fontSize: 12 }}>
          或
        </Divider>

        <Button
          size="large"
          block
          onClick={handleGuest}
          style={styles.guestBtn}
        >
          临时访客进入
          <Text style={{ marginLeft: 8, color: linear.textDim, fontSize: 12 }}>
            无需登录 · 仅体验
          </Text>
        </Button>

        <div style={styles.footer}>
          <Text style={{ color: linear.textDim, fontSize: 12 }}>
            测试账号 · <span className="ln-mono">admin@local.dev / admin123</span>
          </Text>
        </div>
      </div>
    </div>
  );
}

function BrandMark() {
  return (
    <div style={styles.brandMark}>
      <div style={{ ...styles.brandMarkDot, background: linear.accent }} />
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    background: "var(--ln-ground)",
    position: "relative",
  },
  card: {
    width: "100%",
    maxWidth: 400,
    padding: 32,
    background: "var(--ln-surface-1)",
    border: "1px solid var(--ln-hairline)",
    borderRadius: "var(--ln-radius-md)",
    boxShadow: "0 1px 2px rgba(0,0,0,0.3)",
    position: "relative",
    zIndex: 1,
  },
  brandRow: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  brandMark: {
    width: 24,
    height: 24,
    borderRadius: 6,
    background: "var(--ln-surface-2)",
    border: "1px solid var(--ln-hairline-strong)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  brandMarkDot: {
    width: 10,
    height: 10,
    borderRadius: 3,
  },
  brandWord: {
    color: linear.text,
    fontSize: 14,
    fontWeight: 500,
    letterSpacing: "-0.01em",
  },
  title: {
    fontSize: 28,
    margin: 0,
  },
  subtitle: {
    display: "block",
    marginTop: 8,
    color: linear.textMuted,
    fontSize: 14,
  },
  label: {
    color: linear.textMuted,
    fontSize: 12,
    fontWeight: 500,
    letterSpacing: "0.02em",
    textTransform: "uppercase",
  },
  inputIcon: {
    color: linear.textDim,
  },
  formMeta: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 20,
  },
  forgotLink: {
    color: linear.textMuted,
    fontSize: 13,
  },
  guestBtn: {
    height: 44,
    background: "var(--ln-surface-2)",
    border: "1px solid var(--ln-hairline-strong)",
    color: linear.text,
  },
  footer: {
    marginTop: 24,
    paddingTop: 16,
    borderTop: "1px solid var(--ln-hairline)",
    textAlign: "center",
  },
};
