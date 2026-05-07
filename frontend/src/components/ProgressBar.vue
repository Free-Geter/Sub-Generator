<template>
  <div class="progress-bar-wrapper">
    <el-steps :active="activeStep" finish-status="success" align-center>
      <el-step title="音频提取" :icon="getStepIcon(0)" />
      <el-step title="语音识别" :icon="getStepIcon(1)" />
      <el-step title="翻译" :icon="getStepIcon(2)" />
      <el-step title="SRT生成" :icon="getStepIcon(3)" />
    </el-steps>
    <div class="step-progress" v-if="progress > 0">
      <el-progress
        :percentage="progress"
        :stroke-width="10"
        :format="(p) => p + '%'"
        status="primary"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Loading, Check, Clock } from '@element-plus/icons-vue'
import { markRaw } from 'vue'

const props = defineProps({
  currentStep: { type: Number, default: 0 },
  progress: { type: Number, default: 0 }
})

const activeStep = computed(() => props.currentStep)

function getStepIcon(stepIndex) {
  if (stepIndex < props.currentStep) return markRaw(Check)
  if (stepIndex === props.currentStep) return markRaw(Loading)
  return markRaw(Clock)
}
</script>

<style scoped>
.progress-bar-wrapper {
  padding: 20px 0;
}
.step-progress {
  margin-top: 24px;
  padding: 0 40px;
}
</style>
