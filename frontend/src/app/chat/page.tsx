"use client";

import { ChatApp } from "@/components/chat/ChatApp";
import { FullPageLoading } from "@/components/ui";
import { useRequireRole } from "@/lib/auth";
import type { Role } from "@/lib/types";

// Everyone can chat; agents and admins use it to see what users see.
const ROLES: Role[] = ["member", "staff", "agent", "admin"];

export default function ChatPage() {
  const user = useRequireRole(ROLES);
  if (!user) return <FullPageLoading />;
  return <ChatApp user={user} />;
}
