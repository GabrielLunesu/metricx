"use client";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { fetchQA, fetchQAStream } from "@/lib/api";
import { currentUser } from "@/lib/auth";
import ConversationThread from "./components/ConversationThread";
import { renderMarkdownLite } from "@/lib/markdown";
import ChatConsole from "./components/ChatConsole";

export default function CopilotPage() {
  const searchParams = useSearchParams();
  const question = searchParams.get("q");
  const workspaceId = searchParams.get("ws");

  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [resolvedWs, setResolvedWs] = useState(workspaceId || null);
  const processedRef = useRef(false);

  // SSE streaming state (v2.1)
  // WHY: Real-time stage updates provide better UX than polling
  // Stages: queued → translating → executing → formatting → complete
  const [stage, setStage] = useState(null);

  // Resolve workspace id from session if not present in URL
  useEffect(() => {
    if (workspaceId) {
      setResolvedWs(workspaceId);
      return;
    }
    let mounted = true;
    currentUser()
      .then((u) => {
        if (!mounted) return;
        setResolvedWs(u?.workspace_id || null);
      })
      .catch(() => setResolvedWs(null));
    return () => {
      mounted = false;
    };
  }, [workspaceId]);

  // Process URL question parameter
  useEffect(() => {
    if (!resolvedWs || !question || processedRef.current) return;
    processedRef.current = true;
    handleSubmit(question.trim());
  }, [question, resolvedWs]);

  // Handle question submission with SSE streaming (v2.1)
  // WHAT: Uses streaming for real-time progress, falls back to polling if streaming fails
  // WHY: Better UX with live stage updates, graceful degradation for older browsers
  const handleSubmit = async (q) => {
    if (!resolvedWs || !q.trim() || loading) return;

    // Add user message immediately with timestamp (optimistic UI)
    const userMessage = {
      type: 'user',
      text: q,
      timestamp: Date.now()
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setStage('queued'); // Initial stage

    // Helper to add AI response
    const addAiResponse = (res) => {
      const aiMessage = {
        type: 'ai',
        text: renderMarkdownLite(res.answer),
        timestamp: Date.now(),
        visuals: res.visuals,
        data: res.data,
        executedDsl: res.executed_dsl
      };
      setMessages((prev) => [...prev, aiMessage]);
    };

    // Helper to add error message
    const addErrorMessage = (error) => {
      const errorMessage = {
        type: 'ai',
        text: `I encountered an error: ${error}. Please try again.`,
        timestamp: Date.now(),
        isError: true
      };
      setMessages((prev) => [...prev, errorMessage]);
    };

    try {
      // Try SSE streaming first (preferred for better UX)
      const result = await fetchQAStream({
        workspaceId: resolvedWs,
        question: q,
        onStage: (newStage) => {
          // Update stage for UI feedback
          // Stages: queued → translating → executing → formatting
          setStage(newStage);
        }
      });
      addAiResponse(result);
    } catch (streamError) {
      // Fallback to polling if streaming fails
      // WHY: Graceful degradation for browsers without ReadableStream support
      console.warn('[Copilot] SSE streaming failed, falling back to polling:', streamError.message);

      try {
        const result = await fetchQA({ workspaceId: resolvedWs, question: q });
        addAiResponse(result);
      } catch (pollError) {
        addErrorMessage(pollError.message);
      }
    } finally {
      setLoading(false);
      setStage(null); // Clear stage when done
    }
  };

  return (
    <div className="mesh-bg h-full relative flex flex-col md:pl-[90px]">
      {/* Conversation Area */}
      <main className="flex-1 overflow-y-auto pt-8 pb-48 w-full">
        {/* Pass stage for real-time progress indicator (v2.1) */}
        <ConversationThread messages={messages} isLoading={loading} stage={stage} />
      </main>

      {/* Fixed Input Bar */}
      <ChatConsole onSubmit={handleSubmit} disabled={loading} noWorkspace={!resolvedWs} />
    </div>
  );
}
