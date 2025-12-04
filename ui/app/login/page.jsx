"use client";

/**
 * LoginPage - Combined login and registration page
 * Matches the new white theme with blue/cyan accents
 * Related: HeroSectionNew.jsx, auth pages
 */

import { useState } from "react";
import { login, register } from "../../lib/auth";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";

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
    <main className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-gray-50 via-white to-gray-50/50 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-br from-blue-100/40 via-cyan-100/30 to-transparent rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-md">
        {/* Back to home link */}
        <a
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors mb-8 group"
        >
          <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
          Back to home
        </a>

        {/* Logo */}
        <div className="flex justify-center mb-8">
          <Image
            src="/logo.png"
            alt="metricx"
            width={180}
            height={50}
            className="h-12 w-auto"
            priority
          />
        </div>

        {/* Auth card */}
        <div className="bg-white/80 backdrop-blur-xl border border-gray-200/60 rounded-3xl p-8 shadow-xl shadow-gray-200/40">
          {/* Mode toggle */}
          <div className="flex gap-2 mb-8 p-1 bg-gray-100 rounded-full">
            <button
              onClick={() => {
                setMode("login");
                setError("");
              }}
              className={`flex-1 px-4 py-2.5 rounded-full text-sm font-medium transition-all ${
                mode === "login"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => {
                setMode("register");
                setError("");
              }}
              className={`flex-1 px-4 py-2.5 rounded-full text-sm font-medium transition-all ${
                mode === "register"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={onSubmit} className="space-y-5">
            {mode === "register" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-xl bg-white border border-gray-200 px-4 py-3 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20 transition-all"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <input
                type="email"
                required
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl bg-white border border-gray-200 px-4 py-3 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
              <input
                type="password"
                required
                minLength={8}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl bg-white border border-gray-200 px-4 py-3 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20 transition-all"
              />
              {mode === "login" && (
                <div className="flex justify-end mt-2">
                  <a
                    href="/auth/forgot-password"
                    className="text-xs text-blue-600 hover:text-blue-700 font-medium transition-colors"
                  >
                    Forgot password?
                  </a>
                </div>
              )}
            </div>

            {error && (
              <div className={`p-4 rounded-xl text-sm ${
                error.includes("created")
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : "bg-red-50 text-red-700 border border-red-200"
              }`}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-gray-800 to-gray-950 text-white px-4 py-3.5 font-medium hover:shadow-lg hover:shadow-gray-900/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  {mode === "login" ? "Sign In" : "Create Account"}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-200/60 text-center">
            <p className="text-sm text-gray-500">
              {mode === "login" ? "Don't have an account? " : "Already have an account? "}
              <button
                onClick={() => {
                  setMode(mode === "login" ? "register" : "login");
                  setError("");
                }}
                className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
              >
                {mode === "login" ? "Register" : "Sign in"}
              </button>
            </p>
          </div>
        </div>

        <p className="text-xs text-gray-400 text-center mt-6">
          By signing in, you agree to our{" "}
          <a href="/terms" className="text-gray-500 hover:text-gray-700 underline">Terms of Service</a>
          {" "}and{" "}
          <a href="/privacy" className="text-gray-500 hover:text-gray-700 underline">Privacy Policy</a>
        </p>
      </div>
    </main>
  );
}
