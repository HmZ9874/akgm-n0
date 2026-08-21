import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AKGM-N0 · 实验汇报",
  description: "匿名概念形成、验证证据与搜索成本对照。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}

