/**
 * 知识库笔记页面 - Markdown编辑器 + 文件夹管理
 */
import { useState, useEffect } from 'react';
import { Layout, List, Input, Button, Modal, Form, Tag, Space, Tree, message, Popconfirm, Select } from 'antd';
import { PlusOutlined, FolderOutlined, FileTextOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DOMPurify from 'dompurify';
import { notesApi } from '../services/api';

const { Sider, Content } = Layout;

export default function Notes() {
  const [notes, setNotes] = useState<any[]>([]);
  const [folders, setFolders] = useState<string[]>([]);
  const [selectedNote, setSelectedNote] = useState<any>(null);
  const [selectedFolder, setSelectedFolder] = useState<string>('');
  const [editMode, setEditMode] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [content, setContent] = useState('');
  const [form] = Form.useForm();

  const fetchNotes = async () => {
    try {
      const res = await notesApi.list({ folder: selectedFolder || undefined });
      setNotes(res.data.items);
      setFolders(res.data.folders);
    } catch { message.error('获取笔记失败'); }
  };

  useEffect(() => { fetchNotes(); }, [selectedFolder]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await notesApi.create(values);
      message.success('创建成功');
      setModalOpen(false);
      form.resetFields();
      fetchNotes();
    } catch { message.error('创建失败'); }
  };

  const handleSave = async () => {
    if (!selectedNote) return;
    await notesApi.update(selectedNote.id, { content });
    message.success('保存成功');
    setEditMode(false);
    fetchNotes();
  };

  const handleDelete = async (id: number) => {
    await notesApi.delete(id);
    if (selectedNote?.id === id) setSelectedNote(null);
    message.success('删除成功');
    fetchNotes();
  };

  const treeData = [
    {
      title: '所有笔记',
      key: '',
      icon: <FolderOutlined />,
      children: folders.map(f => ({ title: f, key: f, icon: <FolderOutlined /> })),
    },
  ];

  return (
    <Layout style={{ flex: 1, minHeight: 0, borderRadius: 8, overflow: 'hidden' }}>
      <Sider width={180} theme="light" style={{ borderRight: '1px solid #f0f0f0', overflow: 'auto' }}>
        <div style={{ padding: '8px' }}>
          <Button type="primary" icon={<PlusOutlined />} block onClick={() => setModalOpen(true)}>
            新建笔记
          </Button>
        </div>
        <Tree
          showIcon
          defaultExpandAll
          treeData={treeData}
          selectedKeys={[selectedFolder]}
          onSelect={keys => { setSelectedNote(null); setSelectedFolder(keys[0] as string || ''); }}
        />
      </Sider>
      <Sider width={280} theme="light" style={{ borderRight: '1px solid #f0f0f0', overflow: 'auto' }}>
        <List
          dataSource={notes}
          renderItem={(item: any) => (
            <List.Item
              style={{ cursor: 'pointer', background: selectedNote?.id === item.id ? '#e6f7ff' : undefined }}
              onClick={() => { setSelectedNote(item); setContent(item.content); setEditMode(false); }}
            >
              <List.Item.Meta
                avatar={<FileTextOutlined />}
                title={item.title}
                description={
                  <Space size={4}>{(item.tags || []).map((t: string) => <Tag key={t} color="blue" style={{ fontSize: 10 }}>{t}</Tag>)}</Space>
                }
              />
            </List.Item>
          )}
        />
      </Sider>
      <Content style={{ padding: '16px', overflow: 'auto' }}>
        {selectedNote ? (
          <div>
            <Space style={{ marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>{selectedNote.title}</h2>
              {editMode ? (
                <Button type="primary" onClick={handleSave}>保存</Button>
              ) : (
                <Button onClick={() => setEditMode(true)}>编辑</Button>
              )}
              <Popconfirm title="确认删除?" onConfirm={() => handleDelete(selectedNote.id)}>
                <Button danger>删除</Button>
              </Popconfirm>
            </Space>
            {editMode ? (
              <Input.TextArea
                value={content}
                onChange={e => setContent(e.target.value)}
                rows={25}
                style={{ fontFamily: 'monospace' }}
              />
            ) : (
              <div className="markdown-body" style={{ padding: 16, border: '1px solid #f0f0f0', borderRadius: 8 }}>
                {/* 【踩坑提醒】Markdown渲染必须用DOMPurify过滤，防止XSS攻击 */}
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {DOMPurify.sanitize(content || '*暂无内容*')}
                </ReactMarkdown>
              </div>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 100, color: '#999' }}>选择一篇笔记查看</div>
        )}
      </Content>

      <Modal title="新建笔记" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="folder" label="文件夹" initialValue="default"><Input /></Form.Item>
          <Form.Item name="tags" label="标签"><Select mode="tags" placeholder="输入后回车" /></Form.Item>
          <Form.Item name="content" label="内容（Markdown）"><Input.TextArea rows={6} /></Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}
