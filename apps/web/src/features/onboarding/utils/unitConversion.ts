// Conversion constants
const CM_PER_INCH = 2.54
const KG_PER_LB = 0.453592

// Height conversions
export function cmToFeetInches(cm: number): { feet: number; inches: number } {
  const totalInches = cm / CM_PER_INCH
  const feet = Math.floor(totalInches / 12)
  const inches = Math.round(totalInches % 12)
  return { feet, inches }
}

export function feetInchesToCm(feet: number, inches: number): number {
  const totalInches = feet * 12 + inches
  return Math.round(totalInches * CM_PER_INCH * 10) / 10
}

// Weight conversions
export function kgToLbs(kg: number): number {
  return Math.round(kg / KG_PER_LB * 10) / 10
}

export function lbsToKg(lbs: number): number {
  return Math.round(lbs * KG_PER_LB * 10) / 10
}

// Display formatters
export function formatHeight(cm: number, units: 'metric' | 'imperial'): string {
  if (units === 'imperial') {
    const { feet, inches } = cmToFeetInches(cm)
    return `${feet}'${inches}"`
  }
  return `${cm} cm`
}

export function formatWeight(kg: number, units: 'metric' | 'imperial'): string {
  if (units === 'imperial') {
    return `${kgToLbs(kg)} lbs`
  }
  return `${kg} kg`
}
