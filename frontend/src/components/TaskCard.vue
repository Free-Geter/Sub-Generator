<template>
  <el-card class="task-card" shadow="hover">
    <div class="task-header">
      <el-checkbox
        v-if="selectable"
        :model-value="selected"
        class="task-checkbox"
        @click.stop
        @change="$emit('toggleSelect', task.id)"
      />
      <span class="task-name">{{ task.video_name || task.filename || '未知视频' }}</span>
      <el-tag :type="statusType" size="small">{{ statusText }}</el-tag>
    </div>
    <div class="task-info">
      <span v-if="task.target_lang">目标语言：{{ langLabel(task.target_lang) }}</span>
      <span v-if="task.translation_engine">引擎：{{ task.translation_engine }}</span>
      <span v-if="task.whisper_model">模型：{{ task.whisper_model }}</span>
    </div>
    <div class="task-time">
      创建时间：{{ formatTime(task.created_at) }}
    </div>

    <!-- 展开的进度面板 -->
    <el-collapse-transition>
      <div v-if="expanded" class="progress-panel" @click.stop>
        <el-divider />
        <ProgressBar :currentStep="currentStep" :progress="liveTask.progress || task.progress || 0" />
        <div class="progress-detail">
          <p>当前步骤：<strong>{{ currentStepName }}</strong></p>
          <p>总进度：<strong>{{ Math.round(liveTask.progress || task.progress || 0) }}%</strong></p>
          <p v-if="elapsed" class="step-message">已耗时：{{ elapsed }}</p>
          <p v-if="statusMsg" class="step-message">{{ statusMsg }}</p>
        </div>

        <!-- 失败原因 -->
        <div v-if="(liveTask.status || task.status) === 'failed' && (liveTask.error_message || task.error_message)" class="task-error">
          <span class="error-label">失败原因：</span>{{ liveTask.error_message || task.error_message }}
        </div>

        <div class="progress-actions">
          <el-button
            v-if="(liveTask.status || task.status) === 'done'"
            type="primary"
            size="small"
            @click="$emit('download', task)"
          >下载SRT</el-button>
          <el-button
            v-if="(liveTask.status || task.status) === 'done'"
            type="success"
            size="small"
            @click="$emit('retranslate', task)"
          >重新翻译</el-button>
          <el-button
            v-if="isActive"
            type="danger"
            size="small"
            @click="$emit('cancel', task)"
          >取消</el-button>
        </div>
      </div>
    </el-collapse-transition>

    <div class="task-actions">
      <el-button
        v-if="canRerun"
        type="warning"
        size="small"
        plain
        @click="$emit('rerun', task)"
      >重新执行</el-button>
      <el-button
        :type="expanded ? 'warning' : 'info'"
        size="small"
        plain
        @click="toggleExpand"
      >{{ expanded ? '收起进度' : '查看进度' }}</el-button>
      <el-button
        v-if="(liveTask.status || task.status) === 'done'"
        type="primary"
        size="small"
        @click="$emit('download', task)"
      >下载SRT</el-button>
      <el-button
        type="danger"
        size="small"
        plain
        @click="$emit('delete', task)"
      >删除</el-button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, watch, onUnmounted } from 'vue'
import ProgressBar from '@/components/ProgressBar.vue'
import api from '@/api'

const props = defineProps({
  task: { type: Object, required: true },
  selectable: { type: Boolean, default: false },
  selected: { type: Boolean, default: false }
})

defineEmits(['download', 'retranslate', 'cancel', 'delete', 'rerun', 'toggleSelect'])

const expanded = ref(false)
const liveTask = reactive({ status: '', progress: 0, error_message: '', created_at: null })
const now = ref(Date.now())

let pollTimer = null
let clockTimer = null

const STEP_MAP = { extracting: 0, recognizing: 1, translating: 2, generating: 3, done: 4, failed: -1 }
const stepNames = ['音频提取', '语音识别', '翻译', 'SRT生成']
const FINAL_STATUSES = ['done', 'failed', 'cancelled']

const LANG_LABELS = {
  zh: '中文', en: '英文', ja: '日文', ko: '韩文',
  fr: '法文', de: '德文', es: '西班牙文'
}

const isActive = computed(() => {
  const s = liveTask.status || props.task.status
  return ['pending', 'extracting', 'recognizing', 'translating', 'generating'].includes(s)
})

const canRerun = computed(() => {
  const s = liveTask.status || props.task.status
  return ['done', 'failed', 'cancelled'].includes(s)
})

const currentStatus = computed(() => liveTask.status || props.task.status)

const statusType = computed(() => {
  const map = { pending: 'info', extracting: 'warning', recognizing: 'warning', translating: 'warning', generating: 'warning', done: 'success', failed: 'danger', cancelled: 'info' }
  return map[currentStatus.value] || 'info'
})

const statusText = computed(() => {
  const map = { pending: '等待中', extracting: '提取音频', recognizing: '语音识别', translating: '翻译中', generating: '生成字幕', done: '已完成', failed: '失败', cancelled: '已取消' }
  return map[currentStatus.value] || currentStatus.value
})

const currentStep = computed(() => {
  const idx = STEP_MAP[currentStatus.value]
  return idx !== undefined && idx >= 0 ? idx : 0
})

const currentStepName = computed(() => {
  if (currentStatus.value === 'done') return '全部完成'
  if (currentStatus.value === 'failed') return '任务失败'
  if (currentStatus.value === 'cancelled') return '已取消'
  const idx = STEP_MAP[currentStatus.value]
  if (idx !== undefined && idx >= 0 && idx < stepNames.length) return stepNames[idx]
  return '准备中'
})

const statusMsg = computed(() => {
  if (FINAL_STATUSES.includes(currentStatus.value)) return ''
  const range = {
    extracting: { min: 5, max: 30 }, recognizing: { min: 30, max: 60 },
    translating: { min: 62, max: 90 }, generating: { min: 92, max: 100 }
  }[currentStatus.value]
  if (!range) return ''
  const prog = liveTask.progress || props.task.progress || 0
  const rawPct = Math.round((prog - range.min) / (range.max - range.min) * 100)
  const pct = Math.max(0, Math.min(100, rawPct))  // 边界保护：0~100
  const desc = {
    extracting: `正在提取音频... ${pct}%`, recognizing: `正在语音识别... ${pct}%`,
    translating: `正在翻译字幕... ${pct}%`, generating: `正在生成 SRT 文件... ${pct}%`
  }
  return desc[currentStatus.value] || ''
})

const elapsed = computed(() => {
  const raw = liveTask.created_at || props.task.created_at
  if (!raw) return ''
  // 处理后端返回的无时区 UTC 时间：补 Z 让 JS 正确解析为 UTC
  const timeStr = typeof raw === 'string' && !raw.endsWith('Z') && !raw.includes('+') && !raw.includes('-', 10) ? raw + 'Z' : raw
  const createdAt = new Date(timeStr)
  if (isNaN(createdAt.getTime())) return ''
  const seconds = Math.floor((now.value - createdAt.getTime()) / 1000)
  if (seconds < 0) return ''
  if (seconds < 60) return `${seconds} 秒`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins < 60) return `${mins} 分 ${secs} 秒`
  const hrs = Math.floor(mins / 60)
  return `${hrs} 时 ${mins % 60} 分 ${secs} 秒`
})

function langLabel(code) { return LANG_LABELS[code] || code }

function formatTime(time) {
  if (!time) return '-'
  const dt = typeof time === 'string' && !time.endsWith('Z') && !time.includes('+') ? time + 'Z' : time
  return new Date(dt).toLocaleString('zh-CN')
}

async function fetchTaskStatus() {
  try {
    const res = await api.getTask(props.task.id)
    const t = res.data
    if (t.status) liveTask.status = t.status
    if (t.progress !== undefined) liveTask.progress = t.progress
    if (t.error_message) liveTask.error_message = t.error_message
    if (t.created_at) liveTask.created_at = t.created_at
    if (FINAL_STATUSES.includes(t.status)) stopPolling()
  } catch (e) { /* ignore */ }
}

function startPolling() {
  stopPolling()
  // 先同步初始状态
  liveTask.status = props.task.status
  liveTask.progress = props.task.progress || 0
  liveTask.error_message = props.task.error_message || ''
  liveTask.created_at = props.task.created_at
  if (!FINAL_STATUSES.includes(liveTask.status)) {
    fetchTaskStatus()
    pollTimer = setInterval(fetchTaskStatus, 2000)
    clockTimer = setInterval(() => { now.value = Date.now() }, 1000)
  }
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (clockTimer) { clearInterval(clockTimer); clockTimer = null }
}

function toggleExpand() {
  expanded.value = !expanded.value
  if (expanded.value) {
    startPolling()
  } else {
    stopPolling()
  }
}

watch(() => props.task.status, (newVal) => {
  if (expanded.value) {
    liveTask.status = newVal
    if (FINAL_STATUSES.includes(newVal)) stopPolling()
  }
})

onUnmounted(() => stopPolling())
</script>

<style scoped>
.task-card {
  margin-bottom: 12px;
  user-select: none;
  transition: transform 0.15s;
}
.task-card:hover {
  transform: translateY(-1px);
}
.task-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}
.task-checkbox {
  margin-right: 10px;
  flex-shrink: 0;
}
.task-name {
  font-weight: 600;
  font-size: 15px;
  flex: 1;
}
.task-info {
  color: #909399;
  font-size: 13px;
  margin-bottom: 4px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.task-time {
  color: #909399;
  font-size: 12px;
  margin-bottom: 8px;
}
.progress-panel {
  margin-top: 4px;
}
.progress-detail {
  padding: 8px 0;
  color: #606266;
}
.progress-detail p {
  margin: 6px 0;
  font-size: 14px;
}
.step-message {
  color: #909399;
  font-size: 13px;
}
.task-error {
  margin-bottom: 8px;
  padding: 8px 12px;
  background: #fef0f0;
  border-left: 3px solid #f56c6c;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 13px;
  line-height: 1.5;
}
.error-label {
  font-weight: 600;
}
.progress-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding-bottom: 8px;
}
.task-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
