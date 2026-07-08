/**
 * API 服务层 - 统一管理所有后端 API 调用
 */
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

// ========== 论文管理 ==========
export const papersApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; tag?: string; status?: string }) =>
    api.get('/papers', { params }),
  get: (id: number) => api.get(`/papers/${id}`),
  create: (data: any) => api.post('/papers', data),
  update: (id: number, data: any) => api.put(`/papers/${id}`, data),
  delete: (id: number) => api.delete(`/papers/${id}`),
  upload: (id: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/papers/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getTags: () => api.get('/papers/tags/all'),
  importMeta: (identifier: string) => api.post('/papers/import', { identifier }),
  exportBibtex: (ids?: number[]) =>
    api.get('/papers/export/bibtex', { params: ids?.length ? { ids: ids.join(',') } : {}, responseType: 'text' }),
  importBibtex: (content: string) => api.post('/papers/import-bibtex', { content }),
  extractFulltext: (id: number) => api.post(`/papers/${id}/extract`),
  getFulltext: (id: number) => api.get(`/papers/${id}/fulltext`),
  downloadPdf: (id: number, url: string) => api.post(`/papers/${id}/download-pdf`, { url }),
  fileUrl: (id: number) => `/api/v1/papers/${id}/file`,
};

// ========== 笔记管理 ==========
export const notesApi = {
  list: (params?: { folder?: string; tag?: string; search?: string; paper_id?: number }) =>
    api.get('/notes', { params }),
  get: (id: number) => api.get(`/notes/${id}`),
  create: (data: any) => api.post('/notes', data),
  update: (id: number, data: any) => api.put(`/notes/${id}`, data),
  delete: (id: number) => api.delete(`/notes/${id}`),
  getTags: () => api.get('/notes/tags/all'),
};

// ========== 实验记录 ==========
export const experimentsApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; search?: string; group_id?: number }) =>
    api.get('/experiments', { params }),
  get: (id: number) => api.get(`/experiments/${id}`),
  create: (data: any) => api.post('/experiments', data),
  update: (id: number, data: any) => api.put(`/experiments/${id}`, data),
  delete: (id: number) => api.delete(`/experiments/${id}`),
  upload: (id: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/experiments/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ========== 实验组管理（重复实验/消融实验对比）==========
export const experimentGroupsApi = {
  list: () => api.get('/experiment-groups'),
  get: (id: number) => api.get(`/experiment-groups/${id}`),
  create: (data: any) => api.post('/experiment-groups', data),
  update: (id: number, data: any) => api.put(`/experiment-groups/${id}`, data),
  delete: (id: number) => api.delete(`/experiment-groups/${id}`),
  compare: (id: number) => api.get(`/experiment-groups/${id}/compare`),
  addRun: (id: number) => api.post(`/experiment-groups/${id}/add-run`),
};

// ========== 任务管理 ==========
export const tasksApi = {
  board: () => api.get('/tasks/board'),
  list: (params?: { status?: string; priority?: string }) => api.get('/tasks', { params }),
  create: (data: any) => api.post('/tasks', data),
  update: (id: number, data: any) => api.put(`/tasks/${id}`, data),
  delete: (id: number) => api.delete(`/tasks/${id}`),
  reorder: (data: { todo: number[]; in_progress: number[]; done: number[] }) =>
    api.post('/tasks/reorder', data),
};

// ========== 全文搜索 ==========
export const searchApi = {
  query: (params: { q: string; type?: 'all' | 'paper' | 'note'; limit?: number }) =>
    api.get('/search', { params }),
};

// ========== AI 问答 ==========
export const aiApi = {
  chat: (data: { session_id: string; message: string; context?: string }) =>
    fetch('/api/v1/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  sessions: () => api.get('/ai/sessions'),
  sessionMessages: (sessionId: string) => api.get(`/ai/sessions/${sessionId}`),
  deleteSession: (sessionId: string) => api.delete(`/ai/sessions/${sessionId}`),
};

export default api;
