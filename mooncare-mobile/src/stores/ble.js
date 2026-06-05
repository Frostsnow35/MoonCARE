import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { BleClient } from '@capacitor-community/bluetooth-le'
import { biometric_upload_raw } from '../api'
import { get_kv, set_kv, remove_kv } from '../services/kv'

const SERVICE_UUID = '12345678-1234-1234-1234-1234567890ab'
const CHARACTERISTIC_UUID = 'abcdefab-1234-1234-1234-abcdefabcdef'

function data_view_to_string(data_view) {
  const uint8 = new Uint8Array(data_view.buffer, data_view.byteOffset, data_view.byteLength)
  return new TextDecoder().decode(uint8)
}

export const useBleStore = defineStore('ble', () => {
  const status = ref('disconnected')
  const error_msg = ref('')
  const device_id = ref('')
  const device_name = ref('')
  const last_packet = ref(null)

  const should_reconnect = ref(true)
  const reconnect_attempt = ref(0)

  const is_connected = computed(() => status.value === 'connected')
  const is_connecting = computed(() => status.value === 'connecting')

  async function initialize() {
    try {
      await BleClient.initialize()
      const saved_device_id = await get_kv('ble_device_id')
      const saved_device_name = await get_kv('ble_device_name')
      if (saved_device_id) device_id.value = saved_device_id
      if (saved_device_name) device_name.value = saved_device_name
    } catch (err) {
      status.value = 'error'
      error_msg.value = err?.message || '蓝牙初始化失败'
    }
  }

  async function pick_and_connect() {
    error_msg.value = ''
    should_reconnect.value = true
    status.value = 'connecting'
    try {
      await BleClient.initialize()
      const device = await BleClient.requestDevice({
        services: [SERVICE_UUID],
        optionalServices: [SERVICE_UUID],
      })

      device_id.value = device.deviceId
      device_name.value = device.name || 'MoonCare'
      await set_kv('ble_device_id', device_id.value)
      await set_kv('ble_device_name', device_name.value)

      await connect(device_id.value)
    } catch (err) {
      status.value = 'disconnected'
      error_msg.value = err?.message || '未选择设备或连接失败'
    }
  }

  async function connect(target_device_id) {
    error_msg.value = ''
    should_reconnect.value = true
    status.value = 'connecting'
    try {
      await BleClient.initialize()
      await BleClient.connect(target_device_id, () => on_disconnect(target_device_id))

      await BleClient.startNotifications(target_device_id, SERVICE_UUID, CHARACTERISTIC_UUID, on_notification)

      reconnect_attempt.value = 0
      status.value = 'connected'
    } catch (err) {
      status.value = 'error'
      error_msg.value = err?.message || '连接失败'
      schedule_reconnect()
    }
  }

  async function disconnect() {
    should_reconnect.value = false
    error_msg.value = ''
    try {
      if (device_id.value) {
        try {
          await BleClient.stopNotifications(device_id.value, SERVICE_UUID, CHARACTERISTIC_UUID)
        } catch (_) {}
        try {
          await BleClient.disconnect(device_id.value)
        } catch (_) {}
      }
    } finally {
      status.value = 'disconnected'
    }
  }

  async function forget_device() {
    await disconnect()
    device_id.value = ''
    device_name.value = ''
    await remove_kv('ble_device_id')
    await remove_kv('ble_device_name')
  }

  function on_disconnect(target_device_id) {
    if (device_id.value === target_device_id) {
      status.value = 'disconnected'
    }
    schedule_reconnect()
  }

  function schedule_reconnect() {
    if (!should_reconnect.value) return
    if (!device_id.value) return
    if (status.value === 'connecting') return

    const attempt = reconnect_attempt.value + 1
    reconnect_attempt.value = attempt
    const delay_ms = Math.min(15000, 500 * Math.pow(2, attempt))
    status.value = 'connecting'

    setTimeout(() => {
      if (!should_reconnect.value) return
      if (!device_id.value) return
      connect(device_id.value)
    }, delay_ms)
  }

  async function on_notification(value) {
    try {
      const raw = data_view_to_string(value)
      const packet = JSON.parse(raw)
      last_packet.value = packet

      await biometric_upload_raw(
        {
          temp: packet.temp ?? null,
          bpm: packet.bpm ?? null,
          motion: packet.motion ?? 'LOW',
          wearing: packet.wearing ?? false,
        },
        device_id.value || 'DEVICE_001',
      )
    } catch (_) {}
  }

  return {
    status,
    error_msg,
    device_id,
    device_name,
    last_packet,
    is_connected,
    is_connecting,
    initialize,
    pick_and_connect,
    connect,
    disconnect,
    forget_device,
  }
})

