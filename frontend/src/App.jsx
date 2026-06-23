import { useState } from 'react'
import { Layout, Menu, theme } from 'antd'
import { FileTextOutlined, SearchOutlined, UploadOutlined } from '@ant-design/icons'
import UploadPage from './pages/UploadPage'
import SearchPage from './pages/SearchPage'
import DocumentListPage from './pages/DocumentListPage'

const { Header, Content } = Layout

function App() {
  const [currentPage, setCurrentPage] = useState('upload')
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  const renderPage = () => {
    switch (currentPage) {
      case 'upload':
        return <UploadPage />
      case 'search':
        return <SearchPage />
      case 'list':
        return <DocumentListPage />
      default:
        return <UploadPage />
    }
  }

  const menuItems = [
    {
      key: 'upload',
      icon: <UploadOutlined />,
      label: '上传文档',
    },
    {
      key: 'search',
      icon: <SearchOutlined />,
      label: '搜索文档',
    },
    {
      key: 'list',
      icon: <FileTextOutlined />,
      label: '文档列表',
    },
  ]

  return (
    <Layout className="app-container" style={{ padding: 0, minHeight: '100vh' }}>
      <Layout>
        <Header style={{
          display: 'flex',
          alignItems: 'center',
          background: 'rgba(26, 26, 46, 0.8)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(255,255,255,0.1)'
        }}>
          <div style={{
            color: '#fff',
            fontSize: '20px',
            fontWeight: 'bold',
            marginRight: '40px',
            textShadow: '0 0 10px rgba(114, 46, 209, 0.5)'
          }}>
            文档管理系统
          </div>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[currentPage]}
            onClick={({ key }) => setCurrentPage(key)}
            items={menuItems}
            style={{ background: 'transparent', flex: 1, border: 'none' }}
          />
        </Header>
        <Content style={{ padding: '24px' }}>
          <div
            style={{
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
              padding: '24px',
              minHeight: 'calc(100vh - 160px)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
              border: '1px solid rgba(255,255,255,0.1)',
            }}
          >
            {renderPage()}
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}

export default App
