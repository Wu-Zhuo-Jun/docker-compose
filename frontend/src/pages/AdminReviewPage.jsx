import { useState, useEffect, useCallback } from "react";
import { Table, Button, Tag, Space, Typography, App as AntApp, message as antdMessage, Modal, Input, Tabs, Avatar, Empty, Spin, Card, Statistic, Tooltip } from "antd";
import { CheckOutlined, CloseOutlined, FileTextOutlined, ClockCircleOutlined, UserOutlined, CalendarOutlined, ReloadOutlined, ExclamationCircleOutlined } from "@ant-design/icons";
import { listPendingReviews, listAllReviews, approveReview, rejectReview } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { linear } from "@/styles/tokens";

const { Text, Title } = Typography;
const { TextArea } = Input;

function AdminReviewPage() {
  const { user } = useAuth();
  const { modal, message: messageApi } = AntApp.useApp();
  const reviewerId = user?.id || 1;

  const [activeTab, setActiveTab] = useState("pending");
  const [pendingReviews, setPendingReviews] = useState([]);
  const [approvedReviews, setApprovedReviews] = useState([]);
  const [rejectedReviews, setRejectedReviews] = useState([]);
  const [allReviews, setAllReviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [rejectModal, setRejectModal] = useState({ open: false, review: null });
  const [rejectComment, setRejectComment] = useState("");

  // 一次性加载所有数据
  const loadAllData = useCallback(async () => {
    setLoading(true);
    try {
      const [pending, approved, rejected, all] = await Promise.all([
        listPendingReviews(reviewerId),
        listAllReviews(reviewerId, "approved"),
        listAllReviews(reviewerId, "rejected"),
        listAllReviews(reviewerId),
      ]);
      setPendingReviews(pending || []);
      setApprovedReviews(approved || []);
      setRejectedReviews(rejected || []);
      setAllReviews(all || []);
    } catch (err) {
      console.error("Failed to load reviews:", err);
      messageApi.error("加载审核数据失败");
    } finally {
      setLoading(false);
    }
  }, [reviewerId, messageApi]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // 审批通过
  const handleApprove = async (review) => {
    setActionLoading(review.id);
    try {
      await approveReview(review.id, reviewerId);
      messageApi.success("已通过审批，文档已索引到向量库");
      loadAllData();
    } catch (err) {
      console.error("Failed to approve:", err);
      messageApi.error("审批失败: " + (err.message || "未知错误"));
    } finally {
      setActionLoading(null);
    }
  };

  // 弹出拒绝对话框
  const showRejectModal = (review) => {
    setRejectModal({ open: true, review });
    setRejectComment("");
  };

  // 确认拒绝
  const handleReject = async () => {
    const review = rejectModal.review;
    if (!review) return;

    setActionLoading(review.id);
    try {
      await rejectReview(review.id, reviewerId, rejectComment);
      messageApi.success("已拒绝文档");
      setRejectModal({ open: false, review: null });
      setRejectComment("");
      loadAllData();
    } catch (err) {
      console.error("Failed to reject:", err);
      messageApi.error("拒绝失败: " + (err.message || "未知错误"));
    } finally {
      setActionLoading(null);
    }
  };

  // 表格列定义
  const columns = [
    {
      title: "文档",
      dataIndex: "filename",
      key: "filename",
      render: (filename, record) => (
        <Space>
          <FileTextOutlined style={{ color: linear.accent }} />
          <div>
            <div style={{ color: linear.text, fontWeight: 500 }}>{filename}</div>
            <Text
              style={{
                fontSize: 11,
                color: linear.textDim,
                fontFamily: linear.font.mono,
              }}>
              {/* {record.doc_id?.slice(0, 8)}... */}
              {record.doc_id}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: "上传者",
      dataIndex: "uploader_username",
      key: "uploader",
      width: 140,
      render: (username, record) => (
        <Space size={6}>
          <Avatar
            size={20}
            style={{
              background: linear.surface3,
              color: linear.textMuted,
              fontSize: 10,
              fontWeight: 600,
            }}>
            {username?.[0]?.toUpperCase() || <UserOutlined />}
          </Avatar>
          <Text style={{ color: linear.textMuted, fontSize: 13 }}>{username || `用户#${record.uploader_id}`}</Text>
        </Space>
      ),
    },
    {
      title: "提交时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
      render: (createdAt) => (
        <Text style={{ color: linear.textMuted, fontSize: 12 }}>
          <CalendarOutlined style={{ marginRight: 4 }} />
          {new Date(createdAt).toLocaleString("zh-CN", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Text>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status) => {
        const config = {
          pending: { color: "orange", text: "待审核", icon: <ClockCircleOutlined /> },
          approved: { color: "green", text: "已通过", icon: <CheckOutlined /> },
          rejected: { color: "red", text: "已拒绝", icon: <CloseOutlined /> },
        };
        const c = config[status] || config.pending;
        return (
          <Tag color={c.color} icon={c.icon}>
            {c.text}
          </Tag>
        );
      },
    },
  ];

  // 待审核列表的操作列
  const pendingColumns = [
    ...columns,
    {
      title: "操作",
      key: "actions",
      width: 200,
      render: (_, record) => (
        <Space size={6}>
          <Button type="primary" size="small" icon={<CheckOutlined />} onClick={() => handleApprove(record)} loading={actionLoading === record.id} style={{ height: 28 }}>
            通过
          </Button>
          <Button danger size="small" icon={<CloseOutlined />} onClick={() => showRejectModal(record)} loading={actionLoading === record.id} style={{ height: 28 }}>
            拒绝
          </Button>
        </Space>
      ),
    },
  ];

  // 全部记录的额外列
  const allColumns = [
    ...columns,
    {
      title: "审核人",
      dataIndex: "reviewer_username",
      key: "reviewer",
      width: 120,
      render: (username) => (username ? <Text style={{ color: linear.textMuted, fontSize: 13 }}>{username}</Text> : <Text style={{ color: linear.textDim, fontSize: 12 }}>—</Text>),
    },
    {
      title: "审核时间",
      dataIndex: "reviewed_at",
      key: "reviewed_at",
      width: 160,
      render: (reviewedAt) =>
        reviewedAt ? (
          <Text style={{ color: linear.textMuted, fontSize: 12 }}>
            {new Date(reviewedAt).toLocaleString("zh-CN", {
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </Text>
        ) : (
          <Text style={{ color: linear.textDim, fontSize: 12 }}>—</Text>
        ),
    },
    {
      title: "审核意见",
      dataIndex: "review_comment",
      key: "comment",
      ellipsis: true,
      render: (comment) =>
        comment ? (
          <Tooltip title={comment}>
            <Text style={{ color: linear.textMuted, fontSize: 12 }}>{comment}</Text>
          </Tooltip>
        ) : (
          <Text style={{ color: linear.textDim, fontSize: 12 }}>—</Text>
        ),
    },
  ];

  // 统计
  const stats = {
    pending: pendingReviews.length,
    approved: approvedReviews.length,
    rejected: rejectedReviews.length,
    total: allReviews.length,
  };

  const tabItems = [
    {
      key: "pending",
      label: (
        <span>
          <ClockCircleOutlined /> 待审核
          {pendingReviews.length > 0 && (
            <Tag color="orange" style={{ marginLeft: 6 }}>
              {pendingReviews.length}
            </Tag>
          )}
        </span>
      ),
      children: (
        <Table
          columns={pendingColumns}
          dataSource={pendingReviews}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          locale={{
            emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text style={{ color: linear.textDim }}>暂无待审核文档</Text>} />,
          }}
        />
      ),
    },
    {
      key: "approved",
      label: (
        <span>
          <CheckOutlined /> 已通过
        </span>
      ),
      children: (
        <Table
          columns={allColumns}
          dataSource={approvedReviews}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          locale={{
            emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text style={{ color: linear.textDim }}>暂无已通过的文档</Text>} />,
          }}
        />
      ),
    },
    {
      key: "rejected",
      label: (
        <span>
          <CloseOutlined /> 已拒绝
        </span>
      ),
      children: (
        <Table
          columns={allColumns}
          dataSource={rejectedReviews}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          locale={{
            emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text style={{ color: linear.textDim }}>暂无已拒绝的文档</Text>} />,
          }}
        />
      ),
    },
    {
      key: "all",
      label: "全部记录",
      children: <Table columns={allColumns} dataSource={allReviews} rowKey="id" loading={loading} pagination={{ pageSize: 10, showSizeChanger: false }} />,
    },
  ];

  return (
    <div>
      {/* 页面标题区 */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          marginBottom: 24,
        }}>
        <div>
          <Title
            level={3}
            style={{
              color: linear.text,
              marginBottom: 6,
              fontWeight: 600,
            }}>
            文档审核
          </Title>
          <Text style={{ color: linear.textMuted, fontSize: 13 }}>审核用户上传的文档，通过后将索引到向量知识库</Text>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={loadAllData}
          style={{ height: 36 }}>
          刷新
        </Button>
      </div>

      {/* 统计卡片 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 16,
          marginBottom: 24,
        }}>
        <Card
          bordered={false}
          style={{
            background: "var(--ln-surface-1)",
            border: "1px solid var(--ln-hairline)",
            borderRadius: 8,
          }}>
          <Statistic
            title={<Text style={{ color: linear.textMuted, fontSize: 12 }}>待审核</Text>}
            value={pendingReviews.length}
            valueStyle={{
              color: linear.accent,
              fontSize: 28,
              fontWeight: 600,
            }}
            prefix={<ClockCircleOutlined />}
          />
        </Card>
        <Card
          bordered={false}
          style={{
            background: "var(--ln-surface-1)",
            border: "1px solid var(--ln-hairline)",
            borderRadius: 8,
          }}>
          <Statistic
            title={<Text style={{ color: linear.textMuted, fontSize: 12 }}>已通过</Text>}
            value={stats.approved}
            valueStyle={{
              color: linear.success,
              fontSize: 28,
              fontWeight: 600,
            }}
            prefix={<CheckOutlined />}
          />
        </Card>
        <Card
          bordered={false}
          style={{
            background: "var(--ln-surface-1)",
            border: "1px solid var(--ln-hairline)",
            borderRadius: 8,
          }}>
          <Statistic
            title={<Text style={{ color: linear.textMuted, fontSize: 12 }}>已拒绝</Text>}
            value={stats.rejected}
            valueStyle={{
              color: linear.danger,
              fontSize: 28,
              fontWeight: 600,
            }}
            prefix={<CloseOutlined />}
          />
        </Card>
        <Card
          bordered={false}
          style={{
            background: "var(--ln-surface-1)",
            border: "1px solid var(--ln-hairline)",
            borderRadius: 8,
          }}>
          <Statistic
            title={<Text style={{ color: linear.textMuted, fontSize: 12 }}>总记录</Text>}
            value={stats.total}
            valueStyle={{
              color: linear.text,
              fontSize: 28,
              fontWeight: 600,
            }}
            prefix={<FileTextOutlined />}
          />
        </Card>
      </div>

      {/* 标签页 */}
      <Card
        bordered={false}
        style={{
          background: "var(--ln-surface-1)",
          border: "1px solid var(--ln-hairline)",
          borderRadius: 8,
        }}
        bodyStyle={{ padding: 0 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          style={{ padding: "0 20px" }}
          tabBarStyle={{
            margin: 0,
            borderBottom: "1px solid var(--ln-hairline)",
            paddingTop: 8,
          }}
        />
      </Card>

      {/* 拒绝对话框 */}
      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: linear.danger }} />
            <span>拒绝文档</span>
          </Space>
        }
        open={rejectModal.open}
        onCancel={() => setRejectModal({ open: false, review: null })}
        onOk={handleReject}
        okText="确认拒绝"
        cancelText="取消"
        okButtonProps={{ danger: true }}
        confirmLoading={actionLoading === rejectModal.review?.id}>
        <div style={{ marginBottom: 12 }}>
          <Text style={{ color: linear.textMuted }}>即将拒绝文档：</Text>
          <Text
            strong
            style={{
              color: linear.text,
              marginLeft: 4,
            }}>
            {rejectModal.review?.filename}
          </Text>
        </div>
        <Text
          style={{
            color: linear.textMuted,
            fontSize: 13,
            display: "block",
            marginBottom: 8,
          }}>
          拒绝原因（可选）：
        </Text>
        <TextArea value={rejectComment} onChange={(e) => setRejectComment(e.target.value)} placeholder="请输入拒绝原因，将记录在审核意见中..." rows={3} maxLength={500} showCount />
      </Modal>
    </div>
  );
}

export default AdminReviewPage;
