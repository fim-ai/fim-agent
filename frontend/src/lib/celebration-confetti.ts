// Multi-burst celebration sequence built on canvas-confetti.
// Used by onboarding's final step and the post-checkout success state.
// Respects prefers-reduced-motion and renders above modals (z-index 9999).

import confetti from "canvas-confetti"

const CONFETTI_COLORS = [
  "#f59e0b", "#fbbf24",   // amber
  "#6366f1", "#8b5cf6",   // purple / indigo
  "#ec4899", "#f472b6",   // pink
  "#10b981", "#34d399",   // green
  "#3b82f6", "#60a5fa",   // blue
  "#f97316", "#fb923c",   // orange
  "#ef4444",              // red
]

export function fireCelebrationConfetti() {
  const defaults = {
    colors: CONFETTI_COLORS,
    disableForReducedMotion: true,
    zIndex: 9999,
  }

  // Wave 1: two side cannons (left + right), angled inward
  confetti({ ...defaults, particleCount: 50, spread: 65, angle: 60,  origin: { x: 0, y: 0.65 }, startVelocity: 50 })
  confetti({ ...defaults, particleCount: 50, spread: 65, angle: 120, origin: { x: 1, y: 0.65 }, startVelocity: 50 })

  // Wave 2 (200ms later): center burst upward
  setTimeout(() => {
    confetti({ ...defaults, particleCount: 60, spread: 90, origin: { x: 0.5, y: 0.7 }, startVelocity: 45 })
  }, 200)

  // Wave 3 (800ms): gentle drifting pieces from center
  setTimeout(() => {
    confetti({ ...defaults, particleCount: 30, spread: 140, origin: { x: 0.5, y: 0.5 }, startVelocity: 25, gravity: 0.6, scalar: 1.2, ticks: 300 })
  }, 800)
}
