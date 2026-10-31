/**
 * Motion tokens and policy: the only durations, curves and distances the app animates with.
 *
 * Principles (see docs/motion.md):
 * - Motion answers a user action or explains a change. Nothing moves on its own or loops.
 * - Feedback starts on touch-down; exits are instant; no animation ever gates input.
 * - Only opacity and transform are animated, on the native driver, so a busy JS thread cannot drop frames.
 * - With the OS reduce-motion setting on, nothing slides, scales or flies; short cross-fades remain.
 * - Emergency surfaces (SOS, crash countdown, cancel) use none of this: no entrance, no delay, no scale.
 *
 * Kept free of react-native imports so the policy can be unit-tested under plain Node.
 */

export const duration = {
  /** Touch-down response; short enough to read as immediate. */
  pressIn: 80,
  /** Release back to rest. */
  pressOut: 160,
  /** Small in-place state changes: tab pill, page dots, segmented thumb, cross-fades. */
  fast: 150,
  /** Content arriving after a screen is already visible. */
  base: 220,
  /** Map camera moves (recentre, jump to a search result). */
  map: 650,
} as const;

/** Cubic-bezier control points. `enter`: decelerating ease-out; `move`: symmetric ease-in-out. */
export const curve = {
  enter: [0.2, 0, 0, 1],
  move: [0.4, 0, 0.2, 1],
} as const;

export const distance = {
  /** How far arriving content travels into place, in dp. */
  enter: 8,
} as const;

export const scale = {
  /** Pressed size for buttons, cards, chips and floating buttons. */
  press: 0.97,
  /** Starting width fraction of the active tab pill as it grows into place. */
  pill: 0.6,
} as const;

export const opacity = {
  /** Icon-only buttons and text links while pressed. */
  dim: 0.5,
  /** Scale feedback replaced by a light dim when reduce motion is on. */
  reducedPress: 0.8,
} as const;

export const stagger = {
  step: 35,
  /** Items past this index appear with the last staggered one, so a long list never trickles in. */
  maxItems: 6,
} as const;

/**
 * The one choreographed sequence in the app: the first onboarding frame, shown once per install.
 * Windows are ms from the screen mounting. It never gates input: the slide can be swiped and the next
 * button pressed from the first frame, and any interaction completes the sequence instantly.
 */
export const intro = {
  /** Stage 1: the arch backdrop settles in behind the artwork (the white page itself is never animated). */
  backdrop: { delay: 0, duration: 300 },
  /** Stage 2: the emblem artwork (lotus, lions and its baked-in caption). */
  artwork: { delay: 300, duration: 700, fromScale: 0.92 },
  /** Stage 3: the "Saarthi 26" wordmark rises the standard enter distance. */
  title: { delay: 1000, duration: 500 },
  /** Stage 4: page dots and the next button. */
  controls: { delay: 1500, duration: 300, fromScale: 0.92 },
} as const;

export type IntroStage = { delay: number; duration: number; fromScale: number; fromOffset: number };

/** Intro stages for the reduce-motion preference: reduced = everything cross-fades together, nothing moves. */
export function introFor(reduced: boolean): Record<keyof typeof intro, IntroStage> {
  const stage = (s: { delay: number; duration: number; fromScale?: number }, offset = 0): IntroStage =>
    reduced
      ? { delay: 0, duration: duration.fast, fromScale: 1, fromOffset: 0 }
      : { delay: s.delay, duration: s.duration, fromScale: s.fromScale ?? 1, fromOffset: offset };
  return {
    backdrop: stage(intro.backdrop),
    artwork: stage(intro.artwork),
    title: stage(intro.title, distance.enter),
    controls: stage(intro.controls),
  };
}

/** Spinners stay hidden this long, so fast responses never flash a loading state. */
export const loadingDelay = 300;

export const staggerDelay = (index: number): number =>
  Math.max(0, Math.min(Math.floor(index), stagger.maxItems)) * stagger.step;

/** Resolved motion values for the current reduce-motion preference. */
export function motionFor(reduced: boolean) {
  return {
    enterOffset: reduced ? 0 : distance.enter,
    enterDuration: reduced ? duration.fast : duration.base,
    pressScale: reduced ? 1 : scale.press,
    pressOpacity: reduced ? opacity.reducedPress : 1,
    pillFrom: reduced ? 1 : scale.pill,
    mapDuration: reduced ? 0 : duration.map,
    staggerDelay: (index: number) => (reduced ? 0 : staggerDelay(index)),
    stackAnimation: reduced ? ("fade" as const) : ("slide_from_right" as const),
  };
}

export type Motion = ReturnType<typeof motionFor>;
