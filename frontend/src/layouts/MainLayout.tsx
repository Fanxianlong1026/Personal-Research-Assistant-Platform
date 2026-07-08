/**
 * 主布局组件 - 侧边栏导航 + 全屏内容区域
 */
import { Layout, Menu, Typography } from 'antd';
import {
  BookOutlined,
  FileTextOutlined,
  ExperimentOutlined,
  CheckSquareOutlined,
  RobotOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';

const { Sider, Content } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: '/search', icon: <SearchOutlined />, label: '全文搜索' },
  { key: '/papers', icon: <BookOutlined />, label: '论文管理' },
  { key: '/notes', icon: <FileTextOutlined />, label: '知识库笔记' },
  { key: '/experiments', icon: <ExperimentOutlined />, label: '实验记录' },
  { key: '/tasks', icon: <CheckSquareOutlined />, label: '任务管理' },
  { key: '/ai-chat', icon: <RobotOutlined />, label: 'AI 问答' },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider
        theme="dark"
        width={200}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
        }}
      >
        <div style={{
          padding: '20px 16px 16px',
          textAlign: 'center',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}>
          <Title level={4} style={{ color: '#fff', margin: 0, fontSize: 18, letterSpacing: 2 }}>
            科研助手
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0, marginTop: 8 }}
        />
      </Sider>
      <Layout style={{ marginLeft: 200, height: '100vh' }}>
        <Content
          style={{
            padding: '20px 24px',
            background: '#fff',
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
