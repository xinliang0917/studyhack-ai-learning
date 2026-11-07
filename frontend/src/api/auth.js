import api from "./index"

export const register = (username, password) =>
  api.post('/auth/register/password', { username, password })

export const login = (username, password) =>
  api.post('/auth/login/password', { username, password })

export const registerFace = (username, imageBase64) =>
  api.post('/auth/register/face', { username, image_base64: imageBase64 })

export const loginFace = (username, imageBase64) =>
  api.post('/auth/login/face', { username, image_base64: imageBase64 })

export const getMe = () => api.get('/auth/me')
