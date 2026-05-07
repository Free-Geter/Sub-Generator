<template>
  <div class="progress-page">
    <el-card class="progress-card">
      <template #header>
        <div class="progress-header">
          <span class="title">任务进度</span>
          <el-tag :type="statusType" v-if="status">{{ statusText }}</el-tag>
        </div>
      </template>

      <ProgressBar :currentStep="currentStep" :progress="totalProgress" />

      <div class="progress-detail">
        <p>当前步骤：<strong>{{ currentStepName }}</strong></p>
        <p>总进度：<strong>{{ totalProgress }}%</strong></p>
        <p v-if="message" class="step-message">{{ message }}</p>
      </div>

      <div class="progress-actions" v-if="status === 'done' || status === 'completed'">
        <el-button type="primary" @click="handleDownload">下载 SRT</el-button>
        <el-button type="success" @click="showPreview = true">查看预览</el-button>
      </div>

      <div class="progress-actions" v-if="status === 'failed'">
        <el-alert type="error" :title="errorMsg || '任务执行失败'" show-icon :closable="false" />
      </div>
    </el-card>

    <SubtitlePreview v-model="showPreview" :taskId="taskId" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ProgressBar from '@/components/ProgressBar.vue'
import SubtitlePreview from '@/components/SubtitlePreview.vue'
import { createWebSocket } from '@/utils/websocket'
import api from '@/api'

const route = useRoute()
const taskId = computed(() => route.params.id)

const currentStep = ref(0)
const totalProgress = ref(0)
const status = ref('')
const message = ref('')
const errorMsg = ref('')
const showPreview = ref(false)

let wsConnection = null

const stepNames = ['音频提取', '语音识别', '翻译', 'SRT生成']

const currentStepName = computed(() => {
  if (status.value === 'done' || status.value === 'completed') return '全部完成'
  return stepNames[currentStep.value] || '准备中'
})

const statusType = computed(() => {
  const map = { pending: 'info', processing: 'warning', done: 'success', completed: 'success', failed: 'danger' }
  return map[status.value] || 'info'
})

const statusText = computed(() => {
  const map = { pending: '等待中', processing: '处理中', done: '已完成', completed: '已完成', failed: '失败' }
  return map[status.value] || status.value
})

function handleWsMessage(data) {
  if (data.step !== undefined) currentStep.value = data.step
  if (data.progress !== undefined) totalProgress.value = data.progress
  if (data.status) status.value = data.status
  if (data.message) message.value = data.message
  if (data.error) errorMsg.value = data.error

  if (data.status === 'done' || data.status === 'completed') {
    totalProgress.value = 100
    currentStep.value = 4
  }
}

function handleWsClose() {
  if (!status.value || status.value === 'processing') {
    ElMessage.warning('WebSocket 连接已断开')
  }
}

async function handleDownload() {
  try {
    const res = await api.downloadSrt(taskId.value)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `subtitle_${taskId.value}.srt`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

onMounted(async () => {
  // Try to fetch existing task status first
  try {
    const res = await api.getTask(taskId.value)
    const task = res.data
    if (task.status) status.value = task.status
    if (task.progress) totalProgress.value = task.progress
    if (task.step !== undefined) currentStep.value = task.step
  } catch (e) {
    // ignore
  }

  // Connect WebSocket
  wsConnection = createWebSocket(taskId.value, handleWsMessage, handleWsClose)
})

onUnmounted(() => {
  if (wsConnection) wsConnection.close()
})
</script>

<style scoped>
.progress-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}
.progress-card {
  margin-bottom: 20px;
}
.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.progress-header .title {
  font-weight: 600;
  font-size: 18px;
}
.progress-detail {
  padding: 16px 0;
  color: #606266;
}
.progress-detail p {
  margin: 8px 0;
}
.step-message {
  color: #909399;
  font-size: 13px;
}
.progress-actions {
  padding-top: 16px;
  display: flex;
  gap: 12px;
}
</style>
