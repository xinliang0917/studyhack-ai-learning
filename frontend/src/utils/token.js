const TOKEN_KEY = "token"
const COOKIE_NAME = "app_token"

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
  document.cookie = `${COOKIE_NAME}=${token}; path=/; SameSite=Lax`
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  document.cookie = `${COOKIE_NAME}=; path=/; Max-Age=0; SameSite=Lax`
}
