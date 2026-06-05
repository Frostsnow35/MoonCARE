<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useBleStore } from '../stores/ble'
import { biometric_upload_raw } from '../api'

const ble_store = useBleStore()

const can_reconnect = computed(() => Boolean(ble_store.device_id) && !ble_store.is_connected)

const is_simulating = ref(false)
const simulate_error = ref('')
let simulate_timer = null

function make_simulated_packet() {
  const now = Date.now()
  const temp = 36.2 + ((now % 8000) / 8000) * 0.8
  const bpm = 68 + ((now % 5000) / 5000) * 18
  const motion = (now % 3) === 0 ? 'LOW' : (now % 3) === 1 ? 'MID' : 'HIGH'
  return {
    temp: Number(temp.toFixed(2)),
    bpm: Number(bpm.toFixed(1)),
    motion,
    wearing: true,
  }
}

async function start_simulation() {
  if (is_simulating.value) return
  simulate_error.value = ''
  is_simulating.value = true

  const tick = async () => {
    try {
      const packet = make_simulated_packet()
      ble_store.last_packet = packet
      await biometric_upload_raw(packet, 'EMULATOR_SIM')
    } catch (err) {
      simulate_error.value = err?.response?.data?.detail || err?.message || '模拟上报失败'
    }
  }

  await tick()
  simulate_timer = setInterval(tick, 2000)
}

function stop_simulation() {
  is_simulating.value = false
  simulate_error.value = ''
  if (simulate_timer) {
    clearInterval(simulate_timer)
    simulate_timer = null
  }
}

onMounted(async () => {
  await ble_store.initialize()
  if (ble_store.device_id && !ble_store.is_connected) {
    ble_store.connect(ble_store.device_id)
  }
})

onBeforeUnmount(() => {
  stop_simulation()
})
</script>

<template>
  <section class="page">
    <div class="card">
      <div class="row">
        <div class="label">状态</div>
        <div class="value">{{ ble_store.status }}</div>
      </div>
      <div v-if="ble_store.error_msg" class="error">{{ ble_store.error_msg }}</div>

      <div class="row">
        <div class="label">设备</div>
        <div class="value">
          <div>{{ ble_store.device_name || '未选择' }}</div>
          <div class="muted">{{ ble_store.device_id || '' }}</div>
        </div>
      </div>

      <div class="actions">
        <button class="btn primary" :disabled="ble_store.is_connecting" @click="ble_store.pick_and_connect">
          选择设备并连接
        </button>
        <button class="btn" :disabled="!can_reconnect || ble_store.is_connecting" @click="ble_store.connect(ble_store.device_id)">
          重连
        </button>
        <button class="btn" :disabled="!ble_store.is_connected" @click="ble_store.disconnect">断开</button>
        <button class="btn danger" :disabled="ble_store.is_connecting" @click="ble_store.forget_device">忘记设备</button>
      </div>

      <div class="actions">
        <button class="btn primary" :disabled="is_simulating" @click="start_simulation">开始模拟上报</button>
        <button class="btn" :disabled="!is_simulating" @click="stop_simulation">停止模拟上报</button>
      </div>

      <div class="muted">
        模拟器常见情况无法验证真实蓝牙连接，可用模拟上报验证后端链路是否通畅
      </div>

      <div v-if="simulate_error" class="error">{{ simulate_error }}</div>
    </div>

    <div class="card">
      <div class="row">
        <div class="label">最近数据</div>
        <div class="value monospace">{{ ble_store.last_packet ? JSON.stringify(ble_store.last_packet) : '暂无' }}</div>
      </div>
    </div>
  </section>
</template>
