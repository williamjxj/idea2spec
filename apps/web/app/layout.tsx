import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Project CTO",
  description: "Multi-agent workflow engine — transform an idea into structured project artifacts",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#0f172a", minHeight: "100vh" }}>{children}</body>
    </html>
  );
}
