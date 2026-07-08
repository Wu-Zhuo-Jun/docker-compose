import { useState, useEffect, useRef, useCallback } from "react";
import {
  Input,
  Button,
  Avatar,
  Tag,
  Empty,
  Spin,
  Typography,
  Tooltip,
  message as antdMessage,
  App as AntApp,
  Collapse,
} from "antd";
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  PlusOutlined,
  DeleteOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  MessageOutlined,
  ThunderboltOutlined,
  StopOutlined,
} from "@ant-design/icons";
import {
  listSessions,
  createSession,
  getSession,
  deleteSession,
  multiTurnQAStream,
  updateSession,
} from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { linear } from "@/styles/tokens";

const { TextArea } = Input;
const { Text, Title } = Typography;
const { Panel } = Collapse;

const SUGGESTED_QUERIES = [
  "D9W 的最大功率是多少？",
  "机器重量对比",
  "恒华客流参数查询",
  "如何提高识别准确率？",
];

function ChatPage() {
  const { user } = useAuth();
  const { message: messageApi } = AntApp.useApp();
  const userId = user?.id || 1;

  // 会话列表
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingSession, setLoadingSession] = useState(false);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // 加载会话列表
  const loadSessions = useCallback(async () => {
    if (!userId) return;
    setLoadingSessions(true);
    try {
      const data = await listSessions(userId, 50);
      setSessions(data || []);
    } catch (err) {
      console.error("Failed to load sessions:", err);
      antdMessage.error("加载会话列表失败");
    } finally {
      setLoadingSessions(false);
    }
  }, [userId, antdMessage]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // 加载指定会话详情
  const loadSession = useCallback(
    async (sessionId) => {
      if (!sessionId || !userId) {
        setMessages([]);
        return;
      }
      setLoadingSession(true);
      try {
        const data = await getSession(sessionId, userId);
        setMessages(data.messages || []);
        setCurrentSessionId(sessionId);
      } catch (err) {
        console.error("Failed to load session:", err);
        antdMessage.error("加载会话详情失败");
        setMessages([]);
      } finally {
        setLoadingSession(false);
      }
    },
    [userId, antdMessage]
  );

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollTop = messagesEndRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 创建新会话
  const handleNewSession = async () => {
    if (!userId) return;
    try {
      const newSession = await createSession(userId, "新对话");
      setSessions((prev) => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);
      setMessages([]);
      setInput("");
      textareaRef.current?.focus();
    } catch (err) {
      console.error("Failed to create session:", err);
      antdMessage.error("创建会话失败");
    }
  };

  // 删除会话
  const handleDeleteSession = async (sessionId, e) => {
    e?.stopPropagation();
    if (!userId) return;
    try {
      await deleteSession(sessionId, userId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
      antdMessage.success("会话已删除");
    } catch (err) {
      console.error("Failed to delete session:", err);
      antdMessage.error("删除会话失败");
    }
  };

  // 切换会话
  const handleSelectSession = (sessionId) => {
    if (sessionId === currentSessionId) return;
    loadSession(sessionId);
  };

  // 中断当前流式请求
  const abortRef = useRef(null);
  const handleAbort = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setLoading(false);
  };

  // 发送问题 - 流式版本
  const handleSend = (overrideQuery) => {
    const queryText = (overrideQuery || input).trim();
    if (!queryText || loading) return;

    const userMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: queryText,
      created_at: new Date().toISOString(),
    };

    // 立即在 UI 上显示用户消息
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    // 占位的助手消息（流式填充）
    const assistantId = `stream-${Date.now()}`;
    const assistantPlaceholder = {
      id: assistantId,
      role: "assistant",
      content: "",
      metadata: {},
      created_at: new Date().toISOString(),
      streaming: true,
    };
    setMessages((prev) => [...prev, assistantPlaceholder]);

    const controller = multiTurnQAStream(
      userId,
      queryText,
      currentSessionId,
      10,
      {
        onSession: (data) => {
          if (data.session_id && data.session_id !== currentSessionId) {
            setCurrentSessionId(data.session_id);
          }
        },
        onChunk: (data) => {
          // 增量更新助手消息内容
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: data.answer }
                : m
            )
          );
        },
        onSources: (data) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    metadata: {
                      sources: data.sources || [],
                      groups: data.groups || {},
                      used_chunks: data.used_chunks || 0,
                      total_retrieved: data.total_retrieved || 0,
                      total_docs: data.total_docs || 0,
                    },
                  }
                : m
            )
          );
        },
        onDone: (data) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, id: data.message_id || assistantId, streaming: false }
                : m
            )
          );
          setLoading(false);
          abortRef.current = null;
          // 重新加载会话列表（可能产生新会话 / 标题更新）
          loadSessions();
        },
        onError: (err) => {
          console.error("Stream error:", err);
          antdMessage.error("问答请求失败: " + (err.message || "未知错误"));
          // 移除占位助手消息和用户消息
          setMessages((prev) =>
            prev.filter((m) => m.id !== assistantId && m.id !== userMessage.id)
          );
          setLoading(false);
          abortRef.current = null;
        },
      }
    );
    abortRef.current = controller;
  };

  // 处理键盘事件
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 格式化时间
  const formatTime = (isoStr) => {
    if (!isoStr) return "";
    try {
      const d = new Date(isoStr);
      return d.toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  };

  // 截断文本
  const truncate = (str, max = 30) => {
    if (!str) return "";
    return str.length > max ? str.slice(0, max) + "..." : str;
  };

  return (
    <div style={chatLayoutStyles.container}>
      {/* 侧边栏 - 会话列表 */}
      <div style={chatLayoutStyles.sidebar}>
        <div style={chatLayoutStyles.sidebarHeader}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleNewSession}
            block
            style={{ height: 38, fontWeight: 500 }}
          >
            新建对话
          </Button>
        </div>

        <div style={chatLayoutStyles.sessionList}>
          {loadingSessions ? (
            <div style={{ textAlign: "center", padding: 24 }}>
              <Spin size="small" />
            </div>
          ) : sessions.length === 0 ? (
            <div style={chatLayoutStyles.emptyState}>
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <Text style={{ color: linear.textDim, fontSize: 12 }}>
                    暂无对话
                  </Text>
                }
              />
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleSelectSession(session.id)}
                className="session-item-row"
                style={{
                  ...chatLayoutStyles.sessionItem,
                  ...(currentSessionId === session.id
                    ? chatLayoutStyles.sessionItemActive
                    : {}),
                }}
              >
                <MessageOutlined
                  style={{
                    color:
                      currentSessionId === session.id
                        ? linear.accent
                        : linear.textDim,
                    fontSize: 13,
                    flexShrink: 0,
                  }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      color:
                        currentSessionId === session.id
                          ? linear.text
                          : linear.textMuted,
                      fontWeight: currentSessionId === session.id ? 500 : 400,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {session.title || "新对话"}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: linear.textDim,
                      marginTop: 2,
                    }}
                  >
                    {formatTime(session.updated_at)}
                  </div>
                </div>
                <Tooltip title="删除对话">
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => handleDeleteSession(session.id, e)}
                    style={{
                      opacity: 0.6,
                      color: linear.textDim,
                      flexShrink: 0,
                    }}
                    className="session-delete-btn"
                  />
                </Tooltip>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 主对话区 */}
      <div style={chatLayoutStyles.main}>
        {/* 消息列表 */}
        <div style={chatLayoutStyles.messagesContainer} ref={messagesEndRef}>
          {loadingSession ? (
            <div style={{ textAlign: "center", padding: 80 }}>
              <Spin tip="加载中..." />
            </div>
          ) : messages.length === 0 ? (
            <div style={chatLayoutStyles.welcomeContainer}>
              <Avatar
                size={56}
                style={{
                  background: linear.accentSurface,
                  color: linear.accent,
                  marginBottom: 20,
                }}
                icon={<ThunderboltOutlined style={{ fontSize: 28 }} />}
              />
              <Title
                level={3}
                style={{
                  color: linear.text,
                  marginBottom: 8,
                  fontWeight: 600,
                }}
              >
                开始一段新的对话
              </Title>
              <Text
                style={{
                  color: linear.textMuted,
                  fontSize: 14,
                  marginBottom: 32,
                  display: "block",
                }}
              >
                基于文档库的智能问答，支持多轮上下文理解
              </Text>

              <div style={chatLayoutStyles.suggestedQueries}>
                {SUGGESTED_QUERIES.map((q, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleSend(q)}
                    style={chatLayoutStyles.suggestedQuery}
                  >
                    <span style={{ color: linear.text, fontSize: 13 }}>{q}</span>
                    <SendOutlined
                      style={{ color: linear.textDim, fontSize: 12 }}
                    />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={chatLayoutStyles.messagesList}>
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  isUser={msg.role === "user"}
                />
              ))}
              {loading && (
                <div style={chatLayoutStyles.thinkingMessage}>
                  <Avatar
                    size={32}
                    style={{
                      background: linear.accentSurface,
                      color: linear.accent,
                      flexShrink: 0,
                    }}
                    icon={<RobotOutlined />}
                  />
                  <div style={chatLayoutStyles.thinkingBubble}>
                    <Spin size="small" />
                    <Text style={{ color: linear.textMuted, marginLeft: 10 }}>
                      正在思考...
                    </Text>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 输入区 */}
        <div style={chatLayoutStyles.inputContainer}>
          <div style={chatLayoutStyles.inputWrapper}>
            <TextArea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                currentSessionId
                  ? "继续提问...（Enter 发送，Shift+Enter 换行）"
                  : "输入问题开始新对话..."
              }
              autoSize={{ minRows: 1, maxRows: 6 }}
              style={{
                background: "transparent",
                border: "none",
                boxShadow: "none",
                color: linear.text,
                fontSize: 14,
                resize: "none",
                padding: "8px 0",
              }}
              disabled={loading}
            />
            <div style={chatLayoutStyles.inputActions}>
              <Text style={{ fontSize: 11, color: linear.textDim }}>
                {input.length} 字符
              </Text>
              {loading ? (
                <Button
                  danger
                  icon={<StopOutlined />}
                  onClick={handleAbort}
                  style={{ height: 32, fontWeight: 500 }}
                >
                  停止
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={() => handleSend()}
                  disabled={!input.trim()}
                  style={{ height: 32, fontWeight: 500 }}
                >
                  发送
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 消息气泡组件
function MessageBubble({ message, isUser }) {
  const metadata = message.metadata || {};
  const hasSources = metadata.sources && metadata.sources.length > 0;
  const hasGroups = metadata.groups && Object.keys(metadata.groups).length > 0;

  return (
    <div
      style={{
        ...chatLayoutStyles.messageRow,
        flexDirection: isUser ? "row-reverse" : "row",
      }}
    >
      <Avatar
        size={32}
        style={{
          background: isUser ? linear.surface3 : linear.accentSurface,
          color: isUser ? linear.text : linear.accent,
          flexShrink: 0,
          fontSize: 14,
          fontWeight: 600,
        }}
        icon={isUser ? <UserOutlined /> : <RobotOutlined />}
      />
      <div
        style={{
          ...chatLayoutStyles.bubble,
          ...(isUser ? chatLayoutStyles.bubbleUser : chatLayoutStyles.bubbleAssistant),
        }}
      >
        <div style={chatLayoutStyles.bubbleContent}>
          {message.content}
          {message.streaming && message.content && (
            <span
              style={{
                display: "inline-block",
                width: 6,
                height: 14,
                marginLeft: 2,
                verticalAlign: "text-bottom",
                background: linear.accent,
                animation: "chat-cursor-blink 1s steps(2) infinite",
              }}
            />
          )}
        </div>

        {/* 助手回答 - 显示元数据 */}
        {!isUser && (hasSources || hasGroups) && (
          <div style={chatLayoutStyles.metaContainer}>
            <div style={chatLayoutStyles.metaTags}>
              {metadata.total_retrieved !== undefined && (
                <Tag style={chatLayoutStyles.metaTag}>
                  <DatabaseOutlined style={{ marginRight: 4 }} />
                  {metadata.total_retrieved} 个片段
                </Tag>
              )}
              {metadata.used_chunks !== undefined && metadata.used_chunks > 0 && (
                <Tag style={chatLayoutStyles.metaTag}>
                  使用 {metadata.used_chunks} 个相关片段
                </Tag>
              )}
              {metadata.total_docs !== undefined && metadata.total_docs > 0 && (
                <Tag style={chatLayoutStyles.metaTag}>
                  涉及 {metadata.total_docs} 个文档
                </Tag>
              )}
            </div>

            {hasSources && (
              <div style={{ marginTop: 10 }}>
                <Text
                  style={{
                    fontSize: 11,
                    color: linear.textDim,
                    letterSpacing: "0.04em",
                    textTransform: "uppercase",
                  }}
                >
                  参考文档
                </Text>
                <div style={chatLayoutStyles.sourcesList}>
                  {metadata.sources.map((src, idx) => (
                    <Tag
                      key={idx}
                      style={chatLayoutStyles.sourceTag}
                      icon={<FileTextOutlined />}
                    >
                      {src}
                    </Tag>
                  ))}
                </div>
              </div>
            )}

            {hasGroups && (
              <Collapse
                ghost
                size="small"
                style={{ marginTop: 8 }}
                items={Object.entries(metadata.groups).map(([docName, chunks]) => ({
                  key: docName,
                  label: (
                    <span
                      style={{
                        fontSize: 12,
                        color: linear.textMuted,
                      }}
                    >
                      <FileTextOutlined
                        style={{ color: linear.accent, marginRight: 6 }}
                      />
                      {docName}
                      <span
                        style={{
                          marginLeft: 8,
                          color: linear.textDim,
                          fontSize: 11,
                        }}
                      >
                        ({chunks.length} 个片段)
                      </span>
                    </span>
                  ),
                  children: (
                    <div style={{ paddingTop: 4 }}>
                      {chunks.map((chunk, idx) => (
                        <div
                          key={idx}
                          style={chatLayoutStyles.chunkItem}
                        >
                          <Text
                            style={{
                              fontSize: 12,
                              color: linear.textMuted,
                              lineHeight: 1.7,
                            }}
                          >
                            {chunk.content?.slice(0, 200)}
                            {chunk.content?.length > 200 ? "..." : ""}
                          </Text>
                        </div>
                      ))}
                    </div>
                  ),
                }))}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const chatLayoutStyles = {
  container: {
    display: "flex",
    height: "calc(100vh - 56px - 64px)",
    marginTop: -16,
    marginLeft: -40,
    marginRight: -40,
    marginBottom: -32,
    background: "var(--ln-ground)",
    borderRadius: 12,
    overflow: "hidden",
    border: "1px solid var(--ln-hairline)",
  },
  sidebar: {
    width: 280,
    background: "var(--ln-ground)",
    borderRight: "1px solid var(--ln-hairline)",
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
  },
  sidebarHeader: {
    padding: 16,
    borderBottom: "1px solid var(--ln-hairline)",
  },
  sessionList: {
    flex: 1,
    overflowY: "auto",
    padding: "8px 8px",
  },
  sessionItem: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 12px",
    borderRadius: 6,
    cursor: "pointer",
    marginBottom: 2,
    transition: "background 150ms " + linear.ease,
  },
  sessionItemActive: {
    background: linear.accentSurface,
  },
  emptyState: {
    padding: 32,
    textAlign: "center",
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    background: "var(--ln-ground)",
    minWidth: 0,
  },
  messagesContainer: {
    flex: 1,
    overflowY: "auto",
    padding: "32px 40px",
  },
  welcomeContainer: {
    maxWidth: 640,
    margin: "80px auto 0",
    textAlign: "center",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  suggestedQueries: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 10,
    width: "100%",
    maxWidth: 540,
    marginTop: 8,
  },
  suggestedQuery: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 16px",
    background: "var(--ln-surface-1)",
    border: "1px solid var(--ln-hairline)",
    borderRadius: 8,
    cursor: "pointer",
    transition: "all 150ms " + linear.ease,
  },
  messagesList: {
    maxWidth: 880,
    margin: "0 auto",
  },
  messageRow: {
    display: "flex",
    gap: 12,
    marginBottom: 24,
    alignItems: "flex-start",
  },
  bubble: {
    maxWidth: "75%",
    borderRadius: 12,
    padding: "12px 16px",
    wordBreak: "break-word",
  },
  bubbleUser: {
    background: linear.accent,
    color: "#fff",
  },
  bubbleAssistant: {
    background: "var(--ln-surface-1)",
    border: "1px solid var(--ln-hairline)",
    color: linear.text,
  },
  bubbleContent: {
    fontSize: 14,
    lineHeight: 1.7,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  metaContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTop: "1px solid var(--ln-hairline)",
  },
  metaTags: {
    display: "flex",
    gap: 6,
    flexWrap: "wrap",
  },
  metaTag: {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid var(--ln-hairline)",
    color: linear.textMuted,
    fontSize: 11,
    margin: 0,
  },
  sourcesList: {
    display: "flex",
    gap: 6,
    flexWrap: "wrap",
    marginTop: 6,
  },
  sourceTag: {
    background: linear.accentSurface,
    color: linear.accent,
    border: "1px solid rgba(94,106,210,0.20)",
    fontSize: 11,
    margin: 0,
  },
  chunkItem: {
    padding: "8px 10px",
    background: "rgba(0,0,0,0.20)",
    border: "1px solid var(--ln-hairline)",
    borderRadius: 6,
    marginBottom: 6,
  },
  thinkingMessage: {
    display: "flex",
    gap: 12,
    marginBottom: 24,
    alignItems: "flex-start",
  },
  thinkingBubble: {
    background: "var(--ln-surface-1)",
    border: "1px solid var(--ln-hairline)",
    borderRadius: 12,
    padding: "12px 16px",
    display: "flex",
    alignItems: "center",
  },
  inputContainer: {
    borderTop: "1px solid var(--ln-hairline)",
    padding: "16px 40px 20px",
    background: "var(--ln-ground)",
  },
  inputWrapper: {
    maxWidth: 880,
    margin: "0 auto",
    background: "var(--ln-surface-1)",
    border: "1px solid var(--ln-hairline-strong)",
    borderRadius: 12,
    padding: "8px 16px",
    transition: "border-color 150ms " + linear.ease,
  },
  inputActions: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 4,
    paddingTop: 4,
    borderTop: "1px solid var(--ln-hairline)",
  },
};

export default ChatPage;
