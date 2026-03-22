import type { RiskAlert } from '../types';

/**
 * 从预警卡片解析要在问诊里展示的病害/虫害名称（兼容仅有 title 的旧数据）。
 */
export function riskAlertDisplayName(alert: Partial<RiskAlert> & { risk_item?: string }): string {
  const item = alert.risk_item?.trim();
  if (item) return item;
  const name = alert.name?.trim();
  if (name) return name;
  const title = alert.title?.trim();
  if (title) {
    const m = title.match(/^(.+?)风险预警/);
    if (m?.[1]) return m[1].trim();
    return title.replace(/\s*\([\d.]+%\)\s*$/, '').trim() || title;
  }
  return '当前预警';
}
