const SESSION_COOKIE_NAME = 'session_present'

export function hasActiveSession(): boolean {
  if (typeof document === 'undefined') {
    return false
  }

  return document.cookie
    .split(';')
    .map((cookie) => cookie.trim())
    .some((cookie) => cookie.startsWith(`${SESSION_COOKIE_NAME}=`))
}
