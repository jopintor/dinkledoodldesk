// Client-side chat history. The backend's RAG endpoint is stateless for now (PR #18), so the
// browser keeps each user's conversations in localStorage. When `GET /conversations` lands,
// load the sidebar from it instead.
import type { Citation, HistoryItem, Priority, Role, ToolCall } from "@/lib/types";

export type ChatItem =
  | { kind: "user"; id: string; at: string; content: string; piiRedacted?: boolean }
  | {
      kind: "assistant";
      id: string;
      at: string;
      content: string;
      citations: Citation[];
      confidence?: number;
      offerEscalation?: boolean;
      serverId?: string;
    }
  | { kind: "agent"; id: string; at: string; name: string; content: string }
  | { kind: "tool"; id: string; at: string; call: ToolCall }
  | {
      kind: "escalation";
      id: string;
      at: string;
      agentName: string | null;
      ticketNumber: string;
      jiraKey: string | null;
      priority: Priority;
      firstReplyMinutes: number;
    }
  | { kind: "system"; id: string; at: string; content: string }
  | { kind: "error"; id: string; at: string; content: string; retry?: string };

export type Conversation = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  status: "active" | "escalated" | "resolved";
  items: ChatItem[];
  ticket?: { ticketNumber: string; jiraKey: string | null };
  agentName?: string | null;
  /** Server message ids already shown (agent/system messages pulled while escalated). */
  seen?: string[];
};

export const newId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const key = (userId: string) => `dinkdesk.chats.${userId}`;

export function loadConversations(userId: string): Conversation[] | null {
  try {
    const raw = localStorage.getItem(key(userId));
    return raw ? (JSON.parse(raw) as Conversation[]) : null;
  } catch {
    return null;
  }
}

export function saveConversations(userId: string, convos: Conversation[]) {
  try {
    localStorage.setItem(key(userId), JSON.stringify(convos.slice(0, 30)));
  } catch {
    // storage full or blocked; history just won't persist
  }
}

export function greeting(firstName: string): ChatItem {
  return {
    kind: "assistant",
    id: newId(),
    at: new Date().toISOString(),
    content: `Hi ${firstName}, what can I help with?`,
    citations: [],
  };
}

export function emptyConversation(firstName: string): Conversation {
  const now = new Date().toISOString();
  return { id: newId(), title: "New chat", createdAt: now, updatedAt: now, status: "active", items: [greeting(firstName)] };
}

const TITLE_RULES: [RegExp, string][] = [
  [/staffid|password|forgot|locked out|code never/i, "StaffID password reset"],
  [/dinkpos.*pin|pin.*dinkpos/i, "DinkPOS PIN locked"],
  [/staff wi-?fi|wi-?fi/i, "Wi-Fi keeps dropping"],
  [/card terminal|host not reachable|tappay/i, "Card terminal error"],
  [/double[- ]?book|twice|court \d/i, "Court booking problem"],
  [/member app/i, "Member App sign-in"],
];

export function titleFor(firstMessage: string) {
  for (const [re, title] of TITLE_RULES) if (re.test(firstMessage)) return title;
  const t = firstMessage.trim().replace(/\s+/g, " ");
  return t.length > 36 ? `${t.slice(0, 35)}…` : t;
}

/** Last turns sent to /rag/ask as context. */
export function historyOf(items: ChatItem[]): HistoryItem[] {
  return items
    .filter((i): i is Extract<ChatItem, { kind: "user" | "assistant" }> => i.kind === "user" || i.kind === "assistant")
    .slice(1) // skip the greeting
    .map((i) => ({ role: i.kind, content: i.content.slice(0, 4000) }));
}

export const QUICK_QUESTIONS: Record<"staff" | "member", string[]> = {
  staff: ["My DinkPOS PIN is locked", "Staff Wi-Fi keeps dropping", "Card terminal says “Host not reachable”"],
  member: ["I can't sign in to the Member App", "What's the member Wi-Fi password?", "My court booking shows up twice"],
};

export function quickQuestionsFor(role: Role) {
  return role === "member" ? QUICK_QUESTIONS.member : QUICK_QUESTIONS.staff;
}

/** Example history so the sidebar matches the design in mock mode (Figma screen 02). */
export function sampleConversations(firstName: string, role: Role): Conversation[] {
  const daysAgo = (d: number) => new Date(Date.now() - d * 86_400_000).toISOString();
  const make = (title: string, d: number, q: string, a: string): Conversation => ({
    id: newId(),
    title,
    createdAt: daysAgo(d),
    updatedAt: daysAgo(d),
    status: "resolved",
    items: [
      { ...greeting(firstName), at: daysAgo(d) },
      { kind: "user", id: newId(), at: daysAgo(d), content: q },
      { kind: "assistant", id: newId(), at: daysAgo(d), content: a, citations: [] },
    ],
  });
  if (role === "member") {
    return [
      make("Court 3 double-booked", 2, "Court 3 shows up twice in my bookings.", "That's usually a sync delay. Pull down to refresh; if it's still there after 5 minutes I can report it."),
    ];
  }
  return [
    make("Receipt printer offline (DAS)", 2, "The receipt printer at the DAS front desk is offline.", "Check that the printer is on and the USB cable is in, then restart DinkPOS. I opened ticket ITH-1150 for you."),
    make("PickleHub-Staff Wi-Fi drops", 3, "PickleHub-Staff Wi-Fi drops every few minutes.", "Forget PickleHub-Staff on your device and reconnect with your StaffID password."),
    make("Court 3 double-booked", 4, "Court 3 is double-booked tonight.", "I created ticket ITH-1187 so the front desk can cancel the duplicate."),
  ];
}
