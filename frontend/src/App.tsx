/**
 * 应用入口 - 路由配置
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './layouts/MainLayout';
import Papers from './pages/Papers';
import Notes from './pages/Notes';
import Experiments from './pages/Experiments';
import Tasks from './pages/Tasks';
import AIChat from './pages/AIChat';
import Search from './pages/Search';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/papers" replace />} />
            <Route path="search" element={<Search />} />
            <Route path="papers" element={<Papers />} />
            <Route path="notes" element={<Notes />} />
            <Route path="experiments" element={<Experiments />} />
            <Route path="tasks" element={<Tasks />} />
            <Route path="ai-chat" element={<AIChat />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
