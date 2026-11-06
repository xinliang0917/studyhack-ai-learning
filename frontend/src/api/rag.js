import api from "./index"

export const chatRag = (payload) => api.post("/rag/chat", payload)

export const listSessions = () => api.get("/rag/sessions")

export const createSession = (title) => api.post("/rag/sessions", { title })

export const getSession = (id) => api.get(`/rag/sessions/${id}`)

export const deleteSession = (id) => api.delete(`/rag/sessions/${id}`)

export const evaluateRag = (cases, k = 5) => api.post("/rag/evaluate", { cases, k })
