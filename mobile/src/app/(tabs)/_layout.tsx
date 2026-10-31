import { Redirect } from "expo-router";
import { Tabs } from "expo-router/js-tabs";
import { useAuth } from "../../auth/AuthContext";
import { TabBar } from "../../components/TabBar";
import { TABS } from "../../content/tabs";

export default function TabsLayout() {
  const { token, user } = useAuth();
  if (!token || !user) return <Redirect href="/welcome" />;
  if (!user.emailVerified) return <Redirect href="/verify" />;

  return (
    <Tabs
      screenOptions={{ headerShown: false }}
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
        <Tabs.Screen key={t.name} name={t.name} />
      ))}
    </Tabs>
  );
}
