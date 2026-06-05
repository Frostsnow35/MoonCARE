<script setup>
import { ref, onMounted } from 'vue'
import { get_kv, set_kv } from '../services/kv'

const api_base_url = ref('')
const saved_msg = ref('')

onMounted(async () => {
  api_base_url.value = (await get_kv('api_base_url')) || ''
})

async function save() {
  saved_msg.value = ''
  await set_kv('api_base_url', api_base_url.value.trim())
  saved_msg.value = '已保存'
  setTimeout(() => {
    saved_msg.value = ''
  }, 1200)
}
</script>

<template>
  <section class="page">
    <div class="card">
      <div class="row">
        <div class="label">API Base URL</div>
        <input class="input" v-model="api_base_url" placeholder="http://159.75.13.158:8000/api/v1" />
      </div>
      <div class="actions">
        <button class="btn primary" @click="save">保存</button>
        <div class="muted" v-if="saved_msg">{{ saved_msg }}</div>
      </div>
      <div class="muted">
        真机访问服务器后端示例：http://159.75.13.158:8000/api/v1
      </div>
    </div>
  </section>
</template>
