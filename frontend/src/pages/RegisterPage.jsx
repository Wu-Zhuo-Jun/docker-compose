import { useState } from "react";
import { Form, Input, Button, App as AntApp, Typography, Divider } from "antd";
import { LockOutlined, UserOutlined, ArrowRightOutlined, EyeInvisibleOutlined, EyeTwoTone } from "@ant-design/icons";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { linear } from "@/styles/tokens";

const { Title, Text } = Typography;

export default function RegisterPage() {
  const { register, isAuthenticated, isGuest, hydrated } = useAuth();
  const navigate = useNavigate();
  const { message } = AntApp.useApp();
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  if (hydrated && !submitting && (isAuthenticated || isGuest)) {
    return <Navigate to="/app" replace />;
  }

  const handleSubmit = async (values) => {
    if (values.password !== values.confirmPassword) {
      form.setFields([{ name: "confirmPassword", errors: ["两次输入的密码不一致"] }]);
      return;
    }
    setSubmitting(true);
    try {
      await register(values);
      message.success("注册成功，请登录");
      navigate("/login", { replace: true });
    } catch (err) {
      if (err?.message?.includes("已存在")) {
        form.setFields([{ name: "username", errors: [err.message] }]);
      } else {
        message.error(err.message || "注册失败，请重试");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={styles.page}>
      <div className="login-aurora" />
      <div className="login-grain" />
      <div style={styles.card}>
        <div style={styles.brandRow}>
          <BrandMark />
          <span className="ln-mono" style={styles.brandWord}>compose-yml</span>
        </div>

        <div style={{ marginTop: 40 }}>
          <h1 className="ln-display" style={styles.title}>
            创建账号
          </h1>
          <Text style={styles.subtitle}>
            注册后即可使用完整的文档管理与检索功能
          </Text>
        </div>

        <Form
          form={form}
          layout="vertical"
          requiredMark={false}
          onFinish={handleSubmit}
          style={{ marginTop: 32 }}
          autoComplete="on"
        >
          <Form.Item
            name="username"
            label={<span style={styles.label}>用户名</span>}
            rules={[
              { required: true, message: "请输入用户名" },
              { min: 3, message: "用户名至少 3 位" },
              { max: 64, message: "用户名过长" },
              { pattern: /^[a-zA-Z0-9_-]+$/, message: "仅支持字母、数字、下划线和短横线" },
            ]}
          >
            <Input
              size="large"
              prefix={<UserOutlined style={styles.inputIcon} />}
              placeholder="choose a username"
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
              autoComplete="new-password"
              iconRender={(visible) =>
                visible ? <EyeTwoTone twoToneColor={linear.textMuted} /> : <EyeInvisibleOutlined style={styles.inputIcon} />
              }
            />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label={<span style={styles.label}>确认密码</span>}
            rules={[
              { required: true, message: "请再次输入密码" },
              { min: 6, message: "密码至少 6 位" },
            ]}
            style={{ marginTop: 16 }}
          >
            <Input.Password
              size="large"
              prefix={<LockOutlined style={styles.inputIcon} />}
              placeholder="再输一次"
              autoComplete="new-password"
              iconRender={(visible) =>
                visible ? <EyeTwoTone twoToneColor={linear.textMuted} /> : <EyeInvisibleOutlined style={styles.inputIcon} />
              }
            />
          </Form.Item>

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
            {submitting ? "注册中" : "注册"}
          </Button>
        </Form>

        <Divider plain style={{ margin: "24px 0 16px", color: linear.textDim, fontSize: 12 }}>
          已有账号
        </Divider>

        <Link to="/login">
          <Button size="large" block style={styles.loginBtn}>
            返回登录
          </Button>
        </Link>
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
  loginBtn: {
    height: 44,
    background: "var(--ln-surface-2)",
    border: "1px solid var(--ln-hairline-strong)",
    color: linear.text,
  },
};
