# Assets for the "HorrorStory" composition

Download these from the links your Claude session gave you and place them
here with these exact names, then run `npx remotion render src/index.ts
HorrorStory out.mp4` (or open Remotion Studio with `npm run dev`).

```
public/horror/
  audio/
    scene1.mp3 .. scene7.mp3   (narration, one file per story beat)
    music.mp3                  (background ambience, loops for the full video)
  images/
    scene1.jpg .. scene7.jpg   (one image per story beat)
```

Each scene's length on screen is derived automatically from its narration
file's real duration (see `calculateHorrorMetadata` in `src/HorrorStory.tsx`)
— no manual timing needed. Just make sure `sceneN.mp3` and `sceneN.jpg`
correspond to the same story beat.
