/**
 * 环境风险展示与 backend/app/services/fuzzy_engine.py 中 CitrusFuzzyEngine._risk_level 对齐：
 * - 高风险: score >= 65
 * - 中风险: 35 <= score < 65
 * - 低风险: score < 35
 */
export const FUZZY_RISK_HIGH_MIN = 65;
export const FUZZY_RISK_MEDIUM_MIN = 35;

export type FuzzyRiskLevel = 'high' | 'medium' | 'low';

export function fuzzyRiskLevel(score: number): FuzzyRiskLevel {
  if (score >= FUZZY_RISK_HIGH_MIN) return 'high';
  if (score >= FUZZY_RISK_MEDIUM_MIN) return 'medium';
  return 'low';
}

/** 进度条颜色（0–100 分） */
export function riskBarColorClass(score: number): string {
  const lv = fuzzyRiskLevel(score);
  if (lv === 'high') return 'bg-red-500';
  if (lv === 'medium') return 'bg-yellow-500';
  return 'bg-green-500';
}

export function riskLevelLabelZh(score: number): string {
  const lv = fuzzyRiskLevel(score);
  if (lv === 'high') return '高风险';
  if (lv === 'medium') return '中风险';
  return '低风险';
}
