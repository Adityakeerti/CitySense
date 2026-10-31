import { request } from "./client";
import type {
  Avatar,
  AvatarChatResponse,
  ChatIntent,
  CityEvent,
  Complaint,
  Incident,
  MapConfig,
  OtpSentResponse,
  Place,
  ToggleResponse,
  TokenResponse,
  User,
} from "./types";

export const authApi = {
  login: (email: string, password: string) =>
    request<TokenResponse>("POST", "/api/auth/login", { body: { email, password }, auth: false }),
  register: (body: { email: string; password: string; fullName: string; language?: string }) =>
    request<TokenResponse>("POST", "/api/auth/register", { body, auth: false }),
  sendOtp: (email: string) => request<OtpSentResponse>("POST", "/api/auth/otp/send", { body: { email }, auth: false }),
  verifyOtp: (email: string, code: string) =>
    request<TokenResponse>("POST", "/api/auth/otp/verify", { body: { email, code }, auth: false }),
  me: () => request<User>("GET", "/api/auth/me"),
  forgotPassword: (email: string) =>
    request<OtpSentResponse>("POST", "/api/auth/password/forgot", { body: { email }, auth: false }),
  resetPassword: (email: string, code: string, newPassword: string) =>
    request<TokenResponse>("POST", "/api/auth/password/reset", { body: { email, code, newPassword }, auth: false }),
};

export const geoApi = {
  config: () => request<MapConfig>("GET", "/api/geo/config", { auth: false }),
  geocode: (q: string, near?: { lat: number; lng: number }) =>
    request<{ places: Place[] }>("GET", "/api/geo/geocode", { query: { q, limit: 5, lat: near?.lat, lng: near?.lng } }),
  reverse: (lat: number, lng: number) => request<Place>("GET", "/api/geo/reverse", { query: { lat, lng } }),
};

export const avatarApi = {
  nearby: (lat: number, lng: number, radiusMeters: number) =>
    request<Avatar[]>("GET", "/api/avatars", { query: { lat, lng, radiusMeters } }),
  search: (q: string, near?: { lat: number; lng: number }) =>
    request<Avatar[]>("GET", "/api/avatars", { query: { q, lat: near?.lat, lng: near?.lng, radiusMeters: near ? 50000 : undefined } }),
  get: (id: string) => request<Avatar>("GET", `/api/avatars/${id}`),
  saved: () => request<Avatar[]>("GET", "/api/avatars/saved"),
  setSaved: (id: string, on: boolean) => request<ToggleResponse>(on ? "PUT" : "DELETE", `/api/avatars/${id}/save`),
  setLiked: (id: string, on: boolean) => request<ToggleResponse>(on ? "PUT" : "DELETE", `/api/avatars/${id}/like`),
  chat: (id: string, body: { message?: string; intent?: ChatIntent; language?: string; sessionId?: string }) =>
    request<AvatarChatResponse>("POST", `/api/avatars/${id}/chat`, { body }),
};

export const civicApi = {
  meta: () => request<{ priorities: string[]; escalationLadder: string[] }>("GET", "/api/complaints/meta"),
  mine: () => request<Complaint[]>("GET", "/api/complaints/mine"),
  track: (trackingId: string) => request<Complaint>("GET", `/api/complaints/${encodeURIComponent(trackingId)}`),
  file: (body: {
    title: string;
    description: string;
    category?: string;
    priority?: string;
    latitude: number;
    longitude: number;
    citizenName?: string;
  }) => request<Complaint>("POST", "/api/complaints", { body }),
  events: () => request<CityEvent[]>("GET", "/api/city-events"),
};

export const incidentApi = {
  list: () => request<Incident[]>("GET", "/api/incidents"),
};
