import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useTaskStore = defineStore('task', () => {
  const currentTask = ref(null)
  const taskList = ref([])
  const settings = ref(null)

  async function fetchTask(id) {
    const res = await api.getTask(id)
    currentTask.value = res.data
    return res.data
  }

  async function createTask(data) {
    const res = await api.createTask(data)
    currentTask.value = res.data
    return res.data
  }

  async function fetchHistory() {
    const res = await api.getHistory()
    taskList.value = res.data
    return res.data
  }

  async function fetchSettings() {
    const res = await api.getSettings()
    settings.value = res.data
    return res.data
  }

  async function updateSettings(data) {
    const res = await api.updateSettings(data)
    settings.value = res.data
    return res.data
  }

  return {
    currentTask,
    taskList,
    settings,
    fetchTask,
    createTask,
    fetchHistory,
    fetchSettings,
    updateSettings,
  }
})
