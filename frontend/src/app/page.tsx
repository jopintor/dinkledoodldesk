"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { FullPageLoading } from "@/components/ui";
import { homeFor, useAuth } from "@/lib/auth";

// Sends people to the login page or to their role's home screen.
export default function Home() {
  const auth = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (auth.status === "anonymous") router.replace("/login");
    if (auth.status === "authenticated") router.replace(homeFor(auth.user.role));
  }, [auth, router]);

  return <FullPageLoading />;
}
