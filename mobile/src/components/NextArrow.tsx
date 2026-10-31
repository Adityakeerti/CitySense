import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet } from "react-native";

export function NextArrow({ onPress, label = "Next" }: { onPress: () => void; label?: string }) {
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={styles.btn} hitSlop={10}>
      <Ionicons name="chevron-forward" size={20} color="#fff" />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#111",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer" as any,
  },
});
