import { DMSerifDisplay_400Regular } from "@expo-google-fonts/dm-serif-display";
import {
  Urbanist_400Regular,
  Urbanist_500Medium,
  Urbanist_600SemiBold,
  Urbanist_700Bold,
} from "@expo-google-fonts/urbanist";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { StyleSheet, Text, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import { config, isConfigured } from "../config";
import { colors } from "../theme";

SplashScreen.preventAutoHideAsync().catch(() => {});

function RootStack() {
  const { ready } = useAuth();
  const [fontsLoaded] = useFonts({
    DMSerifDisplay_400Regular,
    Urbanist_400Regular,
    Urbanist_500Medium,
    Urbanist_600SemiBold,
    Urbanist_700Bold,
  });
  const loaded = ready && fontsLoaded;

  useEffect(() => {
    if (loaded) SplashScreen.hideAsync().catch(() => {});
  }, [loaded]);

  if (!loaded) return null;
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.surface }, animation: "slide_from_right" }}>
      <Stack.Screen name="(tabs)" options={{ animation: "fade" }} />
    </Stack>
  );
}

export default function RootLayout() {
  if (!isConfigured) {
    // Misconfigured build: fail loudly instead of calling a guessed URL.
    return (
      <View style={styles.misconfig}>
        <Text style={styles.title}>App not configured</Text>
        <Text style={styles.body}>
          EXPO_PUBLIC_API_BASE_URL is missing or invalid ("{config.apiBaseUrl}"). Set it in mobile/.env and rebuild.
        </Text>
      </View>
    );
  }
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <StatusBar style="dark" />
        <RootStack />
      </AuthProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  misconfig: { flex: 1, justifyContent: "center", padding: 32, backgroundColor: "#fff" },
  title: { fontSize: 20, fontWeight: "700", marginBottom: 8 },
  body: { fontSize: 15, color: "#555" },
});
