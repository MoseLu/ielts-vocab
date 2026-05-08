## Style Prompt

Soft hand-drawn mobile login animation for 雅思冲刺: a bright white canvas, warm orange fruit motifs, tender spring grass, and a readable little girl with a fluffy cat running across a rounded hill. The mascot art should echo the app logo's dreamy peach-pink crayon mood without copying its composition, pose, or exact character details.

## Colors

- Background: `#FFFDFC`
- Orange: `#FF9F43`
- Soft orange: `#FFE5C4`
- Citrus highlight: `#FFD89E`
- Leaf green: `#8BBE52`
- Grass: `#DDF2AE`
- Ink brown: `#5A2E1B`
- Blush: `#FFB7A7`

## Typography

- No text in the rendered video. Login copy is handled by the React Native screen.

## Motion Rules

- The girl and cat must be legible at mobile size.
- The girl must read clearly as a human child: visible face, hair, torso, arms, legs, and shoes.
- The girl and cat subject must be generated raster art, not hand-authored SVG.
- The running cycle uses 8 raster frames with stable character identity, fixed visual center, and a shared foot/paw baseline.
- Grass and flowers move horizontally to make the running scene feel alive.
- All loops must be finite for deterministic rendering.
- Motion comes from a HyperFrames-style GSAP timeline, not React Native Animated.

## What NOT to Do

- Do not replace the orange fruit motif with social-login or chat-bubble graphics.
- Do not rely on tiny ambiguous silhouettes.
- Do not use purple/blue gradients, stock imagery, or static backgrounds.
- Do not put login inputs inside the first entry screen.
