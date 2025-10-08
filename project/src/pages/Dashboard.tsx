import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Cloud, Sun, CloudRain, Leaf, MessageCircle, FileText, ChevronRight, Settings } from 'lucide-react';
import { useAppStore } from '../lib/store';
import { getCachedOrchardHealth, getCachedOrchardAlerts } from '../services/cache';
import { WeatherData, RiskAlert } from '../types';
import SmartOrchard from '../components/SmartOrchard';
import Spinner from '../components/Spinner';

const Dashboard = () => {
  const navigate = useNavigate();
  const { orchard, user } = useAppStore();
  
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [briefing, setBriefing] = useState('');
  const [riskAlerts, setRiskAlerts] = useState<RiskAlert[]>([]);
  const [healthScore, setHealthScore] = useState(0);
  const [hasNewAlerts, setHasNewAlerts] = useState(false);
  // 移除未使用的 riskDistribution，避免重复渲染和告警
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    console.log('Dashboard useEffect - orchard:', orchard);
    if (orchard) {
      const fetchData = async () => {
        try {
          setIsLoading(true);
          console.log('Fetching dashboard data for orchard:', orchard.id);
          // 使用缓存，避免快速路由切换重复请求
          const [healthRes, alertsRes] = await Promise.all([
            getCachedOrchardHealth(orchard.id),
            getCachedOrchardAlerts(orchard.id)
          ]);
          
          const healthData = healthRes.data.data;
          const weatherData = healthData.current_weather || { temperature: 22, humidity: 60, condition: 'sunny' };
          setWeather(weatherData);
          setBriefing(healthData.ai_daily_briefing);
          setHealthScore(healthData.health_score);
          setHasNewAlerts(healthData.has_new_alerts);
          setRiskAlerts(Array.isArray(alertsRes.data) ? alertsRes.data : []);
          
          console.log('Dashboard data loaded:', {
            weather: weatherData,
            briefing: healthData.ai_daily_briefing,
            healthScore: healthData.health_score,
            riskDistribution: healthData.risk_distribution
          });
        } catch (error) {
          console.error("Failed to fetch dashboard data", error);
          setError(error instanceof Error ? error.message : "Failed to fetch data");
        } finally {
          setIsLoading(false);
        }
      };
      fetchData();
    }
  }, [orchard]);

  const WeatherIcon = () => {
    if (!weather) return null;
    switch (weather.condition) {
      case 'sunny': return <Sun className="w-6 h-6 text-yellow-500" />;
      case 'cloudy': return <Cloud className="w-6 h-6 text-gray-500" />;
      case 'rainy': return <CloudRain className="w-6 h-6 text-blue-500" />;
    }
  };
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600 mb-4">加载失败: {error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  if (!orchard) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-gray-600 mb-4">未找到果园信息</p>
          <button 
            onClick={() => navigate('/orchard-setup')} 
            className="px-4 py-2 bg-green-600 text-white rounded-lg"
          >
            设置果园
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-gradient-to-br from-green-50 to-blue-50 p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="font-bold text-2xl text-gray-800">{orchard?.name}</h1>
          <p className="text-gray-600">你好, {user?.name}</p>
        </div>
        <button onClick={() => navigate('/edit-orchard')} className="p-2 bg-white rounded-full shadow-sm">
          <Settings className="w-6 h-6 text-gray-600" />
        </button>
      </div>

      <div className="flex justify-between items-center bg-white/80 backdrop-blur-sm rounded-xl p-3 shadow-sm">
        <div className="flex items-center gap-2">
          <WeatherIcon />
          <span className="text-lg font-medium">{weather?.temperature || '--'}°C</span>
          <span className="text-sm text-gray-600">{weather?.humidity || '--'}%</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold text-green-600">{healthScore}%</span>
          <span className="text-sm text-gray-600">健康度</span>
          {hasNewAlerts && (
            <div 
              className="w-3 h-3 bg-red-500 rounded-full animate-pulse cursor-pointer"
              onClick={() => navigate('/alerts')}
            />
          )}
        </div>
      </div>

      <SmartOrchard 
        healthScore={healthScore}
        riskAlerts={riskAlerts}
        weatherCondition={weather?.condition || 'sunny'}
      />

      

      <div className="mb-6">
        <div className="bg-white rounded-2xl p-4 shadow-lg border border-green-100">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
              <Leaf className="w-5 h-5 text-green-600" />
            </div>
            <div className="flex-1">
              <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">{briefing}</p>
              <p className="text-xs text-gray-500 mt-2">AI农艺师 · 刚刚</p>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <button 
          onClick={() => navigate('/diagnosis')}
          className="w-full bg-green-600 text-white rounded-2xl p-4 flex items-center justify-between shadow-lg active:scale-95 transition-transform"
        >
          <div className="flex items-center gap-3">
            <MessageCircle className="w-6 h-6" />
            <span className="font-semibold">开始诊断</span>
          </div>
          <ChevronRight className="w-5 h-5" />
        </button>
        
        <button 
          onClick={() => navigate('/cases')}
          className="w-full bg-white border border-gray-200 text-gray-700 rounded-2xl p-4 flex items-center justify-between shadow-sm active:scale-95 transition-transform"
        >
          <div className="flex items-center gap-3">
            <FileText className="w-6 h-6" />
            <span className="font-semibold">记录农事</span>
          </div>
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default Dashboard;