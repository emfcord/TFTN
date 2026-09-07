import "./index.css";
import { MyComposition } from "./Composition";
import { TFTNPromoComposition } from "./TFTNPromo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <MyComposition />
      <TFTNPromoComposition />
    </>
  );
};
