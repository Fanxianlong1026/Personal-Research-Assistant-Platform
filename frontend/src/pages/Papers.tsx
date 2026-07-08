/**
 * 论文管理页面
 */
import { useState, useEffect } from 'react';
import {
  Table, Button, Input, Modal, Form, Tag, Space, Upload, message, Select, Popconfirm,
  Drawer, Descriptions, Rate, Typography, Empty, Checkbox,
} from 'antd';
import {
  PlusOutlined, UploadOutlined, SearchOutlined, DownloadOutlined, ImportOutlined,
  FilePdfOutlined, LinkOutlined,
} from '@ant-design/icons';
import { papersApi, notesApi } from '../services/api';

const { Paragraph, Link, Text } = Typography;

const statusColors: Record<string, string> = {
  unread: 'default',
  reading: 'processing',
  finished: 'success',
  archived: 'warning',
};
const statusLabels: Record<string, string> = {
  unread: '未读',
  reading: '阅读中',
  finished: '已读完',
  archived: '已归档',
};

export default function Papers() {
  const [papers, setPapers] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPaper, setEditingPaper] = useState<any>(null);
  const [importId, setImportId] = useState('');
  const [importing, setImporting] = useState(false);
  const [importedPdfUrl, setImportedPdfUrl] = useState('');
  const [autoDownloadPdf, setAutoDownloadPdf] = useState(true);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [bibtexOpen, setBibtexOpen] = useState(false);
  const [bibtexText, setBibtexText] = useState('');
  const [importingBib, setImportingBib] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailPaper, setDetailPaper] = useState<any>(null);
  const [linkedNotes, setLinkedNotes] = useState<any[]>([]);
  const [fulltextOpen, setFulltextOpen] = useState(false);
  const [fulltextContent, setFulltextContent] = useState('');
  const [fulltextLoading, setFulltextLoading] = useState(false);
  const [readerOpen, setReaderOpen] = useState(false);
  const [readerPaper, setReaderPaper] = useState<any>(null);
  const [form] = Form.useForm();

  const fetchPapers = async (page = 1) => {
    setLoading(true);
    try {
      const res = await papersApi.list({ page, page_size: 15, search: search || undefined });
      setPapers(res.data.items);
      setTotal(res.data.total);
    } catch { message.error('获取论文列表失败'); }
    setLoading(false);
  };

  useEffect(() => { fetchPapers(); }, []);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingPaper) {
        await papersApi.update(editingPaper.id, values);
        message.success('更新成功');
      } else {
        const created = await papersApi.create(values);
        message.success('创建成功');
        if (importedPdfUrl && autoDownloadPdf) {
          const hide = message.loading('正在下载 PDF…', 0);
          try {
            await papersApi.downloadPdf(created.data.id, importedPdfUrl);
            hide();
            message.success('PDF 已下载并关联');
          } catch (e: any) {
            hide();
            message.warning(`论文已创建，但 PDF 下载失败：${e?.response?.data?.detail || '未知错误'}`);
          }
        }
      }
      setModalOpen(false);
      form.resetFields();
      setEditingPaper(null);
      setImportedPdfUrl('');
      fetchPapers();
    } catch { message.error('保存失败'); }
  };

  const handleDelete = async (id: number) => {
    await papersApi.delete(id);
    message.success('删除成功');
    fetchPapers();
  };

  const handleUpload = async (id: number, file: File) => {
    await papersApi.upload(id, file);
    message.success('上传成功');
    fetchPapers();
  };

  const handleImport = async () => {
    if (!importId.trim()) { message.warning('请输入 DOI 或 arXiv 链接/编号'); return; }
    setImporting(true);
    try {
      const res = await papersApi.importMeta(importId.trim());
      const d = res.data;
      form.setFieldsValue({
        title: d.title,
        authors: d.authors,
        abstract: d.abstract,
        journal: d.journal,
        year: d.year ?? undefined,
        doi: d.doi,
        url: d.url,
      });
      setImportedPdfUrl(d.pdf_url || '');
      message.success(d.pdf_url
        ? '已填入元数据（含 PDF 直链），保存时可自动下载'
        : '已填入元数据，请核对后保存');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '获取失败');
    }
    setImporting(false);
  };

  const openCreate = () => {
    setEditingPaper(null);
    form.resetFields();
    setImportId('');
    setImportedPdfUrl('');
    setModalOpen(true);
  };

  const handleExport = async () => {
    try {
      const ids = selectedRowKeys.map(Number);
      const res = await papersApi.exportBibtex(ids);
      const text: string = typeof res.data === 'string' ? res.data : String(res.data);
      if (!text.trim()) { message.warning('没有可导出的论文'); return; }
      const blob = new Blob([text], { type: 'application/x-bibtex;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `papers-${new Date().toISOString().slice(0, 10)}.bib`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已导出 ${ids.length || total} 篇`);
    } catch { message.error('导出失败'); }
  };

  const handleImportBibtex = async () => {
    if (!bibtexText.trim()) { message.warning('请粘贴或上传 .bib 内容'); return; }
    setImportingBib(true);
    try {
      const res = await papersApi.importBibtex(bibtexText);
      message.success(`成功导入 ${res.data.created} 篇（解析 ${res.data.parsed} 条）`);
      setBibtexOpen(false);
      setBibtexText('');
      fetchPapers();
    } catch { message.error('导入失败，请检查 .bib 格式'); }
    setImportingBib(false);
  };

  const openDetail = async (paper: any) => {
    setDetailPaper(paper);
    setDetailOpen(true);
    setLinkedNotes([]);
    try {
      const res = await notesApi.list({ paper_id: paper.id });
      setLinkedNotes(res.data.items || []);
    } catch { /* 关联笔记加载失败时静默 */ }
  };

  const handleExtract = async (paperId: number) => {
    const hide = message.loading('正在提取正文…', 0);
    try {
      const res = await papersApi.extractFulltext(paperId);
      hide();
      message.success(`已提取正文 ${res.data.chars} 字，可在全文搜索中命中`);
    } catch (e: any) {
      hide();
      message.error(e?.response?.data?.detail || '提取失败');
    }
  };

  const viewFulltext = async (paperId: number) => {
    setFulltextOpen(true);
    setFulltextContent('');
    setFulltextLoading(true);
    try {
      const res = await papersApi.getFulltext(paperId);
      setFulltextContent(res.data.fulltext || '');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '获取正文失败');
    } finally {
      setFulltextLoading(false);
    }
  };

  const columns = [
    {
      title: '标题', dataIndex: 'title', key: 'title', ellipsis: true,
      render: (t: string, record: any) => <a onClick={() => openDetail(record)}>{t}</a>,
    },
    { title: '作者', dataIndex: 'authors', key: 'authors', ellipsis: true },
    { title: '年份', dataIndex: 'year', key: 'year', width: 80 },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color={statusColors[s]}>{statusLabels[s] || s}</Tag>,
    },
    {
      title: '标签', dataIndex: 'tags', key: 'tags', width: 200,
      render: (tags: string[]) => (tags || []).map(t => <Tag key={t} color="blue">{t}</Tag>),
    },
    {
      title: '操作', key: 'action', width: 200,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => { setEditingPaper(record); form.setFieldsValue(record); setModalOpen(true); }}>
            编辑
          </Button>
          <Upload showUploadList={false} beforeUpload={(f) => { handleUpload(record.id, f); return false; }}>
            <Button size="small" icon={<UploadOutlined />}>PDF</Button>
          </Upload>
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ width: '100%', flex: 1 }}>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索论文..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onPressEnter={() => fetchPapers()}
          style={{ width: 300 }}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          添加论文
        </Button>
        <Button icon={<DownloadOutlined />} onClick={handleExport}>
          导出 BibTeX{selectedRowKeys.length ? `（${selectedRowKeys.length}）` : ''}
        </Button>
        <Button icon={<ImportOutlined />} onClick={() => { setBibtexText(''); setBibtexOpen(true); }}>
          导入 BibTeX
        </Button>
      </Space>

      <Table columns={columns} dataSource={papers} rowKey="id" loading={loading}
        rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
        pagination={{ total, pageSize: 15, onChange: fetchPapers }} />

      <Modal title={editingPaper ? '编辑论文' : '添加论文'} open={modalOpen} onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingPaper(null); }} width={640}>
        {!editingPaper && (
          <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
            <Input
              placeholder="粘贴 DOI 或 arXiv 链接/编号，自动填充"
              value={importId}
              onChange={e => setImportId(e.target.value)}
              onPressEnter={handleImport}
              allowClear
            />
            <Button type="primary" loading={importing} onClick={handleImport}>获取</Button>
          </Space.Compact>
        )}
        {!editingPaper && importedPdfUrl && (
          <div style={{ marginTop: -8, marginBottom: 16 }}>
            <Checkbox checked={autoDownloadPdf} onChange={e => setAutoDownloadPdf(e.target.checked)}>
              保存时自动下载并关联 PDF
            </Checkbox>
          </div>
        )}
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="authors" label="作者"><Input /></Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="year" label="年份"><Input type="number" style={{ width: 120 }} /></Form.Item>
            <Form.Item name="journal" label="期刊/会议"><Input style={{ width: 200 }} /></Form.Item>
            <Form.Item name="status" label="状态">
              <Select style={{ width: 120 }} options={Object.entries(statusLabels).map(([v, l]) => ({ value: v, label: l }))} />
            </Form.Item>
          </Space>
          <Form.Item name="abstract" label="摘要"><Input.TextArea rows={4} /></Form.Item>
          <Form.Item name="doi" label="DOI"><Input /></Form.Item>
          <Form.Item name="tags" label="标签（逗号分隔）">
            <Select mode="tags" placeholder="输入后回车添加" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="导入 BibTeX" open={bibtexOpen} onOk={handleImportBibtex}
        confirmLoading={importingBib} okText="导入"
        onCancel={() => setBibtexOpen(false)} width={640}>
        <Space style={{ marginBottom: 8 }}>
          <Upload showUploadList={false} accept=".bib,.txt"
            beforeUpload={(f) => { f.text().then(setBibtexText); return false; }}>
            <Button icon={<UploadOutlined />}>选择 .bib 文件</Button>
          </Upload>
          <Text type="secondary">或直接粘贴下方</Text>
        </Space>
        <Input.TextArea rows={12} value={bibtexText} onChange={e => setBibtexText(e.target.value)}
          placeholder="@article{key, title={...}, author={...}, year={2020}, ...}" />
      </Modal>

      <Drawer title="论文详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={560}>
        {detailPaper && (
          <>
            <Descriptions column={1} size="small" bordered styles={{ label: { width: 90 } }}>
              <Descriptions.Item label="标题">{detailPaper.title}</Descriptions.Item>
              <Descriptions.Item label="作者">{detailPaper.authors || '—'}</Descriptions.Item>
              <Descriptions.Item label="年份">{detailPaper.year || '—'}</Descriptions.Item>
              <Descriptions.Item label="期刊/会议">{detailPaper.journal || '—'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={statusColors[detailPaper.status]}>{statusLabels[detailPaper.status] || detailPaper.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="评分">
                {detailPaper.rating ? <Rate disabled value={detailPaper.rating} /> : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="DOI">
                {detailPaper.doi
                  ? <Link href={`https://doi.org/${detailPaper.doi}`} target="_blank">{detailPaper.doi}</Link>
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="链接">
                {detailPaper.url ? <Link href={detailPaper.url} target="_blank">{detailPaper.url}</Link> : '—'}
              </Descriptions.Item>
            </Descriptions>

            <Space style={{ margin: '16px 0' }}>
              {detailPaper.file_path
                ? <>
                    <Button type="primary" icon={<FilePdfOutlined />} onClick={() => { setReaderPaper(detailPaper); setReaderOpen(true); }}>
                      阅读 PDF
                    </Button>
                    <Button onClick={() => window.open(papersApi.fileUrl(detailPaper.id), '_blank')}>新标签打开</Button>
                    <Button onClick={() => viewFulltext(detailPaper.id)}>查看正文</Button>
                    <Button onClick={() => handleExtract(detailPaper.id)}>提取正文</Button>
                  </>
                : <Text type="secondary"><FilePdfOutlined /> 未上传 PDF</Text>}
            </Space>

            {detailPaper.abstract && (
              <>
                <Text strong>摘要</Text>
                <Paragraph style={{ marginTop: 8, color: '#555' }}>{detailPaper.abstract}</Paragraph>
              </>
            )}

            <Text strong><LinkOutlined /> 关联笔记（{linkedNotes.length}）</Text>
            <div style={{ marginTop: 8 }}>
              {linkedNotes.length === 0
                ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无关联笔记" />
                : linkedNotes.map((n) => (
                    <div key={n.id} style={{ padding: '8px 12px', border: '1px solid #f0f0f0', borderRadius: 6, marginBottom: 8 }}>
                      <div style={{ fontWeight: 500 }}>{n.title}</div>
                      {n.folder && <Tag style={{ marginTop: 4 }}>{n.folder}</Tag>}
                      {(n.tags || []).map((t: string) => <Tag key={t} color="blue">{t}</Tag>)}
                    </div>
                  ))}
            </div>
          </>
        )}
      </Drawer>

      <Modal
        title={readerPaper?.title || 'PDF 阅读'}
        open={readerOpen}
        onCancel={() => setReaderOpen(false)}
        footer={null}
        width="90vw"
        style={{ top: 24, maxWidth: 1200 }}
        styles={{ body: { padding: 0, height: '82vh' } }}
        destroyOnHidden
      >
        {readerPaper && (
          <iframe
            title="pdf-reader"
            src={papersApi.fileUrl(readerPaper.id)}
            style={{ width: '100%', height: '100%', border: 'none' }}
          />
        )}
      </Modal>

      <Modal
        title={`PDF 正文（${fulltextContent.length} 字）`}
        open={fulltextOpen}
        onCancel={() => setFulltextOpen(false)}
        footer={null}
        width={800}
      >
        {fulltextLoading
          ? <Text type="secondary">加载中…</Text>
          : fulltextContent
            ? <pre style={{
                whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: '65vh',
                overflow: 'auto', margin: 0, fontFamily: 'inherit', fontSize: 13, lineHeight: 1.7,
              }}>{fulltextContent}</pre>
            : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无正文，请先上传 PDF 并点「提取正文」" />}
      </Modal>
    </div>
  );
}
