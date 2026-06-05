<script setup>
import { computed, onMounted } from 'vue'
import { useBleStore } from '../stores/ble'

const ble_store = useBleStore()

const can_reconnect = computed(() => Boolean(ble_store.device_id) && !ble_store.is_connected)

onMounted(async () => {
  await ble_store.initialize()
  if (ble_store.device_id && !ble_store.is_connected) {
    ble_store.connect(ble_store.device_id)
  }
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
    </div>

    <div class="card">
      <div class="row">
        <div class="label">最近数据</div>
        <div class="value monospace">{{ ble_store.last_packet ? JSON.stringify(ble_store.last_packet) : '暂无' }}</div>
      </div>
    </div>
  </section>
</template>

