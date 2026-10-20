/**
 * Chart colours (light surface). Categorical slots are used in this fixed order and were
 * checked for colour-blind separation; slot 3 is below 3:1 contrast, so every chart that uses it
 * also ships a table with the same values.
 */
export const CHART = {
  series: ['#2a78d6', '#eb6834', '#1baf7a'] as const,
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  mutedText: '#898781',
  secondaryText: '#52514e',
}
