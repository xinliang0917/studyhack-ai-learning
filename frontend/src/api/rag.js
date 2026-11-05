import api from "./index"

export const chatRag = (payload) => api.post("/rag/chat", payload)
