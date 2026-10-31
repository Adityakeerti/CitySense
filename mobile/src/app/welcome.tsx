import { Image } from "expo-image";
import { router } from "expo-router";
import { StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button } from "../components/Button";
import { images } from "../content/onboarding";
import { colors, fonts } from "../theme";

export default function Welcome() {
  const { width } = useWindowDimensions();
  const archW = width * 0.82;
  const archH = archW * (570 / 375);
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.center}>
        <View style={{ width: archW, height: archH, alignItems: "center", justifyContent: "center" }}>
          <Image source={images.archGreen} style={StyleSheet.absoluteFill} contentFit="fill" />
          <Image source={images.kite} style={{ width: archW * 0.62, height: archW * 0.78 }} contentFit="contain" />
          <Text style={styles.title}>Lets goo .</Text>
        </View>
      </View>
      <View style={styles.actions}>
        <Button title="Sign Up" onPress={() => router.push("/signup")} style={styles.btn} compact />
        <Button title="Login" variant="outline" onPress={() => router.push("/login")} style={styles.btn} compact />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  title: { fontFamily: fonts.display, fontSize: 30, color: colors.text, marginTop: 8 },
  actions: { flexDirection: "row", gap: 16, paddingHorizontal: 28, paddingBottom: 28 },
  btn: { flex: 1 },
});
