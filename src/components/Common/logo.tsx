interface LogoProps {
  size?: number;
}

export default function Logo({ size = 80 }: LogoProps) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "20px",
        background: "linear-gradient(135deg,#0066ff,#00d4ff)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        fontSize: size / 2.5,
        fontWeight: 700,
        color: "#fff",
        boxShadow: "0 0 30px rgba(0,150,255,.45)"
      }}
    >
      A
    </div>
  );
}