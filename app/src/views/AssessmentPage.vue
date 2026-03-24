<template>
  <div class="assessment-page page">
    <div class="assessment-page__shell animate-fadeIn">
      <h1 class="page__title">{{ $t('assessment.title') }}</h1>
      <p class="page__subtitle">{{ $t(assessmentSubtitleKey) }}</p>

      <AssessmentEntryPanel @subtitle-change="handleAssessmentSubtitleChange" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import AssessmentEntryPanel from '@/components/entry/AssessmentEntryPanel.vue'

type AssessmentSubtitleKey =
  | 'assessment.subtitle'
  | 'assessment.microphoneNoVoice'

const assessmentSubtitleKey = ref<AssessmentSubtitleKey>('assessment.subtitle')

const handleAssessmentSubtitleChange = (subtitleKey: AssessmentSubtitleKey) => {
  assessmentSubtitleKey.value = subtitleKey
}
</script>

<style lang="scss" scoped>
.assessment-page {
  &__shell {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    max-width: 600px;
  }
}
</style>
