<template>
  <AdminLayout>
    <div class="config-page">
      <header class="page-header">
        <h1>{{ t('admin.config.title') }}</h1>
      </header>

      <!-- Tabs -->
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Therapy Plans Tab -->
      <div v-if="activeTab === 'plans'" class="tab-content">
        <div class="content-header">
          <h2>{{ t('admin.config.therapyPlans') }}</h2>
          <button v-if="adminStore.canEdit" class="btn btn--primary" @click="openPlanModal()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            {{ t('admin.config.createPlan') }}
          </button>
        </div>

        <div class="plans-grid">
          <div v-for="plan in plans" :key="plan.id" class="plan-card">
            <div class="plan-header">
              <h3>{{ plan.name }}</h3>
              <div class="plan-badges">
                <span class="badge intensity" :class="plan.intensity">{{ plan.intensity }}</span>
                <span class="badge style">{{ plan.style }}</span>
              </div>
            </div>
            <p class="plan-description">{{ plan.description || 'No description' }}</p>
            <div class="plan-meta">
              <span>{{ formatDuration(plan.duration) }}</span>
              <span>{{ plan.target_emotions?.length || 0 }} emotions</span>
            </div>
            <div class="plan-actions" v-if="adminStore.canEdit">
              <button class="btn btn--ghost" @click="openPlanModal(plan)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button v-if="adminStore.canDelete" class="btn btn--ghost delete" @click="confirmDeletePlan(plan)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Device Settings Tab -->
      <div v-if="activeTab === 'devices'" class="tab-content">
        <div class="content-header">
          <h2>{{ t('admin.config.deviceSettings') }}</h2>
        </div>

        <div class="device-settings">
          <div v-for="(settings, deviceType) in deviceConfig" :key="deviceType" class="device-section">
            <h3>{{ deviceType }}</h3>
            <div class="settings-grid">
              <div v-for="(value, key) in settings" :key="key" class="setting-item">
                <label>{{ formatSettingKey(key) }}</label>
                <input
                  type="number"
                  :value="value"
                  @change="updateDeviceSetting(deviceType, key, ($event.target as HTMLInputElement).value)"
                  :disabled="!adminStore.canEdit"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Content Library Tab -->
      <div v-if="activeTab === 'content'" class="tab-content">
        <div class="content-header">
          <h2>{{ t('admin.config.contentLibrary') }}</h2>
          <div class="content-filters">
            <button
              v-for="type in contentTypes"
              :key="type.id"
              class="filter-btn"
              :class="{ active: contentFilter === type.id }"
              @click="contentFilter = type.id"
            >
              {{ type.label }}
            </button>
          </div>
        </div>

        <div class="content-list">
          <div v-for="item in filteredContent" :key="item.id" class="content-item">
            <div class="content-icon" :class="item.type">
              <svg v-if="item.type === 'audio'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18V5l12-2v13"/>
                <circle cx="6" cy="18" r="3"/>
                <circle cx="18" cy="16" r="3"/>
              </svg>
              <svg v-else-if="item.type === 'visual'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
                <line x1="7" y1="2" x2="7" y2="22"/>
                <line x1="17" y1="2" x2="17" y2="22"/>
                <line x1="2" y1="12" x2="22" y2="12"/>
                <line x1="2" y1="7" x2="7" y2="7"/>
                <line x1="2" y1="17" x2="7" y2="17"/>
                <line x1="17" y1="17" x2="22" y2="17"/>
                <line x1="17" y1="7" x2="22" y2="7"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <div class="content-info">
              <span class="content-name">{{ item.name }}</span>
              <span class="content-path">{{ item.path }}</span>
            </div>
            <span class="content-type-badge">{{ item.type }}</span>
          </div>
          <div v-if="filteredContent.length === 0" class="no-content">
            {{ t('admin.dashboard.noData') }}
          </div>
        </div>
      </div>

      <!-- Plan Modal -->
      <div v-if="showPlanModal" class="modal-overlay" @click.self="closePlanModal">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ editingPlan ? t('admin.config.editPlan') : t('admin.config.createPlan') }}</h3>
            <button class="close-btn" @click="closePlanModal">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <form @submit.prevent="savePlan" class="modal-body">
            <div class="form-group">
              <label>{{ t('admin.config.planName') }}</label>
              <input v-model="planForm.name" type="text" required />
            </div>
            <div class="form-group">
              <label>{{ t('admin.config.planDescription') }}</label>
              <textarea v-model="planForm.description" rows="3"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('admin.config.intensity') }}</label>
                <select v-model="planForm.intensity">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div class="form-group">
                <label>{{ t('admin.config.style') }}</label>
                <select v-model="planForm.style">
                  <option value="chinese">Chinese</option>
                  <option value="modern">Modern</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>{{ t('admin.config.duration') }}</label>
              <input v-model.number="planForm.duration" type="number" min="60" required />
            </div>
            <div class="form-group">
              <label>{{ t('admin.config.targetEmotions') }}</label>
              <div class="emotion-checkboxes">
                <label v-for="emotion in emotionOptions" :key="emotion" class="checkbox-label">
                  <input
                    type="checkbox"
                    :value="emotion"
                    v-model="planForm.target_emotions"
                  />
                  {{ t(`emotions.${emotion}`) }}
                </label>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn--secondary" @click="closePlanModal">
                {{ t('common.cancel') }}
              </button>
              <button type="submit" class="btn btn--primary">
                {{ t('common.save') }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Delete Confirmation Modal -->
      <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
        <div class="modal modal--small">
          <div class="modal-header">
            <h3>{{ t('admin.config.deletePlan') }}</h3>
          </div>
          <div class="modal-body">
            <p>{{ t('admin.config.deleteConfirm') }}</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn--secondary" @click="showDeleteModal = false">
              {{ t('common.cancel') }}
            </button>
            <button class="btn btn--primary delete" @click="deletePlan">
              {{ t('common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import AdminLayout from '@/components/admin/AdminLayout.vue'
import { useAdminStore } from '@/stores/admin'
import { adminApi } from '@/api'
import type { TherapyPlanConfig, ContentItem } from '@/types'

const { t } = useI18n()
const adminStore = useAdminStore()

const activeTab = ref('plans')
const tabs = [
  { id: 'plans', label: t('admin.config.therapyPlans') },
  { id: 'devices', label: t('admin.config.deviceSettings') },
  { id: 'content', label: t('admin.config.contentLibrary') }
]

const plans = ref<TherapyPlanConfig[]>([])
const deviceConfig = ref<Record<string, Record<string, any>>>({})
const contentItems = ref<ContentItem[]>([])
const contentFilter = ref<string>('all')

const contentTypes = [
  { id: 'all', label: 'All' },
  { id: 'audio', label: t('admin.config.audio') },
  { id: 'visual', label: t('admin.config.visual') },
  { id: 'plan', label: t('admin.config.plan') }
]

const emotionOptions = ['happy', 'sad', 'angry', 'anxious', 'tired', 'fearful', 'surprised', 'disgusted', 'neutral']

const showPlanModal = ref(false)
const showDeleteModal = ref(false)
const editingPlan = ref<TherapyPlanConfig | null>(null)
const planToDelete = ref<TherapyPlanConfig | null>(null)

const planForm = reactive<TherapyPlanConfig>({
  id: '',
  name: '',
  description: '',
  target_emotions: [],
  intensity: 'medium',
  style: 'modern',
  duration: 600
})

const filteredContent = computed(() => {
  if (contentFilter.value === 'all') return contentItems.value
  return contentItems.value.filter(item => item.type === contentFilter.value)
})

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  return `${mins} min`
}

function formatSettingKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function openPlanModal(plan?: TherapyPlanConfig) {
  if (plan) {
    editingPlan.value = plan
    Object.assign(planForm, {
      ...plan,
      target_emotions: Array.isArray(plan.target_emotions) ? [...plan.target_emotions] : []
    })
  } else {
    editingPlan.value = null
    Object.assign(planForm, {
      id: `plan_${Date.now()}`,
      name: '',
      description: '',
      target_emotions: [],
      intensity: 'medium',
      style: 'modern',
      duration: 600
    })
  }
  showPlanModal.value = true
}

function closePlanModal() {
  showPlanModal.value = false
  editingPlan.value = null
}

async function savePlan() {
  try {
    if (editingPlan.value) {
      await adminApi.updateTherapyPlan(planForm.id, planForm)
    } else {
      await adminApi.createTherapyPlan(planForm)
    }
    await loadPlans()
    closePlanModal()
  } catch (error) {
    console.error('Failed to save plan:', error)
  }
}

function confirmDeletePlan(plan: TherapyPlanConfig) {
  planToDelete.value = plan
  showDeleteModal.value = true
}

async function deletePlan() {
  if (!planToDelete.value) return
  try {
    await adminApi.deleteTherapyPlan(planToDelete.value.id)
    await loadPlans()
    showDeleteModal.value = false
    planToDelete.value = null
  } catch (error) {
    console.error('Failed to delete plan:', error)
  }
}

async function updateDeviceSetting(deviceType: string, key: string, value: string) {
  try {
    const numValue = parseFloat(value)
    await adminApi.updateDeviceConfig(deviceType, { [key]: numValue })
    deviceConfig.value[deviceType][key] = numValue
  } catch (error) {
    console.error('Failed to update device setting:', error)
  }
}

async function loadPlans() {
  try {
    const response = await adminApi.getTherapyPlans()
    plans.value = response.plans
  } catch (error) {
    console.error('Failed to load plans:', error)
  }
}

async function loadDeviceConfig() {
  try {
    const response = await adminApi.getDeviceConfig()
    deviceConfig.value = response.devices
  } catch (error) {
    console.error('Failed to load device config:', error)
  }
}

async function loadContent() {
  try {
    const response = await adminApi.getContentLibrary()
    contentItems.value = response.content
  } catch (error) {
    console.error('Failed to load content:', error)
  }
}

onMounted(() => {
  loadPlans()
  loadDeviceConfig()
  loadContent()
})
</script>

<style lang="scss" scoped>
.config-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;

  h1 {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.tab-btn {
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: none;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }

  &.active {
    color: var(--accent-primary);
    background: var(--accent-light);
  }
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h2 {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .btn svg {
    width: 16px;
    height: 16px;
  }
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.plan-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;

  h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.plan-badges {
  display: flex;
  gap: 6px;
}

.badge {
  padding: 2px 8px;
  font-size: 0.7rem;
  font-weight: 500;
  border-radius: var(--radius-full);

  &.intensity {
    &.low { background: rgba(78, 205, 196, 0.2); color: var(--accent-primary); }
    &.medium { background: rgba(249, 199, 79, 0.2); color: var(--warning); }
    &.high { background: rgba(240, 113, 103, 0.2); color: var(--error); }
  }

  &.style {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
  }
}

.plan-description {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 12px;
  line-height: 1.5;
}

.plan-meta {
  display: flex;
  gap: 16px;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.plan-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);

  .btn {
    padding: 8px;

    svg {
      width: 16px;
      height: 16px;
    }

    &.delete:hover {
      color: var(--error);
      background: rgba(240, 113, 103, 0.1);
    }
  }
}

.device-settings {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.device-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;

  h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
    text-transform: capitalize;
  }
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 0.75rem;
    color: var(--text-secondary);
    text-transform: capitalize;
  }

  input {
    padding: 8px 12px;
    font-size: 0.875rem;
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);

    &:focus {
      outline: none;
      border-color: var(--accent-primary);
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
}

.content-filters {
  display: flex;
  gap: 8px;
}

.filter-btn {
  padding: 6px 12px;
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover, &.active {
    color: var(--accent-primary);
    border-color: var(--accent-primary);
    background: var(--accent-light);
  }
}

.content-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.content-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.content-icon {
  width: 36px;
  height: 36px;
  padding: 8px;
  border-radius: var(--radius-md);

  svg {
    width: 100%;
    height: 100%;
  }

  &.audio {
    background: rgba(78, 205, 196, 0.15);
    color: var(--accent-primary);
  }

  &.visual {
    background: rgba(155, 89, 182, 0.15);
    color: #9b59b6;
  }

  &.plan {
    background: rgba(249, 199, 79, 0.15);
    color: var(--warning);
  }
}

.content-info {
  flex: 1;
  display: flex;
  flex-direction: column;

  .content-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .content-path {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
}

.content-type-badge {
  padding: 4px 10px;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
}

.no-content {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
}

// Modal styles
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  width: 100%;
  max-width: 500px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);

  &--small {
    max-width: 400px;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);

  h3 {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .close-btn {
    width: 32px;
    height: 32px;
    padding: 6px;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: var(--radius-md);

    &:hover {
      background: var(--bg-tertiary);
      color: var(--text-primary);
    }

    svg {
      width: 100%;
      height: 100%;
    }
  }
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid var(--border-color);

  .btn.delete {
    background: var(--error);
    color: white;
  }
}

.form-group {
  margin-bottom: 16px;

  label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: 6px;
  }

  input, textarea, select {
    width: 100%;
    padding: 10px 14px;
    font-size: 0.875rem;
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);

    &:focus {
      outline: none;
      border-color: var(--accent-primary);
    }
  }

  textarea {
    resize: vertical;
  }
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.emotion-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  cursor: pointer;

  input {
    width: auto;
  }

  &:has(input:checked) {
    background: var(--accent-light);
    color: var(--accent-primary);
  }
}
</style>
