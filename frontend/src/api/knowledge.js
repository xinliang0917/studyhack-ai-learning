import api from "./index"

export const uploadDocument = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/knowledge/upload', form)
}

export const listDocuments = () => api.get('/knowledge/documents')

export const deleteDocument = (id) => api.delete(`/knowledge/documents/${id}`)

export const refreshIndex = () => api.post('/knowledge/refresh')

export const searchKnowledge = (query, k = 5) =>
  api.get('/knowledge/search', { params: { query, k } })
export const getDocumentContent = (id) => api.get(`/knowledge/documents/${id}/content`)
