<template>
  <div class="history-page">
    <div class="page-header">
      <h2>历史记录</h2>
      <div class="header-actions">
        <el-button @click="fetchData" :loading="loading" circle>
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.length" class="batch-bar">
      <el-checkbox
        :model-value="isAllSelected"
        :indeterminate="isIndeterminate"
        @change="toggleSelectAll"
      >全选</el-checkbox>
      <span class="batch-count">已选 {{ selectedIds.length }} 项</span>
      <el-button type="danger" size="small" plain @click="handleBatchDelete">
        批量删除
      </el-button>
    </div>

    <div v-loading="loading">
      <div v-if="taskList.length">
        <TaskCard
          v-for="task in taskList"
          :key="task.id"
          :task="task"
          :selectable="true"
          :selected="selectedIds.includes(task.id)"
          @toggleSelect="toggleSelect"
          @download="handleDownload"
          @retranslate="openRetranslateDialog"
          @cancel="handleCancel"
          @delete="handleDelete"
          @rerun="handleRerun"
        />
      </div>
      <el-empty v-else description="暂无历史记录" />
    </div>

    <!-- 重新翻译对话框 -->
    <el-dialog v-model="retranslateDialogVisible" title="重新翻译" width="450px">
      <el-form label-position="top">
        <el-form-item label="目标语言">
          <el-select v-model="retranslateForm.target_lang" style="width: 100%">
            <el-option label="中文" value="zh" />
            <el-option label="英文" value="en" />
            <el-option label="日文" value="ja" />
            <el-option label="韩文" value="ko" />
            <el-option label="法文" value="fr" />
            <el-option label="德文" value="de" />
            <el-option label="西班牙文" value="es" />
          </el-select>
        </el-form-item>
        <el-form-item label="翻译引擎">
          <el-radio-group v-model="retranslateForm.engine">
            <el-radio value="deepl">DeepL</el-radio>
            <el-radio value="openai">OpenAI</el-radio>
            <el-radio value="ollama">Ollama</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="retranslateForm.engine === 'ollama'" label="Ollama 模型">
          <el-select
            v-model="retranslateForm.ollama_model"
            style="width: 100%"
            allow-create
            filterable
            placeholder="选择或输入模型名称"
          >
            <el-option
              v-for="m in ollamaModelOptions"
              :key="m"
              :label="m"
              :value="m"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="retranslateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="retranslating" @click="handleRetranslate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import TaskCard from '@/components/TaskCard.vue'
import api from '@/api'

const taskList = ref([])
const loading = ref(false)
const retranslateDialogVisible = ref(false)
const retranslating = ref(false)
const selectedTask = ref(null)
const selectedIds = ref([])
const ollamaModelOptions = ref(['qwen2.5:14b', 'qwen2.5:7b', 'qwen2.5:3b', 'llama3:8b', 'gemma2:9b'])

// 全选 / 部分选中
const isAllSelected = computed(() =>
  taskList.value.length > 0 && selectedIds.value.length === taskList.value.length
)
const isIndeterminate = computed(() =>
  selectedIds.value.length > 0 && selectedIds.value.length < taskList.value.length
)

function toggleSelect(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) {
    selectedIds.value = selectedIds.value.filter(i => i !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]
  }
}

function toggleSelectAll(val) {
  if (val) {
    selectedIds.value = taskList.value.map(t => t.id)
  } else {
    selectedIds.value = []
  }
}

async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedIds.value.length} 个任务吗？此操作不可恢复。`,
      '确认批量删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await api.deleteTasks(selectedIds.value)
    ElMessage.success(`已删除 ${selectedIds.value.length} 个任务`)
    selectedIds.value = []
    fetchData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('批量删除失败：' + (e.response?.data?.detail || e.message))
    }
  }
}

const retranslateForm = reactive({
  target_lang: 'zh',
  engine: 'deepl',
  ollama_model: ''
})

async function fetchData() {
  loading.value = true
  try {
    const res = await api.getHistory()
    taskList.value = res.data
  } catch (e) {
    ElMessage.error('获取历史记录失败')
  } finally {
    loading.value = false
  }
}

async function handleDelete(task) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${task.video_name || task.id}」吗？此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await api.deleteTask(task.id)
    ElMessage.success('已删除')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
    }
  }
}

async function handleDownload(task) {
  try {
    const res = await api.downloadSrt(task.id)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `subtitle_${task.id}.srt`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

async function openRetranslateDialog(task) {
  selectedTask.value = task
  retranslateForm.target_lang = task.target_lang || 'zh'
  retranslateForm.engine = task.translation_engine || 'deepl'
  // 从全局设置加载默认模型
  try {
    const res = await api.getSettings()
    retranslateForm.ollama_model = res.data.ollama_model || 'qwen2.5:14b'
  } catch {
    retranslateForm.ollama_model = 'qwen2.5:14b'
  }
  retranslateDialogVisible.value = true
}

async function handleRetranslate() {
  if (!selectedTask.value) return
  retranslating.value = true
  try {
    const payload = {
      target_lang: retranslateForm.target_lang,
      engine: retranslateForm.engine
    }
    if (retranslateForm.engine === 'ollama' && retranslateForm.ollama_model) {
      payload.ollama_model = retranslateForm.ollama_model
    }
    await api.retranslate(selectedTask.value.id, payload)
    ElMessage.success('重新翻译任务已创建')
    retranslateDialogVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('重新翻译失败：' + (e.response?.data?.detail || e.message))
  } finally {
    retranslating.value = false
  }
}

async function handleRerun(task) {
  try {
    await api.rerunTask(task.id)
    ElMessage.success('任务已重新开始执行')
    fetchData()
  } catch (e) {
    ElMessage.error('重新执行失败：' + (e.response?.data?.detail || e.message))
  }
}

async function handleCancel(task) {
  try {
    await api.cancelTask(task.id)
    ElMessage.success('任务已取消')
    fetchData()
  } catch (e) {
    ElMessage.error('取消失败')
  }
}

onMounted(fetchData)
</script>

<style scoped>
.history-page {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  user-select: none;
  cursor: default;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.batch-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  margin-bottom: 12px;
  background: #f0f9eb;
  border-left: 3px solid #67c23a;
  border-radius: 4px;
}
.batch-count {
  color: #606266;
  font-size: 14px;
  flex: 1;
}
</style>
