// Core types for VoiceCore AI 2.0

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'agent' | 'manager';
  tenantId: string;
  avatar?: string;
}

export interface Tenant {
  id: string;
  name: string;
  subscriptionTier: 'free' | 'pro' | 'enterprise';
  settings: TenantSettings;
}

export interface TenantSettings {
  theme: 'light' | 'dark';
  language: string;
  timezone: string;
  aiPersonalityId?: string;
}

export interface Call {
  id: string;
  tenantId: string;
  from: string;
  to: string;
  status: 'queued' | 'ringing' | 'in-progress' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  duration?: number;
  recording?: string;
  transcription?: string;
  sentiment?: SentimentData;
}

export interface SentimentData {
  score: number;
  emotion: 'happy' | 'sad' | 'angry' | 'neutral' | 'frustrated';
  confidence: number;
}

export interface CRMContact {
  id: string;
  tenantId: string;
  firstName: string;
  lastName: string;
  email?: string;
  phone?: string;
  company?: string;
  tags: string[];
  customFields: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface CRMLead {
  id: string;
  tenantId: string;
  contactId: string;
  status: 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';
  score: number;
  source: string;
  pipelineStageId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface AIPersonality {
  id: string;
  tenantId: string;
  name: string;
  voiceSettings: VoiceSettings;
  conversationStyle: string;
  knowledgeBase: string[];
}

export interface VoiceSettings {
  language: string;
  voice: string;
  speed: number;
  pitch: number;
}

export interface AnalyticsMetrics {
  totalCalls: number;
  activeCalls: number;
  averageDuration: number;
  successRate: number;
  sentimentScore: number;
  callsByHour: Array<{ hour: number; count: number }>;
  callsByStatus: Record<string, number>;
}

export interface WebSocketMessage {
  type: 'call_update' | 'notification' | 'metrics_update';
  payload: any;
  timestamp: string;
}
