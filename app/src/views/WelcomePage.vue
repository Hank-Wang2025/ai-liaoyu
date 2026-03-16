<template>
  <div class="welcome-page page">
    <div class="welcome-page__content animate-fadeIn">
      <!-- Logo 和标题 -->
      <div class="welcome-page__header">
        <div class="welcome-page__logo animate-breathe">
          <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
            <circle cx="60" cy="60" r="55" stroke="url(#gradient)" stroke-width="4"/>
            <path d="M40 60C40 48.954 48.954 40 60 40C71.046 40 80 48.954 80 60C80 71.046 71.046 80 60 80" 
                  stroke="url(#gradient)" stroke-width="4" stroke-linecap="round"/>
            <circle cx="60" cy="60" r="15" fill="url(#gradient)"/>
            <defs>
              <linearGradient id="gradient" x1="0" y1="0" x2="120" y2="120">
                <stop offset="0%" stop-color="#4ecdc4"/>
                <stop offset="100%" stop-color="#45b7aa"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1 class="page__title">{{ $t('welcome.title') }}</h1>
        <p class="page__subtitle">{{ $t('welcome.subtitle') }}</p>
      </div>
      
      <!-- 描述 -->
      <p class="welcome-page__description">
        {{ $t('welcome.description') }}
      </p>
      
      <!-- 开始按钮 -->
      <button class="btn btn--primary btn--large" @click="startHealing">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" 
                stroke="currentColor" stroke-width="2"/>
          <path d="M10 8L16 12L10 16V8Z" fill="currentColor"/>
        </svg>
        {{ $t('welcome.startButton') }}
      </button>
      
      <!-- 语言切换 -->
      <div class="welcome-page__language">
        <button 
          v-for="lang in languages" 
          :key="lang.code"
          class="btn btn--ghost"
          :class="{ 'active': currentLocale === lang.code }"
          @click="changeLanguage(lang.code)"
        >
          {{ lang.name }}
        </button>
      </div>
    </div>
    
    <!-- 背景装饰 -->
    <div class="welcome-page__bg">
      <div class="welcome-page__circle welcome-page__circle--1"></div>
      <div class="welcome-page__circle welcome-page__circle--2"></div>
      <div class="welcome-page__circle welcome-page__circle--3"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const { locale } = useI18n()

const currentLocale = computed(() => locale.value)

const languages = [
  { code: 'zh', name: '中文' },
  { code: 'en', name: 'English' }
]

const changeLanguage = (lang: string) => {
  locale.value = lang
  localStorage.setItem('locale', lang)
}

const startHealing = () => {
  router.push('/assessment')
}
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
    text-align: center;
    max-width: 600px;
  }
  
  &__header {
    margin-bottom: 24px;
  }
  
  &__logo {
    margin-bottom: 32px;
  }
  
  &__description {
    font-size: 1.125rem;
    color: var(--text-secondary);
    margin-bottom: 48px;
    line-height: 1.8;
  }
  
  &__language {
    margin-top: 48px;
    display: flex;
    gap: 16px;
    
    .btn {
      &.active {
        color: var(--accent-primary);
        background: var(--accent-light);
      }
    }
  }
  
  // 背景装饰
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
  0%, 100% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(-30px, 30px);
  }
}
</style>
