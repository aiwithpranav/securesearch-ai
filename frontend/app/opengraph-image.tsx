import { ImageResponse } from "next/og";
export const alt = "SecureSearch AI: search everything you're allowed to see";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export default function Image() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", padding: 80, background: "#070B14", color: "#EAF1FF" }}>
        <div style={{ fontSize: 34, color: "#60A5FA" }}>SecureSearch AI</div>
        <div style={{ fontSize: 72, fontWeight: 700, marginTop: 24, lineHeight: 1.1 }}>Search everything you&apos;re allowed to see. Nothing you&apos;re not.</div>
      </div>
    ),
    size
  );
}
