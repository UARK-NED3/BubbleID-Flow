# Bubble Mask Labeling Protocol

This project currently has one segmentation class: `bubble`.

## Label As Bubble

- visible vapor bubbles attached to or near the heated wall
- partial bubbles cut off by the channel boundary or image edge
- coalesced bubble structures when they form one connected visible vapor region

## Do Not Label

- text overlays from the camera
- channel walls, heater edges, or reflections without a bubble boundary
- dust, scratches, static marks, and glare spots
- large black image background outside the flow channel

## Boundary Convention

Trace the visible bubble boundary as consistently as possible. If only the dark outline is visible, include the enclosed vapor region when it can be inferred from the image. For ambiguous glare or coalescence cases, prefer consistency over excessive detail.

## Dataset Split

Keep validation frames from separate videos or operating-condition folders whenever possible. Adjacent frames are highly correlated and should not be split randomly across train and validation sets.
