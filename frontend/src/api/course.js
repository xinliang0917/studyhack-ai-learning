import api from "./index"

export const generateOutline = (title, fileIds = []) => api.post('/course/outline/generate', { title, file_ids: fileIds })

export const getOutlines = () => api.get('/course/outline')

export const getOutlineDetail = (id) => api.get(`/course/outline/${id}`)

export const getChapters = (outlineId) => api.get(`/course/chapters/${outlineId}`)

export const generateChapterContent = (chapterId) => api.post(`/course/chapter/${chapterId}/generate`)

export const getChapter = (chapterId) => api.get(`/course/chapter/${chapterId}`)

export const updateProgress = (chapterId, status) =>
  api.put('/course/progress', { chapter_id: chapterId, status })

export const getProgress = () => api.get('/course/progress')

export const resetProgress = () => api.post('/course/progress/reset')

export const deleteOutline = (id) => api.delete(`/course/outline/${id}`)

export const getKnowledgeGraph = (outlineId) => api.get(`/learning/graph/${outlineId}`)

export const getLearningDashboard = () => api.get('/learning/dashboard')
