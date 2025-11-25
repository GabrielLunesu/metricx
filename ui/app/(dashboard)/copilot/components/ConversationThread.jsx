import { Sparkles } from "lucide-react";
import { useRef, useEffect } from "react";
import AnswerVisuals from "./AnswerVisuals";

// Stage Indicator Component (v2.1)
// WHAT: Shows real-time progress during QA processing
// WHY: Better UX with live stage updates from SSE streaming
// Stages: queued → translating → executing → formatting → complete
function StageIndicator({ stage }) {
  // Human-readable stage messages (Apple-like minimal copy)
  const stageMessages = {
    queued: "Queuing...",
    translating: "Understanding your question...",
    executing: "Fetching data...",
    formatting: "Preparing answer...",
    processing: "Processing..."
  };

  // Don't show indicator for null/complete stages
  if (!stage || stage === 'complete') return null;

  return (
    <div className="flex items-center gap-2.5 text-sm text-slate-500">
      {/* Subtle pulsing dot - Apple-like */}
      <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
      <span className="font-medium">{stageMessages[stage] || "Processing..."}</span>
    </div>
  );
}

// AI Message Bubble (v2.1 - Subtle Glass Design)
// WHAT: Glass-morphism bubble with lighter blur and cleaner shadows
// WHY: Apple-inspired subtle aesthetic, reduced visual noise
function AIMessage({ text, isTyping, visuals, stage }) {
  return (
    <div className="flex gap-4 group animate-fade-in-up">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-gradient-to-b from-blue-500 to-blue-600 flex items-center justify-center text-white shadow-sm shrink-0 mt-1">
        <Sparkles className="w-4 h-4" />
      </div>
      {/* Bubble - Subtle glass effect (lighter blur, cleaner borders) */}
      <div className="w-full">
        <div className="p-0.5 rounded-2xl">
          <div className="bg-white/95 backdrop-blur-sm border border-slate-200/40 shadow-sm hover:shadow-md transition-shadow duration-300 rounded-2xl p-5 md:p-6 space-y-4">
            {isTyping ? (
              <StageIndicator stage={stage} />
            ) : (
              <div className="text-sm text-slate-700 leading-relaxed space-y-3">
                <div dangerouslySetInnerHTML={{ __html: text }} />
                <AnswerVisuals visuals={visuals} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// User Message Bubble (v2.1 - Subtle Glass Design)
// WHAT: Clean white bubble with subtle border
// WHY: Apple-inspired minimal aesthetic
function UserMessage({ text }) {
  return (
    <div className="flex flex-row-reverse gap-4 group animate-fade-in-up">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 border border-slate-200/60 shadow-sm shrink-0 mt-1">
        <span className="text-xs font-bold">JD</span>
      </div>
      {/* Bubble - Clean white with subtle border */}
      <div className="max-w-[80%] lg:max-w-[70%]">
        <div className="bg-white border border-slate-200/60 shadow-sm px-5 py-3.5 rounded-2xl text-sm leading-relaxed text-slate-700">
          {text}
        </div>
      </div>
    </div>
  );
}

// Conversation Thread (v2.1)
// WHAT: Main conversation container with messages and loading states
// WHY: Displays chat history with real-time stage updates during processing
// PROPS:
//   - messages: Array of user/ai messages
//   - isLoading: Boolean for loading state
//   - stage: Current processing stage (from SSE streaming)
export default function ConversationThread({ messages = [], isLoading, stage }) {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new message arrives or stage changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isLoading, stage]);

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-8 flex flex-col gap-8">
      {/* Empty state when no messages - Apple-like minimal */}
      {messages.length === 0 && !isLoading && (
        <div className="text-center py-20">
          <div className="flex justify-center mb-6">
            <div className="w-12 h-12 rounded-full bg-gradient-to-b from-blue-500 to-blue-600 flex items-center justify-center text-white shadow-sm">
              <Sparkles className="w-6 h-6" />
            </div>
          </div>
          <h2 className="text-xl font-semibold text-slate-800 mb-2">Welcome to AdNavi Copilot</h2>
          <p className="text-slate-500 text-sm">Ask me anything about your campaigns, ad sets, and ads.</p>
        </div>
      )}

      {/* Time Divider for first message */}
      {messages.length > 0 && (
        <div className="flex justify-center">
          <span className="text-[10px] font-medium text-slate-400 bg-slate-100/60 px-3 py-1 rounded-full">
            {new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </span>
        </div>
      )}

      {/* Render actual messages */}
      {messages.map((msg, idx) => (
        <div
          key={msg.timestamp || `${msg.type}-${idx}`}
          style={{ animationDelay: `${idx * 0.08}s` }}
        >
          {msg.type === 'ai' ? (
            <AIMessage text={msg.text} visuals={msg.visuals} />
          ) : (
            <UserMessage text={msg.text} />
          )}
        </div>
      ))}

      {/* Loading indicator with real-time stage updates (v2.1) */}
      {isLoading && (
        <div style={{ animationDelay: `${messages.length * 0.08}s` }}>
          <AIMessage isTyping={true} stage={stage} />
        </div>
      )}

      {/* Invisible div for auto-scroll target */}
      <div ref={messagesEndRef} />
    </div>
  );
}
