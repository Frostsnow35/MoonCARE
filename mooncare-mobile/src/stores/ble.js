import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { biometricAPI } from '../api'

// 与 ESP32 代码中完全一致的 UUID
const SERVICE_UUID      = '12345678-1234-1234-1234-1234567890ab'
const CHARACTERISTIC_UUID = 'abcdefab-1234-1234-1234-abcdefabcdef'

export const useBleStore = defineStore('ble', () => {
  // ── 状态 ──────────────────────────────────────────
  const status = ref('disconnected')   // disconnected | connecting | connected | error
  const errorMsg = ref('')
  const lastPacket = ref(null)         // 最近一次解析成功的数据包
  const deviceName = ref('')

  let bleDevice = null
  let bleCharacteristic = null

  // ── 计算属性 ──────────────────────────────────────
  const isConnected = computed(() => status.value === 'connected')
  const isConnecting = computed(() => status.value === 'connecting')

  // ── 连接 ──────────────────────────────────────────
  async function connect() {
    if (!navigator.bluetooth) {
      errorMsg.value = '浏览器不支持 Web Bluetooth，请使用 Chrome 或 Edge'
      status.value = 'error'
      return
    }

    try {
      status.value = 'connecting'
      errorMsg.value = ''

      // Windows Chrome 对 128-bit 自定义 UUID filter 支持不稳定，用设备名过滤更可靠
      bleDevice = await navigator.bluetooth.requestDevice({
        filters: [
          { name: 'MoonCare-Demo' },
          { namePrefix: 'MoonCare' },
        ],
        optionalServices: [SERVICE_UUID]
      })

      deviceName.value = bleDevice.name || 'MoonCare-Demo'
      bleDevice.addEventListener('gattserverdisconnected', onDisconnected)

      const server  = await bleDevice.gatt.connect()
      const service = await server.getPrimaryService(SERVICE_UUID)
      bleCharacteristic = await service.getCharacteristic(CHARACTERISTIC_UUID)

      // 订阅 Notify，每次 ESP32 推送数据时触发
      await bleCharacteristic.startNotifications()
      bleCharacteristic.addEventListener('characteristicvaluechanged', onData)

      status.value = 'connected'
    } catch (err) {
      // 用户取消选择器不算错误
      if (err.name === 'NotFoundError' || err.message?.includes('cancelled')) {
        status.value = 'disconnected'
      } else {
        errorMsg.value = err.message || '连接失败'
        status.value = 'error'
      }
    }
  }

  // ── 断开 ──────────────────────────────────────────
  async function disconnect() {
    if (bleCharacteristic) {
      try { await bleCharacteristic.stopNotifications() } catch (_) {}
      bleCharacteristic.removeEventListener('characteristicvaluechanged', onData)
      bleCharacteristic = null
    }
    if (bleDevice?.gatt?.connected) {
      bleDevice.gatt.disconnect()
    }
    bleDevice = null
    status.value = 'disconnected'
    deviceName.value = ''
  }

  // ── 被动断开回调 ──────────────────────────────────
  function onDisconnected() {
    status.value = 'disconnected'
    bleCharacteristic = null
  }

  // ── 接收数据 ──────────────────────────────────────
  // ESP32 发送的格式：{"temp":36.5,"bpm":72.3,"motion":"LOW","wearing":true}
  async function onData(event) {
    try {
      const raw = new TextDecoder().decode(event.target.value)
      const packet = JSON.parse(raw)
      lastPacket.value = packet

      // 字段名与后端 RawBiometricUpload 完全一致：temp / bpm / motion / wearing
      await biometricAPI.uploadRaw({
        temp:    packet.temp    ?? null,
        bpm:     packet.bpm    ?? null,
        motion:  packet.motion  ?? 'LOW',
        wearing: packet.wearing ?? false,
      })
    } catch (err) {
      // JSON 解析失败或上传失败时静默忽略，不中断连接
      console.warn('[BLE] data error:', err)
    }
  }

  return {
    status, errorMsg, lastPacket, deviceName,
    isConnected, isConnecting,
    connect, disconnect,
  }
})