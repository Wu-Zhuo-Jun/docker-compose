import { useState } from "react";
import { Upload, Button, message, Card, Progress, List, Typography, Space, Alert } from "antd";
import { UploadOutlined, FileTextOutlined, CheckCircleOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { uploadPendingDocument } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { linear } from "@/styles/tokens";

const { Dragger } = Upload;
const { Text } = Typography;

function UploadPage() {
  const { user, isGuest } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState(null);

  // 访客也能上传（使用 uploader_id=1 默认用户）
  const uploaderId = user?.id || 1;

  const beforeUpload = (file) => {
    const isDocx = file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" || file.name.endsWith(".docx") || file.name.endsWith(".txt");
    if (!isDocx) {
      message.error("只能上传 .docx 或 .txt 格式的文档！");
    }
    return isDocx;
  };

  const handleUpload = async (file) => {
    if (!file) return;

    setUploading(true);
    setProgress(0);
    setUploadResult(null);

    try {
      // 走审核流程 - 普通上传
      const result = await uploadPendingDocument(file, uploaderId, setProgress);
      setUploadResult(result);
      message.success(`文档 "${result.filename}" 已提交审核!`);
    } catch (error) {
      message.error(error.response?.data?.detail || "上传失败，请重试");
    } finally {
      setUploading(false);
    }

    return false;
  };

  const uploadProps = {
    name: "file",
    multiple: false,
    beforeUpload,
    showUploadList: false,
    customRequest: ({ file, onSuccess, onError }) => {
      handleUpload(file)
        .then(() => onSuccess())
        .catch((err) => onError(err));
    },
  };

  return (
    <div>
      <h2 style={{ marginBottom: "8px", color: "#fff" }}>上传文档</h2>
      <Text style={{ color: linear.textMuted, fontSize: 14, display: "block", marginBottom: 24 }}>
        文档提交后将进入待审核状态,管理员审批通过后才会被索引到知识库
      </Text>

      <Alert
        message="审核流程"
        description="所有用户上传的文档均需管理员审批。审批通过后,文档将自动进行语义分块并索引到向量数据库。"
        type="info"
        showIcon
        icon={<ClockCircleOutlined />}
        style={{
          marginBottom: 20,
          background: linear.accentSurface,
          border: "1px solid rgba(94,106,210,0.25)",
        }}
      />

      <Card
        style={{
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.1)",
        }}>
        <Dragger
          {...uploadProps}
          disabled={uploading}
          style={{
            background: "rgba(114, 46, 209, 0.1)",
            border: "2px dashed rgba(114, 46, 209, 0.5)",
          }}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined style={{ fontSize: "48px", color: "#667eea" }} />
          </p>
          <p className="ant-upload-text" style={{ color: "rgba(255,255,255,0.9)" }}>
            点击或拖拽上传文档
          </p>
          <p className="ant-upload-hint" style={{ color: "rgba(255,255,255,0.6)" }}>
            支持 .docx、.txt 格式
          </p>
        </Dragger>

        {uploading && (
          <div style={{ marginTop: "24px" }}>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Text>上传进度</Text>
              <Progress percent={progress} status="active" />
            </Space>
          </div>
        )}

        {uploadResult && (
          <div style={{ marginTop: "24px" }}>
            <Card
              type="inner"
              style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
              }}
              title={
                <Space>
                  <CheckCircleOutlined style={{ color: "#52c41a" }} />
                  <span>已提交审核</span>
                </Space>
              }>
              <List size="small" style={{ background: "transparent" }}>
                <List.Item>
                  <Text strong style={{ color: "#fff" }}>
                    文件名：
                  </Text>
                  <Text style={{ color: "rgba(255,255,255,0.8)" }}>{uploadResult.filename}</Text>
                </List.Item>
                <List.Item>
                  <Text strong style={{ color: "#fff" }}>
                    文档ID：
                  </Text>
                  <Text code style={{ color: "#722ed1" }}>
                    {uploadResult.doc_id}
                  </Text>
                </List.Item>
                <List.Item>
                  <Text strong style={{ color: "#fff" }}>
                    审核状态：
                  </Text>
                  <Text style={{ color: "#faad14" }}>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    待审核
                  </Text>
                </List.Item>
              </List>

              <Alert
                message={uploadResult.message || "文档已提交审核，等待管理员审批"}
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Card>
          </div>
        )}
      </Card>
    </div>
  );
}

export default UploadPage;
