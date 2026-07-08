/**
 * AI 问答页面 - SSE 流式对话
 */
import { useState, useRef, useEffect } from 'react';
import { Layout, Input, Button, List, Space, message, Card, Typography, Popconfirm } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, DeleteOutlined } from '@ant-design/icons';
import { aiApi } from '../services/api';

const { Sider, Content } = Layout;
const { Text } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<any[]>([]);
  const [currentSession, setCurrentSession] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  const fetchSessions = async () => {
    try {
      const res = await aiApi.sessions();
      setSessions(res.data);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchSessions(); }, []);

  const loadSession = async (sessionId: string) => {
    setCurrentSession(sessionId);
    try {
      const res = await aiApi.sessionMessages(sessionId);
      setMessages(res.data.map((m: any) => ({ role: m.role, content: m.content })));
    } catch { message.error('加载会话失败'); }
  };

  const handleDeleteSession = async (sessionId: string) => {
    await aiApi.deleteSession(sessionId);
    if (currentSession === sessionId) {
      setCurrentSession('');
      setMessages([]);
    }
    fetchSessions();
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    const sessionId = currentSession || crypto.randomUUID();
    if (!currentSession) setCurrentSession(sessionId);

    try {
      const response = await aiApi.chat({
        session_id: sessionId,
        message: userMsg,
      });

      if (!response.ok) {
        const err = await response.json();
        message.error(err.detail || '请求失败');
        setLoading(false);
        return;
      }

      // 从响应头获取实际的session_id
      const newSessionId = response.headers.get('X-Session-Id') || sessionId;
      if (!currentSession) setCurrentSession(newSessionId);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';

      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value);
          const lines = text.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.content) {
                  assistantContent += data.content;
                  setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = { role: 'assistant', content: assistantContent };
                    return updated;
                  });
                } else if (data.error) {
                  message.error(data.error);
                }
              } catch { /* ignore parse errors */ }
            }
          }
        }
      }

      fetchSessions();
    } catch {
      message.error('网络错误');
    }
    setLoading(false);
  };

  const startNewChat = () => {
    setCurrentSession('');
    setMessages([]);
  };

  return (
    <Layout style={{ flex: 1, minHeight: 0, borderRadius: 8, overflow: 'hidden' }}>
      <Sider width={220} theme="light" style={{ borderRight: '1px solid #f0f0f0', overflow: 'auto' }}>
        <div style={{ padding: 8 }}>
          <Button type="primary" block onClick={startNewChat}>新对话</Button>
        </div>
        <List
          dataSource={sessions}
          size="small"
          renderItem={(s: any) => (
            <List.Item
              style={{
                cursor: 'pointer', padding: '8px 12px',
                background: currentSession === s.session_id ? '#e6f7ff' : undefined,
              }}
              onClick={() => loadSession(s.session_id)}
              actions={[
                <Popconfirm title="删除会话?" onConfirm={() => handleDeleteSession(s.session_id)}>
                  <Button size="small" type="text" icon={<DeleteOutlined />} />
                </Popconfirm>
              ]}
            >
              <Text ellipsis style={{ maxWidth: 160 }}>{s.last_message || s.session_id.slice(0, 8)}</Text>
            </List.Item>
          )}
        />
      </Sider>
      <Content style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
          {messages.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 80, color: '#999' }}>
              <RobotOutlined style={{ fontSize: 48 }} />
              <p>科研AI助手，可以帮你解读论文、梳理文献、实验建议等</p>
              <p style={{ fontSize: 12 }}>由本地 Qwen2.5 模型驱动，首次提问需等待模型加载</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 12 }}>
                <Card
                  size="small"
                  style={{
                    maxWidth: '70%',
                    background: msg.role === 'user' ? '#e6f7ff' : '#f6ffed',
                  }}
                >
                  <Space>
                    {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content || '...'}</span>
                  </Space>
                </Card>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
        <div style={{ padding: '12px 16px', borderTop: '1px solid #f0f0f0' }}>
          <Space.Compact style={{ width: '100%' }}>
            <Input
              value={input}
              onChange={e => setInput(e.target.value)}
              onPressEnter={handleSend}
              placeholder="输入你的问题..."
              disabled={loading}
              size="large"
            />
            <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} size="large">
              发送
            </Button>
          </Space.Compact>
        </div>
      </Content>
    </Layout>
  );
}
