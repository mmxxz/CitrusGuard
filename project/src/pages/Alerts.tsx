import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Info, BarChart2 } from 'lucide-react';
import { useAppStore } from '../lib/store';
// 保留原始导出引用以兼容类型，但使用缓存版本调用
// import { getOrchardAlerts, getOrchardHealth } from '../services/apiClient';
import { getCachedOrchardAlerts, getCachedOrchardHealth } from '../services/cache';
import { RiskAlert } from '../types';
import Spinner from '../components/Spinner';
import { riskBarColorClass, FUZZY_RISK_MEDIUM_MIN, FUZZY_RISK_HIGH_MIN } from '../lib/riskDisplay';

const Alerts = () => {
  const navigate = useNavigate();
  const { orchard } = useAppStore();
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [riskDistribution, setRiskDistribution] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (orchard) {
      const fetchAlertData = async () => {
        try {
          setIsLoading(true);
          // 使用缓存，避免快速路由切换重复请求
          const [alertsRes, healthRes] = await Promise.all([
            getCachedOrchardAlerts(orchard.id),
            getCachedOrchardHealth(orchard.id),
          ]);
          
          const rawAlerts = alertsRes?.data;
          const parsedAlerts = Array.isArray(rawAlerts)
            ? rawAlerts
            : (Array.isArray(rawAlerts?.data) ? rawAlerts.data : []);
          setAlerts(parsedAlerts);
          setRiskDistribution(healthRes.data.data.risk_distribution || {});

        } catch (error) {
          console.error("Failed to fetch alert data", error);
        } finally {
          setIsLoading(false);
        }
      };
      fetchAlertData();
    }
  }, [orchard]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="min-h-full bg-gray-50">
      <header className="bg-white px-4 py-3 flex items-center shadow-sm sticky top-0 z-10">
        <button onClick={() => navigate('/')} className="p-1">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <h1 className="flex-1 text-center text-lg font-semibold">风险预警中心</h1>
        <div className="w-7"></div>
      </header>

      <main className="p-4 space-y-4">
        {/* 风险分布显示 */}
        {Object.keys(riskDistribution).length > 0 && (
          <section className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <BarChart2 className="w-6 h-6 text-orange-500" />
              <h2 className="font-semibold text-gray-800 text-base">当前主要风险分布</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                分值 0–100，分级与模糊推理引擎一致（≥{FUZZY_RISK_MEDIUM_MIN} 中风险、≥{FUZZY_RISK_HIGH_MIN} 高风险）
              </p>
            </div>
            <div className="space-y-2">
              {Object.entries(riskDistribution)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 3)
                .map(([disease, risk]) => (
                  <div key={disease} className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">{disease}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-200 rounded-full h-2.5">
                        <div 
                          className={`h-2.5 rounded-full ${riskBarColorClass(risk)}`}
                          style={{ width: `${Math.min(Math.max(risk, 0), 100)}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-600 w-12 text-right">
                        {risk.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </section>
        )}

        {/* 风险预警列表 */}
        <section className="space-y-3">
          {Array.isArray(alerts) && alerts.map(alert => (
            <div key={alert.id} className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-gray-800">{alert.title}</h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  alert.severity === 'high' ? 'bg-red-100 text-red-700' :
                  'bg-yellow-100 text-yellow-700'
                }`}>
                  {alert.severity === 'high' ? '高风险' : '中风险'}
                </span>
              </div>
              
              <div className="space-y-3 text-sm">
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="font-semibold text-gray-700 mb-1">预测依据:</p>
                  <p className="text-gray-600 leading-relaxed">
                    {Array.isArray(alert.basis) ? alert.basis.join('; ') : alert.basis}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="font-semibold text-gray-700 mb-1">识别症状:</p>
                  <p className="text-gray-600 leading-relaxed">{alert.symptoms}</p>
                </div>
              </div>

              <div className="flex gap-3 mt-4">
                <button className="flex-1 bg-gray-100 text-gray-700 rounded-xl py-2.5 text-sm font-medium active:bg-gray-200">
                  忽略
                </button>
                <button 
                  type="button"
                  title="打开智能问诊并自动发送一条说明，便于结合田间情况进一步核实该预警"
                  onClick={() => navigate('/diagnosis', { state: { alertToConfirm: alert } })}
                  className="flex-1 bg-green-600 text-white rounded-xl py-2.5 text-sm font-medium active:bg-green-700"
                >
                  问诊核实
                </button>
              </div>
            </div>
          ))}
        </section>
        
        {alerts.length === 0 && !isLoading && (
          <div className="text-center py-10">
            <Info className="mx-auto w-12 h-12 text-gray-400" />
            <p className="mt-4 text-gray-600">当前无中高风险预警</p>
            <p className="text-sm text-gray-500">果园健康状况良好，请继续保持。</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default Alerts;
