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
          <el-radio-group v-model="form.translation_engine">
            <el-radio value="deepl">DeepL</el-radio>
            <el-radio value="openai">OpenAI</el-radio>
            <el-radio value="ollama">Ollama</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- DeepL 配置 -->
        <template v-if="form.translation_engine === 'deepl'">
          <el-form-item label="DeepL API Key">
            <el-input v-model="form.deepl_api_key" placeholder="请输入 DeepL API Key" show-password />
          </el-form-item>
        </template>

        <!-- OpenAI 配置 -->
        <template v-if="form.translation_engine === 'openai'">
          <el-form-item label="OpenAI API Key">
            <el-input v-model="form.openai_api_key" placeholder="请输入 OpenAI API Key" show-password />
          </el-form-item>
          <el-form-item label="OpenAI Base URL">
            <el-input v-model="form.openai_base_url" placeholder="https://api.openai.com/v1" />
          </el-form-item>
        </template>

        <!-- Ollama 配置 -->
        <template v-if="form.translation_engine === 'ollama'">
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

      <!-- 翻译 Prompt 配置 -->
      <el-card class="section-card">
        <template #header>
          <span class="section-title">翻译 Prompt（自定义提示词）</span>
        </template>
        <el-form-item>
          <el-input
            v-model="form.translation_prompt"
            type="textarea"
            :rows="10"
            :placeholder="defaultPromptPlaceholder"
            resize="vertical"
          />
          <div class="form-tip">
            留空使用内置默认提示词。支持 <code>{'{target_lang}'}</code> 占位符（如"简体中文""English"等）。
          </div>
        </el-form-item>
        <el-button text type="primary" size="small" @click="resetPrompt">
          恢复默认提示词
        </el-button>
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
  translation_engine: 'deepl',
  deepl_api_key: '',
  openai_api_key: '',
  openai_base_url: '',
  ollama_base_url: 'http://localhost:11434',
  ollama_model: '',
  whisper_model: 'base',
  translation_prompt: ''
})

// 内置默认提示词（占位显示用）
const defaultPromptPlaceholder = `你是一位专业的日文字幕翻译专家。请将以下日文字幕逐行翻译成自然流畅的中文。
翻译要求：
1. 输入格式为 [行号] 原文，请保持 [行号] 标记，只输出译文
2. 严格保持行号顺序和数量一致，每行格式：[行号] 译文
3. 不要合并、省略、拆分任何行
4. 注意上下文连贯性，保持对话的流畅感
5. 保持原文的语气和风格（口语/敬语/随意等）
6. 人名、地名使用通用中文译名
7. 遇到日文特有表达时，用地道的中文习惯说法替代`

function resetPrompt() {
  form.translation_prompt = ''
  ElMessage.success('已恢复为内置默认提示词')
}

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
