import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export default {
  // 视频
  getVideos: () => api.get('/videos'),
  getVideoPreview: (path) => api.get('/videos/preview', { params: { path } }),

  // 任务
  createTask: (data) => api.post('/tasks', data),
  getTask: (id) => api.get(`/tasks/${id}`),
  cancelTask: (id) => api.delete(`/tasks/${id}`),
  rerunTask: (id) => api.post(`/tasks/${id}/rerun`),
  downloadSrt: (id) => api.get(`/tasks/${id}/srt`, { responseType: 'blob' }),

  // 历史
  getHistory: () => api.get('/history'),
  retranslate: (id, data) => api.post(`/history/${id}/retranslate`, data),
  deleteTask: (id) => api.delete(`/history/${id}`),
  deleteTasks: (ids) => api.delete('/history/batch', { data: { ids } }),

  // 设置
  getSettings: () => api.get('/settings'),
  updateSettings: (data) => api.put('/settings', data),
}
