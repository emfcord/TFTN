import React from "react";
import {
  AbsoluteFill,
  Audio,
  CalculateMetadataFunction,
  Composition,
  Img,
  Series,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";

// Drop the generated files here to make this composition render:
//   public/horror/audio/scene1.mp3 .. scene7.mp3, music.mp3
//   public/horror/images/scene1.png .. scene7.png
// Duration of each scene is derived automatically from its narration
// audio's real length (see calculateMetadata below) — no need to hardcode
// timings by hand.

type Scene = {
  audio: string;
  image: string;
  caption: string;
};

const SCENES: Scene[] = [
  {
    audio: "horror/audio/scene1.mp3",
    image: "horror/images/scene1.png",
    caption:
      "Dicen que las casas viejas nunca están realmente vacías. Marta llevaba tres noches sin dormir bien, desde que se mudó a la casa de su abuela.",
  },
  {
    audio: "horror/audio/scene2.mp3",
    image: "horror/images/scene2.png",
    caption:
      "Esa noche escuchó pasos en el ático. Lentos. Pausados. Como si algo contara los escalones, uno por uno.",
  },
  {
    audio: "horror/audio/scene3.mp3",
    image: "horror/images/scene3.png",
    caption:
      "Subió con una linterna temblando en la mano. La puerta estaba entreabierta, aunque juraba haberla cerrado con llave.",
  },
  {
    audio: "horror/audio/scene4.mp3",
    image: "horror/images/scene4.png",
    caption:
      "En el centro del cuarto había un espejo, cubierto por una sábana vieja. La tela se movió... sin que hubiera viento.",
  },
  {
    audio: "horror/audio/scene5.mp3",
    image: "horror/images/scene5.png",
    caption:
      "Cuando la retiró, su reflejo la miró. Pero un segundo tarde. Como si repitiera un movimiento que ella aún no había hecho.",
  },
  {
    audio: "horror/audio/scene6.mp3",
    image: "horror/images/scene6.png",
    caption: "Marta sonrió. Y del otro lado del cristal... el reflejo dejó de sonreír.",
  },
  {
    audio: "horror/audio/scene7.mp3",
    image: "horror/images/scene7.png",
    caption: "Esa noche, por primera vez, Marta durmió del otro lado del espejo.",
  },
];

const MUSIC_SRC = "horror/audio/music.mp3";
const FPS = 30;
const TITLE_DURATION = 60;
const OUTRO_DURATION = 45;
const SCENE_PAD_FRAMES = 12;

type Props = {
  sceneDurations: number[];
};

export const calculateHorrorMetadata: CalculateMetadataFunction<Props> = async () => {
  const sceneDurations = await Promise.all(
    SCENES.map(async (scene) => {
      const seconds = await getAudioDurationInSeconds(staticFile(scene.audio));
      return Math.round((seconds ?? 3) * FPS) + SCENE_PAD_FRAMES;
    }),
  );

  const durationInFrames =
    TITLE_DURATION + sceneDurations.reduce((a, b) => a + b, 0) + OUTRO_DURATION;

  return {
    durationInFrames,
    props: { sceneDurations },
  };
};

const Vignette: React.FC = () => {
  const frame = useCurrentFrame();
  const flicker = 0.06 * Math.sin(frame / 5) + 0.06 * Math.sin(frame / 13);

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,0.85) 100%)",
        opacity: 0.9 + flicker,
        pointerEvents: "none",
      }}
    />
  );
};

const TitleCard: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20, TITLE_DURATION - 15, TITLE_DURATION], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: "#000", alignItems: "center", justifyContent: "center" }}>
      <div style={{ opacity, textAlign: "center" }}>
        <h1
          style={{
            margin: 0,
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: 74,
            fontWeight: 700,
            letterSpacing: 6,
            color: "#e2e8f0",
            textShadow: "0 0 24px rgba(148,163,184,0.5)",
          }}
        >
          EL ESPEJO DEL ÁTICO
        </h1>
        <p
          style={{
            marginTop: 18,
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: 26,
            color: "#64748b",
            letterSpacing: 3,
            fontStyle: "italic",
          }}
        >
          Una historia de suspenso
        </p>
      </div>
    </AbsoluteFill>
  );
};

const Caption: React.FC<{ text: string; durationInFrames: number }> = ({
  text,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [0, 15, durationInFrames - SCENE_PAD_FRAMES - 15, durationInFrames - SCENE_PAD_FRAMES],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end" }}>
      <div
        style={{
          opacity,
          margin: "0 120px 90px",
          padding: "22px 36px",
          background: "rgba(0,0,0,0.55)",
          borderRadius: 12,
          maxWidth: 1400,
        }}
      >
        <p
          style={{
            margin: 0,
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: 32,
            lineHeight: 1.4,
            color: "#f1f5f9",
            textAlign: "center",
            textShadow: "0 2px 6px rgba(0,0,0,0.8)",
          }}
        >
          {text}
        </p>
      </div>
    </AbsoluteFill>
  );
};

const StoryScene: React.FC<{ scene: Scene; index: number; durationInFrames: number }> = ({
  scene,
  index,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

  // Ken Burns: slow zoom, alternating pan direction per scene for variety.
  const scale = interpolate(frame, [0, durationInFrames], [1, 1.14], {
    extrapolateRight: "clamp",
  });
  const direction = index % 2 === 0 ? 1 : -1;
  const panX = interpolate(frame, [0, durationInFrames], [0, 40 * direction], {
    extrapolateRight: "clamp",
  });

  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ opacity: fadeIn, background: "#000" }}>
      <Img
        src={staticFile(scene.image)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translateX(${panX}px)`,
        }}
      />
      <Vignette />
      <Caption text={scene.caption} durationInFrames={durationInFrames} />
      <Audio src={staticFile(scene.audio)} volume={1} />
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, OUTRO_DURATION - 15, OUTRO_DURATION], [1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const textOpacity = interpolate(frame, [10, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: "#000", opacity, alignItems: "center", justifyContent: "center" }}>
      <p
        style={{
          opacity: textOpacity,
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontSize: 30,
          letterSpacing: 4,
          color: "#64748b",
        }}
      >
        FIN
      </p>
    </AbsoluteFill>
  );
};

export const HorrorStory: React.FC<Props> = ({ sceneDurations }) => {
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Audio src={staticFile(MUSIC_SRC)} volume={0.22} loop />
      <Series>
        <Series.Sequence durationInFrames={TITLE_DURATION}>
          <TitleCard />
        </Series.Sequence>
        {SCENES.map((scene, i) => (
          <Series.Sequence key={scene.audio} durationInFrames={sceneDurations[i]}>
            <StoryScene scene={scene} index={i} durationInFrames={sceneDurations[i]} />
          </Series.Sequence>
        ))}
        <Series.Sequence durationInFrames={OUTRO_DURATION}>
          <Outro />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};

export const HorrorStoryComposition: React.FC = () => (
  <Composition
    id="HorrorStory"
    component={HorrorStory}
    fps={FPS}
    width={1920}
    height={1080}
    durationInFrames={TITLE_DURATION + SCENES.length * 150 + OUTRO_DURATION}
    calculateMetadata={calculateHorrorMetadata}
    defaultProps={{ sceneDurations: SCENES.map(() => 150) }}
  />
);
