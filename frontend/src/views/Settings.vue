<template>
  <div class="settings-page">
    <h2 class="page-title">全局设置</h2>

    <el-form
      v-loading="loading"
      :model="form"
      label-position="top"
      class="settings-form"
    >
      <!-- 视频源目录 -->
      <el-card class="section-card">
        <template #header>
          <span class="section-title">视频源目录</span>
        </template>
        <el-form-item label="视频源目录">
          <el-input v-model="form.video_source_dir" placeholder="请输入本地视频文件目录路径" />
          <div class="form-tip">系统将从该目录中读取视频文件</div>
        </el-form-item>
      </el-card>

      <!-- 翻译引擎选择 -->
      <el-card class="section-card">
        <template #header>
          <span class="section-title">翻译引擎配置</span>
        </template>

        <el-form-item label="默认翻译引擎">
          <el-radio-group v-model="form.engine">
            <el-radio value="deepl">DeepL</el-radio>
            <el-radio value="openai">OpenAI</el-radio>
            <el-radio value="ollama">Ollama</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- DeepL 配置 -->
        <template v-if="form.engine === 'deepl'">
          <el-form-item label="DeepL API Key">
            <el-input v-model="form.deepl_api_key" placeholder="请输入 DeepL API Key" show-password />
          </el-form-item>
        </template>

        <!-- OpenAI 配置 -->
        <template v-if="form.engine === 'openai'">
          <el-form-item label="OpenAI API Key">
            <el-input v-model="form.openai_api_key" placeholder="请输入 OpenAI API Key" show-password />
          </el-form-item>
          <el-form-item label="OpenAI Base URL">
            <el-input v-model="form.openai_base_url" placeholder="https://api.openai.com/v1" />
          </el-form-item>
        </template>

        <!-- Ollama 配置 -->
        <template v-if="form.engine === 'ollama'">
          <el-form-item label="Ollama Base URL">
            <el-input v-model="form.ollama_base_url" placeholder="http://localhost:11434" />
          </el-form-item>
          <el-form-item label="Ollama 模型名">
            <el-input v-model="form.ollama_model" placeholder="例如：llama3" />
          </el-form-item>
        </template>
      </el-card>

      <!-- Whisper 配置 -->
      <el-card class="section-card">
        <template #header>
          <span class="section-title">Whisper 配置</span>
        </template>
        <el-form-item label="默认 Whisper 模型">
          <el-select v-model="form.whisper_model" style="width: 100%; max-width: 300px;">
            <el-option label="tiny" value="tiny" />
            <el-option label="base" value="base" />
            <el-option label="small" value="small" />
            <el-option label="medium" value="medium" />
            <el-option label="large-v2" value="large-v2" />
          </el-select>
        </el-form-item>
      </el-card>

      <div class="form-actions">
        <el-button type="primary" size="large" :loading="saving" @click="handleSave">
          保存设置
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const saving = ref(false)

const form = reactive({
  video_source_dir: '',
  engine: 'deepl',
  deepl_api_key: '',
  openai_api_key: '',
  openai_base_url: '',
  ollama_base_url: 'http://localhost:11434',
  ollama_model: '',
  whisper_model: 'base'
})

async function fetchSettings() {
  loading.value = true
  try {
    const res = await api.getSettings()
    Object.assign(form, res.data)
  } catch (e) {
    ElMessage.error('获取设置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await api.updateSettings({ ...form })
    ElMessage.success('设置已保存')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

onMounted(fetchSettings)
</script>

<style scoped>
.settings-page {
  padding: 20px;
  max-width: 700px;
  margin: 0 auto;
}
.page-title {
  font-size: 20px;
  margin-bottom: 24px;
}
.section-card {
  margin-bottom: 20px;
}
.section-title {
  font-weight: 600;
  font-size: 15px;
}
.form-actions {
  text-align: right;
  padding-top: 12px;
}
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
