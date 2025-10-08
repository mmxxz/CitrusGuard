import { RiskAlert, CaseFile, WeatherData, Orchard, User } from '../types';

export const mockUser: User = {
  id: 'user-1',
  name: '王先生',
  currentOrchardId: 'orchard-1',
};

export const mockOrchard: Orchard = {
  id: 'orchard-1',
  name: '阳光果园',
  healthScore: 87,
  hasNewAlerts: true,
};

export const mockWeather: WeatherData = {
  condition: 'sunny',
  temperature: 24,
  humidity: 65,
};

export const mockAlerts: RiskAlert[] = [
  {
    id: 'alert-1',
    name: '柑橘溃疡病',
    level: 'high',
    confidence: 85,
    reason: '基于未来72小时高温高湿天气预报',
    type: 'disease'
  },
  {
    id: 'alert-2', 
    name: '红蜘蛛',
    level: 'medium',
    confidence: 70,
    reason: '根据近期叶片黄化历史记录',
    type: 'pest'
  },
  {
    id: 'alert-3',
    name: '缺氮症',
    level: 'low',
    confidence: 60,
    reason: '土壤检测数据异常',
    type: 'deficiency'
  }
];

export const mockCases: CaseFile[] = [
  {
    id: 'case-1',
    date: new Date('2024-01-15').toISOString(),
    diagnosis: '柑橘红蜘蛛',
    status: 'resolved',
    severity: 'medium',
    treatment: '喷施阿维菌素1000倍液',
    effectiveness: 8
  },
  {
    id: 'case-2',
    date: new Date('2024-01-10').toISOString(),
    diagnosis: '柑橘溃疡病',
    status: 'active',
    severity: 'high'
  }
];

export const mockAiDailyBriefing = '早上好！今天湿度较高，请重点关注溃疡病的潜在风险。建议加强果园通风。';
