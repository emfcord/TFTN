import React from "react";
import {
  AbsoluteFill,
  Composition,
  Series,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const BG_GRADIENT =
  "radial-gradient(circle at 50% 20%, #1e1b4b 0%, #020617 60%, #020617 100%)";

const Scene: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill
    style={{
      background: BG_GRADIENT,
      alignItems: "center",
      justifyContent: "center",
      fontFamily:
        "Helvetica, Arial, sans-serif",
    }}
  >
    {children}
  </AbsoluteFill>
);

const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({
    frame,
    fps,
    config: { damping: 12, mass: 0.6 },
  });

  const taglineOpacity = interpolate(frame, [25, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const taglineY = interpolate(frame, [25, 45], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const subOpacity = interpolate(frame, [55, 75], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <Scene>
      <div
        style={{
          transform: `scale(${logoScale})`,
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontSize: 150,
            fontWeight: 900,
            letterSpacing: 20,
            margin: 0,
            background:
              "linear-gradient(90deg, #fcd34d 0%, #fef3c7 50%, #f59e0b 100%)",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            color: "transparent",
          }}
        >
          TFTN
        </h1>
      </div>
      <p
        style={{
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px)`,
          marginTop: 8,
          fontSize: 34,
          color: "#e2e8f0",
          fontWeight: 600,
          letterSpacing: 1,
        }}
      >
        Launch Your Own CryptoNote Coin
      </p>
      <p
        style={{
          opacity: subOpacity,
          marginTop: 28,
          fontSize: 20,
          color: "#64748b",
          letterSpacing: 6,
          textTransform: "uppercase",
        }}
      >
        Powered by ForkNote
      </p>
    </Scene>
  );
};

const FEATURES = [
  {
    title: "Open Source",
    desc: "Fully open CryptoNote codebase, free to fork and customize.",
  },
  {
    title: "Fast Blocks",
    desc: "Quick confirmation times built for real-world payments.",
  },
  {
    title: "Secure Protocol",
    desc: "Battle-tested CryptoNote cryptography and ring signatures.",
  },
  {
    title: "Simple Setup",
    desc: "Launch a network from a single configuration file.",
  },
];

const FeatureRow: React.FC<{ index: number; title: string; desc: string }> = ({
  index,
  title,
  desc,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const delay = 20 + index * 18;

  const progress = spring({
    frame: frame - delay,
    fps,
    config: { damping: 14 },
  });
  const opacity = interpolate(frame, [delay, delay + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const x = interpolate(progress, [0, 1], [-60, 0]);

  return (
    <div
      style={{
        opacity,
        transform: `translateX(${x}px)`,
        display: "flex",
        alignItems: "center",
        gap: 24,
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 20,
        padding: "20px 32px",
        width: 860,
      }}
    >
      <div
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#fcd34d",
          flexShrink: 0,
        }}
      />
      <div>
        <h3 style={{ margin: 0, fontSize: 26, fontWeight: 700, color: "#fff" }}>
          {title}
        </h3>
        <p style={{ margin: "4px 0 0", fontSize: 18, color: "#94a3b8" }}>
          {desc}
        </p>
      </div>
    </div>
  );
};

const Features: React.FC = () => {
  const frame = useCurrentFrame();
  const headingOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <Scene>
      <h2
        style={{
          opacity: headingOpacity,
          fontSize: 52,
          fontWeight: 800,
          color: "#fff",
          marginBottom: 32,
        }}
      >
        Why TFTN?
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {FEATURES.map((f, i) => (
          <FeatureRow key={f.title} index={i} title={f.title} desc={f.desc} />
        ))}
      </div>
    </Scene>
  );
};

const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 10 } });
  const fadeOut = interpolate(frame, [40, 60], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: BG_GRADIENT,
        alignItems: "center",
        justifyContent: "center",
        opacity: fadeOut,
        fontFamily: "Helvetica, Arial, sans-serif",
      }}
    >
      <div style={{ transform: `scale(${scale})`, textAlign: "center" }}>
        <h2 style={{ fontSize: 64, fontWeight: 900, color: "#fff", margin: 0 }}>
          Get Started Today
        </h2>
        <div
          style={{
            marginTop: 28,
            background: "rgba(0,0,0,0.4)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 14,
            padding: "18px 34px",
            fontFamily: "Menlo, Consolas, monospace",
            fontSize: 22,
            color: "#fcd34d",
            display: "inline-block",
          }}
        >
          ./TFTNd --config-file configs/TFTN.conf
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const TFTNPromo: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: "#020617" }}>
      <Series>
        <Series.Sequence durationInFrames={100}>
          <Intro />
        </Series.Sequence>
        <Series.Sequence durationInFrames={140}>
          <Features />
        </Series.Sequence>
        <Series.Sequence durationInFrames={60}>
          <Outro />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};

export const TFTNPromoComposition: React.FC = () => (
  <Composition
    id="TFTNPromo"
    component={TFTNPromo}
    durationInFrames={300}
    fps={30}
    width={1920}
    height={1080}
  />
);
