"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import {
  sendChatMessage,
  type ChatResponse,
  type Citation,
  type AgentLogStep,
  type TimelineEvent,
} from "@/lib/api";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  agentLogs?: AgentLogStep[];
  confidenceScore?: number;
  reasoningSteps?: string[];
  evidenceBase?: string[];
  timeline?: TimelineEvent[];
  loading?: boolean;
}

const WELCOME_MESSAGE: Message = {
  id: "0",
  role: "assistant",
  content: "Hello! I am your **AI Knowledge Assistant**.\n\nI answer questions using only the documents you've uploaded — with full source citations. If you haven't uploaded anything yet, head to the **Documents** page first, then come back and ask me anything about it.",
};

interface ChatContextType {
  messages: Message[];
  isLoading: boolean;
  sendMessage: (text: string) => Promise<void>;
  clearChat: () => void;
}

const ChatContext = createContext<ChatContextType | null>(null);

// Held in this provider (mounted once in the (app) layout, above the pages
// that remount on navigation) so the conversation survives switching to
// another page and back — it's only wiped by an explicit clearChat() call.
export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
    const placeholderId = (Date.now() + 1).toString();
    const placeholder: Message = { id: placeholderId, role: "assistant", content: "", loading: true };
    setMessages(m => [...m, userMsg, placeholder]);
    setIsLoading(true);

    try {
      const data: ChatResponse = await sendChatMessage(text);
      setMessages(m => m.map(msg =>
        msg.id === placeholderId
          ? {
              id: placeholderId,
              role: "assistant",
              content: data.response,
              citations: data.citations,
              agentLogs: data.agent_logs,
              confidenceScore: data.confidence_score,
              reasoningSteps: data.reasoning_steps,
              evidenceBase: data.evidence_base,
              timeline: data.timeline,
            }
          : msg
      ));
    } catch {
      setMessages(m => m.map(msg =>
        msg.id === placeholderId
          ? { ...msg, content: "⚠️ Could not reach the backend. Please ensure the FastAPI server is running.", loading: false }
          : msg
      ));
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearChat = useCallback(() => {
    setMessages([WELCOME_MESSAGE]);
  }, []);

  return (
    <ChatContext.Provider value={{ messages, isLoading, sendMessage, clearChat }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used inside ChatProvider");
  return ctx;
}
