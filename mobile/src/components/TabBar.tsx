import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { colors, fonts } from "../theme";

export interface TabItem {
  name: string;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  iconActive: keyof typeof Ionicons.glyphMap;
}

/** Bottom bar from the mockup: icon + label, active tab gets a soft blue pill behind the icon. */
export function TabBar({
  items,
  activeName,
  onSelect,
}: {
  items: TabItem[];
  activeName: string;
  onSelect: (name: string) => void;
}) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 8) }]}>
      {items.map((t) => {
        const active = t.name === activeName;
        return (
          <Pressable
            key={t.name}
            style={styles.item}
            onPress={() => onSelect(t.name)}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            accessibilityLabel={t.label}
          >
            <View style={[styles.pill, active && styles.pillActive]}>
              <Ionicons name={active ? t.iconActive : t.icon} size={20} color={active ? colors.tabActive : "#4A4A55"} />
            </View>
            <Text style={[styles.label, active && styles.labelActive]}>{t.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    backgroundColor: "#F7F8FC",
    paddingTop: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  item: { flex: 1, alignItems: "center", gap: 2 },
  pill: { width: 52, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  pillActive: { backgroundColor: colors.tabActiveBg },
  label: { fontFamily: fonts.medium, fontSize: 11, color: "#4A4A55" },
  labelActive: { color: colors.tabActive, fontFamily: fonts.bold },
});
