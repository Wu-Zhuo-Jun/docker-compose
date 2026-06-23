import { useState } from 'react'
import { Upload, Button, message, Card, Progress, List, Typography, Space } from 'antd'
import { UploadOutlined, FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { uploadDocument } from '../services/api'

const { Dragger } = Upload
const { Text } = Typography

function UploadPage() {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState(null)

  const beforeUpload = (file) => {
    const isDocx = file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || file.name.endsWith('.docx')
    if (!isDocx) {
      message.error('只能上传 .docx 格式的 Word 文档！')
    }
    return isDocx
  }

  const handleUpload = async (file) => {
    if (!file) return

    setUploading(true)
    setProgress(0)
    setUploadResult(null)

    try {
      const result = await uploadDocument(file, setProgress)
      setUploadResult(result)
      message.success(`文档 "${result.filename}" 上传成功！`)
    } catch (error) {
      message.error(error.response?.data?.detail || '上传失败，请重试')
    } finally {
      setUploading(false)
    }

    return false
  }

  const uploadProps = {
    name: 'file',
    multiple: false,
    beforeUpload,
    showUploadList: false,
    customRequest: ({ file, onSuccess, onError }) => {
      handleUpload(file)
        .then(() => onSuccess())
        .catch((err) => onError(err))
    },
  }

  return (
    <div>
      <h2 style={{ marginBottom: '24px', color: '#fff' }}>上传 Word 文档</h2>

      <Card style={{
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.1)'
      }}>
        <Dragger {...uploadProps} disabled={uploading} style={{
          background: 'rgba(114, 46, 209, 0.1)',
          border: '2px dashed rgba(114, 46, 209, 0.5)'
        }}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined style={{ fontSize: '48px', color: '#667eea' }} />
          </p>
          <p className="ant-upload-text" style={{ color: 'rgba(255,255,255,0.9)' }}>点击或拖拽上传 Word 文档</p>
          <p className="ant-upload-hint" style={{ color: 'rgba(255,255,255,0.6)' }}>支持 .docx 格式，文档将自动进行语义分块处理</p>
        </Dragger>

        {uploading && (
          <div style={{ marginTop: '24px' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text>上传进度</Text>
              <Progress percent={progress} status="active" />
            </Space>
          </div>
        )}

        {uploadResult && (
          <div style={{ marginTop: '24px' }}>
            <Card
              type="inner"
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)'
              }}
              title={
                <Space>
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  <span>上传成功</span>
                </Space>
              }
            >
              <List size="small" style={{ background: 'transparent' }}>
                <List.Item>
                  <Text strong style={{ color: '#fff' }}>文件名：</Text>
                  <Text style={{ color: 'rgba(255,255,255,0.8)' }}>{uploadResult.filename}</Text>
                </List.Item>
                <List.Item>
                  <Text strong style={{ color: '#fff' }}>文档ID：</Text>
                  <Text code style={{ color: '#722ed1' }}>{uploadResult.doc_id}</Text>
                </List.Item>
                <List.Item>
                  <Text strong style={{ color: '#fff' }}>分块数量：</Text>
                  <Text style={{ color: 'rgba(255,255,255,0.8)' }}>{uploadResult.chunk_count} 个块</Text>
                </List.Item>
              </List>

              {uploadResult.chunks && uploadResult.chunks.length > 0 && (
                <div style={{ marginTop: '16px' }}>
                  <Text strong style={{ display: 'block', marginBottom: '8px', color: '#fff' }}>分块预览：</Text>
                  {uploadResult.chunks.slice(0, 3).map((chunk, index) => (
                    <Card
                      key={chunk.id}
                      size="small"
                      style={{ marginBottom: '8px', background: 'rgba(0,0,0,0.3)' }}
                    >
                      <Space>
                        <FileTextOutlined style={{ color: '#722ed1' }} />
                        <Text type="secondary">块 {index + 1}:</Text>
                        <Text style={{ color: 'rgba(255,255,255,0.8)' }}>{chunk.content}</Text>
                      </Space>
                    </Card>
                  ))}
                  {uploadResult.chunks.length > 3 && (
                    <Text type="secondary">...还有 {uploadResult.chunks.length - 3} 个块</Text>
                  )}
                </div>
              )}
            </Card>
          </div>
        )}
      </Card>
    </div>
  )
}

export default UploadPage
