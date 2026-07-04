import { useState } from 'react'
import { Input, Button, Card, Typography, Space, Tag, Empty, Spin, Divider, Collapse } from 'antd'
import { SearchOutlined, RobotOutlined, FileTextOutlined, DatabaseOutlined, DownOutlined } from '@ant-design/icons'
import { qaSearch, searchDocuments } from '@/services/api'

const { TextArea } = Input
const { Text, Title, Paragraph } = Typography
const { Panel } = Collapse

function SearchPage() {
  const [query, setQuery] = useState('')
  const [qaResult, setQaResult] = useState(null)
  const [rawResults, setRawResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [searchMode, setSearchMode] = useState('qa') // 'qa' 或 'raw'

  const handleSearch = async () => {
    if (!query.trim()) return

    setLoading(true)
    setSearched(true)

    try {
      if (searchMode === 'qa') {
        // 问答式搜索
        const data = await qaSearch(query, 10)
        setQaResult(data)
        setRawResults([])
      } else {
        // 原始检索
        const data = await searchDocuments(query, 10)
        setRawResults(data.results || [])
        setQaResult(null)
      }
    } catch (error) {
      console.error('Search error:', error)
      setQaResult(null)
      setRawResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 style={{ marginBottom: '24px', color: '#fff' }}>文档问答</h2>

      <Card style={{
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.1)'
      }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 搜索模式切换 */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <Text type="secondary">搜索模式：</Text>
            <Button.Group>
              <Button
                type={searchMode === 'qa' ? 'primary' : 'default'}
                onClick={() => setSearchMode('qa')}
                icon={<RobotOutlined />}
              >
                智能问答
              </Button>
              <Button
                type={searchMode === 'raw' ? 'primary' : 'default'}
                onClick={() => setSearchMode('raw')}
                icon={<FileTextOutlined />}
              >
                原始检索
              </Button>
            </Button.Group>
          </div>

          {/* 搜索输入框 */}
          <TextArea
            placeholder={searchMode === 'qa'
              ? "输入问题，如：D9W的最大功率是多少？哪台机器更轻？"
              : "输入关键词搜索相关文档内容..."
            }
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                handleSearch()
              }
            }}
          />

          <Button
            type="primary"
            icon={<SearchOutlined />}
            size="large"
            onClick={handleSearch}
            loading={loading}
            style={{ width: '200px' }}
          >
            {searchMode === 'qa' ? '智能回答' : '搜索'}
          </Button>
        </Space>
      </Card>

      {loading && (
        <Card style={{
          marginTop: '24px',
          background: 'rgba(255,255,255,0.05)',
          border: '1px solid rgba(255,255,255,0.1)',
          textAlign: 'center'
        }}>
          <Spin size="large" tip={searchMode === 'qa' ? "AI 正在分析文档..." : "正在搜索..."} />
        </Card>
      )}

      {!loading && searched && searchMode === 'qa' && qaResult && (
        <>
          {/* AI 回答卡片 */}
          <Card
            style={{
              marginTop: '24px',
              background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%)',
              border: '1px solid rgba(102, 126, 234, 0.3)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <RobotOutlined style={{ fontSize: '24px', color: '#667eea', marginTop: '4px' }} />
              <div style={{ flex: 1 }}>
                <Title level={5} style={{ color: '#667eea', marginBottom: '16px' }}>
                  AI 回答
                </Title>
                <Paragraph
                  style={{
                    fontSize: '16px',
                    lineHeight: '2',
                    color: 'rgba(255,255,255,0.95)',
                    whiteSpace: 'pre-wrap'
                  }}
                >
                  {qaResult.answer}
                </Paragraph>

                <Divider style={{ margin: '16px 0', borderColor: 'rgba(255,255,255,0.1)' }} />

                <Space wrap>
                  <Tag color="blue" icon={<DatabaseOutlined />}>
                    检索到 {qaResult.total_retrieved} 个相关片段
                  </Tag>
                  <Tag color="green">
                    涉及 {qaResult.total_docs} 个文档
                  </Tag>
                  <Tag color="purple">
                    使用 {qaResult.used_chunks} 个片段生成回答
                  </Tag>
                </Space>

                {qaResult.sources && qaResult.sources.length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      参考文档：
                    </Text>
                    <Space wrap style={{ marginTop: '4px' }}>
                      {qaResult.sources.map((source, idx) => (
                        <Tag key={idx} color="cyan">{source}</Tag>
                      ))}
                    </Space>
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* 检索详情折叠面板 */}
          {qaResult.groups && Object.keys(qaResult.groups).length > 0 && (
            <Card
              title={
                <Space>
                  <DatabaseOutlined />
                  <span>检索详情</span>
                </Space>
              }
              style={{
                marginTop: '16px',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)'
              }}
            >
              <Collapse
                ghost
                expandIcon={({ isActive }) => <DownOutlined rotate={isActive ? 180 : 0} />}
              >
                {Object.entries(qaResult.groups).map(([docName, chunks]) => (
                  <Panel
                    header={
                      <Space>
                        <FileTextOutlined style={{ color: '#667eea' }} />
                        <Text strong>{docName}</Text>
                        <Tag>{chunks.length} 个片段</Tag>
                      </Space>
                    }
                    key={docName}
                  >
                    {chunks.map((chunk, idx) => (
                      <Card
                        key={idx}
                        size="small"
                        style={{
                          marginBottom: '8px',
                          background: 'rgba(0,0,0,0.2)',
                          border: '1px solid rgba(255,255,255,0.05)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <Text style={{ flex: 1, lineHeight: '1.8', color: 'rgba(255,255,255,0.85)' }}>
                            {chunk.content}
                          </Text>
                          <Tag color={chunk.distance < 0.5 ? 'green' : 'orange'} style={{ marginLeft: '12px', flexShrink: 0 }}>
                            相似度: {(1 - chunk.distance).toFixed(2)}
                          </Tag>
                        </div>
                      </Card>
                    ))}
                  </Panel>
                ))}
              </Collapse>
            </Card>
          )}
        </>
      )}

      {!loading && searched && searchMode === 'raw' && (
        <Card style={{
          marginTop: '24px',
          background: 'rgba(255,255,255,0.05)',
          border: '1px solid rgba(255,255,255,0.1)'
        }}>
          <div style={{ marginBottom: '16px' }}>
            <Space>
              <DatabaseOutlined />
              <Text>找到 {rawResults.length} 个相关结果</Text>
            </Space>
          </div>

          {rawResults.length === 0 ? (
            <Empty description="未找到相关文档，请尝试其他关键词" />
          ) : (
            rawResults.map((item, index) => (
              <Card
                key={item.chunk_id || index}
                size="small"
                style={{
                  marginBottom: '12px',
                  background: 'rgba(0,0,0,0.2)',
                  border: '1px solid rgba(255,255,255,0.1)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <Space style={{ marginBottom: '8px' }}>
                      <Tag color="blue">相关度: {(1 - (item.distance || 0)).toFixed(2)}</Tag>
                      <Text type="secondary">来源: {item.metadata?.source || '未知'}</Text>
                    </Space>
                    <Text style={{ display: 'block', lineHeight: '1.8', color: 'rgba(255,255,255,0.85)' }}>
                      {item.content}
                    </Text>
                  </div>
                  <Tag color={item.distance < 0.5 ? 'green' : 'orange'} style={{ marginLeft: '12px' }}>
                    {(1 - item.distance).toFixed(2)}
                  </Tag>
                </div>
              </Card>
            ))
          )}
        </Card>
      )}
    </div>
  )
}

export default SearchPage
