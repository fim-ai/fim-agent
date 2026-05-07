/**
 * Locale-aware token-count formatter.
 *
 * The billing UI surfaces large token quotas (5,000,000) and small
 * usage counts (823) side-by-side. Rendering everything with a raw
 * thousands-separator clutters card headlines, while a naive `1.0M`
 * loses precision on values like 5,123,000. This helper picks a
 * compact representation that still rounds to one decimal when the
 * value isn't a clean multiple of the unit.
 *
 * Rules:
 *  - >= 1B → "1.5B" or "1B" (drop the decimal when whole)
 *  - >= 1M → "5M" / "5.1M"
 *  - >= 1K → "100K" / "100.5K"
 *  - <  1K → locale-formatted integer (e.g. "999" or "999" depending
 *            on the locale's grouping conventions)
 *
 * The output is intentionally short — designed for table cells and
 * card headlines, not admin INPUT fields where the operator types raw
 * numbers.
 */
export function formatTokens(n: number, locale: string = "en"): string {
  if (!Number.isFinite(n)) return "0"
  const abs = Math.abs(n)

  if (abs >= 1_000_000_000) {
    const v = n / 1_000_000_000
    return `${n % 1_000_000_000 === 0 ? v.toFixed(0) : v.toFixed(1)}B`
  }
  if (abs >= 1_000_000) {
    const v = n / 1_000_000
    return `${n % 1_000_000 === 0 ? v.toFixed(0) : v.toFixed(1)}M`
  }
  if (abs >= 1_000) {
    const v = n / 1_000
    return `${n % 1_000 === 0 ? v.toFixed(0) : v.toFixed(1)}K`
  }
  return n.toLocaleString(locale)
}
