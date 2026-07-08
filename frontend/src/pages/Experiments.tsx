/**
 * 实验记录页面 - 支持实验分组、重复运行对比、消融实验
 * 布局：左侧实验组列表 + 右侧对比表格/实验列表
 */
import { useState, useEffect } from 'react';
import {
  Layout, List, Card, Tag, Button, Modal, Form, Input, Select,
  Space, message, Popconfirm, Descriptions, Table,
  Statistic, Row, Col, Empty,
} from 'antd';
import {
  PlusOutlined, ExperimentOutlined, BarChartOutlined,
} from '@ant-design/icons';
import { experimentsApi, experimentGroupsApi } from '../services/api';
import MetricsChart from '../components/MetricsChart';

/** 判断对比数据中是否存在可绘图的数值型指标 */
const hasNumericMetric = (data: any): boolean =>
  !!data?.rows?.some((r: any) =>
    (data.metric_keys || []).some((k: string) => !Number.isNaN(parseFloat(r.metrics?.[k]))),
  );

const { Sider, Content } = Layout;

const statusColors: Record<string, string> = {
  running: 'processing', completed: 'success', failed: 'error', archived: 'default',
};

export default function Experiments() {
  // 实验组
  const [groups, setGroups] = useState<any[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<any>(null);
  const [compareData, setCompareData] = useState<any>(null);

  // 独立实验（不属于任何组）
  const [standaloneExps, setStandaloneExps] = useState<any[]>([]);
  const [allExps, setAllExps] = useState<any[]>([]);

  // UI状态
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [runModalOpen, setRunModalOpen] = useState(false);
  const [selectedExp, setSelectedExp] = useState<any>(null);
  const [groupForm] = Form.useForm();
  const [runForm] = Form.useForm();

  // ========== 数据加载 ==========
  const fetchGroups = async () => {
    try {
      const res = await experimentGroupsApi.list();
      setGroups(res.data);
    } catch { message.error('获取实验组失败'); }
  };

  const fetchAllExperiments = async () => {
    try {
      const res = await experimentsApi.list({ page_size: 100 });
      setAllExps(res.data.items);
      setStandaloneExps(res.data.items.filter((e: any) => !e.group_id));
    } catch { message.error('获取实验记录失败'); }
  };

  const fetchCompare = async (groupId: number) => {
    try {
      const res = await experimentGroupsApi.compare(groupId);
      setCompareData(res.data);
    } catch { message.error('获取对比数据失败'); }
  };

  useEffect(() => { fetchGroups(); fetchAllExperiments(); }, []);

  const handleSelectGroup = async (group: any) => {
    setSelectedGroup(group);
    await fetchCompare(group.id);
  };

  // ========== 实验组操作 ==========
  const handleCreateGroup = async () => {
    try {
      const values = await groupForm.validateFields();
      // 解析 compare_metrics：逗号分隔的字符串转数组
      if (typeof values.compare_metrics === 'string') {
        values.compare_metrics = values.compare_metrics.split(',').map((s: string) => s.trim()).filter(Boolean);
      }
      // 解析 base_parameters：JSON字符串转对象
      if (typeof values.base_parameters_str === 'string' && values.base_parameters_str.trim()) {
        try {
          values.base_parameters = JSON.parse(values.base_parameters_str);
        } catch {
          message.warning('基准参数格式错误，请使用JSON格式如 {"lr": 0.001}');
          return;
        }
      }
      delete values.base_parameters_str;
      await experimentGroupsApi.create(values);
      message.success('实验组创建成功');
      setGroupModalOpen(false);
      groupForm.resetFields();
      fetchGroups();
    } catch { message.error('创建失败'); }
  };

  const handleDeleteGroup = async (id: number) => {
    await experimentGroupsApi.delete(id);
    message.success('删除成功');
    if (selectedGroup?.id === id) {
      setSelectedGroup(null);
      setCompareData(null);
    }
    fetchGroups();
    fetchAllExperiments();
  };

  const handleAddRun = async () => {
    if (!selectedGroup) return;
    try {
      const values = await runForm.validateFields();
      if (typeof values.metrics_str === 'string' && values.metrics_str.trim()) {
        try { values.metrics = JSON.parse(values.metrics_str); } catch { /* ignore */ }
      }
      if (typeof values.parameters_str === 'string' && values.parameters_str.trim()) {
        try { values.parameters = JSON.parse(values.parameters_str); } catch { /* ignore */ }
      }
      delete values.metrics_str;
      delete values.parameters_str;

      // 先添加run，然后更新其数据
      const runRes = await experimentGroupsApi.addRun(selectedGroup.id);
      const runId = runRes.data.id;
      if (Object.keys(values).length > 0) {
        await experimentsApi.update(runId, {
          ...values,
          group_id: selectedGroup.id,
        });
      }
      message.success('新运行已添加');
      setRunModalOpen(false);
      runForm.resetFields();
      handleSelectGroup(selectedGroup);
      fetchAllExperiments();
    } catch { message.error('添加失败'); }
  };

  const handleDeleteExp = async (id: number) => {
    await experimentsApi.delete(id);
    message.success('删除成功');
    if (selectedGroup) handleSelectGroup(selectedGroup);
    fetchAllExperiments();
  };

  // ========== 对比表格列 ==========
  const getCompareColumns = () => {
    if (!compareData) return [];
    const cols: any[] = [
      { title: '运行', dataIndex: 'variant', key: 'variant', fixed: 'left' as const, width: 150 },
      { title: 'Run #', dataIndex: 'run_number', key: 'run_number', width: 70 },
      { title: '状态', dataIndex: 'status', key: 'status', width: 80,
        render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag> },
      { title: '日期', dataIndex: 'date', key: 'date', width: 120,
        render: (d: string) => new Date(d).toLocaleDateString() },
    ];

    // 参数列
    (compareData.param_keys || []).forEach((key: string) => {
      cols.push({
        title: `参数: ${key}`,
        key: `param_${key}`,
        width: 120,
        render: (_: any, record: any) => {
          const val = record.parameters?.[key];
          return val !== 'N/A' ? <Tag>{String(val)}</Tag> : '-';
        },
      });
    });

    // 指标列
    (compareData.metric_keys || []).forEach((key: string) => {
      const summary = compareData.summary?.[key];
      cols.push({
        title: <span><BarChartOutlined /> {key}</span>,
        key: `metric_${key}`,
        width: 120,
        render: (_: any, record: any) => {
          const val = record.metrics?.[key];
          if (val === 'N/A') return '-';
          const numVal = parseFloat(val);
          const isBest = summary && numVal === summary.max;
          const isWorst = summary && numVal === summary.min;
          return (
            <span style={{
              fontWeight: isBest ? 700 : 400,
              color: isBest ? '#52c41a' : isWorst ? '#ff4d4f' : undefined,
            }}>
              {val}
              {isBest && ' ★'}
            </span>
          );
        },
      });
    });

    // 操作列
    cols.push({
      title: '操作', key: 'action', width: 120, fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => {
            const exp = allExps.find((e: any) => e.id === record.id);
            if (exp) setSelectedExp(exp);
          }}>详情</Button>
          <Popconfirm title="删除?" onConfirm={() => handleDeleteExp(record.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    });

    return cols;
  };

  return (
    <Layout style={{ flex: 1, minHeight: 0, borderRadius: 8, overflow: 'hidden' }}>
      <Sider width={240} theme="light" style={{ borderRight: '1px solid #f0f0f0', overflow: 'auto' }}>
        <div style={{ padding: '8px' }}>
          <Button type="primary" icon={<PlusOutlined />} block onClick={() => setGroupModalOpen(true)}>
            新建实验组
          </Button>
        </div>
        <List
          dataSource={groups}
          size="small"
          renderItem={(g: any) => (
            <List.Item
              style={{
                cursor: 'pointer',
                background: selectedGroup?.id === g.id ? '#e6f7ff' : undefined,
                padding: '8px 12px',
              }}
              onClick={() => handleSelectGroup(g)}
              actions={[
                <Popconfirm title="删除实验组及其所有运行?" onConfirm={() => handleDeleteGroup(g.id)}>
                  <Button size="small" type="text" danger>x</Button>
                </Popconfirm>
              ]}
            >
              <List.Item.Meta
                avatar={<ExperimentOutlined />}
                title={g.name}
                description={`${g.compare_metrics?.length || 0} 个对比指标`}
              />
            </List.Item>
          )}
        />
        {groups.length === 0 && (
          <Empty description="暂无实验组" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: 20 }} />
        )}
      </Sider>

      <Content style={{ padding: 16, overflow: 'auto' }}>
        {selectedGroup && compareData ? (
          <div>
            <Space style={{ marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>{compareData.group_name}</h2>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setRunModalOpen(true)}>
                添加运行
              </Button>
            </Space>
            {selectedGroup.description && <p style={{ color: '#666' }}>{selectedGroup.description}</p>}

            {/* 统计摘要 */}
            {compareData.summary && Object.keys(compareData.summary).length > 0 && (
              <Card size="small" style={{ marginBottom: 16 }} title="对比摘要">
                <Row gutter={16}>
                  {(compareData.metric_keys || []).map((key: string) => {
                    const s = compareData.summary?.[key];
                    if (!s || typeof s !== 'object' || !s.mean) return null;
                    return (
                      <Col key={key} span={6}>
                        <Statistic title={`${key} (均值)`} value={s.mean} precision={4}
                          suffix={<span style={{ fontSize: 12 }}>±{s.std}</span>} />
                        <div style={{ fontSize: 12, color: '#999' }}>
                          最佳: <span style={{ color: '#52c41a' }}>{s.max}</span>
                          {' | '}
                          最差: <span style={{ color: '#ff4d4f' }}>{s.min}</span>
                          {' | '}共 {s.count} 次
                        </div>
                      </Col>
                    );
                  })}
                  {compareData.summary.best_run && (
                    <Col span={6}>
                      <Statistic title="最佳运行" value={compareData.summary.best_run.variant}
                        suffix={<span style={{ fontSize: 12 }}>
                          {compareData.metric_keys?.[0]}={compareData.summary.best_run.value}
                        </span>} />
                    </Col>
                  )}
                </Row>
              </Card>
            )}

            {/* 参数差异提示 */}
            {compareData.summary?.parameter_differences && (
              <Card size="small" style={{ marginBottom: 16, borderColor: '#faad14' }}
                title={<span style={{ color: '#faad14' }}>消融变量检测</span>}>
                {compareData.summary.parameter_differences.map((d: any, i: number) => (
                  <div key={i}>
                    <Tag color="orange">{d.key}</Tag>
                    变化值: {d.values.map((v: any, j: number) => (
                      <Tag key={j}>{String(v)}</Tag>
                    ))}
                  </div>
                ))}
              </Card>
            )}

            {/* 指标对比图 */}
            {hasNumericMetric(compareData) && (
              <Card size="small" style={{ marginBottom: 16 }} title="指标对比图">
                <MetricsChart compareData={compareData} />
              </Card>
            )}

            {/* 对比表格 */}
            <Table
              dataSource={compareData.rows}
              columns={getCompareColumns()}
              rowKey="id"
              size="small"
              pagination={false}
              scroll={{ x: 'max-content' }}
            />
          </div>
        ) : (
          <div>
            <h2>所有实验记录</h2>
            <p style={{ color: '#999' }}>选择左侧实验组查看对比，或在此查看所有独立实验</p>
            <List
              dataSource={standaloneExps}
              renderItem={(item: any) => (
                <Card style={{ marginBottom: 8 }} size="small">
                  <Space>
                    <span style={{ fontWeight: 500 }}>{item.title}</span>
                    <Tag color={statusColors[item.status]}>{item.status}</Tag>
                    <span style={{ color: '#999' }}>{new Date(item.experiment_date).toLocaleDateString()}</span>
                    {(item.tags || []).map((t: string) => <Tag key={t}>{t}</Tag>)}
                    {item.metrics && Object.entries(item.metrics).map(([k, v]) => (
                      <Tag key={k} color="blue">{k}={String(v)}</Tag>
                    ))}
                    <Button size="small" onClick={() => setSelectedExp(item)}>详情</Button>
                    <Popconfirm title="删除?" onConfirm={() => handleDeleteExp(item.id)}>
                      <Button size="small" danger>删除</Button>
                    </Popconfirm>
                  </Space>
                </Card>
              )}
            />
            {standaloneExps.length === 0 && <Empty description="暂无独立实验记录" />}
          </div>
        )}
      </Content>

      {/* 实验详情弹窗 */}
      <Modal title="实验详情" open={!!selectedExp} onCancel={() => setSelectedExp(null)} footer={null} width={640}>
        {selectedExp && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="标题">{selectedExp.title}</Descriptions.Item>
            <Descriptions.Item label="变体">{selectedExp.variant || '-'}</Descriptions.Item>
            <Descriptions.Item label="Run #">{selectedExp.run_number}</Descriptions.Item>
            <Descriptions.Item label="描述">{selectedExp.description}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColors[selectedExp.status]}>{selectedExp.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="日期">{new Date(selectedExp.experiment_date).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="参数"><pre>{JSON.stringify(selectedExp.parameters, null, 2)}</pre></Descriptions.Item>
            <Descriptions.Item label="结果">{selectedExp.results}</Descriptions.Item>
            <Descriptions.Item label="指标"><pre>{JSON.stringify(selectedExp.metrics, null, 2)}</pre></Descriptions.Item>
            <Descriptions.Item label="备注">{selectedExp.notes || '-'}</Descriptions.Item>
            <Descriptions.Item label="附件">
              {(selectedExp.attachments || []).map((a: any, i: number) => <div key={i}>{a.name}</div>)}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* 新建实验组弹窗 */}
      <Modal title="新建实验组" open={groupModalOpen} onOk={handleCreateGroup}
        onCancel={() => setGroupModalOpen(false)} width={560}>
        <Form form={groupForm} layout="vertical">
          <Form.Item name="name" label="实验组名称" rules={[{ required: true }]}>
            <Input placeholder="如: BERT Fine-tuning 消融实验" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="实验目的、背景等" />
          </Form.Item>
          <Form.Item name="base_parameters_str" label="基准参数 (JSON)">
            <Input.TextArea rows={3} placeholder='{"lr": 0.001, "batch_size": 32, "epochs": 10}' />
          </Form.Item>
          <Form.Item name="compare_metrics" label="关注指标（逗号分隔）">
            <Input placeholder="accuracy, f1, loss" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 添加运行弹窗 */}
      <Modal title={`添加运行 - ${selectedGroup?.name || ''}`} open={runModalOpen}
        onOk={handleAddRun} onCancel={() => setRunModalOpen(false)} width={560}>
        <Form form={runForm} layout="vertical">
          <Form.Item name="variant" label="变体名称">
            <Input placeholder="如: w/o Attention, lr=0.01, Baseline" />
          </Form.Item>
          <Form.Item name="parameters_str" label="参数覆盖 (JSON，留空则继承基准)">
            <Input.TextArea rows={2} placeholder='{"lr": 0.01}' />
          </Form.Item>
          <Form.Item name="metrics_str" label="指标结果 (JSON)">
            <Input.TextArea rows={2} placeholder='{"accuracy": 0.95, "f1": 0.92}' />
          </Form.Item>
          <Form.Item name="results" label="结果描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} placeholder="本次运行的特殊情况" />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[
              { value: 'running', label: '进行中' }, { value: 'completed', label: '已完成' },
              { value: 'failed', label: '失败' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}
