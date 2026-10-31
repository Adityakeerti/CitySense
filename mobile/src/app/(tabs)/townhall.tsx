import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { errorMessage } from "../../api/client";
import { civicApi } from "../../api/endpoints";
import type { CityEvent, Complaint } from "../../api/types";
import { Card } from "../../components/Card";
import { ScreenHeader } from "../../components/ScreenHeader";
import { ErrorBanner } from "../../components/StateViews";
import { StatusBadge } from "../../components/StatusBadge";
import { colors, fonts, radius } from "../../theme";
import { timeAgo } from "../../utils/geo";

export default function Townhall() {
  const [mine, setMine] = useState<Complaint[]>([]);
  const [events, setEvents] = useState<CityEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [trackId, setTrackId] = useState("");

  const load = useCallback(async () => {
    setError(null);
    const [m, e] = await Promise.allSettled([civicApi.mine(), civicApi.events()]);
    if (m.status === "fulfilled") setMine(m.value);
    if (e.status === "fulfilled") setEvents(e.value);
    const failed = [m, e].find((r) => r.status === "rejected") as PromiseRejectedResult | undefined;
    if (failed) setError(errorMessage(failed.reason));
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const track = () => {
    const id = trackId.trim().toUpperCase();
    if (id) router.push({ pathname: "/complaint/[trackingId]", params: { trackingId: id } });
  };

  return (
    <View style={styles.fill}>
      <ScreenHeader title="Townhall" subtitle="Report civic issues and follow them to resolution" />
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={async () => {
              setRefreshing(true);
              await load();
              setRefreshing(false);
            }}
          />
        }
        keyboardShouldPersistTaps="handled"
      >
        {error ? <ErrorBanner message={error} onRetry={load} /> : null}

        <Pressable style={styles.report} onPress={() => router.push("/complaint/new")} accessibilityRole="button">
          <View style={styles.reportIcon}>
            <Ionicons name="megaphone" size={22} color="#fff" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.reportTitle}>Report an issue</Text>
            <Text style={styles.reportSub}>Potholes, garbage, water, streetlights…</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color="#fff" />
        </Pressable>

        <Card style={styles.trackCard}>
          <Text style={styles.section}>Track a complaint</Text>
          <View style={styles.trackRow}>
            <TextInput
              value={trackId}
              onChangeText={setTrackId}
              placeholder="Tracking ID, e.g. CS-123456"
              placeholderTextColor="#A6A6B0"
              autoCapitalize="characters"
              style={styles.trackInput}
              onSubmitEditing={track}
              returnKeyType="search"
            />
            <Pressable style={styles.trackBtn} onPress={track} accessibilityLabel="Track">
              <Ionicons name="search" size={18} color="#fff" />
            </Pressable>
          </View>
        </Card>

        <Text style={styles.section}>My complaints</Text>
        {mine.length === 0 ? (
          <Text style={styles.empty}>You haven't filed anything yet.</Text>
        ) : (
          mine.map((c) => (
            <Pressable
              key={c.id}
              style={styles.item}
              onPress={() => router.push({ pathname: "/complaint/[trackingId]", params: { trackingId: c.trackingId } })}
            >
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={styles.itemTitle} numberOfLines={1}>
                  {c.title}
                </Text>
                <Text style={styles.itemSub}>
                  {c.trackingId} · {c.department.replace(/_/g, " ")} · {timeAgo(c.createdAt)}
                </Text>
              </View>
              <StatusBadge value={c.status} />
            </Pressable>
          ))
        )}

        <Text style={styles.section}>Around town</Text>
        {events.length === 0 ? (
          <Text style={styles.empty}>No city events right now.</Text>
        ) : (
          events.map((e) => (
            <View key={e.id} style={styles.item}>
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={styles.itemTitle}>{e.title}</Text>
                {e.description ? (
                  <Text style={styles.itemSub} numberOfLines={2}>
                    {e.description}
                  </Text>
                ) : null}
                <Text style={styles.itemSub}>
                  {e.category.toLowerCase()} · {timeAgo(e.startsAt)}
                </Text>
              </View>
              <StatusBadge value={e.severity} />
            </View>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1, backgroundColor: colors.surface },
  content: { paddingHorizontal: 20, paddingBottom: 32, gap: 12 },
  report: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    padding: 16,
  },
  reportIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: "rgba(255,255,255,0.18)", alignItems: "center", justifyContent: "center" },
  reportTitle: { color: "#fff", fontFamily: fonts.bold, fontSize: 17 },
  reportSub: { color: "rgba(255,255,255,0.85)", fontFamily: fonts.regular, fontSize: 13 },
  trackCard: { padding: 14, gap: 10 },
  trackRow: { flexDirection: "row", gap: 10 },
  trackInput: {
    flex: 1,
    height: 44,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingHorizontal: 12,
    fontFamily: fonts.medium,
    color: colors.text,
  },
  trackBtn: { width: 44, height: 44, borderRadius: radius.sm, backgroundColor: colors.navy, alignItems: "center", justifyContent: "center" },
  section: { fontFamily: fonts.bold, fontSize: 16, color: colors.text, marginTop: 8 },
  empty: { fontFamily: fonts.regular, color: colors.textMuted, fontSize: 14 },
  item: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    padding: 14,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceAlt,
  },
  itemTitle: { fontFamily: fonts.semibold, fontSize: 15, color: colors.text },
  itemSub: { fontFamily: fonts.regular, fontSize: 12, color: colors.textMuted },
});
