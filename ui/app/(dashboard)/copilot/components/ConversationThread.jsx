import { Sparkles } from "lucide-react";
import { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useUser } from "@clerk/nextjs";
import AnswerVisuals from "./AnswerVisuals";
import ThinkingAccordion from "@/components/copilot/ThinkingAccordion";

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

// AI Message Bubble (v5.0 - With Tool Events)
// WHAT: Glass-morphism bubble with ThinkingAccordion for tool transparency
// WHY: Apple-inspired subtle aesthetic + shows what the agent is doing
function AIMessage({ text, isTyping, visuals, stage, toolEvents = [] }) {
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
            {/* ThinkingAccordion - Shows tool execution steps */}
            {toolEvents.length > 0 && (
              <ThinkingAccordion steps={toolEvents} isThinking={isTyping} />
            )}
            
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
// PROPS:
//   - text: Message content
//   - user: Clerk user object (for avatar and name)
function UserMessage({ text, user }) {
  // Get user initials for fallback avatar
  const getInitials = () => {
    if (user?.firstName && user?.lastName) {
      return `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`.toUpperCase();
    }
    if (user?.firstName) {
      return user.firstName.charAt(0).toUpperCase();
    }
    return 'U';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
      className="flex flex-row-reverse gap-4 group"
    >
      {/* Avatar - Shows user profile image or initials */}
      <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 border border-slate-200/60 shadow-sm shrink-0 mt-1 overflow-hidden">
        {user?.imageUrl ? (
          <img src={user.imageUrl} alt="Profile" className="w-full h-full object-cover" />
        ) : (
          <span className="text-xs font-bold">{getInitials()}</span>
        )}
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

// Conversation Thread (v5.0)
// WHAT: Main conversation container with messages, streaming, and tool events
// WHY: Displays chat history with real-time token streaming and tool transparency
// PROPS:
//   - messages: Array of user/ai messages (each ai message may have toolEvents)
//   - isLoading: Boolean for loading state
//   - stage: Current processing stage (from SSE streaming)
//   - streamingText: Text being streamed token-by-token (typing effect)
//   - toolEvents: Current tool events during streaming (for live typing indicator)
export default function ConversationThread({ messages = [], isLoading, stage, streamingText = '', toolEvents = [] }) {
  const messagesEndRef = useRef(null);
  const { user } = useUser();

  // Auto-scroll to bottom when new message arrives, stage changes, or streaming text updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isLoading, stage, streamingText]);

  return (
    <div className="w-full flex flex-col gap-8">
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
            Welcome to metricx Copilot
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
              <AIMessage
                text={msg.text}
                visuals={msg.visuals}
                toolEvents={msg.toolEvents || []}
              />
            ) : (
              <UserMessage text={msg.text} user={user} />
            )}
          </div>
        ))}
      </AnimatePresence>

      {/* Loading indicator with streaming text (v5.0) */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            key="loading-indicator"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
          >
            {streamingText ? (
              // Show streaming text with typing cursor + tool events
              <AIMessage 
                text={streamingText + '<span class="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse"></span>'} 
                toolEvents={toolEvents}
              />
            ) : (
              // Show stage indicator while waiting for tokens + tool events
              <AIMessage isTyping={true} stage={stage} toolEvents={toolEvents} />
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Invisible div for auto-scroll target */}
      <div ref={messagesEndRef} />
    </div>
  );
}
