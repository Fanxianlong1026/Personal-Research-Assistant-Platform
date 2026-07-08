/**
 * 任务看板页面（支持拖拽排序）
 */
import { useState, useEffect } from 'react';
import { Card, Tag, Button, Modal, Form, Input, Select, Space, message, Popconfirm, Badge } from 'antd';
import { PlusOutlined, HolderOutlined } from '@ant-design/icons';
import { tasksApi } from '../services/api';

const priorityColors: Record<string, string> = {
  low: 'green', medium: 'blue', high: 'orange', urgent: 'red',
};
const priorityLabels: Record<string, string> = {
  low: '低', medium: '中', high: '高', urgent: '紧急',
};

const COLUMNS = ['todo', 'in_progress', 'done'] as const;
type ColumnKey = (typeof COLUMNS)[number];

export default function Tasks() {
  const [board, setBoard] = useState<any>({ todo: [], in_progress: [], done: [] });
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<any>(null);
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverCol, setDragOverCol] = useState<ColumnKey | null>(null);
  const [form] = Form.useForm();

  const fetchBoard = async () => {
    try {
      const res = await tasksApi.board();
      setBoard(res.data);
    } catch { message.error('获取任务看板失败'); }
  };

  useEffect(() => { fetchBoard(); }, []);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (values.due_date) values.due_date = values.due_date.format('YYYY-MM-DD');
      if (editingTask) {
        await tasksApi.update(editingTask.id, values);
      } else {
        await tasksApi.create(values);
      }
      message.success('保存成功');
      setModalOpen(false);
      form.resetFields();
      setEditingTask(null);
      fetchBoard();
    } catch { message.error('保存失败'); }
  };

  const handleStatusChange = async (id: number, status: string) => {
    await tasksApi.update(id, { status });
    fetchBoard();
  };

  const handleDelete = async (id: number) => {
    await tasksApi.delete(id);
    message.success('删除成功');
    fetchBoard();
  };

  // 把被拖拽任务移动到目标列；beforeId 为 null 时追加到列尾，否则插入到该卡片之前
  const moveTask = async (taskId: number, targetStatus: ColumnKey, beforeId: number | null) => {
    if (beforeId === taskId) return;
    const cols: Record<ColumnKey, any[]> = {
      todo: [...board.todo], in_progress: [...board.in_progress], done: [...board.done],
    };
    let moved: any;
    for (const key of COLUMNS) {
      const idx = cols[key].findIndex((t) => t.id === taskId);
      if (idx >= 0) { moved = cols[key][idx]; cols[key].splice(idx, 1); break; }
    }
    if (!moved) return;
    moved = { ...moved, status: targetStatus };
    const target = cols[targetStatus];
    const insertIdx = beforeId != null ? target.findIndex((t) => t.id === beforeId) : -1;
    if (insertIdx >= 0) target.splice(insertIdx, 0, moved);
    else target.push(moved);

    setBoard(cols);
    try {
      await tasksApi.reorder({
        todo: cols.todo.map((t) => t.id),
        in_progress: cols.in_progress.map((t) => t.id),
        done: cols.done.map((t) => t.id),
      });
    } catch {
      message.error('排序保存失败');
      fetchBoard();
    }
  };

  const renderColumn = (title: string, status: ColumnKey, items: any[], color: string) => (
    <div
      style={{
        flex: 1,
        padding: '0 8px',
        background: dragOverCol === status ? 'rgba(24,144,255,0.06)' : 'transparent',
        borderRadius: 8,
        transition: 'background 0.15s',
      }}
      onDragOver={(e) => { e.preventDefault(); setDragOverCol(status); }}
      onDragLeave={(e) => { if (e.currentTarget === e.target) setDragOverCol(null); }}
      onDrop={(e) => {
        e.preventDefault();
        if (draggedId != null) moveTask(draggedId, status, null);
        setDragOverCol(null);
      }}
    >
      <h3 style={{ borderBottom: `3px solid ${color}`, paddingBottom: 8, marginBottom: 12 }}>
        {title} <Badge count={items.length} style={{ backgroundColor: color }} />
      </h3>
      <div style={{ minHeight: 80 }}>
        {items.map((task: any) => (
          <Card
            key={task.id}
            size="small"
            style={{ marginBottom: 8, cursor: 'grab', opacity: draggedId === task.id ? 0.4 : 1 }}
            draggable
            onDragStart={(e) => { setDraggedId(task.id); e.dataTransfer.effectAllowed = 'move'; }}
            onDragEnd={() => { setDraggedId(null); setDragOverCol(null); }}
            onDragOver={(e) => { e.preventDefault(); setDragOverCol(status); }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (draggedId != null) moveTask(draggedId, status, task.id);
              setDragOverCol(null);
            }}
          >
            <div style={{ fontWeight: 500 }}>
              <HolderOutlined style={{ color: '#bbb', marginRight: 6 }} />
              {task.title}
            </div>
            {task.description && <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>{task.description}</div>}
            <Space style={{ marginTop: 8 }} size={4}>
              <Tag color={priorityColors[task.priority]}>{priorityLabels[task.priority]}</Tag>
              {(task.tags || []).map((t: string) => <Tag key={t}>{t}</Tag>)}
              {task.due_date && <Tag color="cyan">{task.due_date}</Tag>}
            </Space>
            <Space style={{ marginTop: 8 }}>
              {status !== 'todo' && (
                <Button size="small" onClick={() => handleStatusChange(task.id, status === 'done' ? 'in_progress' : 'todo')}>
                  ← 后退
                </Button>
              )}
              {status !== 'done' && (
                <Button size="small" type="primary" onClick={() => handleStatusChange(task.id, status === 'todo' ? 'in_progress' : 'done')}>
                  前进 →
                </Button>
              )}
              <Button size="small" onClick={() => { setEditingTask(task); form.setFieldsValue(task); setModalOpen(true); }}>
                编辑
              </Button>
              <Popconfirm title="确认删除?" onConfirm={() => handleDelete(task.id)}>
                <Button size="small" danger>删除</Button>
              </Popconfirm>
            </Space>
          </Card>
        ))}
      </div>
    </div>
  );

  return (
    <div>
      <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }}
        onClick={() => { setEditingTask(null); form.resetFields(); setModalOpen(true); }}>
        新建任务
      </Button>

      <div style={{ display: 'flex', gap: 16 }}>
        {renderColumn('待办', 'todo', board.todo || [], '#1890ff')}
        {renderColumn('进行中', 'in_progress', board.in_progress || [], '#faad14')}
        {renderColumn('已完成', 'done', board.done || [], '#52c41a')}
      </div>

      <Modal title={editingTask ? '编辑任务' : '新建任务'} open={modalOpen} onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingTask(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={3} /></Form.Item>
          <Space>
            <Form.Item name="priority" label="优先级">
              <Select style={{ width: 120 }} options={Object.entries(priorityLabels).map(([v, l]) => ({ value: v, label: l }))} />
            </Form.Item>
            <Form.Item name="status" label="状态">
              <Select style={{ width: 120 }} options={[
                { value: 'todo', label: '待办' }, { value: 'in_progress', label: '进行中' }, { value: 'done', label: '已完成' },
              ]} />
            </Form.Item>
          </Space>
          <Form.Item name="tags" label="标签"><Select mode="tags" placeholder="输入后回车" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
