<template>
  <AdminLayout>
    <div class="dashboard">
      <header class="dashboard-header">
        <h1>{{ t('admin.dashboard.title') }}</h1>
        <button class="btn btn--secondary" @click="refreshData">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          {{ t('common.refresh') }}
        </button>
      </header>

      <!-- Stats Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon sessions">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.total_sessions }}</span>
            <span class="stat-label">{{ t('admin.dashboard.totalSessions') }}</span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon today">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.sessions_today }}</span>
            <span class="stat-label">{{ t('admin.dashboard.todaySessions') }}</span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon duration">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ formatDuration(stats.avg_session_duration_seconds) }}</span>
            <span class="stat-label">{{ t('admin.dashboard.avgDuration') }}</span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon devices">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ deviceStatus.connected_count }}/{{ deviceStatus.total }}</span>
            <span class="stat-label">{{ t('admin.dashboard.connectedDevices') }}</span>
          </div>
        </div>
      </div>

      <div class="dashboard-grid">
        <!-- Device Status -->
        <section class="dashboard-card devices-card">
          <h2>{{ t('admin.dashboard.deviceStatus') }}</h2>
          <div class="device-list">
            <div
              v-for="device in deviceStatus.devices"
              :key="device.name"
              class="device-item"
              :class="{ connected: device.connected }"
            >
              <div class="device-icon">
                <component :is="getDeviceIcon(device.type)" />
              </div>
              <div class="device-info">
                <span class="device-name">{{ device.name }}</span>
                <span class="device-type">{{ device.type }}</span>
              </div>
              <div class="device-status">
                <span class="status-dot" :class="{ online: device.connected }"></span>
                <span>{{ device.connected ? 'Online' : 'Offline' }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Daily Trend Chart -->
        <section class="dashboard-card chart-card">
          <h2>{{ t('admin.dashboard.dailyTrend') }}</h2>
          <div class="chart-container" v-if="stats.daily_sessions.length > 0">
            <Bar :data="dailyChartData" :options="chartOptions" />
          </div>
          <div class="no-data" v-else>{{ t('admin.dashboard.noData') }}</div>
        </section>

        <!-- Emotion Distribution -->
        <section class="dashboard-card chart-card">
          <h2>{{ t('admin.dashboard.emotionDistribution') }}</h2>
          <div class="chart-container" v-if="Object.keys(stats.emotion_distribution).length > 0">
            <Doughnut :data="emotionChartData" :options="doughnutOptions" />
          </div>
          <div class="no-data" v-else>{{ t('admin.dashboard.noData') }}</div>
        </section>

        <!-- Recent Sessions -->
        <section class="dashboard-card sessions-card">
          <h2>{{ t('admin.dashboard.recentSessions') }}</h2>
          <div class="sessions-list" v-if="recentSessions.length > 0">
            <div v-for="session in recentSessions" :key="session.id" class="session-item">
              <div class="session-emotion">
                <span class="emotion-badge" :class="session.initial_emotion_category">
                  {{ t(`emotions.${session.initial_emotion_category}`) }}
                </span>
              </div>
              <div class="session-info">
                <span class="session-time">{{ formatTime(session.start_time) }}</span>
                <span class="session-duration">{{ formatDuration(session.duration_seconds || 0) }}</span>
              </div>
            </div>
          </div>
          <div class="no-data" v-else>{{ t('admin.dashboard.noData') }}</div>
        </section>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import AdminLayout from '@/components/admin/AdminLayout.vue'
import { adminApi } from '@/api'
import type { UsageStats, DeviceStatusResponse, SessionListItem } from '@/types'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend)

const { t } = useI18n()

const stats = ref<UsageStats>({
  total_sessions: 0,
  total_duration_seconds: 0,
  avg_session_duration_seconds: 0,
  sessions_today: 0,
  sessions_this_week: 0,
  sessions_this_month: 0,
  emotion_distribution: {},
  daily_sessions: []
})

const deviceStatus = ref<DeviceStatusResponse>({
  devices: [],
  total: 0,
  connected_count: 0
})

const recentSessions = ref<SessionListItem[]>([])

const dailyChartData = computed(() => ({
  labels: stats.value.daily_sessions.map(d => d.date.slice(5)),
  datasets: [{
    label: t('admin.dashboard.totalSessions'),
    data: stats.value.daily_sessions.map(d => d.count),
    backgroundColor: 'rgba(78, 205, 196, 0.6)',
    borderColor: 'rgba(78, 205, 196, 1)',
    borderWidth: 1
  }]
}))

const emotionChartData = computed(() => {
  const colors = {
    happy: '#4ecdc4',
    sad: '#7ec8e3',
    angry: '#f07167',
    anxious: '#f9c74f',
    tired: '#a0a0a0',
    fearful: '#9b59b6',
    surprised: '#e74c3c',
    disgusted: '#27ae60',
    neutral: '#95a5a6'
  }
  
  const labels = Object.keys(stats.value.emotion_distribution)
  const data = Object.values(stats.value.emotion_distribution)
  const bgColors = labels.map(l => colors[l as keyof typeof colors] || '#666')
  
  return {
    labels: labels.map(l => t(`emotions.${l}`)),
    datasets: [{
      data,
      backgroundColor: bgColors,
      borderWidth: 0
    }]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false }
  },
  scales: {
    y: {
      beginAtZero: true,
      grid: { color: 'rgba(255,255,255,0.1)' },
      ticks: { color: '#a0a0a0' }
    },
    x: {
      grid: { display: false },
      ticks: { color: '#a0a0a0' }
    }
  }
}

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right' as const,
      labels: { color: '#a0a0a0' }
    }
  }
}

function getDeviceIcon(type: string) {
  const icons: Record<string, any> = {
    light: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M9 18h6' }),
      h('path', { d: 'M10 22h4' }),
      h('path', { d: 'M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14' })
    ]),
    audio: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('polygon', { points: '11 5 6 9 2 9 2 15 6 15 11 19 11 5' }),
      h('path', { d: 'M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07' })
    ]),
    chair: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M19 9V6a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v3' }),
      h('path', { d: 'M3 11v5a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5a2 2 0 0 0-4 0v2H7v-2a2 2 0 0 0-4 0Z' }),
      h('path', { d: 'M5 18v2' }),
      h('path', { d: 'M19 18v2' })
    ]),
    scent: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M8 2h8l4 10H4L8 2Z' }),
      h('path', { d: 'M12 12v10' }),
      h('path', { d: 'M8 22h8' })
    ]),
    bio: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M22 12h-4l-3 9L9 3l-3 9H2' })
    ]),
    camera: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z' }),
      h('circle', { cx: '12', cy: '13', r: '4' })
    ])
  }
  return icons[type] || icons.light
}

function formatDuration(seconds: number): string {
  if (!seconds) return '0m'
  const mins = Math.floor(seconds / 60)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  const remainMins = mins % 60
  return `${hours}h ${remainMins}m`
}

function formatTime(timeStr: string): string {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleString()
}

async function loadData() {
  try {
    const [statsData, devicesData, sessionsData] = await Promise.all([
      adminApi.getUsageStats(),
      adminApi.getDeviceStatus(),
      adminApi.getSessions({ page: 1, page_size: 5 })
    ])
    stats.value = statsData
    deviceStatus.value = devicesData
    recentSessions.value = sessionsData.sessions
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

async function refreshData() {
  await loadData()
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;

  @media (max-width: 1200px) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.stat-icon {
  width: 48px;
  height: 48px;
  padding: 12px;
  border-radius: var(--radius-md);

  svg {
    width: 100%;
    height: 100%;
  }

  &.sessions {
    background: rgba(78, 205, 196, 0.15);
    color: var(--accent-primary);
  }

  &.today {
    background: rgba(249, 199, 79, 0.15);
    color: var(--warning);
  }

  &.duration {
    background: rgba(126, 200, 227, 0.15);
    color: var(--info);
  }

  &.devices {
    background: rgba(155, 89, 182, 0.15);
    color: #9b59b6;
  }
}

.stat-content {
  display: flex;
  flex-direction: column;

  .stat-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .stat-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

.dashboard-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: 20px;

  h2 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
  }
}

.device-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.device-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  opacity: 0.6;

  &.connected {
    opacity: 1;
  }
}

.device-icon {
  width: 32px;
  height: 32px;
  color: var(--text-secondary);

  svg {
    width: 100%;
    height: 100%;
  }
}

.device-info {
  flex: 1;
  display: flex;
  flex-direction: column;

  .device-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .device-type {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
}

.device-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--text-muted);

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--error);

    &.online {
      background: var(--success);
    }
  }
}

.chart-container {
  height: 200px;
}

.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.emotion-badge {
  padding: 4px 12px;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: var(--radius-full);
  background: var(--accent-light);
  color: var(--accent-primary);

  &.anxious { background: rgba(249, 199, 79, 0.2); color: var(--warning); }
  &.sad { background: rgba(126, 200, 227, 0.2); color: var(--info); }
  &.angry { background: rgba(240, 113, 103, 0.2); color: var(--error); }
  &.tired { background: rgba(160, 160, 160, 0.2); color: var(--text-secondary); }
}

.session-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;

  .session-time {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .session-duration {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 150px;
  color: var(--text-muted);
  font-size: 0.875rem;
}
</style>
