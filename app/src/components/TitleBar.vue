<template>
  <div class="title-bar">
    <div class="title-bar__drag-region">
      <span class="title-bar__title">{{ $t('common.appName') }}</span>
    </div>
    <div class="title-bar__controls">
      <button class="title-bar__btn" @click="minimize" title="最小化">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <rect y="5" width="12" height="2" fill="currentColor"/>
        </svg>
      </button>
      <button class="title-bar__btn" @click="maximize" title="最大化">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <rect x="1" y="1" width="10" height="10" stroke="currentColor" stroke-width="2" fill="none"/>
        </svg>
      </button>
      <button class="title-bar__btn title-bar__btn--close" @click="close" title="关闭">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path d="M1 1L11 11M11 1L1 11" stroke="currentColor" stroke-width="2"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
const minimize = () => {
  window.electronAPI?.minimizeWindow()
}

const maximize = () => {
  window.electronAPI?.maximizeWindow()
}

const close = () => {
  window.electronAPI?.closeWindow()
}
</script>

<style lang="scss" scoped>
.title-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 32px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  -webkit-app-region: drag;
  user-select: none;
  
  &__drag-region {
    flex: 1;
    display: flex;
    align-items: center;
    padding-left: 80px; // macOS 窗口按钮空间
  }
  
  &__title {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }
  
  &__controls {
    display: flex;
    -webkit-app-region: no-drag;
  }
  
  &__btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 46px;
    height: 32px;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
    
    &:hover {
      background: var(--bg-tertiary);
      color: var(--text-primary);
    }
    
    &--close:hover {
      background: var(--error);
      color: white;
    }
  }
}
</style>
