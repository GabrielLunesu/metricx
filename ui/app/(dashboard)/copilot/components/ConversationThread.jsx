import { Sparkles } from "lucide-react";
import { useRef, useEffect } from "react";

function AIMessage({ text, isTyping }) {
  return (
    <div className="flex gap-4 group animate-fade-in-up">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-gradient-to-b from-blue-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 shrink-0 mt-1">
        <Sparkles className="w-4 h-4" />
      </div>
      {/* Bubble */}
      <div className="max-w-[90%] lg:max-w-[85%] w-full">
        <div className="bubble-ai p-1.5 rounded-2xl">
          <div className="bg-white/50 rounded-xl p-5">
            {isTyping ? (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                <span>Getting your data...</span>
              </div>
            ) : (
              <div className="text-sm text-slate-700 leading-relaxed" dangerouslySetInnerHTML={{ __html: text }} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function UserMessage({ text }) {
  return (
    <div className="flex flex-row-reverse gap-4 group animate-fade-in-up">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 border border-white shadow-sm shrink-0 mt-1">
        <span className="text-xs font-bold">JD</span>
      </div>
      {/* Bubble */}
      <div className="max-w-[80%] lg:max-w-[70%]">
        <div className="bubble-user px-5 py-3.5 rounded-2xl text-sm leading-relaxed text-slate-700">
          {text}
        </div>
      </div>
    </div>
  );
}

export default function ConversationThread({ messages = [], isLoading }) {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new message arrives
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isLoading]);

  return (
    <div className="max-w-[900px] mx-auto px-4 sm:px-6 flex flex-col gap-10">
      {/* Empty state when no messages */}
      {messages.length === 0 && !isLoading && (
        <div className="text-center py-20">
          <div className="flex justify-center mb-6">
            <div className="w-12 h-12 rounded-full bg-gradient-to-b from-blue-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
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
          <span className="text-[10px] font-medium text-slate-400 bg-slate-100/50 px-3 py-1 rounded-full">
            {new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </span>
        </div>
      )}

      {/* Render actual messages */}
      {messages.map((msg, idx) => (
        <div
          key={msg.timestamp || `${msg.type}-${idx}`}
          style={{ animationDelay: `${idx * 0.1}s` }}
        >
          {msg.type === 'ai' ? (
            <AIMessage text={msg.text} />
          ) : (
            <UserMessage text={msg.text} />
          )}
        </div>
      ))}

      {/* Typing indicator during loading */}
      {isLoading && (
        <div style={{ animationDelay: `${messages.length * 0.1}s` }}>
          <AIMessage isTyping={true} />
        </div>
      )}

      {/* Invisible div for auto-scroll target */}
      <div ref={messagesEndRef} />
    </div>
  );
}
