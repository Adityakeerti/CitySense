import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { errorMessage } from "../../api/client";
import { civicApi, geoApi } from "../../api/endpoints";
import { useAuth } from "../../auth/AuthContext";
import { AuthHeader } from "../../components/AuthHeader";
import { Button } from "../../components/Button";
import { LinkText } from "../../components/LinkText";
import { ErrorBanner } from "../../components/StateViews";
import { TextField } from "../../components/TextField";
import { useUserLocation } from "../../hooks/useUserLocation";
import { FadeIn } from "../../motion/FadeIn";
import { Tap } from "../../motion/Tap";
import { colors, fonts, radius } from "../../theme";

export default function NewComplaint() {
  const { user } = useAuth();
  const { coords, status, refresh } = useUserLocation();
  const [priorities, setPriorities] = useState<string[]>([]);
  const [priority, setPriority] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    civicApi
      .meta()
      .then((m) => {
        setPriorities(m.priorities);
        // Middle of the configured scale as the default.
        setPriority(m.priorities[Math.floor((m.priorities.length - 1) / 2)] ?? null);
      })
      .catch((e) => setError(errorMessage(e)));
  }, []);

  useEffect(() => {
    if (!coords) return;
    geoApi
      .reverse(coords.latitude, coords.longitude)
      .then((p) => setAddress(p.displayName))
      .catch(() => setAddress(null));
  }, [coords]);

  const submit = async () => {
    if (!title.trim() || !description.trim()) return setError("Add a title and a short description");
    if (!coords) return setError("We need your location to route the complaint to the right ward");
    setBusy(true);
    setError(null);
    try {
      const c = await civicApi.file({
        title: title.trim(),
        description: description.trim(),
        priority: priority ?? undefined,
        latitude: coords.latitude,
        longitude: coords.longitude,
        citizenName: user?.fullName,
      });
      router.replace({ pathname: "/complaint/[trackingId]", params: { trackingId: c.trackingId } });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <AuthHeader title="Report an issue" fallback="/townhall" />
          <TextField label="What's wrong?" placeholder="e.g. Deep pothole near the bus stop" value={title} onChangeText={setTitle} maxLength={255} />
          <TextField
            label="Details"
            placeholder="Describe the problem and any landmark"
            value={description}
            onChangeText={setDescription}
            multiline
            style={{ height: 110, paddingTop: 12, textAlignVertical: "top" }}
          />

          {priorities.length > 0 && (
            // Priorities come from core after the form is up; ease them in rather than pushing content down abruptly.
            <FadeIn>
              <Text style={styles.label}>Priority</Text>
              <View style={styles.chips}>
                {priorities.map((p) => (
                  <Tap
                    key={p}
                    onPress={() => setPriority(p)}
                    style={[styles.chip, priority === p && styles.chipActive]}
                    accessibilityRole="radio"
                    accessibilityState={{ selected: priority === p }}
                  >
                    <Text style={[styles.chipText, priority === p && styles.chipTextActive]}>{p.toLowerCase()}</Text>
                  </Tap>
                ))}
              </View>
            </FadeIn>
          )}

          <Text style={styles.label}>Location</Text>
          <View style={styles.location}>
            <Ionicons name="location" size={18} color={colors.primary} />
            <Text style={styles.locationText} numberOfLines={2}>
              {coords
                ? (address ?? `${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`)
                : status === "pending"
                  ? "Finding your location…"
                  : "Location unavailable"}
            </Text>
            {!coords && status !== "pending" ? (
              <LinkText style={styles.retry} onPress={() => void refresh()}>
                Retry
              </LinkText>
            ) : null}
          </View>
          <Text style={styles.hint}>The department is picked automatically from your description.</Text>

          {error ? <ErrorBanner message={error} /> : null}
          <Button title="Submit complaint" onPress={submit} loading={busy} style={{ marginTop: 12 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  content: { paddingHorizontal: 24, paddingBottom: 32 },
  label: { fontFamily: fonts.medium, fontSize: 14, color: colors.text, marginBottom: 8 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 16 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: fonts.medium, color: colors.text, textTransform: "capitalize" },
  chipTextActive: { color: "#fff" },
  location: { flexDirection: "row", alignItems: "center", gap: 8, padding: 12, borderRadius: radius.sm, backgroundColor: colors.surfaceAlt },
  locationText: { flex: 1, fontFamily: fonts.regular, color: colors.text, fontSize: 13 },
  retry: { fontFamily: fonts.bold, color: colors.primary },
  hint: { fontFamily: fonts.regular, color: colors.textMuted, fontSize: 12, marginTop: 8, marginBottom: 8 },
});
