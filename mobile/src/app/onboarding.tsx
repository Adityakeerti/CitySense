import { Image } from "expo-image";
import { router } from "expo-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Animated,
  FlatList,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  Pressable,
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
import { introFor, isReducedMotion, timing, useReducedMotion } from "../motion";
import { splashRemaining } from "../motion/splash";
import { colors, fonts } from "../theme";

type IntroStyles = ReturnType<typeof useIntro>["styles"];

/** Once per app launch: re-mounting onboarding in the same session (or any re-render) shows it settled. */
let introPlayed = false;
/** Upper bound on waiting for the emblem to decode before the sequence starts anyway. */
const ARTWORK_WAIT_MS = 250;

/**
 * Frame 1 opening sequence (backdrop, emblem, wordmark, controls; timings in motion/tokens `intro`).
 * Opacity and transform only, on the native driver. Never blocks input: `finish()` snaps everything
 * to rest and is called on the first swipe or tap.
 */
function useIntro() {
  const play = useRef(!introPlayed).current;
  const reduced = useReducedMotion();
  const v = useRef({
    backdrop: new Animated.Value(play ? 0 : 1),
    artwork: new Animated.Value(play ? 0 : 1),
    title: new Animated.Value(play ? 0 : 1),
    controls: new Animated.Value(play ? 0 : 1),
  }).current;
  const anim = useRef<Animated.CompositeAnimation | null>(null);
  const done = useRef(!play);
  // Movement is fixed when the sequence starts, so a reduce-motion change mid-way cannot make content jump.
  const [stages] = useState(() => introFor(isReducedMotion()));

  const finish = useCallback(() => {
    if (done.current) return;
    done.current = true;
    anim.current?.stop();
    v.backdrop.setValue(1);
    v.artwork.setValue(1);
    v.title.setValue(1);
    v.controls.setValue(1);
  }, [v]);

  const start = useCallback(() => {
    if (done.current || anim.current) return;
    introPlayed = true;
    // On a cold start the native splash is still dissolving over this screen: begin once it has cleared so
    // the backdrop stage is actually seen. Under reduce motion nothing waits.
    const lead = isReducedMotion() ? 0 : splashRemaining();
    anim.current = Animated.parallel(
      (["backdrop", "artwork", "title", "controls"] as const).map((k) =>
        // The backdrop is an in-place dissolve: the symmetric `move` curve spreads it over its full 300 ms.
        // (The front-loaded `enter` curve finishes 90% of a fade in about half its time, so the arch read as a pop.)
        timing(v[k], 1, {
          duration: stages[k].duration,
          delay: lead + stages[k].delay,
          curve: k === "backdrop" ? "move" : "enter",
        }),
      ),
    );
    anim.current.start(({ finished }) => {
      if (finished) done.current = true;
    });
  }, [v, stages]);

  useEffect(() => {
    if (!play) return;
    const fallback = setTimeout(start, ARTWORK_WAIT_MS);
    return () => {
      clearTimeout(fallback);
      anim.current?.stop();
    };
    // Mount-only by design.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Turning reduce motion on while the sequence is running settles it immediately. If it was already on
  // when the screen opened, `stages` is the reduced cross-fade and must be allowed to run.
  const startedReduced = useRef(isReducedMotion()).current;
  useEffect(() => {
    if (reduced && !startedReduced) finish();
  }, [reduced, startedReduced, finish]);

  const styles = useMemo(() => {
    const rise = (value: Animated.Value, offset: number) =>
      value.interpolate({ inputRange: [0, 1], outputRange: [offset, 0] });
    const scaleFrom = (value: Animated.Value, s: number) =>
      value.interpolate({ inputRange: [0, 1], outputRange: [s, 1] });
    return {
      backdrop: { opacity: v.backdrop },
      artwork: { opacity: v.artwork, transform: [{ scale: scaleFrom(v.artwork, stages.artwork.fromScale) }] },
      title: { opacity: v.title, transform: [{ translateY: rise(v.title, stages.title.fromOffset) }] },
      dots: { opacity: v.controls },
      arrow: { opacity: v.controls, transform: [{ scale: scaleFrom(v.controls, stages.controls.fromScale) }] },
    };
  }, [v, stages]);

  return { styles, start, finish };
}

export default function Onboarding() {
  const { width } = useWindowDimensions();
  const list = useRef<FlatList<Slide>>(null);
  const [index, setIndex] = useState(0);
  const { completeOnboarding } = useAuth();
  const intro = useIntro();

  const finish = async () => {
    await completeOnboarding();
    router.replace("/welcome");
  };

  const next = async () => {
    intro.finish();
    const nextIndex = index + 1;
    if (nextIndex < slides.length) {
      // Update now: momentum-end events don't fire for programmatic scrolls on iOS, and the dots
      // should move with the tap rather than after the slide settles.
      setIndex(nextIndex);
      const animated = !isReducedMotion();
      try {
        list.current?.scrollToOffset({ offset: nextIndex * width, animated });
      } catch {
        list.current?.scrollToIndex({ index: nextIndex, animated });
      }
    } else {
      await finish();
    }
  };

  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const newIdx = Math.round(e.nativeEvent.contentOffset.x / width);
    if (newIdx !== index && newIdx >= 0 && newIdx < slides.length) {
      setIndex(newIdx);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <View style={{ flex: 1 }} />
        <Pressable onPress={finish} hitSlop={10} style={styles.skipBtn}>
          <Text style={styles.skipText}>Skip</Text>
        </Pressable>
      </View>
      <FlatList
        ref={list}
        data={slides}
        keyExtractor={(s) => s.key}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={onScroll}
        scrollEventThrottle={16}
        onMomentumScrollEnd={onScroll}
        getItemLayout={(_, i) => ({
          length: width,
          offset: width * i,
          index: i,
        })}
        onScrollToIndexFailed={(info) => {
          list.current?.scrollToOffset({ offset: info.index * width, animated: !isReducedMotion() });
        }}
        // A swipe means the user is moving on: settle the intro instead of animating under their finger.
        onScrollBeginDrag={intro.finish}
        renderItem={({ item, index: i }) => (
          <SlideView
            slide={item}
            width={width}
            intro={i === 0 ? intro.styles : undefined}
            onArtworkLoad={i === 0 ? intro.start : undefined}
          />
        )}
      />
      <View style={styles.footer}>
        <Animated.View style={intro.styles.dots}>
          <PageDots count={slides.length} index={index} />
        </Animated.View>
        {/* Pressable from the first frame, even while still fading in. */}
        <Animated.View style={intro.styles.arrow}>
          <NextArrow onPress={next} label={index === slides.length - 1 ? "Get started" : "Next slide"} />
        </Animated.View>
      </View>
    </SafeAreaView>
  );
}

function SlideView({
  slide,
  width,
  intro,
  onArtworkLoad,
}: {
  slide: Slide;
  width: number;
  /** Frame 1 only: entrance styles. Wrappers keep each element's own size, so nothing shifts. */
  intro?: IntroStyles;
  onArtworkLoad?: () => void;
}) {
  const archW = width * 0.82;
  const archH = archW * (570 / 375);
  return (
    <View style={[styles.slide, { width }]}>
      <View style={{ width: archW, height: archH }}>
        <Animated.View style={[StyleSheet.absoluteFill, intro?.backdrop]}>
          <Image source={slide.arch} style={StyleSheet.absoluteFill} contentFit="fill" />
        </Animated.View>
        {slide.variant === "emblem" && (
          <View style={styles.emblemWrap}>
            <Animated.View style={intro?.artwork}>
              <Image
                source={images.emblem}
                style={{ width: archW * 0.9, height: archW * 0.95 }}
                contentFit="contain"
                onLoad={onArtworkLoad}
              />
            </Animated.View>
            <Animated.Text style={[styles.emblemTitle, intro?.title]}>{slide.title}</Animated.Text>
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
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    paddingHorizontal: 24,
    paddingTop: 12,
  },
  skipBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  skipText: {
    fontFamily: fonts.medium,
    fontSize: 14,
    color: colors.textMuted,
  },
  slide: { alignItems: "center", paddingTop: 12 },
  emblemWrap: { flex: 1, alignItems: "center", justifyContent: "center", paddingTop: 12 },
  emblemTitle: { fontFamily: fonts.display, fontSize: 26, color: colors.text, marginTop: -8 },
  ghost: { position: "absolute", opacity: 0.35 },
  title: { fontFamily: fonts.display, fontSize: 30, color: colors.text, marginTop: 20 },
  grid: { flex: 1, justifyContent: "center", paddingHorizontal: 18, gap: 14 },
  gridTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  gridRow: { flexDirection: "row", justifyContent: "space-between" },
  footer: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 28, paddingBottom: 20 },
});
