// Linear recipe token bridge — single source of truth for the whole app.
// Reference: references/style-recipes/linear.md
export const linear = {
  ground: "#08090A",
  surface1: "#16171C",
  surface2: "#1E1F25",
  surface3: "#26272E",
  hairline: "rgba(255,255,255,0.06)",
  hairlineStrong: "rgba(255,255,255,0.10)",
  text: "#F7F8F8",
  textMuted: "#9CA3AF",
  textDim: "#6B7280",
  accent: "#5E6AD2",          // Linear purple — < 5% pixel budget
  accentHover: "#6E7AE0",
  accentSurface: "rgba(94,106,210,0.10)",
  danger: "#F87171",
  success: "#34D399",
  radius: { sm: 6, md: 12, lg: 16 }, // never above 16
  shadow: { raised: "0 1px 2px rgba(0,0,0,0.3)" },
  ease: "cubic-bezier(0.22, 1, 0.36, 1)",
  duration: { hover: "150ms", layout: "400ms" },
  // Purple-black ambient palette — supports the layered static background.
  // These are background-only tokens; do not surface them to components.
  purpleDeep: "#2A1B5E",
  purpleGlow: "#7C7AE6",
  purpleAlpha1: "rgba(94,106,210,0.10)",
  purpleAlpha2: "rgba(94,106,210,0.06)",
  purpleAlpha3: "rgba(124,122,230,0.05)",
  meshTop: "linear-gradient(180deg, rgba(42,27,94,0.35) 0%, transparent 60%)",
  meshCorner: "radial-gradient(60% 80% at 15% 0%, rgba(94,106,210,0.12) 0%, transparent 60%)",
  font: {
    display: `'Inter Tight', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`,
    body: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`,
    mono: `ui-monospace, 'JetBrains Mono', 'Geist Mono', SFMono-Regular, monospace`,
  },
};

// AntD ConfigProvider theme — maps Linear tokens to AntD tokens.
export const antdTheme = (mode = "dark") => ({
  algorithm: mode === "dark" ? 9 /* darkAlgorithm */ : undefined, // resolved at runtime in main.jsx
  token: {
    colorPrimary: linear.accent,
    colorInfo: linear.accent,
    colorSuccess: linear.success,
    colorError: linear.danger,
    colorBgBase: linear.ground,
    colorBgContainer: linear.surface1,
    colorBgElevated: linear.surface2,
    colorBgLayout: linear.ground,
    colorBorder: linear.hairline,
    colorBorderSecondary: linear.hairline,
    colorText: linear.text,
    colorTextSecondary: linear.textMuted,
    colorTextTertiary: linear.textDim,
    borderRadius: linear.radius.sm,
    borderRadiusLG: linear.radius.md,
    fontFamily: linear.font.body,
    motionDurationMid: "200ms",
    motionEaseInOut: linear.ease,
  },
  components: {
    Layout: {
      headerBg: "transparent",
      siderBg: linear.ground,
      bodyBg: linear.ground,
      headerHeight: 56,
    },
    Menu: {
      darkItemBg: "transparent",
      darkItemSelectedBg: linear.accentSurface,
      darkItemSelectedColor: linear.text,
      darkItemHoverBg: "rgba(255,255,255,0.04)",
      darkItemColor: linear.textMuted,
      itemHeight: 36,
      itemBorderRadius: linear.radius.sm,
    },
    Card: {
      colorBgContainer: linear.surface1,
      colorBorderSecondary: linear.hairline,
      borderRadiusLG: linear.radius.md,
    },
    Button: {
      borderRadius: linear.radius.sm,
      controlHeight: 36,
      fontWeight: 500,
    },
    Input: {
      colorBgContainer: linear.surface2,
      activeBorderColor: linear.accent,
      hoverBorderColor: linear.accent,
      borderRadius: linear.radius.sm,
    },
    Table: {
      colorBgContainer: "transparent",
      headerBg: linear.surface2,
      headerColor: linear.textMuted,
      rowHoverBg: "rgba(255,255,255,0.02)",
      borderColor: linear.hairline,
    },
    Tag: {
      defaultBg: linear.surface2,
      defaultColor: linear.textMuted,
    },
    Modal: {
      contentBg: linear.surface1,
      headerBg: linear.surface1,
    },
  },
});
