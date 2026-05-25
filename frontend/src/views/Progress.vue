<template>
  <div class="progress-page">
    <el-card class="progress-card">
      <template #header>
        <div class="progress-header">
          <span class="title">任务进度</span>
          <el-tag :type="statusType" v-if="status">{{ statusText }}</el-tag>
        </div>
      </template>

      <!-- 加载骨架 -->
      <template v-if="loading">
        <el-skeleton :rows="4" animated />
      </template>

      <template v-else>
        <ProgressBar :currentStep="currentStep" :progress="totalProgress" />

        <div class="progress-detail">
          <p>当前步骤：<strong>{{ currentStepName }}</strong></p>
          <p>总进度：<strong>{{ Math.round(totalProgress) }}%</strong></p>
          <p v-if="elapsedTime" class="step-message">已耗时：{{ elapsedTime }}</p>
          <p v-if="statusMessage" class="step-message">{{ statusMessage }}</p>
        </div>

        <div class="progress-actions" v-if="status === 'done'">
          <el-button type="primary" @click="handleDownload">下载 SRT</el-button>
          <el-button type="success" @click="showPreview = true">查看预览</el-button>
        </div>

        <div class="progress-actions" v-if="status === 'failed'">
          <el-alert type="error" :title="errorMsg || '任务执行失败'" show-icon :closable="false" />
        </div>

        <div class="progress-actions" v-if="isFinished">
          <el-button @click="$router.push('/')">返回首页</el-button>
        </div>
      </template>
    </el-card>

    <SubtitlePreview v-model="showPreview" :taskId="taskId" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ProgressBar from '@/components/ProgressBar.vue'
import SubtitlePreview from '@/components/SubtitlePreview.vue'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const taskId = computed(() => route.params.id)

const currentStep = ref(0)
const totalProgress = ref(0)
const status = ref('')
const errorMsg = ref('')
const showPreview = ref(false)
const loading = ref(true)
const createdAt = ref(null)
const now = ref(Date.now())

let pollTimer = null
let clockTimer = null

// 后端 status → 数字索引映射
const STEP_MAP = { extracting: 0, recognizing: 1, translating: 2, generating: 3, done: 4, failed: -1 }
const stepNames = ['音频提取', '语音识别', '翻译', 'SRT生成']
const FINAL_STATUSES = ['done', 'failed', 'cancelled']

// 各阶段的进度范围（用于推导状态描述）
const PHASE_RANGE = {
  extracting:   { min: 5,  max: 30  },
  recognizing:  { min: 30, max: 60  },
  translating:  { min: 62, max: 90  },
  generating:   { min: 92, max: 100 },
}

const isFinished = computed(() => FINAL_STATUSES.includes(status.value))

const currentStepName = computed(() => {
  if (status.value === 'done') return '全部完成'
  if (status.value === 'failed') return '任务失败'
  if (status.value === 'cancelled') return '已取消'
  const idx = STEP_MAP[status.value]
  if (idx !== undefined && idx >= 0 && idx < stepNames.length) return stepNames[idx]
  return '准备中'
})

const statusType = computed(() => {
  const map = {
    pending: 'info', extracting: 'warning', recognizing: 'warning',
    translating: 'warning', generating: 'warning',
    done: 'success', failed: 'danger', cancelled: 'info'
  }
  return map[status.value] || 'info'
})

const statusText = computed(() => {
  const map = {
    pending: '等待中', extracting: '提取音频', recognizing: '语音识别',
    translating: '翻译中', generating: '生成字幕',
    done: '已完成', failed: '失败', cancelled: '已取消'
  }
  return map[status.value] || status.value
})

// 从进度推导友好描述（后端不在 DB 存 message，WS 不再使用）
const statusMessage = computed(() => {
  if (isFinished.value) return ''
  const range = PHASE_RANGE[status.value]
  if (!range) return ''
  const pct = Math.round((totalProgress.value - range.min) / (range.max - range.min) * 100)
  const clamped = Math.max(0, Math.min(100, pct))  // 边界保护：0~100
  const phaseDesc = {
    extracting:  `正在提取音频... ${clamped}%`,
    recognizing: `正在语音识别... ${clamped}%`,
    translating: `正在翻译字幕... ${clamped}%`,
    generating:  `正在生成 SRT 文件... ${clamped}%`,
  }
  return phaseDesc[status.value] || ''
})

const elapsedTime = computed(() => {
  if (!createdAt.value) return ''
  const seconds = Math.floor((now.value - createdAt.value) / 1000)
  if (seconds < 60) return `${seconds} 秒`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins} 分 ${secs} 秒`
})

// ── 轮询：每 2 秒拉取任务状态 ──
async function fetchTaskStatus() {
  try {
    const res = await api.getTask(taskId.value)
    const task = res.data

    // 更新状态
    if (task.status) {
      status.value = task.status
      const stepIdx = STEP_MAP[task.status]
      if (stepIdx !== undefined && stepIdx >= 0) currentStep.value = stepIdx
    }
    if (task.progress !== undefined) totalProgress.value = task.progress
    if (task.error_message) errorMsg.value = task.error_message
    if (task.created_at) {
      let dt = task.created_at
      // 后端 utcnow() 无时区标记，补 Z 防止被当成当地时间
      if (typeof dt === 'string' && !dt.endsWith('Z') && !dt.includes('+')) {
        dt += 'Z'
      }
      createdAt.value = new Date(dt).getTime()
    }

    loading.value = false

    // 终态则停止轮询
    if (FINAL_STATUSES.includes(task.status)) {
      stopPolling()
    }
  } catch (e) {
    if (!loading.value) {
      // 首次加载失败才报错
    }
  }
}

function startPolling() {
  fetchTaskStatus()  // 立即执行一次
  pollTimer = setInterval(fetchTaskStatus, 2000)
  clockTimer = setInterval(() => { now.value = Date.now() }, 1000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (clockTimer) { clearInterval(clockTimer); clockTimer = null }
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

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
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
  user-select: none;
  cursor: default;
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
