import { Preferences } from '@capacitor/preferences'

export async function get_kv(key) {
  try {
    const result = await Preferences.get({ key })
    return result.value ?? null
  } catch (_) {
    return localStorage.getItem(key)
  }
}

export async function set_kv(key, value) {
  const normalized_value = value == null ? '' : String(value)
  try {
    await Preferences.set({ key, value: normalized_value })
  } catch (_) {
    localStorage.setItem(key, normalized_value)
  }
}

export async function remove_kv(key) {
  try {
    await Preferences.remove({ key })
  } catch (_) {
    localStorage.removeItem(key)
  }
}

