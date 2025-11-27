"use client";
import { useState } from "react";
import { login, register } from "../../lib/auth";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "login") {
        await login(email, password);
        router.push("/dashboard");
      } else {
        await register(name, email, password);
        setMode("login");
        setError("Account created! Please check your email to verify your account before signing in.");
      }
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen grid place-items-center p-8 bg-white">
      <div className="text-center space-y-6 w-full max-w-md">
        {/* Back to home link */}
        <a href="/" className="inline-block text-sm font-medium text-neutral-500 hover:text-cyan-600 transition-colors mb-4">
          ← Back to home
        </a>

        {/* App title */}
        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight gradient-text mb-8">
          metricx
        </h1>

        {/* Auth card */}
        <div className="glass-card border border-neutral-200/60 rounded-3xl p-8 text-left shadow-xl">
          <div className="flex gap-4 mb-6 justify-center">
            <button
              onClick={() => {
                setMode("login");
                setError("");
              }}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${mode === "login"
                ? "bg-cyan-500 text-white shadow-lg shadow-cyan-500/30"
                : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
                }`}
            >
              Sign In
            </button>
            <button
              onClick={() => {
                setMode("register");
                setError("");
              }}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${mode === "register"
                ? "bg-cyan-500 text-white shadow-lg shadow-cyan-500/30"
                : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
                }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-2xl bg-white border border-neutral-200 px-4 py-3 text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">Email</label>
              <input
                type="email"
                required
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-2xl bg-white border border-neutral-200 px-4 py-3 text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">Password</label>
              <input
                type="password"
                required
                minLength={8}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-2xl bg-white border border-neutral-200 px-4 py-3 text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all"
              />
              <div className="flex justify-end mt-1">
                <a href="/auth/forgot-password" className="text-xs text-cyan-600 hover:text-cyan-700 font-medium transition-colors">
                  Forgot password?
                </a>
              </div>
            </div>

            {error && (
              <div className={`p-3 rounded-2xl text-sm ${error.includes("created")
                ? "bg-green-50 text-green-700 border border-green-200"
                : "bg-red-50 text-red-700 border border-red-200"
                }`}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-cyan-600 text-white px-4 py-3 font-medium hover:shadow-lg hover:shadow-cyan-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Processing..." : mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-neutral-200/60 text-center">
            <p className="text-sm text-neutral-500">
              {mode === "login" ? "Don't have an account? " : "Already have an account? "}
              <button
                onClick={() => {
                  setMode(mode === "login" ? "register" : "login");
                  setError("");
                }}
                className="text-cyan-600 hover:text-cyan-700 font-medium transition-colors"
              >
                {mode === "login" ? "Register" : "Sign in"}
              </button>
            </p>
          </div>
        </div>

        <p className="text-xs text-neutral-400">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </main>
  );
}

