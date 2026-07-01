# Final QA Checklist

Use this checklist before packaging or publishing a video.

## Topic And Promise

- [ ] Cover, title, opening, voiceover, visuals, and publish copy all serve the same promise.
- [ ] The viewer can explain the video in one plain sentence.
- [ ] The video gives a method, judgment, checklist, or useful viewpoint.

## Render Hygiene

- [ ] Old `source/segments/s*.png`, `s*.mp4`, `segments.txt`, and `silent.mp4` were cleared before re-rendering.
- [ ] `qa/segment_contact_sheets/` was generated from clips listed in `segments.txt`.
- [ ] `qa/contact-sheet-final-all-frames.jpg` or png was generated from the final MP4.
- [ ] QA did not rely only on source images without subtitles.

## Timeline

- [ ] Scene switches follow final audio or VTT timing, not storyboard estimates.
- [ ] The current subtitle explains the current frame.
- [ ] There is no moment where the image has moved on while subtitles still explain the previous image.

## Subtitles

- [ ] Subtitles are no more than two lines.
- [ ] Subtitles are not clipped by the video edge or player-safe area.
- [ ] Subtitles do not cover key cards, flow nodes, takeaway bars, or arrows.
- [ ] English terms preserve spacing, for example `Claude Code`, `Context Engineering`, and `Prompt Engineering`.

## Visuals

- [ ] Each frame has one clear main idea.
- [ ] Each frame has a visible reading order.
- [ ] Titles, cards, nodes, arrows, lines, and takeaway bars do not overlap.
- [ ] No key element touches the edge or gets cropped.
- [ ] Arrows are complete and arrowheads are visible.
- [ ] Backgrounds are clean solid colors or very low-noise surfaces. No grid, checker, or noisy texture by default.

## Cover And Publish Package

- [ ] The cover can be understood in one second.
- [ ] The cover contains a hook, not only a source name or feature name.
- [ ] The cover headline has no overlap, cropping, or unreadable small text.
- [ ] If the cover headline changed, title, short title, description, QA notes, and platform cover exports were updated together.
- [ ] The package contains final video, cover, QA report, source process files, and publish copy.
