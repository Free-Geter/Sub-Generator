<template>
  <div class="history-page">
    <div class="page-header">
      <h2>历史记录</h2>
      <el-button @click="fetchData" :loading="loading" circle>
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>

    <div v-loading="loading">
      <div v-if="taskList.length">
        <TaskCard
          v-for="task in taskList"
          :key="task.id"
          :task="task"
          @download="handleDownload"
          @retranslate="openRetranslateDialog"
          @cancel="handleCancel"
        />
      </div>
      <el-empty v-else description="暂无历史记录" />
    </div>

    <!-- 重新翻译对话框 -->
    <el-dialog v-model="retranslateDialogVisible" title="重新翻译" width="450px">
      <el-form label-position="top">
        <el-form-item label="目标语言">
          <el-select v-model="retranslateForm.target_language" style="width: 100%">
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
      </el-form>
      <template #footer>
        <el-button @click="retranslateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="retranslating" @click="handleRetranslate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import TaskCard from '@/components/TaskCard.vue'
import api from '@/api'

const router = useRouter()
const taskList = ref([])
const loading = ref(false)
const retranslateDialogVisible = ref(false)
const retranslating = ref(false)
const selectedTask = ref(null)

const retranslateForm = reactive({
  target_language: 'zh',
  engine: 'deepl'
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

function openRetranslateDialog(task) {
  selectedTask.value = task
  retranslateForm.target_language = task.target_language || 'zh'
  retranslateForm.engine = task.engine || 'deepl'
  retranslateDialogVisible.value = true
}

async function handleRetranslate() {
  if (!selectedTask.value) return
  retranslating.value = true
  try {
    const res = await api.retranslate(selectedTask.value.id, {
      target_language: retranslateForm.target_language,
      engine: retranslateForm.engine
    })
    ElMessage.success('重新翻译任务已创建')
    retranslateDialogVisible.value = false
    const taskId = res.data.id || res.data.task_id
    if (taskId) {
      router.push(`/progress/${taskId}`)
    } else {
      fetchData()
    }
  } catch (e) {
    ElMessage.error('重新翻译失败：' + (e.response?.data?.detail || e.message))
  } finally {
    retranslating.value = false
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
}
</style>
