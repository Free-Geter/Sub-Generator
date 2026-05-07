<template>
  <el-dialog
    v-model="visible"
    title="字幕预览"
    width="700px"
    destroy-on-close
    @open="fetchSubtitle"
  >
    <div v-loading="loading" class="subtitle-content">
      <div v-if="subtitleLines.length" class="subtitle-list">
        <div v-for="(item, index) in subtitleLines" :key="index" class="subtitle-item">
          <span class="subtitle-index">{{ item.index }}</span>
          <span class="subtitle-time">{{ item.time }}</span>
          <p class="subtitle-text">{{ item.text }}</p>
        </div>
      </div>
      <el-empty v-else-if="!loading" description="暂无字幕内容" />
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/api'

const props = defineProps({
  taskId: { type: String, default: '' },
  modelValue: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const subtitleLines = ref([])

async function fetchSubtitle() {
  if (!props.taskId) return
  loading.value = true
  subtitleLines.value = []
  try {
    const res = await api.downloadSrt(props.taskId)
    const text = await res.data.text()
    parseSrt(text)
  } catch (e) {
    console.error('Failed to load subtitle:', e)
  } finally {
    loading.value = false
  }
}

function parseSrt(text) {
  const blocks = text.trim().split(/\n\n+/)
  subtitleLines.value = blocks.map(block => {
    const lines = block.split('\n')
    return {
      index: lines[0] || '',
      time: lines[1] || '',
      text: lines.slice(2).join('\n')
    }
  }).filter(item => item.index && item.time)
}
</script>

<style scoped>
.subtitle-content {
  max-height: 500px;
  overflow-y: auto;
}
.subtitle-item {
  padding: 8px 12px;
  border-bottom: 1px solid #ebeef5;
}
.subtitle-item:last-child {
  border-bottom: none;
}
.subtitle-index {
  font-weight: bold;
  color: #409eff;
  margin-right: 12px;
}
.subtitle-time {
  color: #909399;
  font-size: 12px;
  font-family: monospace;
}
.subtitle-text {
  margin: 4px 0 0 0;
  font-size: 14px;
  line-height: 1.6;
}
</style>
