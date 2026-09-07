import "./index.css";
import { MyComposition } from "./Composition";
import { TFTNPromoComposition } from "./TFTNPromo";
import { HorrorStoryComposition } from "./HorrorStory";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <MyComposition />
      <TFTNPromoComposition />
      <HorrorStoryComposition />
    </>
  );
};
