import { useState, useEffect } from "react";
import { Table, Button, Space, Popconfirm, message, Card, Typography, Tag, Empty } from "antd";
import { DeleteOutlined, ReloadOutlined, FileTextOutlined } from "@ant-design/icons";
import { listDocuments, deleteDocument } from "../services/api";

const { Title, Text } = Typography;

function DocumentListPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [fetchError, setFetchError] = useState(false);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const data = await listDocuments();
      setDocuments(data?.documents || []);
    } catch (error) {
      console.error("Failed to fetch documents:", error);
      message.error("获取文档列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDelete = async (docId) => {
    setDeletingId(docId);
    try {
      await deleteDocument(docId);
      message.success("文档删除成功");
      fetchDocuments();
    } catch (error) {
      message.error(error.response?.data?.detail || "删除失败");
    } finally {
      setDeletingId(null);
    }
  };

  const columns = [
    {
      title: "文件名",
      dataIndex: "source",
      key: "source",
      render: (text) => (
        <Space>
          <FileTextOutlined style={{ color: "#722ed1" }} />
          <Text strong style={{ color: "#fff" }}>
            {text}
          </Text>
        </Space>
      ),
    },
    {
      title: "文档ID",
      dataIndex: "doc_id",
      key: "doc_id",
      render: (text) => <Text code>{text}</Text>,
    },
    {
      title: "分块数",
      dataIndex: "total_chunks",
      key: "total_chunks",
      render: (count) => <Tag color="blue">{count} 个块</Tag>,
    },
    {
      title: "操作",
      key: "action",
      width: 150,
      render: (_, record) => (
        <Space>
          <Popconfirm title="确认删除" description="确定要删除这个文档吗？删除后将无法恢复。" onConfirm={() => handleDelete(record.doc_id)} okText="确认" cancelText="取消">
            <Button danger type="text" icon={<DeleteOutlined />} loading={deletingId === record.doc_id}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <h2 style={{ margin: 0, color: "#fff" }}>文档列表</h2>
        <Button icon={<ReloadOutlined />} onClick={fetchDocuments} loading={loading}>
          刷新
        </Button>
      </div>

      <Card
        style={{
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.1)",
        }}>
        {documents.length === 0 && !loading ? (
          <Empty description="暂无上传的文档" image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Button type="primary" onClick={() => (window.location.href = "#/upload")}>
              去上传文档
            </Button>
          </Empty>
        ) : (
          <Table
            columns={columns}
            dataSource={documents}
            rowKey="doc_id"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 个文档`,
            }}
          />
        )}
      </Card>
    </div>
  );
}

export default DocumentListPage;
