export interface ReportEffectiveness {
  rating?: string | null
  emotion_improvement?: number | null
}

const ratingKeys = new Set([
  'excellent',
  'good',
  'moderate',
  'minimal',
  'none',
])

export function getImprovementText(
  effectiveness: ReportEffectiveness | null | undefined,
  fallbackImprovement: number,
  translate: (key: string) => string,
): string {
  const rating = effectiveness?.rating
  if (rating && ratingKeys.has(rating)) {
    return translate(`report.improvementRatings.${rating}`)
  }

  const percent = Math.round(Math.abs(fallbackImprovement) * 100)
  if (fallbackImprovement > 0.2) return `+${percent}%`
  if (fallbackImprovement < -0.2) return `-${percent}%`
  return translate('report.improvementRatings.stable')
}
