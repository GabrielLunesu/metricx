import { Sparkles } from "lucide-react";
import { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-3 text-sm text-slate-500"
    >
      {/* Glassmorphic Mini Loader */}
      <div className="relative w-5 h-5">
        <svg className="w-full h-full" viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="loader-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#06b6d4" />
            </linearGradient>
          </defs>

          {/* Background Ring */}
          <circle cx="25" cy="25" r="20" stroke="rgba(203, 213, 225, 0.3)" strokeWidth="5" />

          {/* Rotating Arc */}
          <path d="M 25 5 a 20 20 0 0 1 20 20" stroke="url(#loader-gradient)" strokeWidth="5" strokeLinecap="round">
            <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="1s" repeatCount="indefinite" />
          </path>
        </svg>

        {/* Inner Glow */}
        <div className="absolute inset-0 bg-blue-400/20 blur-md rounded-full animate-pulse"></div>
      </div>

      <motion.span
        key={stage} // Animate text change
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        className="font-medium bg-gradient-to-r from-slate-600 to-slate-400 bg-clip-text text-transparent"
      >
        {stageMessages[stage] || "Processing..."}
      </motion.span>
    </motion.div>
  );
}

// AI Message Bubble (v2.1 - Subtle Glass Design)
// WHAT: Glass-morphism bubble with lighter blur and cleaner shadows
// WHY: Apple-inspired subtle aesthetic, reduced visual noise
function AIMessage({ text, isTyping, visuals, stage }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }} // Apple-like spring/ease
      className="flex gap-4 group"
    >
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-gradient-to-b from-blue-500 to-blue-600 flex items-center justify-center text-white shadow-sm shrink-0 mt-1">
        <Sparkles className="w-4 h-4" />
      </div>
      {/* Bubble - Subtle glass effect (lighter blur, cleaner borders) */}
      <div className="max-w-full">
        <div className="p-0.5 rounded-2xl">
          <motion.div
            layout // Enable layout animation for smooth expansion
            transition={{
              layout: { duration: 0.4, type: "spring", bounce: 0.2 }
            }}
            className="bg-white/95 backdrop-blur-sm border border-slate-200/40 shadow-sm hover:shadow-md transition-shadow duration-300 rounded-2xl p-5 md:p-6 space-y-4 overflow-hidden"
          >
            <AnimatePresence mode="wait">
              {isTyping ? (
                <motion.div
                  key="typing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <StageIndicator stage={stage} />
                </motion.div>
              ) : (
                <motion.div
                  key="content"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.1, duration: 0.4 }}
                  className="text-sm text-slate-700 leading-relaxed space-y-3"
                >
                  <div dangerouslySetInnerHTML={{ __html: text }} />
                  <AnswerVisuals visuals={visuals} />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}

// User Message Bubble (v2.1 - Subtle Glass Design)
// WHAT: Clean white bubble with subtle border
// WHY: Apple-inspired minimal aesthetic
function UserMessage({ text }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
      className="flex flex-row-reverse gap-4 group"
    >
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
    </motion.div>
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
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="flex justify-center mb-6"
          >
            <div className="w-12 h-12 rounded-full bg-gradient-to-b from-blue-500 to-blue-600 flex items-center justify-center text-white shadow-sm">
              <Sparkles className="w-6 h-6" />
            </div>
          </motion.div>
          <motion.h2
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="text-xl font-semibold text-slate-800 mb-2"
          >
            Welcome to AdNavi Copilot
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="text-slate-500 text-sm"
          >
            Ask me anything about your campaigns, ad sets, and ads.
          </motion.p>
        </div>
      )}

      {/* Time Divider for first message */}
      {messages.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex justify-center"
        >
          <span className="text-[10px] font-medium text-slate-400 bg-slate-100/60 px-3 py-1 rounded-full">
            {new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </span>
        </motion.div>
      )}

      {/* Render actual messages */}
      <AnimatePresence mode="popLayout">
        {messages.map((msg, idx) => (
          <div
            key={msg.timestamp || `${msg.type}-${idx}`}
          >
            {msg.type === 'ai' ? (
              <AIMessage text={msg.text} visuals={msg.visuals} />
            ) : (
              <UserMessage text={msg.text} />
            )}
          </div>
        ))}
      </AnimatePresence>

      {/* Loading indicator with real-time stage updates (v2.1) */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            key="loading-indicator"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
          >
            <AIMessage isTyping={true} stage={stage} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Invisible div for auto-scroll target */}
      <div ref={messagesEndRef} />
    </div>
  );
}
