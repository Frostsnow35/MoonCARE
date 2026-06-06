function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
}

export function getCurrentUserId() {
  return getStoredUser()?.id || 'guest'
}

export function getUserScopedKey(prefix) {
  return `${prefix}:${getCurrentUserId()}`
}

export function clearUserScopedKeys(prefixes = []) {
  const suffix = `:${getCurrentUserId()}`
  const allKeys = Object.keys(localStorage)

  prefixes.forEach(prefix => {
    for (const key of allKeys) {
      if (key === prefix || key === `${prefix}${suffix}`) {
        localStorage.removeItem(key)
      }
    }
  })
}
