import { Redirect } from "expo-router";
import { Tabs } from "expo-router/js-tabs";
import { useAuth } from "../../auth/AuthContext";
import { TabBar } from "../../components/TabBar";
import { TABS } from "../../content/tabs";
import { duration, easing } from "../../motion";

// Quick cross-fade between tabs (native driver; a dissolve, so it stays on under reduce motion).
const FADE = {
  animation: "fade",
  transitionSpec: { animation: "timing", config: { duration: duration.fast, easing: easing.move } },
} as const;

export default function TabsLayout() {
  const { token, user } = useAuth();
  if (!token || !user) return <Redirect href="/welcome" />;
  if (!user.emailVerified) return <Redirect href="/verify" />;

  return (
    <Tabs
      screenOptions={{ headerShown: false, ...FADE }}
      tabBar={({ state, navigateToTab }) => {
        const active = state.routes[state.index]?.name ?? "explore";
        const select = (name: string) => {
          const route = state.routes.find((r) => r.name === name);
          if (route) navigateToTab(route.key);
        };
        return <TabBar items={TABS} activeName={active} onSelect={select} />;
      }}
    >
      {TABS.map((t) => (
        // The map renders into a GLSurfaceView on Android, which ignores view opacity: fading it would flicker.
        <Tabs.Screen key={t.name} name={t.name} options={t.name === "explore" ? { animation: "none" } : undefined} />
      ))}
    </Tabs>
  );
}
