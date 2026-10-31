import { Image } from "expo-image";
import { router } from "expo-router";
import { useRef, useState } from "react";
import {
  FlatList,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuth } from "../auth/AuthContext";
import { NextArrow } from "../components/NextArrow";
import { PageDots } from "../components/PageDots";
import { images, type Slide, slides } from "../content/onboarding";
import { colors, fonts } from "../theme";

export default function Onboarding() {
  const { width } = useWindowDimensions();
  const list = useRef<FlatList<Slide>>(null);
  const [index, setIndex] = useState(0);
  const { completeOnboarding } = useAuth();

  const next = async () => {
    if (index < slides.length - 1) {
      list.current?.scrollToIndex({ index: index + 1, animated: true });
    } else {
      await completeOnboarding();
      router.replace("/welcome");
    }
  };

  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) =>
    setIndex(Math.round(e.nativeEvent.contentOffset.x / width));

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <FlatList
        ref={list}
        data={slides}
        keyExtractor={(s) => s.key}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={onScroll}
        renderItem={({ item }) => <SlideView slide={item} width={width} />}
      />
      <View style={styles.footer}>
        <PageDots count={slides.length} index={index} />
        <NextArrow onPress={next} label={index === slides.length - 1 ? "Get started" : "Next slide"} />
      </View>
    </SafeAreaView>
  );
}

function SlideView({ slide, width }: { slide: Slide; width: number }) {
  const archW = width * 0.82;
  const archH = archW * (570 / 375);
  return (
    <View style={[styles.slide, { width }]}>
      <View style={{ width: archW, height: archH }}>
        <Image source={slide.arch} style={StyleSheet.absoluteFill} contentFit="fill" />
        {slide.variant === "emblem" && (
          <View style={styles.emblemWrap}>
            <Image source={images.emblem} style={{ width: archW * 0.9, height: archW * 0.95 }} contentFit="contain" />
            <Text style={styles.emblemTitle}>{slide.title}</Text>
          </View>
        )}
        {slide.variant === "avatar" && (
          <>
            <Image source={images.faceSikh} style={[styles.ghost, { left: -6, top: archH * 0.22, width: archW * 0.36, height: archW * 0.36 }]} />
            <Image source={images.faceHijab} style={[styles.ghost, { right: -10, top: archH * 0.16, width: archW * 0.4, height: archW * 0.4 }]} />
            <Image source={images.cow} style={{ position: "absolute", left: -archW * 0.08, top: -archW * 0.12, width: archW * 0.34, height: archW * 0.31 }} contentFit="contain" />
            <Image source={images.sikhMan} style={{ position: "absolute", bottom: archH * 0.08, alignSelf: "center", width: archW * 0.86, height: archH * 0.78 }} contentFit="contain" />
          </>
        )}
        {slide.variant === "grid" && (
          <View style={styles.grid}>
            <View style={styles.gridTop}>
              <Image source={images.faceBoy} style={{ width: archW * 0.5, height: archW * 0.5, borderRadius: archW * 0.25, backgroundColor: "#E2A4F0" }} contentFit="cover" />
              <View style={{ gap: 10 }}>
                {images.faces.slice(0, 2).map((f: number, i: number) => (
                  <Image key={i} source={f} style={{ width: archW * 0.22, height: archW * 0.22 }} contentFit="contain" />
                ))}
              </View>
            </View>
            <View style={styles.gridRow}>
              {images.faces.slice(2).map((f: number, i: number) => (
                <Image key={i} source={f} style={{ width: archW * 0.24, height: archW * 0.24 }} contentFit="contain" />
              ))}
            </View>
          </View>
        )}
      </View>
      {slide.variant !== "emblem" && <Text style={styles.title}>{slide.title}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  slide: { alignItems: "center", paddingTop: 24 },
  emblemWrap: { flex: 1, alignItems: "center", justifyContent: "center", paddingTop: 12 },
  emblemTitle: { fontFamily: fonts.display, fontSize: 26, color: colors.text, marginTop: -8 },
  ghost: { position: "absolute", opacity: 0.35 },
  title: { fontFamily: fonts.display, fontSize: 30, color: colors.text, marginTop: 20 },
  grid: { flex: 1, justifyContent: "center", paddingHorizontal: 18, gap: 14 },
  gridTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  gridRow: { flexDirection: "row", justifyContent: "space-between" },
  footer: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 28, paddingBottom: 20 },
});
