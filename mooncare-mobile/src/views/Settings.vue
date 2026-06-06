<template>
  <section class="settings-page">
    <div class="settings-shell">
      <div class="page-head">
        <h1>设置</h1>
        <p>管理账户、安全验证、通知提醒、本地缓存与版本信息。</p>
      </div>

      <div v-if="pageMessage" class="page-message" :class="pageError ? 'is-error' : 'is-success'">
        {{ pageMessage }}
      </div>

      <div class="settings-group">
        <h2>账户信息</h2>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>昵称</strong>
            <span>{{ authStore.user?.nickname || '未设置' }}</span>
          </div>
          <button type="button" class="row-button" @click="openPanel('nickname')">修改</button>
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>邮箱</strong>
            <span>{{ authStore.user?.email || '未绑定' }}</span>
          </div>
          <button type="button" class="row-button" @click="openPanel('email')">换绑</button>
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>密码</strong>
            <span>已设置</span>
          </div>
          <button type="button" class="row-button" @click="openPanel('password')">修改</button>
        </div>
      </div>

      <div class="settings-group">
        <h2>通知与设备</h2>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>通知提醒</strong>
            <span>{{ notificationsEnabled ? '已开启' : '已关闭' }}</span>
          </div>
          <button type="button" class="row-button" @click="openPanel('notifications')">调整</button>
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>蓝牙设备</strong>
            <span>{{ bleStatusText }}</span>
          </div>
          <router-link to="/ble" class="row-button as-link">查看</router-link>
        </div>
      </div>

      <div class="settings-group">
        <h2>数据与隐私</h2>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>本地缓存</strong>
            <span>聊天记录缓存与音乐偏好</span>
          </div>
          <button type="button" class="row-button" @click="clearLocalCache">清理</button>
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>隐私与数据说明</strong>
            <span>查看本地缓存、账号数据与注销说明</span>
          </div>
          <button type="button" class="row-button" @click="openPanel('privacy')">查看</button>
        </div>
      </div>

      <div class="settings-group">
        <h2>关于</h2>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>版本信息</strong>
            <span>{{ appVersion }} · {{ buildMarker }}</span>
          </div>
          <button type="button" class="row-button" @click="openPanel('about')">查看</button>
        </div>
      </div>

      <div class="settings-group">
        <h2>账号操作</h2>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>退出登录</strong>
            <span>退出当前设备上的登录状态</span>
          </div>
          <button type="button" class="row-button" @click="logout">退出</button>
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <strong>账号注销</strong>
            <span>永久删除当前账号及其数据</span>
          </div>
          <button type="button" class="row-button danger" @click="openPanel('delete')">注销</button>
        </div>
      </div>
    </div>

    <div v-if="activePanel" class="overlay" @click.self="closePanel">
      <div class="panel-card">
        <div class="panel-head">
          <div>
            <h3>{{ panelTitle }}</h3>
            <p>{{ panelDescription }}</p>
          </div>
          <button type="button" class="close-button" @click="closePanel">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div v-if="panelMessage" class="panel-message" :class="panelError ? 'is-error' : 'is-success'">
          {{ panelMessage }}
        </div>

        <div v-if="activePanel === 'nickname'" class="panel-body">
          <label class="field-label" for="nickname-input">昵称</label>
          <input id="nickname-input" v-model.trim="nickname" type="text" maxlength="100" class="field-input" />
          <button type="button" class="primary-button" :disabled="savingNickname" @click="saveNickname">
            {{ savingNickname ? '保存中...' : '保存昵称' }}
          </button>
        </div>

        <div v-else-if="activePanel === 'email'" class="panel-body">
          <div class="field-block">
            <label class="field-label" for="new-email-input">新邮箱</label>
            <input id="new-email-input" v-model.trim="newEmail" type="email" autocomplete="email" class="field-input" />
          </div>

          <div class="field-block">
            <label class="field-label" for="current-password-input">当前密码</label>
            <input id="current-password-input" v-model="currentPasswordForEmail" type="password" autocomplete="current-password" class="field-input" />
          </div>

          <div class="inline-action">
            <div class="inline-copy">
              <strong>发送验证码到新邮箱</strong>
              <span>确认当前密码后，验证码会发送到新的邮箱地址。</span>
            </div>
            <button type="button" class="row-button" :disabled="sendingEmailCode" @click="sendEmailChangeCode">
              {{ sendingEmailCode ? '发送中' : '发送验证码' }}
            </button>
          </div>

          <div class="field-block">
            <label class="field-label" for="email-code-input">验证码</label>
            <input id="email-code-input" v-model.trim="emailChangeCode" type="text" inputmode="numeric" maxlength="6" class="field-input" />
          </div>

          <button type="button" class="primary-button" :disabled="confirmingEmailChange" @click="confirmEmailChange">
            {{ confirmingEmailChange ? '确认中...' : '确认换绑邮箱' }}
          </button>
        </div>

        <div v-else-if="activePanel === 'password'" class="panel-body">
          <div class="inline-action">
            <div class="inline-copy">
              <strong>发送验证码</strong>
              <span>验证码会发送到当前绑定邮箱：{{ authStore.user?.email || '未绑定邮箱' }}</span>
            </div>
            <button type="button" class="row-button" :disabled="sendingPasswordCode" @click="sendPasswordResetCode">
              {{ sendingPasswordCode ? '发送中' : '发送验证码' }}
            </button>
          </div>

          <div class="field-block">
            <label class="field-label" for="password-code-input">验证码</label>
            <input id="password-code-input" v-model.trim="passwordResetCode" type="text" inputmode="numeric" maxlength="6" class="field-input" />
          </div>

          <div class="field-block">
            <label class="field-label" for="new-password-input">新密码</label>
            <input id="new-password-input" v-model="newPassword" type="password" autocomplete="new-password" class="field-input" />
          </div>

          <div class="field-block">
            <label class="field-label" for="confirm-password-input">确认新密码</label>
            <input id="confirm-password-input" v-model="confirmNewPassword" type="password" autocomplete="new-password" class="field-input" />
          </div>

          <button type="button" class="primary-button" :disabled="resettingPassword" @click="resetPassword">
            {{ resettingPassword ? '提交中...' : '确认修改密码' }}
          </button>
        </div>

        <div v-else-if="activePanel === 'notifications'" class="panel-body">
          <label class="switch-card">
            <div>
              <strong>通知提醒</strong>
              <p>控制周期提醒和陪伴通知的发送状态。</p>
            </div>
            <input v-model="notificationsEnabled" type="checkbox" class="toggle" />
          </label>

          <button type="button" class="primary-button" :disabled="savingNotifications" @click="saveNotifications">
            {{ savingNotifications ? '保存中...' : '保存通知设置' }}
          </button>
        </div>

        <div v-else-if="activePanel === 'about'" class="panel-body">
          <div class="info-card">
            <div class="info-row">
              <span>应用版本</span>
              <strong>{{ appVersion }}</strong>
            </div>
            <div class="info-row">
              <span>构建标记</span>
              <strong>{{ buildMarker }}</strong>
            </div>
            <div class="info-row">
              <span>当前账号</span>
              <strong>{{ authStore.user?.email || '未登录' }}</strong>
            </div>
          </div>
        </div>

        <div v-else-if="activePanel === 'privacy'" class="panel-body">
          <div class="info-card multiline">
            <p>1. 聊天缓存和音乐喜欢列表只保存在当前账号对应的本地设备空间中。</p>
            <p>2. 清理本地缓存不会删除服务器上的日记、周期和账号数据。</p>
            <p>3. 账号注销会永久删除当前账号及其关联数据，请谨慎操作。</p>
            <p>4. 情绪和健康相关内容仅供参考，不替代专业医生或心理咨询建议。</p>
          </div>
        </div>

        <div v-else-if="activePanel === 'delete'" class="panel-body">
          <div class="field-block">
            <label class="field-label" for="delete-password-input">当前密码</label>
            <input id="delete-password-input" v-model="deletePassword" type="password" autocomplete="current-password" class="field-input" />
          </div>

          <div class="field-block">
            <label class="field-label" for="delete-confirm-input">请输入“注销”确认</label>
            <input id="delete-confirm-input" v-model.trim="deleteConfirmText" type="text" class="field-input" />
          </div>

          <button type="button" class="danger-button" :disabled="deletingAccount" @click="deleteAccount">
            {{ deletingAccount ? '处理中...' : '永久注销账号' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { MOBILE_BUILD_MARKER } from '../services/apiConfig'
import { clearUserScopedKeys } from '../services/userScopedStorage'
import { useAuthStore } from '../stores/auth'
import { useBleStore } from '../stores/ble'

const router = useRouter()
const authStore = useAuthStore()
const bleStore = useBleStore()

const appVersion = '1.0.1-account-settings'
const buildMarker = MOBILE_BUILD_MARKER

const activePanel = ref('')
const pageMessage = ref('')
const pageError = ref(false)
const panelMessage = ref('')
const panelError = ref(false)

const nickname = ref('')
const savingNickname = ref(false)

const notificationsEnabled = ref(true)
const savingNotifications = ref(false)

const newEmail = ref('')
const currentPasswordForEmail = ref('')
const emailChangeCode = ref('')
const sendingEmailCode = ref(false)
const confirmingEmailChange = ref(false)

const sendingPasswordCode = ref(false)
const passwordResetCode = ref('')
const newPassword = ref('')
const confirmNewPassword = ref('')
const resettingPassword = ref(false)

const deletePassword = ref('')
const deleteConfirmText = ref('')
const deletingAccount = ref(false)

const bleStatusText = computed(() => {
  if (bleStore.isConnected) return '已连接'
  if (bleStore.isConnecting) return '连接中'
  return '未连接'
})

const panelTitle = computed(() => {
  return {
    nickname: '修改昵称',
    email: '换绑邮箱',
    password: '修改密码',
    notifications: '通知提醒',
    about: '版本信息',
    privacy: '隐私与数据说明',
    delete: '账号注销',
  }[activePanel.value] || ''
})

const panelDescription = computed(() => {
  return {
    nickname: '修改你的公开昵称，保存后会同步到当前账号。',
    email: '使用当前密码和新邮箱验证码完成换绑。',
    password: '通过当前绑定邮箱收到的验证码完成密码修改。',
    notifications: '调整周期提醒和陪伴通知的开启状态。',
    about: '查看当前安装包版本和构建信息。',
    privacy: '了解缓存、账号数据和注销影响范围。',
    delete: '注销后将永久删除当前账号及关联数据。',
  }[activePanel.value] || ''
})

function setPageMessage(message, isError = false) {
  pageMessage.value = message
  pageError.value = isError
}

function setPanelMessage(message, isError = false) {
  panelMessage.value = message
  panelError.value = isError
}

function resetPageMessage() {
  pageMessage.value = ''
  pageError.value = false
}

function resetPanelMessage() {
  panelMessage.value = ''
  panelError.value = false
}

function resetPanelFields() {
  nickname.value = authStore.user?.nickname || ''
  newEmail.value = ''
  currentPasswordForEmail.value = ''
  emailChangeCode.value = ''
  passwordResetCode.value = ''
  newPassword.value = ''
  confirmNewPassword.value = ''
  deletePassword.value = ''
  deleteConfirmText.value = ''
}

function openPanel(panel) {
  resetPanelMessage()
  resetPanelFields()
  activePanel.value = panel
}

function closePanel() {
  activePanel.value = ''
  resetPanelMessage()
}

async function syncProfileFromServer() {
  if (!authStore.isAuthenticated) return
  const profile = await authStore.fetchProfile()
  nickname.value = profile?.nickname || ''
  notificationsEnabled.value = profile?.notifications_enabled ?? true
}

async function saveNickname() {
  if (savingNickname.value) return
  savingNickname.value = true
  resetPanelMessage()
  try {
    await authStore.updateProfile({ nickname: nickname.value || null })
    setPanelMessage('昵称已保存。')
    setPageMessage('昵称已更新。')
  } catch (error) {
    setPanelMessage(error.response?.data?.detail || '昵称保存失败，请稍后重试。', true)
  } finally {
    savingNickname.value = false
  }
}

async function sendEmailChangeCode() {
  if (sendingEmailCode.value) return
  sendingEmailCode.value = true
  resetPanelMessage()
  try {
    const response = await authStore.requestEmailChange(newEmail.value, currentPasswordForEmail.value)
    setPanelMessage(response.__message || '验证码已发送到新邮箱。')
  } catch (error) {
    setPanelMessage(error.response?.data?.detail || error.userMessage || '验证码发送失败。', true)
  } finally {
    sendingEmailCode.value = false
  }
}

async function confirmEmailChange() {
  if (confirmingEmailChange.value) return
  confirmingEmailChange.value = true
  resetPanelMessage()
  try {
    await authStore.confirmEmailChange(newEmail.value, emailChangeCode.value)
    await syncProfileFromServer()
    setPageMessage('邮箱已换绑成功。')
    setPanelMessage('新邮箱已生效。')
    closePanel()
  } catch (error) {
    setPanelMessage(error.response?.data?.detail || error.userMessage || '邮箱换绑失败。', true)
  } finally {
    confirmingEmailChange.value = false
  }
}

async function sendPasswordResetCode() {
  if (sendingPasswordCode.value) return
  sendingPasswordCode.value = true
  resetPanelMessage()
  try {
    const response = await authStore.forgotPassword(authStore.user?.email || '')
    setPanelMessage(response.__message || '验证码已发送到当前绑定邮箱。')
  } catch (error) {
    setPanelMessage(error.response?.data?.detail || error.userMessage || '验证码发送失败。', true)
  } finally {
    sendingPasswordCode.value = false
  }
}

async function resetPassword() {
  if (resettingPassword.value) return
  if (newPassword.value !== confirmNewPassword.value) {
    setPanelMessage('两次输入的新密码不一致。', true)
    return
  }

  resettingPassword.value = true
  resetPanelMessage()
  try {
    const response = await authStore.resetPassword(authStore.user?.email || '', passwordResetCode.value, newPassword.value)
    setPanelMessage(response.__message || '密码已修改，请重新登录。')
    setPageMessage('密码已修改，请重新登录。')
    authStore.logout()
    router.push('/login')
  } catch (error) {
    setPanelMessage(error.response?.data?.detail || error.userMessage || '密码修改失败。', true)
  } finally {
    resettingPassword.value = false
  }
}

async function saveNotifications() {
  if (savingNotifications.value) return
  savingNotifications.value = true
  resetPanelMessage()
  try {
    await authStore.updateProfile({ notifications_enabled: notificationsEnabled.value })
    setPanelMessage('通知设置已保存。')
    setPageMessage('通知设置已更新。')
  } catch (error) {
    setPanelMessage(error.response?.data?.detail || '通知设置保存失败。', true)
  } finally {
    savingNotifications.value = false
  }
}

function clearLocalCache() {
  clearUserScopedKeys(['mooncare_chat_session', 'mooncare_liked_music'])
  setPageMessage('当前账号的本地缓存已清理。')
}

function logout() {
  authStore.logout()
  router.push('/login')
}

async function deleteAccount() {
  if (deletingAccount.value) return
  deletingAccount.value = true
  resetPanelMessage()
  try {
    const response = await authStore.deleteAccount(deletePassword.value, deleteConfirmText.value)
    authStore.logout()
    setPageMessage(response.__message || '账号已注销。')
    router.push('/login')
  } catch (error) {
    setPanelMessage(error.response?.data?.detail || '账号注销失败。', true)
  } finally {
    deletingAccount.value = false
  }
}

onMounted(async () => {
  resetPageMessage()
  resetPanelMessage()
  nickname.value = authStore.user?.nickname || ''
  notificationsEnabled.value = authStore.user?.notifications_enabled ?? true
  await syncProfileFromServer()
})
</script>

<style scoped>
.settings-page {
  min-height: calc(100vh - 56px);
  background: linear-gradient(180deg, #fff7fb 0%, #f8fafc 100%);
}

.settings-shell {
  width: min(100%, 448px);
  margin: 0 auto;
  padding: 20px 16px calc(88px + env(safe-area-inset-bottom, 0));
}

.page-head h1 {
  margin: 0;
  color: #1f2937;
  font-size: 28px;
  font-weight: 800;
}

.page-head p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.page-message,
.panel-message {
  margin-top: 14px;
  border-radius: 16px;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.5;
}

.page-message.is-success,
.panel-message.is-success {
  background: #ecfdf5;
  color: #166534;
}

.page-message.is-error,
.panel-message.is-error {
  background: #fff1f2;
  color: #be123c;
}

.settings-group {
  margin-top: 16px;
  border: 1px solid #fbcfe8;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  padding: 14px;
  box-shadow: 0 16px 32px rgba(244, 114, 182, 0.08);
}

.settings-group h2 {
  margin: 0 0 8px;
  color: #1f2937;
  font-size: 15px;
  font-weight: 800;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
}

.setting-row + .setting-row {
  border-top: 1px solid #f1f5f9;
}

.setting-copy {
  min-width: 0;
}

.setting-copy strong {
  display: block;
  color: #1f2937;
  font-size: 14px;
  font-weight: 700;
}

.setting-copy span {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.row-button {
  min-width: 64px;
  height: 34px;
  flex: 0 0 auto;
  border: 1px solid #fbcfe8;
  border-radius: 999px;
  background: #fff6f8;
  color: #db2777;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 700;
}

.row-button.danger {
  border-color: #fecaca;
  background: #fff1f2;
  color: #dc2626;
}

.as-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
}

.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.32);
  padding: 16px;
}

.panel-card {
  width: min(100%, 388px);
  max-height: 78vh;
  overflow-y: auto;
  border-radius: 24px;
  background: #ffffff;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.16);
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 16px 12px;
  border-bottom: 1px solid #f1f5f9;
}

.panel-head h3 {
  margin: 0;
  color: #1f2937;
  font-size: 18px;
  font-weight: 800;
}

.panel-head p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.close-button {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: #f8fafc;
  color: #64748b;
}

.close-button svg {
  width: 18px;
  height: 18px;
}

.panel-body {
  padding: 14px 16px 16px;
}

.field-block + .field-block,
.inline-action + .field-block,
.field-block + .inline-action {
  margin-top: 12px;
}

.field-label {
  display: block;
  margin-bottom: 6px;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.field-input {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 14px;
  outline: none;
}

.field-input:focus {
  border-color: #f472b6;
  box-shadow: 0 0 0 3px rgba(244, 114, 182, 0.12);
}

.inline-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #f1f5f9;
  border-radius: 18px;
  background: #f8fafc;
  padding: 12px;
}

.inline-copy strong {
  display: block;
  color: #1f2937;
  font-size: 14px;
}

.inline-copy span {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.switch-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #f1f5f9;
  border-radius: 18px;
  background: #f8fafc;
  padding: 14px 12px;
}

.switch-card strong {
  display: block;
  color: #1f2937;
  font-size: 14px;
}

.switch-card p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.toggle {
  width: 18px;
  height: 18px;
  accent-color: #ec4899;
  flex: 0 0 auto;
}

.primary-button,
.danger-button {
  width: 100%;
  min-height: 44px;
  border: 0;
  border-radius: 999px;
  margin-top: 14px;
  font-size: 14px;
  font-weight: 700;
}

.primary-button {
  background: linear-gradient(135deg, #f472b6, #ec4899);
  color: #ffffff;
}

.danger-button {
  background: #ef4444;
  color: #ffffff;
}

.info-card {
  border: 1px solid #f1f5f9;
  border-radius: 18px;
  background: #f8fafc;
  padding: 12px;
}

.info-card.multiline p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.info-card.multiline p + p {
  margin-top: 10px;
}

.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
}

.info-row + .info-row {
  border-top: 1px solid #e2e8f0;
}

.info-row span {
  color: #475569;
  font-size: 13px;
}

.info-row strong {
  color: #1f2937;
  font-size: 13px;
}
</style>
