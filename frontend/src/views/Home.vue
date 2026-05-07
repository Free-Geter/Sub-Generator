<template>
  <div class="home-page">
    <el-row :gutter="24">
      <el-col :xs="24" :sm="24" :md="14" :lg="14">
        <el-card class="section-card">
          <template #header>
            <span class="card-title">选择视频文件</span>
          </template>
          <FileBrowser @select="handleVideoSelect" />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="10" :lg="10">
        <el-card class="section-card">
          <template #header>
            <span class="card-title">参数配置</span>
          </template>
          <el-form label-position="top" :model="form">
            <el-form-item label="目标语言">
              <el-select v-model="form.target_language" placeholder="请选择目标语言" style="width: 100%">
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
              <el-radio-group v-model="form.engine">
                <el-radio value="deepl">DeepL</el-radio>
                <el-radio value="openai">OpenAI</el-radio>
                <el-radio value="ollama">Ollama</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="Whisper 模型">
              <el-select v-model="form.whisper_model" placeholder="请选择模型" style="width: 100%">
                <el-option label="tiny" value="tiny" />
                <el-option label="base" value="base" />
                <el-option label="small" value="small" />
                <el-option label="medium" value="medium" />
                <el-option label="large-v2" value="large-v2" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>

        <div class="selected-info" v-if="selectedVideo">
          <el-alert
            :title="`已选择：${selectedVideo.name}`"
            type="success"
            :closable="false"
            show-icon
          />
        </div>

        <el-button
          type="primary"
          size="large"
          class="start-btn"
          :loading="submitting"
          :disabled="!selectedVideo"
          @click="handleStart"
        >
          开始生成字幕
        </el-button>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import FileBrowser from '@/components/FileBrowser.vue'
import api from '@/api'

const router = useRouter()

const selectedVideo = ref(null)
const submitting = ref(false)

const form = reactive({
  target_language: 'zh',
  engine: 'deepl',
  whisper_model: 'base'
})

function handleVideoSelect(video) {
  selectedVideo.value = video
}

async function handleStart() {
  if (!selectedVideo.value) {
    ElMessage.warning('请先选择视频文件')
    return
  }
  submitting.value = true
  try {
    const payload = {
      video_path: selectedVideo.value.path || selectedVideo.value.name,
      target_language: form.target_language,
      engine: form.engine,
      whisper_model: form.whisper_model
    }
    const res = await api.createTask(payload)
    const taskId = res.data.id || res.data.task_id
    ElMessage.success('任务创建成功')
    router.push(`/progress/${taskId}`)
  } catch (e) {
    ElMessage.error('任务创建失败：' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.home-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
.section-card {
  margin-bottom: 20px;
}
.card-title {
  font-weight: 600;
  font-size: 16px;
}
.selected-info {
  margin: 16px 0;
}
.start-btn {
  width: 100%;
  margin-top: 16px;
  font-size: 16px;
}
</style>
