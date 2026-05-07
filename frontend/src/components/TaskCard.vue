<template>
  <el-card class="task-card" shadow="hover">
    <div class="task-header">
      <span class="task-name">{{ task.video_name || task.filename || '未知视频' }}</span>
      <el-tag :type="statusType" size="small">{{ statusText }}</el-tag>
    </div>
    <div class="task-info">
      <span v-if="task.target_language">目标语言：{{ task.target_language }}</span>
      <span v-if="task.engine">引擎：{{ task.engine }}</span>
    </div>
    <div class="task-time">
      创建时间：{{ formatTime(task.created_at) }}
    </div>
    <div v-if="task.progress !== undefined && task.status === 'processing'" class="task-progress">
      <el-progress :percentage="task.progress || 0" :stroke-width="6" />
    </div>
    <div class="task-actions">
      <el-button
        v-if="task.status === 'done' || task.status === 'completed'"
        type="primary"
        size="small"
        @click="$emit('download', task)"
      >下载SRT</el-button>
      <el-button
        v-if="task.status === 'done' || task.status === 'completed'"
        type="success"
        size="small"
        @click="$emit('retranslate', task)"
      >重新翻译</el-button>
      <el-button
        v-if="task.status === 'processing' || task.status === 'pending'"
        type="danger"
        size="small"
        @click="$emit('cancel', task)"
      >取消</el-button>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: { type: Object, required: true }
})

defineEmits(['download', 'retranslate', 'cancel'])

const statusType = computed(() => {
  const map = {
    pending: 'info',
    processing: 'warning',
    done: 'success',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return map[props.task.status] || 'info'
})

const statusText = computed(() => {
  const map = {
    pending: '等待中',
    processing: '处理中',
    done: '已完成',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return map[props.task.status] || props.task.status
})

function formatTime(time) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}
</script>

<style scoped>
.task-card {
  margin-bottom: 12px;
}
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.task-name {
  font-weight: 600;
  font-size: 15px;
}
.task-info {
  color: #909399;
  font-size: 13px;
  margin-bottom: 4px;
  display: flex;
  gap: 16px;
}
.task-time {
  color: #909399;
  font-size: 12px;
  margin-bottom: 8px;
}
.task-progress {
  margin-bottom: 8px;
}
.task-actions {
  display: flex;
  gap: 8px;
}
</style>
