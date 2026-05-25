<template>
  <div class="file-browser">
    <el-table
      :data="videos"
      v-loading="loading"
      highlight-current-row
      @current-change="handleSelect"
      style="width: 100%"
      empty-text="暂无视频文件"
    >
      <el-table-column prop="name" label="文件名" min-width="200">
        <template #default="{ row }">
          <div class="file-name">
            <el-icon><VideoCamera /></el-icon>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="120">
        <template #default="{ row }">
          {{ formatSize(row.size) }}
        </template>
      </el-table-column>
      <el-table-column prop="duration" label="时长" width="100">
        <template #default="{ row }">
          {{ formatDuration(row.duration) }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { VideoCamera } from '@element-plus/icons-vue'
import api from '@/api'

const emit = defineEmits(['select'])

const videos = ref([])
const loading = ref(false)

async function fetchVideos() {
  loading.value = true
  try {
    const res = await api.getVideos()
    videos.value = res.data
  } catch (e) {
    console.error('Failed to fetch videos:', e)
  } finally {
    loading.value = false
  }
}

function handleSelect(row) {
  emit('select', row)
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

onMounted(fetchVideos)
</script>

<style scoped>
.file-browser {
  width: 100%;
}
.file-browser :deep(.el-table__row) {
  cursor: pointer;
  user-select: none;
}
.file-name {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
