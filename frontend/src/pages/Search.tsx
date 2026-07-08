/**
 * 全文搜索页面 - 跨论文/笔记、跨字段检索（后端 SQLite FTS5）
 */
import { useState } from 'react';
import {
  Input, List, Card, Tag, Segmented, Empty, Spin, Typography, Space, Modal, Descriptions,
} from 'antd';
import { FileTextOutlined, BookOutlined, SearchOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DOMPurify from 'dompurify';
import { searchApi, papersApi, notesApi } from '../services/api';

const { Text } = Typography;

interface SearchResult {
  type: 'paper' | 'note';
  id: number;
  title: string;
  snippet: string;
  score: number;
  meta: any;
}

/** 把片段中的查询词高亮（纯文本拆分，避免 XSS）。 */
function highlight(snippet: string, terms: string[]) {
  if (!terms.length) return snippet;
  const escaped = terms
    .filter(Boolean)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!escaped.length) return snippet;
  const re = new RegExp(`(${escaped.join('|')})`, 'gi');
  const parts = snippet.split(re);
  return parts.map((part, i) =>
    re.test(part) ? (
      <mark key={i} style={{ background: '#ffe58f', padding: 0 }}>{part}</mark>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

export default function Search() {
  const [keyword, setKeyword] = useState('');
  const [type, setType] = useState<'all' | 'paper' | 'note'>('all');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [terms, setTerms] = useState<string[]>([]);
  const [detail, setDetail] = useState<any>(null);
  const [detailKind, setDetailKind] = useState<'paper' | 'note'>('paper');

  const runSearch = async (kw: string, t: 'all' | 'paper' | 'note') => {
    const q = kw.trim();
    if (!q) {
      setResults([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    setSearched(true);
    setTerms(q.split(/\s+/).filter(Boolean));
    try {
      const res = await searchApi.query({ q, type: t, limit: 50 });
      setResults(res.data.results);
    } catch {
      setResults([]);
    }
    setLoading(false);
  };

  const openDetail = async (r: SearchResult) => {
    try {
      if (r.type === 'paper') {
        const res = await papersApi.get(r.id);
        setDetail(res.data);
        setDetailKind('paper');
      } else {
        const res = await notesApi.get(r.id);
        setDetail(res.data);
        setDetailKind('note');
      }
    } catch { /* ignore */ }
  };

  return (
    <div style={{ width: '100%', flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <h2 style={{ marginTop: 0 }}>全文搜索</h2>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onSearch={(v) => runSearch(v, type)}
          placeholder="搜索论文、笔记内容（标题/作者/摘要/正文…）"
          allowClear
          enterButton={<><SearchOutlined /> 搜索</>}
          size="large"
          style={{ width: 480 }}
        />
        <Segmented
          value={type}
          onChange={(v) => {
            const nt = v as 'all' | 'paper' | 'note';
            setType(nt);
            if (keyword.trim()) runSearch(keyword, nt);
          }}
          options={[
            { label: '全部', value: 'all' },
            { label: '论文', value: 'paper' },
            { label: '笔记', value: 'note' },
          ]}
        />
      </Space>

      <div style={{ flex: 1, overflow: 'auto' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin /></div>
        ) : searched && results.length === 0 ? (
          <Empty description="没有找到匹配的内容" />
        ) : !searched ? (
          <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
            <SearchOutlined style={{ fontSize: 40 }} />
            <p>输入关键词，跨论文与笔记进行全文检索</p>
          </div>
        ) : (
          <>
            <Text type="secondary">共 {results.length} 条结果</Text>
            <List
              style={{ marginTop: 8 }}
              dataSource={results}
              renderItem={(r) => (
                <Card
                  size="small"
                  hoverable
                  style={{ marginBottom: 10 }}
                  onClick={() => openDetail(r)}
                >
                  <Space orientation="vertical" size={2} style={{ width: '100%' }}>
                    <Space>
                      {r.type === 'paper'
                        ? <Tag icon={<BookOutlined />} color="blue">论文</Tag>
                        : <Tag icon={<FileTextOutlined />} color="green">笔记</Tag>}
                      <span style={{ fontWeight: 600 }}>{highlight(r.title, terms)}</span>
                    </Space>
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      {highlight(r.snippet, terms)}
                    </Text>
                    <Space size={4} wrap style={{ fontSize: 12, color: '#999' }}>
                      {r.type === 'paper' && r.meta.authors && <span>{r.meta.authors}</span>}
                      {r.type === 'paper' && r.meta.year && <span>· {r.meta.year}</span>}
                      {r.type === 'paper' && r.meta.journal && <span>· {r.meta.journal}</span>}
                      {r.type === 'note' && r.meta.folder && <Tag>{r.meta.folder}</Tag>}
                    </Space>
                  </Space>
                </Card>
              )}
            />
          </>
        )}
      </div>

      <Modal
        title={detail?.title}
        open={!!detail}
        onCancel={() => setDetail(null)}
        footer={null}
        width={720}
      >
        {detail && detailKind === 'paper' && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="作者">{detail.authors || '-'}</Descriptions.Item>
            <Descriptions.Item label="年份">{detail.year || '-'}</Descriptions.Item>
            <Descriptions.Item label="期刊">{detail.journal || '-'}</Descriptions.Item>
            <Descriptions.Item label="DOI">{detail.doi || '-'}</Descriptions.Item>
            <Descriptions.Item label="状态">{detail.status}</Descriptions.Item>
            <Descriptions.Item label="摘要">{detail.abstract || '-'}</Descriptions.Item>
            <Descriptions.Item label="快速笔记">{detail.notes_text || '-'}</Descriptions.Item>
          </Descriptions>
        )}
        {detail && detailKind === 'note' && (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {DOMPurify.sanitize(detail.content || '')}
            </ReactMarkdown>
          </div>
        )}
      </Modal>
    </div>
  );
}
