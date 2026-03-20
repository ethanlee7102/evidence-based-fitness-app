const KG_PER_LB = 0.453592

export { kgToLbs, lbsToKg } from '../../onboarding/utils/unitConversion'

/**
 * Display weight in the user's preferred unit.
 * Rounds to nearest whole number for clean display (no 89.9 artifacts).
 */
export function displayWeight(kg: number, units: 'metric' | 'imperial'): number {
  if (units === 'imperial') {
    return Math.round(kg / KG_PER_LB)
  }
  return Math.round(kg * 10) / 10
}

/**
 * Convert input weight to kg for storage.
 * Uses full precision (no rounding) so round-trips are lossless.
 */
export function inputToKg(value: number, units: 'metric' | 'imperial'): number {
  if (units === 'imperial') {
    return value * KG_PER_LB
  }
  return value
}

/**
 * Get the weight unit label for display.
 */
export function weightUnit(units: 'metric' | 'imperial'): string {
  return units === 'imperial' ? 'lbs' : 'kg'
}

/**
 * Format duration in seconds to HH:MM:SS or MM:SS.
 */
export function formatDuration(seconds: number): string {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  const pad = (n: number) => String(n).padStart(2, '0')

  if (hrs > 0) {
    return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`
  }
  return `${pad(mins)}:${pad(secs)}`
}

/**
 * Format volume (weight * reps) for display with appropriate unit.
 */
export function formatVolume(
  volumeKg: number,
  units: 'metric' | 'imperial',
): string {
  const value = displayWeight(volumeKg, units)
  const unit = weightUnit(units)
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}k ${unit}`
  }
  return `${Math.round(value)} ${unit}`
}
