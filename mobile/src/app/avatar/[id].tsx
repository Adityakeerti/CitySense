import { FontAwesome6, Ionicons } from "@expo/vector-icons";
import { Image } from "expo-image";
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  KeyboardAvoidingView,
  Linking,
  Platform,
  ScrollView,
  type ScrollViewInstance,
  Share,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { errorMessage } from "../../api/client";
import { avatarApi } from "../../api/endpoints";
import type { Avatar, ChatIntent } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { LinkText } from "../../components/LinkText";
import { ErrorBanner, Loading } from "../../components/StateViews";
import { TabBar } from "../../components/TabBar";
import { TABS } from "../../content/tabs";
import { absoluteUrl } from "../../config";
import { images } from "../../content/onboarding";
import { duration, isReducedMotion, timing } from "../../motion";
import { FadeIn } from "../../motion/FadeIn";
import { Tap } from "../../motion/Tap";
import { colors, fonts, radius } from "../../theme";

interface Message {
  id: string;
  from: "me" | "avatar";
  text: string;
  link?: string;
  sources?: string[];
}

const CHIPS: { intent: ChatIntent; label: string; icon: keyof typeof Ionicons.glyphMap; needs?: keyof Avatar }[] = [
  { intent: "INTRO", label: "Introduce yourself?", icon: "hand-left-outline" },
  { intent: "PRICING", label: "Pricing", icon: "pricetag-outline" },
  { intent: "WEBSITE", label: "Official Website", icon: "globe-outline", needs: "websiteUrl" },
];

export default function AvatarScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const { language } = useAuth();
  const [avatar, setAvatar] = useState<Avatar | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const session = useRef<string | undefined>(undefined);
  const scroll = useRef<ScrollViewInstance>(null);
  // The portrait recedes once a conversation starts, so the thread stays readable over it.
  const heroOpacity = useRef(new Animated.Value(1)).current;
  const chatting = messages.length > 0;

  useEffect(() => {
    timing(heroOpacity, chatting ? 0.35 : 1, { duration: duration.base, curve: "move" }).start();
  }, [chatting, heroOpacity]);

  const load = useCallback(async () => {
    setError(null);
    try {
      setAvatar(await avatarApi.get(id));
    } catch (e) {
      setError(errorMessage(e));
    }
  }, [id]);

  useEffect(() => {
    setAvatar(null);
    setMessages([]);
    session.current = undefined;
    void load();
  }, [load]);

  const ask = async (opts: { message?: string; intent?: ChatIntent; label: string }) => {
    if (!avatar || sending) return;
    setMessages((m) => [...m, { id: `${Date.now()}-me`, from: "me", text: opts.label }]);
    setSending(true);
    try {
      const res = await avatarApi.chat(avatar.id, {
        message: opts.message,
        intent: opts.intent,
        language,
        sessionId: session.current,
      });
      session.current = res.sessionId;
      setMessages((m) => [...m, { id: `${Date.now()}-av`, from: "avatar", text: res.reply, link: res.link, sources: res.sources }]);
    } catch (e) {
      setMessages((m) => [...m, { id: `${Date.now()}-err`, from: "avatar", text: `⚠️ ${errorMessage(e)}` }]);
    } finally {
      setSending(false);
    }
  };

  const send = () => {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    void ask({ message: text, label: text });
  };

  // Optimistic toggle; core returns the authoritative count.
  const toggle = async (kind: "liked" | "saved") => {
    if (!avatar) return;
    const next = !avatar[kind];
    setAvatar({ ...avatar, [kind]: next, likeCount: kind === "liked" ? avatar.likeCount + (next ? 1 : -1) : avatar.likeCount });
    try {
      const res = kind === "liked" ? await avatarApi.setLiked(avatar.id, next) : await avatarApi.setSaved(avatar.id, next);
      if (kind === "liked") setAvatar((a) => (a ? { ...a, likeCount: res.count } : a));
    } catch (e) {
      setAvatar((a) => (a ? { ...a, [kind]: !next } : a));
      setError(errorMessage(e));
    }
  };

  const share = () => {
    if (!avatar) return;
    void Share.share({ message: `${avatar.name} — ${avatar.title}${avatar.websiteUrl ? `\n${avatar.websiteUrl}` : ""}` });
  };

  if (!avatar) {
    return error ? (
      <View style={[styles.fill, { paddingTop: insets.top + 24, paddingHorizontal: 16 }]}>
        <ErrorBanner message={error} onRetry={load} />
      </View>
    ) : (
      <Loading />
    );
  }

  const socials = [
    { key: "instagram", url: avatar.socials.instagram, icon: "instagram" as const, bg: "#E1306C" },
    { key: "threads", url: avatar.socials.threads, icon: "threads" as const, bg: "#000" },
    { key: "x", url: avatar.socials.x, icon: "x-twitter" as const, bg: "#000" },
  ].filter((s) => !!s.url);
  const chips = CHIPS.filter((c) => !c.needs || !!avatar[c.needs]);

  return (
    <KeyboardAvoidingView style={styles.fill} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      {/* Profile arrives after the screen is already up: fade it in place; the tab bar stays put. */}
      <FadeIn from="none" style={styles.fill}>
        <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
          <Tap style={styles.back} onPress={() => (router.canGoBack() ? router.back() : router.replace("/explore"))} accessibilityLabel="Back">
            <Ionicons name="arrow-undo" size={18} color="#fff" />
          </Tap>
          <View style={styles.namePill}>
            <Text style={styles.name} numberOfLines={1}>
              {avatar.name}
            </Text>
            <View style={styles.botWrap}>
              <Image source={images.bot} style={styles.bot} contentFit="contain" />
            </View>
          </View>
          <View style={{ width: 36 }} />
        </View>

        <View style={styles.stage}>
          <Animated.View style={[styles.hero, { opacity: heroOpacity }]}>
            <Image
              source={{ uri: absoluteUrl(avatar.heroImageUrl) }}
              style={StyleSheet.absoluteFill}
              contentFit="contain"
              accessibilityLabel={`${avatar.name}, ${avatar.title}`}
            />
          </Animated.View>
          <View style={styles.rail}>
            <RailButton icon={avatar.liked ? "heart" : "heart-outline"} color={avatar.liked ? colors.dot : colors.text} label={String(avatar.likeCount)} onPress={() => toggle("liked")} a11y={avatar.liked ? "Unlike" : "Like"} />
            <RailButton icon={avatar.saved ? "bookmark" : "bookmark-outline"} color={colors.text} label="Save" onPress={() => toggle("saved")} a11y={avatar.saved ? "Remove from saved" : "Save"} />
            {socials.map((s) => (
              <Tap key={s.key} style={[styles.social, { backgroundColor: s.bg }]} onPress={() => Linking.openURL(s.url!)} accessibilityLabel={`Open ${s.key}`}>
                <FontAwesome6 name={s.icon} size={18} color="#fff" />
              </Tap>
            ))}
            <RailButton icon="add-circle-outline" color={colors.text} onPress={share} a11y="Share" />
          </View>

          {messages.length > 0 && (
            <ScrollView
              ref={scroll}
              style={styles.thread}
              contentContainerStyle={{ gap: 8, padding: 4 }}
              // Follow the conversation as it grows (sent message, typing indicator, reply) without a timer.
              onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: !isReducedMotion() })}
            >
              {messages.map((m) => (
                <FadeIn key={m.id} style={[styles.bubble, m.from === "me" ? styles.mine : styles.theirs]}>
                  <Text style={[styles.bubbleText, m.from === "me" && { color: "#fff" }]}>{m.text}</Text>
                  {m.link ? (
                    <LinkText style={styles.linkText} containerStyle={{ alignSelf: "flex-start" }} accessibilityRole="link" onPress={() => Linking.openURL(m.link!)}>
                      Open website ↗
                    </LinkText>
                  ) : null}
                  {m.sources && m.sources.length > 0 ? <Text style={styles.sources}>Sources: {m.sources.join(" · ")}</Text> : null}
                </FadeIn>
              ))}
              {sending ? (
                <FadeIn style={{ alignSelf: "flex-start", margin: 8 }}>
                  <ActivityIndicator color={colors.primary} accessibilityLabel={`${avatar.name} is replying`} />
                </FadeIn>
              ) : null}
            </ScrollView>
          )}
        </View>

        <View style={styles.meta}>
          <Ionicons name="star" size={14} color={colors.star} />
          <Text style={styles.rating}>{Number(avatar.rating).toFixed(2)}</Text>
          <Text style={styles.reviews}>({avatar.reviewCount} reviews)</Text>
          <Text style={styles.titleText} numberOfLines={1}>
            · {avatar.title}
          </Text>
        </View>

        <View style={styles.chatCard}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
            {chips.map((c) => (
              <Tap key={c.intent} style={styles.chip} onPress={() => ask({ intent: c.intent, label: c.label })} disabled={sending} accessibilityLabel={c.label}>
                <Ionicons name={c.icon} size={12} color={colors.warning} />
                <Text style={styles.chipText}>{c.label}</Text>
              </Tap>
            ))}
          </ScrollView>
          <View style={styles.inputRow}>
            <TextInput
              value={draft}
              onChangeText={setDraft}
              placeholder="Type your message here..."
              placeholderTextColor="#8A8A95"
              style={styles.input}
              onSubmitEditing={send}
              returnKeyType="send"
              maxLength={2000}
            />
            <Tap feedback="dim" onPress={send} disabled={!draft.trim() || sending} hitSlop={8} accessibilityLabel="Send message">
              <Ionicons name="send" size={20} color={draft.trim() ? colors.accentBlue : "#B8C7E8"} />
            </Tap>
          </View>
        </View>
      </FadeIn>
      {/* Same bottom bar as the tabs (mockup screen 9); avatars are opened from Explore. */}
      <TabBar items={TABS} activeName="explore" onSelect={(name) => router.navigate(`/${name}` as never)} />
    </KeyboardAvoidingView>
  );
}

function RailButton({
  icon,
  color,
  label,
  onPress,
  a11y,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  label?: string;
  onPress: () => void;
  a11y: string;
}) {
  return (
    <Tap style={styles.railBtn} onPress={onPress} accessibilityLabel={a11y}>
      <View style={styles.railCircle}>
        <Ionicons name={icon} size={20} color={color} />
      </View>
      {label ? <Text style={styles.railLabel}>{label}</Text> : null}
    </Tap>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1, backgroundColor: colors.surface },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16 },
  back: { width: 36, height: 36, borderRadius: 8, backgroundColor: "#9A9AA3", alignItems: "center", justifyContent: "center" },
  namePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: colors.navy,
    borderRadius: radius.pill,
    paddingLeft: 28,
    paddingRight: 6,
    height: 42,
    minWidth: 180,
    justifyContent: "space-between",
  },
  name: { color: "#fff", fontFamily: fonts.bold, fontSize: 16, flexShrink: 1 },
  botWrap: { width: 30, height: 30, borderRadius: 15, backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  bot: { width: 24, height: 24 },
  stage: { flex: 1, marginTop: 8 },
  hero: { position: "absolute", top: 0, bottom: 0, left: 0, right: 56 },
  rail: { position: "absolute", right: 12, top: "18%", alignItems: "center", gap: 12 },
  railBtn: { alignItems: "center" },
  railCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  railLabel: { fontFamily: fonts.medium, fontSize: 10, color: colors.textMuted, marginTop: 2 },
  social: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" },
  thread: { position: "absolute", left: 12, right: 64, bottom: 4, maxHeight: "70%" },
  bubble: { maxWidth: "88%", borderRadius: 14, paddingHorizontal: 12, paddingVertical: 9 },
  mine: { alignSelf: "flex-end", backgroundColor: colors.primary, borderBottomRightRadius: 4 },
  theirs: { alignSelf: "flex-start", backgroundColor: colors.surfaceAlt, borderBottomLeftRadius: 4, borderWidth: 1, borderColor: colors.border },
  bubbleText: { fontFamily: fonts.regular, fontSize: 14, color: colors.text, lineHeight: 20 },
  linkText: { marginTop: 6, fontFamily: fonts.bold, color: colors.accentBlue },
  sources: { marginTop: 6, fontFamily: fonts.regular, fontSize: 11, color: colors.textMuted },
  meta: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 4, paddingHorizontal: 16, marginTop: 6 },
  rating: { fontFamily: fonts.bold, fontSize: 13, color: colors.text },
  reviews: { fontFamily: fonts.regular, fontSize: 12, color: colors.textMuted },
  titleText: { fontFamily: fonts.regular, fontSize: 12, color: colors.textMuted, flexShrink: 1 },
  chatCard: {
    margin: 12,
    marginBottom: 10,
    padding: 10,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
    gap: 8,
  },
  chips: { gap: 8 },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: colors.chip,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: radius.pill,
  },
  chipText: { fontFamily: fonts.medium, fontSize: 12, color: colors.text },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: colors.surfaceAlt,
    borderRadius: radius.md,
    paddingHorizontal: 14,
    height: 46,
  },
  input: { flex: 1, fontFamily: fonts.regular, fontSize: 14, color: colors.text },
});
