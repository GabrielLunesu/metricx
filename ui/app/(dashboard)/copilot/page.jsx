"use client";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { fetchQA, fetchQAStream, fetchQASemantic, fetchQAAgent } from "@/lib/api";
import { currentUser } from "@/lib/workspace";
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

  // Tool events state (v5.0 - Agentic Feedback)
  // WHY: Shows users what the agent is doing in real-time
  const [toolEvents, setToolEvents] = useState([]);

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

  // Handle question submission with Agentic Copilot (v4.0)
  // WHAT: Uses LangGraph + Claude agent first, falls back to semantic/streaming/polling
  // WHY: Feels like talking to a smart human that understands any question naturally
  //      Agent generates visualizations automatically for comparison queries
  // Streaming message state for typing effect
  const [streamingText, setStreamingText] = useState('');
  const streamingIdRef = useRef(null);
  const streamingBufferRef = useRef(''); // Buffer for accumulating tokens
  const rafRef = useRef(null); // requestAnimationFrame ID

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
    setStreamingText(''); // Reset streaming text
    streamingBufferRef.current = ''; // Reset buffer
    setToolEvents([]); // Reset tool events for new question

    // Create a placeholder AI message for streaming
    const streamingId = Date.now();
    streamingIdRef.current = streamingId;

    // Function to flush buffer to state (called via requestAnimationFrame)
    const flushBuffer = () => {
      if (streamingIdRef.current === streamingId && streamingBufferRef.current) {
        setStreamingText(streamingBufferRef.current);
      }
      rafRef.current = requestAnimationFrame(flushBuffer);
    };
    // Start the render loop
    rafRef.current = requestAnimationFrame(flushBuffer);

    // Helper to add final AI response (replaces streaming placeholder)
    const addAiResponse = (res) => {
      // Stop the render loop
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      setStreamingText(''); // Clear streaming text
      streamingBufferRef.current = ''; // Clear buffer
      streamingIdRef.current = null;
      const aiMessage = {
        type: 'ai',
        text: renderMarkdownLite(res.answer),
        timestamp: Date.now(),
        visuals: res.visuals,
        data: res.data,
        executedDsl: res.executed_dsl,
        // NEW: Include tool events and data sources for display
        toolEvents: res.toolEvents || [],
        toolCallsMade: res.toolCallsMade || [],
      };
      setMessages((prev) => [...prev, aiMessage]);
    };

    // Helper to add error message
    const addErrorMessage = (error) => {
      // Stop the render loop
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      setStreamingText('');
      streamingBufferRef.current = '';
      streamingIdRef.current = null;
      const errorMessage = {
        type: 'ai',
        text: `I encountered an error: ${error}. Please try again.`,
        timestamp: Date.now(),
        isError: true
      };
      setMessages((prev) => [...prev, errorMessage]);
    };

    try {
      // Try Agentic Copilot with streaming (preferred - typing effect)
      const result = await fetchQAAgent({
        workspaceId: resolvedWs,
        question: q,
        onStage: (newStage) => {
          setStage(newStage);
        },
        onToken: (token) => {
          // Accumulate tokens in buffer (RAF will flush to state)
          if (streamingIdRef.current === streamingId) {
            streamingBufferRef.current += token;
          }
        },
        // NEW: Capture tool events for ThinkingAccordion
        onToolEvent: (event) => {
          setToolEvents((prev) => [...prev, event]);
        }
      });
      addAiResponse(result);
    } catch {
      // Fallback to Semantic Layer if agent fails
      // Stop the render loop when falling back
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      setStreamingText('');
      streamingBufferRef.current = '';

      try {
        const result = await fetchQASemantic({
          workspaceId: resolvedWs,
          question: q,
          onStage: (newStage) => {
            setStage(newStage);
          }
        });
        addAiResponse(result);
      } catch {
        // Fallback to SSE streaming if semantic fails
        try {
          const result = await fetchQAStream({
            workspaceId: resolvedWs,
            question: q,
            onStage: (newStage) => {
              setStage(newStage);
            }
          });
          addAiResponse(result);
        } catch {
          // Final fallback to polling
          try {
            const result = await fetchQA({ workspaceId: resolvedWs, question: q });
            addAiResponse(result);
          } catch (pollError) {
            addErrorMessage(pollError.message);
          }
        }
      }
    } finally {
      setLoading(false);
      setStage(null); // Clear stage when done
    }
  };

  return (
    <div className="mesh-bg h-full relative flex flex-col items-center">
      {/* Conversation Area - centered in available space */}
      <main className="flex-1 overflow-y-auto pt-8 pb-52 md:pb-44 w-full max-w-[900px] px-4">
        {/* Pass stage, streamingText, and toolEvents for real-time feedback (v5.0) */}
        <ConversationThread
          messages={messages}
          isLoading={loading}
          stage={stage}
          streamingText={streamingText}
          toolEvents={toolEvents}
        />
      </main>

      {/* Input Bar - absolute within centered container */}
      <ChatConsole onSubmit={handleSubmit} disabled={loading} noWorkspace={!resolvedWs} />
    </div>
  );
}
