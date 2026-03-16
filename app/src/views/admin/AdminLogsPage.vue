<template>
  <AdminLayout>
    <div class="logs-page">
      <header class="page-header">
        <h1>{{ t('admin.logs.title') }}</h1>
        <button class="btn btn--secondary" @click="refreshLogs">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          {{ t('common.refresh') }}
        </button>
      </header>

      <!-- Filters -->
      <div class="filters">
        <div class="filter-group">
          <label>{{ t('admin.logs.level') }}</label>
          <select v-model="filters.level" @change="loadLogs">
            <option value="">{{ t('admin.logs.allLevels') }}</option>
            <option v-for="level in logLevels" :key="level" :value="level">{{ level }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>{{ t('admin.logs.module') }}</label>
          <select v-model="filters.module" @change="loadLogs">
            <option value="">{{ t('admin.logs.allModules') }}</option>
            <option v-for="mod in logModules" :key="mod" :value="mod">{{ mod }}</option>
          </select>
        </div>
      </div>

      <!-- Logs Table -->
      <div class="logs-table-container">
        <table class="logs-table">
          <thead>
            <tr>
              <th class="col-time">{{ t('admin.logs.timestamp') }}</th>
              <th class="col-level">{{ t('admin.logs.level') }}</th>
              <th class="col-module">{{ t('admin.logs.module') }}</th>
              <th class="col-message">{{ t('admin.logs.message') }}</th>
              <th class="col-actions">{{ t('common.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id" :class="['log-row', `level-${log.level.toLowerCase()}`]">
              <td class="col-time">{{ formatTime(log.timestamp) }}</td>
              <td class="col-level">
                <span class="level-badge" :class="log.level.toLowerCase()">{{ log.level }}</span>
              </td>
              <td class="col-module">{{ log.module }}</td>
              <td class="col-message">
                <span class="message-text">{{ log.message }}</span>
              </td>
              <td class="col-actions">
                <button
                  v-if="log.details"
                  class="btn btn--ghost btn--small"
                  @click="showLogDetails(log)"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="logs.length === 0" class="no-logs">
          {{ t('admin.logs.noLogs') }}
        </div>
      </div>

      <!-- Pagination -->
      <div class="pagination" v-if="totalPages > 1">
        <button
          class="btn btn--ghost"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button
          class="btn btn--ghost"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      </div>

      <!-- Log Details Modal -->
      <div v-if="selectedLog" class="modal-overlay" @click.self="selectedLog = null">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ t('admin.logs.viewDetails') }}</h3>
            <button class="close-btn" @click="selectedLog = null">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="detail-row">
              <span class="detail-label">{{ t('admin.logs.timestamp') }}:</span>
              <span class="detail-value">{{ formatTime(selectedLog.timestamp) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">{{ t('admin.logs.level') }}:</span>
              <span class="level-badge" :class="selectedLog.level.toLowerCase()">{{ selectedLog.level }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">{{ t('admin.logs.module') }}:</span>
              <span class="detail-value">{{ selectedLog.module }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">{{ t('admin.logs.message') }}:</span>
              <span class="detail-value">{{ selectedLog.message }}</span>
            </div>
            <div v-if="selectedLog.details" class="detail-row details-section">
              <span class="detail-label">{{ t('common.details') }}:</span>
              <pre class="details-json">{{ JSON.stringify(selectedLog.details, null, 2) }}</pre>
            </div>
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
import { adminApi } from '@/api'
import type { LogEntry } from '@/types'

const { t } = useI18n()

const logs = ref<LogEntry[]>([])
const logLevels = ref<string[]>([])
const logModules = ref<string[]>([])
const totalLogs = ref(0)
const currentPage = ref(1)
const pageSize = 50
const selectedLog = ref<LogEntry | null>(null)

const filters = reactive({
  level: '',
  module: ''
})

const totalPages = computed(() => Math.ceil(totalLogs.value / pageSize))

function formatTime(timestamp: string): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString()
}

function showLogDetails(log: LogEntry) {
  selectedLog.value = log
}

async function loadLogs() {
  try {
    const response = await adminApi.getLogs({
      level: filters.level || undefined,
      module: filters.module || undefined,
      page: currentPage.value,
      page_size: pageSize
    })
    logs.value = response.logs
    totalLogs.value = response.total
  } catch (error) {
    console.error('Failed to load logs:', error)
  }
}

async function loadFilters() {
  try {
    const [levelsRes, modulesRes] = await Promise.all([
      adminApi.getLogLevels(),
      adminApi.getLogModules()
    ])
    logLevels.value = levelsRes.levels
    logModules.value = modulesRes.modules
  } catch (error) {
    console.error('Failed to load filters:', error)
  }
}

async function refreshLogs() {
  currentPage.value = 1
  await loadLogs()
}

async function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  await loadLogs()
}

onMounted(() => {
  loadFilters()
  loadLogs()
})
</script>

<style lang="scss" scoped>
.logs-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  h1 {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .btn svg {
    width: 16px;
    height: 16px;
  }
}

.filters {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  select {
    padding: 8px 12px;
    font-size: 0.875rem;
    color: var(--text-primary);
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    min-width: 150px;

    &:focus {
      outline: none;
      border-color: var(--accent-primary);
    }
  }
}

.logs-table-container {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;

  th, td {
    padding: 12px 16px;
    text-align: left;
  }

  th {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-color);
  }

  td {
    font-size: 0.875rem;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-color);
  }

  tr:last-child td {
    border-bottom: none;
  }

  .col-time {
    width: 180px;
    white-space: nowrap;
  }

  .col-level {
    width: 100px;
  }

  .col-module {
    width: 150px;
  }

  .col-message {
    min-width: 300px;
  }

  .col-actions {
    width: 60px;
    text-align: center;
  }
}

.log-row {
  transition: background var(--transition-fast);

  &:hover {
    background: var(--bg-tertiary);
  }

  &.level-error {
    background: rgba(240, 113, 103, 0.05);
  }

  &.level-warning {
    background: rgba(249, 199, 79, 0.05);
  }
}

.level-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 0.7rem;
  font-weight: 600;
  border-radius: var(--radius-full);
  text-transform: uppercase;

  &.debug {
    background: rgba(160, 160, 160, 0.2);
    color: var(--text-secondary);
  }

  &.info {
    background: rgba(126, 200, 227, 0.2);
    color: var(--info);
  }

  &.warning {
    background: rgba(249, 199, 79, 0.2);
    color: var(--warning);
  }

  &.error, &.critical {
    background: rgba(240, 113, 103, 0.2);
    color: var(--error);
  }
}

.message-text {
  display: block;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn--small {
  padding: 6px;

  svg {
    width: 14px;
    height: 14px;
  }
}

.no-logs {
  padding: 60px 20px;
  text-align: center;
  color: var(--text-muted);
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;

  .page-info {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .btn svg {
    width: 16px;
    height: 16px;
  }
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
  max-width: 600px;
  max-height: 80vh;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
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
  overflow-y: auto;
}

.detail-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }

  .detail-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    min-width: 100px;
  }

  .detail-value {
    font-size: 0.875rem;
    color: var(--text-primary);
    word-break: break-word;
  }
}

.details-section {
  flex-direction: column;
  gap: 8px;
}

.details-json {
  padding: 12px;
  font-size: 0.75rem;
  font-family: 'Monaco', 'Menlo', monospace;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
