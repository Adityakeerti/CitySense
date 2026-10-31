import { StyleSheet, View } from "react-native";
import { colors } from "../theme";

export function PageDots({ count, index }: { count: number; index: number }) {
  return (
    <View style={styles.row} accessibilityLabel={`Page ${index + 1} of ${count}`}>
      {Array.from({ length: count }, (_, i) => (
        <View key={i} style={[styles.dot, i === index ? styles.active : null]} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: 4, alignItems: "center" },
  dot: { width: 8, height: 4, borderRadius: 2, backgroundColor: colors.dotInactive },
  active: { width: 14, backgroundColor: colors.dot },
});
