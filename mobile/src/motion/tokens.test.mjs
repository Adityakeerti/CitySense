// Motion policy tests. Run: npm test (node --test, no extra dependencies).
import assert from "node:assert/strict";
import { test } from "node:test";
import { distance, duration, introFor, loadingDelay, motionFor, scale, stagger, staggerDelay } from "./tokens.ts";

test("touch feedback reads as immediate", () => {
  assert.ok(duration.pressIn <= 100, "press-in must land within ~6 frames");
  assert.ok(duration.pressOut <= 200);
});

test("no content animation is long enough to feel like waiting", () => {
  for (const [name, ms] of Object.entries(duration)) {
    if (name === "map") continue; // camera flights travel distance; still well under a second
    assert.ok(ms <= 250, `${name} is ${ms}ms`);
  }
  assert.ok(duration.map < 1000);
});

test("stagger is capped so long lists never trickle in", () => {
  assert.equal(staggerDelay(0), 0);
  assert.equal(staggerDelay(1), stagger.step);
  assert.equal(staggerDelay(500), stagger.maxItems * stagger.step);
  assert.equal(staggerDelay(-3), 0);
  assert.ok(stagger.maxItems * stagger.step + duration.base <= 450, "last staggered item settles in under half a second");
});

test("press scale is subtle", () => {
  assert.ok(scale.press >= 0.95 && scale.press < 1);
});

test("reduce motion removes movement but keeps short fades", () => {
  const m = motionFor(true);
  assert.equal(m.enterOffset, 0);
  assert.equal(m.pressScale, 1);
  assert.equal(m.pillFrom, 1);
  assert.equal(m.mapDuration, 0);
  assert.equal(m.staggerDelay(5), 0);
  assert.equal(m.stackAnimation, "fade");
  assert.ok(m.enterDuration > 0 && m.enterDuration <= duration.fast);
  assert.ok(m.pressOpacity < 1, "pressed controls still respond visibly");
});

test("default motion keeps native slide navigation", () => {
  const m = motionFor(false);
  assert.equal(m.stackAnimation, "slide_from_right");
  assert.ok(m.enterOffset > 0 && m.enterOffset <= 12);
  assert.equal(m.pressOpacity, 1);
});

test("spinners wait before appearing so fast loads do not flash", () => {
  assert.ok(loadingDelay >= 200 && loadingDelay <= 500);
});

test("onboarding intro runs its four stages in order and is fully settled by 1.8 s", () => {
  const s = introFor(false);
  const order = [s.backdrop, s.artwork, s.title, s.controls];
  for (let i = 1; i < order.length; i++) {
    assert.ok(order[i].delay >= order[i - 1].delay, "stages start in sequence");
  }
  assert.equal(s.artwork.delay, 300);
  assert.equal(s.title.delay, 1000);
  assert.equal(s.controls.delay, 1500);
  const end = Math.max(...order.map((x) => x.delay + x.duration));
  assert.ok(end <= 1800, `intro ends at ${end}ms`);
});

test("onboarding intro motion stays subtle", () => {
  const s = introFor(false);
  for (const [name, st] of Object.entries(s)) {
    assert.ok(st.fromScale >= 0.9 && st.fromScale <= 1, `${name} scales from ${st.fromScale}`);
    assert.ok(Math.abs(st.fromOffset) <= 12, `${name} travels ${st.fromOffset}`);
  }
  assert.equal(s.title.fromOffset, distance.enter, "the wordmark rises the standard enter distance");
  assert.equal(s.backdrop.fromScale, 1, "the backdrop only fades");
});

test("reduce motion collapses the intro to one short cross-fade with no movement or waiting", () => {
  for (const [name, st] of Object.entries(introFor(true))) {
    assert.equal(st.delay, 0, `${name} must not wait`);
    assert.equal(st.fromScale, 1, `${name} must not scale`);
    assert.equal(st.fromOffset, 0, `${name} must not move`);
    assert.ok(st.duration > 0 && st.duration <= duration.fast);
  }
});

test("first-screen choreography waits out the splash dissolve, and never longer", async () => {
  const { splashHiding, splashRemaining, SPLASH_START_LATENCY_MS } = await import("./splash.ts");
  const total = duration.base + SPLASH_START_LATENCY_MS;
  assert.equal(splashRemaining(1_000), 0, "no wait when the splash never ran");
  splashHiding(duration.base, 5_000);
  assert.equal(splashRemaining(5_000), total);
  assert.equal(splashRemaining(5_000 + 100), total - 100);
  assert.equal(splashRemaining(5_000 + total + 1), 0, "no wait once the dissolve has ended");
  assert.ok(total <= 400, "never holds the first screen back noticeably");
});
