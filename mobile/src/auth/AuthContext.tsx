import * as SecureStore from "expo-secure-store";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setAuthToken, setUnauthorizedHandler } from "../api/client";
import { authApi } from "../api/endpoints";
import type { TokenResponse, User } from "../api/types";

const KEYS = { token: "cs.token", user: "cs.user", onboarded: "cs.onboarded", language: "cs.language" };

interface AuthState {
  ready: boolean;
  token: string | null;
  user: User | null;
  onboarded: boolean;
  language: string;
}

interface AuthContextValue extends AuthState {
  signIn: (res: TokenResponse) => Promise<void>;
  signOut: () => Promise<void>;
  completeOnboarding: () => Promise<void>;
  setLanguage: (lang: string) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    ready: false,
    token: null,
    user: null,
    onboarded: false,
    language: "en",
  });

  useEffect(() => {
    (async () => {
      const [token, userJson, onboarded, language] = await Promise.all([
        SecureStore.getItemAsync(KEYS.token),
        SecureStore.getItemAsync(KEYS.user),
        SecureStore.getItemAsync(KEYS.onboarded),
        SecureStore.getItemAsync(KEYS.language),
      ]);
      setAuthToken(token);
      setState({
        ready: true,
        token,
        user: userJson ? (JSON.parse(userJson) as User) : null,
        onboarded: onboarded === "1",
        language: language ?? "en",
      });
    })();
  }, []);

  const signOut = useCallback(async () => {
    setAuthToken(null);
    await Promise.all([SecureStore.deleteItemAsync(KEYS.token), SecureStore.deleteItemAsync(KEYS.user)]);
    setState((s) => ({ ...s, token: null, user: null }));
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => void signOut());
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  const signIn = useCallback(async (res: TokenResponse) => {
    setAuthToken(res.accessToken);
    await Promise.all([
      SecureStore.setItemAsync(KEYS.token, res.accessToken),
      SecureStore.setItemAsync(KEYS.user, JSON.stringify(res.user)),
      SecureStore.setItemAsync(KEYS.language, res.user.language),
    ]);
    setState((s) => ({ ...s, token: res.accessToken, user: res.user, language: res.user.language }));
  }, []);

  const completeOnboarding = useCallback(async () => {
    await SecureStore.setItemAsync(KEYS.onboarded, "1");
    setState((s) => ({ ...s, onboarded: true }));
  }, []);

  const setLanguage = useCallback(async (language: string) => {
    await SecureStore.setItemAsync(KEYS.language, language);
    setState((s) => ({ ...s, language }));
  }, []);

  const refreshUser = useCallback(async () => {
    const user = await authApi.me();
    await SecureStore.setItemAsync(KEYS.user, JSON.stringify(user));
    setState((s) => ({ ...s, user }));
  }, []);

  const value = useMemo(
    () => ({ ...state, signIn, signOut, completeOnboarding, setLanguage, refreshUser }),
    [state, signIn, signOut, completeOnboarding, setLanguage, refreshUser],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
