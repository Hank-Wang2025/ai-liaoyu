<template>
  <div class="welcome-page page">
    <div class="welcome-page__content animate-fadeIn">
      <div class="welcome-page__header">
        <div class="welcome-page__logo animate-breathe">
          <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
            <circle cx="60" cy="60" r="55" stroke="url(#gradient)" stroke-width="4" />
            <path
              d="M40 60C40 48.954 48.954 40 60 40C71.046 40 80 48.954 80 60C80 71.046 71.046 80 60 80"
              stroke="url(#gradient)"
              stroke-width="4"
              stroke-linecap="round"
            />
            <circle cx="60" cy="60" r="15" fill="url(#gradient)" />
            <defs>
              <linearGradient id="gradient" x1="0" y1="0" x2="120" y2="120">
                <stop offset="0%" stop-color="#4ecdc4" />
                <stop offset="100%" stop-color="#45b7aa" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1 class="page__title">{{ $t('welcome.title') }}</h1>
        <p class="page__subtitle">{{ $t('welcome.subtitle') }}</p>
      </div>

      <p class="welcome-page__description">
        {{ $t('welcome.description') }}
      </p>

      <section class="welcome-page__assessment card">
        <AssessmentEntryPanel :show-back-button="false" />
      </section>

      <div v-if="showLanguageSelector" class="welcome-page__language">
        <button
          v-for="lang in languages"
          :key="lang.code"
          class="btn btn--ghost"
          :class="{ active: currentLocale === lang.code }"
          @click="changeLanguage(lang.code)"
        >
          {{ lang.name }}
        </button>
      </div>
    </div>

    <div class="welcome-page__bg">
      <div class="welcome-page__circle welcome-page__circle--1"></div>
      <div class="welcome-page__circle welcome-page__circle--2"></div>
      <div class="welcome-page__circle welcome-page__circle--3"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AssessmentEntryPanel from '@/components/entry/AssessmentEntryPanel.vue'

const { locale } = useI18n()

const currentLocale = computed(() => locale.value)
const showLanguageSelector = ref(true)

const languages = [
  { code: 'zh', name: '中文' },
  { code: 'en', name: 'English' },
]

const changeLanguage = (lang: string) => {
  locale.value = lang
  localStorage.setItem('locale', lang)
  showLanguageSelector.value = false
}

onMounted(() => {
  localStorage.removeItem('therapy_resume_snapshot')
})
</script>

<style lang="scss" scoped>
.welcome-page {
  position: relative;
  overflow: hidden;

  &__content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    max-width: 1080px;
  }

  &__header {
    margin-bottom: 24px;
    text-align: center;
  }

  &__logo {
    margin-bottom: 32px;
  }

  &__description {
    max-width: 640px;
    font-size: 1.125rem;
    color: var(--text-secondary);
    margin-bottom: 40px;
    line-height: 1.8;
    text-align: center;
  }

  &__assessment {
    width: 100%;
    max-width: 720px;
  }

  &__language {
    margin-top: 40px;
    display: flex;
    gap: 16px;

    .btn {
      &.active {
        color: var(--accent-primary);
        background: var(--accent-light);
      }
    }
  }

  &__bg {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
  }

  &__circle {
    position: absolute;
    border-radius: 50%;
    background: radial-gradient(circle, var(--accent-light) 0%, transparent 70%);

    &--1 {
      width: 600px;
      height: 600px;
      top: -200px;
      right: -200px;
      animation: float 20s ease-in-out infinite;
    }

    &--2 {
      width: 400px;
      height: 400px;
      bottom: -100px;
      left: -100px;
      animation: float 15s ease-in-out infinite reverse;
    }

    &--3 {
      width: 300px;
      height: 300px;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      animation: pulse 8s ease-in-out infinite;
    }
  }
}

@keyframes float {
  0%,
  100% {
    transform: translate(0, 0);
  }

  50% {
    transform: translate(-30px, 30px);
  }
}
</style>
