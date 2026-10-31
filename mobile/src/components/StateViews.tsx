import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { colors, fonts } from "../theme";
import { Button } from "./Button";

export function Loading() {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.primary} />
    </View>
  );
}

export function Empty({ title, body, action }: { title: string; body?: string; action?: { label: string; onPress: () => void } }) {
  return (
    <View style={styles.center}>
      <Text style={styles.title}>{title}</Text>
      {body ? <Text style={styles.body}>{body}</Text> : null}
      {action ? <Button title={action.label} onPress={action.onPress} compact style={{ marginTop: 16 }} /> : null}
    </View>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View style={styles.banner}>
      <Text style={styles.bannerText}>{message}</Text>
      {onRetry ? (
        <Text style={styles.retry} onPress={onRetry} accessibilityRole="button">
          Retry
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32 },
  title: { fontFamily: fonts.bold, fontSize: 17, color: colors.text, textAlign: "center" },
  body: { fontFamily: fonts.regular, fontSize: 14, color: colors.textMuted, textAlign: "center", marginTop: 6 },
  banner: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FDECEC",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 12,
  },
  bannerText: { flex: 1, color: colors.danger, fontFamily: fonts.medium, fontSize: 13 },
  retry: { color: colors.primary, fontFamily: fonts.bold, fontSize: 13 },
});
