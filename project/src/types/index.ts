export interface WeatherData {
  condition: 'sunny' | 'cloudy' | 'rainy';
  temperature: number;
  humidity: number;
}

export interface RiskAlert {
  id: string;
  name: string;
  level: 'high' | 'medium' | 'low';
  confidence: number;
  reason: string;
  type: 'disease' | 'pest' | 'deficiency';
  // 兼容后端新版字段（可选）
  /** 病害/虫害中文名，用于问诊跳转文案等 */
  risk_item?: string;
  title?: string;
  severity?: 'high' | 'medium' | 'low';
  basis?: string[] | string;
  symptoms?: string;
  timestamp?: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  type: 'text' | 'progress' | 'card' | 'clarification' | 'diagnosis_result' | 'diagnosis_report';
  content: string;
  image?: string;
  timestamp: string;
  cardData?: any;
  options?: string[];
  primary_diagnosis?: string;
  confidence?: number;
  secondary_diagnoses?: Array<{
    name: string;
    confidence: number;
  }>;
  prevention_advice?: string;
  treatment_advice?: string;
}

export interface CaseFile {
  id: string;
  date: string;
  diagnosis: string;
  status: 'active' | 'resolved';
  severity: 'high' | 'medium' | 'low';
  treatment?: string;
  effectiveness?: number; // Stored as a number e.g. 8 for 8/10
}

export interface Orchard {
  id: string;
  name: string;
  healthScore: number;
  hasNewAlerts: boolean;
}

export interface OrchardCreate {
  name: string;
  location_latitude?: number;
  location_longitude?: number;
  address_detail?: string;
  main_variety?: string;
  avg_tree_age?: number;
  soil_type?: string;
  last_harvest_date?: string;
}

export interface OrchardUpdate {
  name?: string;
  location_latitude?: number;
  location_longitude?: number;
  address_detail?: string;
  main_variety?: string;
  avg_tree_age?: number;
  soil_type?: string;
  last_harvest_date?: string;
}

export interface User {
  id: string;
  name: string;
  currentOrchardId: string;
}

export interface FarmOperationCreate {
  type: string;
  description: string;
  materials_used: string[];
  operation_date: string; // YYYY-MM-DD
}

export interface DiagnosisResult {
  id: string;
  session_id: string;
  primary_diagnosis: string;
  confidence: number;
  secondary_diagnoses?: Array<{
    name: string;
    confidence: number;
  }>;
  prevention_advice: string;
  treatment_advice: string;
  follow_up_plan: string;
  generated_at: string;
}
