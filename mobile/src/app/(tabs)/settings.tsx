import { Ionicons } from "@expo/vector-icons";
import { Image } from "expo-image";
import { router } from "expo-router";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useAuth } from "../../auth/AuthContext";
import { Card } from "../../components/Card";
import { ScreenHeader } from "../../components/ScreenHeader";
import { config } from "../../config";
import { images } from "../../content/onboarding";
import { colors, fonts, radius } from "../../theme";

/** Chat reply languages the core agent supports. */
const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
];

export default function Settings() {
  const { user, language, setLanguage, signOut } = useAuth();
  if (!user) return null;

  const logout = () =>
    Alert.alert("Log out?", "You'll need to sign in again.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Log out",
        style: "destructive",
        onPress: async () => {
          await signOut();
          router.replace("/welcome");
        },
      },
    ]);

  return (
    <View style={styles.fill}>
      <ScreenHeader title="Settings" />
      <ScrollView contentContainerStyle={styles.content}>
        <Card style={styles.profile}>
          <Image source={images.faceBoy} style={styles.photo} contentFit="cover" />
          <View style={{ flex: 1 }}>
            <Text style={styles.name}>{user.fullName}</Text>
            <Text style={styles.email}>{user.email}</Text>
            <View style={styles.badges}>
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{user.role.toLowerCase()}</Text>
              </View>
              {user.emailVerified ? (
                <View style={[styles.badge, { backgroundColor: "#E5F6EC" }]}>
                  <Ionicons name="checkmark-circle" size={12} color={colors.success} />
                  <Text style={[styles.badgeText, { color: colors.success }]}>verified</Text>
                </View>
              ) : null}
            </View>
          </View>
        </Card>

        <Text style={styles.section}>Chat language</Text>
        <View style={styles.segment}>
          {LANGUAGES.map((l) => (
            <Pressable
              key={l.code}
              style={[styles.segBtn, language === l.code && styles.segActive]}
              onPress={() => setLanguage(l.code)}
              accessibilityRole="radio"
              accessibilityState={{ selected: language === l.code }}
            >
              <Text style={[styles.segText, language === l.code && styles.segTextActive]}>{l.label}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.section}>About</Text>
        <Card style={{ padding: 0 }}>
          <Row icon="server-outline" label="Server" value={config.apiBaseUrl} />
          <Row icon="map-outline" label="Map data" value="© OpenStreetMap contributors" />
        </Card>

        <Pressable style={styles.logout} onPress={logout} accessibilityRole="button">
          <Ionicons name="log-out-outline" size={20} color={colors.danger} />
          <Text style={styles.logoutText}>Log out</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}

function Row({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Ionicons name={icon} size={18} color={colors.textMuted} />
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue} numberOfLines={1}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1, backgroundColor: colors.surface },
  content: { paddingHorizontal: 20, paddingBottom: 40, gap: 12 },
  profile: { flexDirection: "row", alignItems: "center", gap: 16 },
  photo: { width: 64, height: 64, borderRadius: 32, backgroundColor: "#E2A4F0" },
  name: { fontFamily: fonts.bold, fontSize: 18, color: colors.text },
  email: { fontFamily: fonts.regular, fontSize: 13, color: colors.textMuted },
  badges: { flexDirection: "row", gap: 6, marginTop: 6 },
  badge: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: colors.surfaceAlt, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  badgeText: { fontFamily: fonts.semibold, fontSize: 11, color: colors.textMuted },
  section: { fontFamily: fonts.bold, fontSize: 15, color: colors.text, marginTop: 8 },
  segment: { flexDirection: "row", backgroundColor: colors.surfaceAlt, borderRadius: radius.md, padding: 4 },
  segBtn: { flex: 1, height: 40, alignItems: "center", justifyContent: "center", borderRadius: radius.sm },
  segActive: { backgroundColor: colors.surface, elevation: 1, shadowColor: "#000", shadowOpacity: 0.06, shadowRadius: 4 },
  segText: { fontFamily: fonts.medium, color: colors.textMuted },
  segTextActive: { color: colors.primary, fontFamily: fonts.bold },
  row: { flexDirection: "row", alignItems: "center", gap: 10, paddingHorizontal: 16, paddingVertical: 14 },
  rowLabel: { fontFamily: fonts.medium, color: colors.text },
  rowValue: { flex: 1, textAlign: "right", fontFamily: fonts.regular, color: colors.textMuted, fontSize: 13 },
  logout: { flexDirection: "row", gap: 8, alignItems: "center", justifyContent: "center", marginTop: 16, height: 48, borderRadius: radius.sm, borderWidth: 1, borderColor: "#F3C9C9" },
  logoutText: { fontFamily: fonts.bold, color: colors.danger },
});
