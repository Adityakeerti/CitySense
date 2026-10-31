export type Role = "CITIZEN" | "ADMIN" | "CREW";

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: Role;
  language: string;
  emailVerified: boolean;
}

export interface TokenResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  user: User;
}

export interface OtpSentResponse {
  email: string;
  codeLength: number;
  expiresInSeconds: number;
  resendAfterSeconds: number;
}

export interface MapConfig {
  styleUrl: string;
  defaultLatitude: number;
  defaultLongitude: number;
  defaultZoom: number;
  minZoom: number;
  maxZoom: number;
  geofenceRadiusMeters: number;
  attribution: string;
}

export interface Place {
  name: string;
  displayName: string;
  latitude: number;
  longitude: number;
  type?: string;
}

export interface Avatar {
  id: string;
  handle: string;
  name: string;
  title: string;
  category: string;
  persona: string;
  intro: string;
  pricing?: string;
  websiteUrl?: string;
  socials: { instagram?: string; threads?: string; x?: string };
  pinImageUrl: string;
  heroImageUrl: string;
  rating: number;
  reviewCount: number;
  likeCount: number;
  latitude: number;
  longitude: number;
  distanceMeters?: number;
  saved: boolean;
  liked: boolean;
}

export type ChatIntent = "INTRO" | "PRICING" | "WEBSITE";

export interface AvatarChatResponse {
  sessionId: string;
  reply: string;
  intent?: ChatIntent;
  link?: string;
  sources?: string[];
  timestamp: string;
}

export interface ToggleResponse {
  avatarId: string;
  active: boolean;
  count: number;
}

export interface Complaint {
  id: string;
  trackingId: string;
  citizenName?: string;
  title: string;
  description: string;
  category: string;
  department: string;
  priority: string;
  status: string;
  latitude: number;
  longitude: number;
  escalationLevel: number;
  assignedWorker?: string;
  resolutionNotes?: string;
  resolvedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CityEvent {
  id: string;
  title: string;
  description?: string;
  category: string;
  severity: string;
  latitude: number;
  longitude: number;
  startsAt: string;
  endsAt?: string;
  createdAt: string;
}

export interface Incident {
  id: string;
  type: string;
  title: string;
  summary?: string;
  severity: number;
  urgencyScore: number;
  latitude: number;
  longitude: number;
  status: string;
  observationCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface LiveMessage {
  type: string;
  entityId: string;
  data: unknown;
  timestamp: string;
}
