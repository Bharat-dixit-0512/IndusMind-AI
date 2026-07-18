import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The dev indicator defaults to bottom-left, which is exactly where the
  // sidebar's account block sits — it covered the avatar during development.
  devIndicators: { position: "bottom-right" },
};

export default nextConfig;
