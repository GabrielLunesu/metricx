"use client";
/**
 * BlogClientShell — Interactive blog index with animations and filters
 *
 * WHAT: Client component wrapping the blog listing with smooth scrolling,
 *       category filters, scroll animations, and reading progress indicator.
 * WHY:  Enables Lenis smooth scroll, framer-motion animations, and
 *       interactive category filtering while keeping data fetching on server.
 */

import { useEffect, useState, useRef, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import Lenis from "lenis";
import dynamic from "next/dynamic";

const MeshGradientShader = dynamic(
    () =>
        import("@paper-design/shaders-react").then((mod) => ({
            default: mod.MeshGradient,
        })),
    {
        ssr: false,
        loading: () => (
            <div className="w-full h-full bg-gradient-to-br from-blue-50 via-indigo-50 to-cyan-50" />
        ),
    }
);

/* ─── Category colour map (matches categories.json) ─── */
const colorMap = {
    cyan: "bg-cyan-100 text-cyan-700 border-cyan-200",
    blue: "bg-blue-100 text-blue-700 border-blue-200",
    red: "bg-red-100 text-red-700 border-red-200",
    pink: "bg-pink-100 text-pink-700 border-pink-200",
    purple: "bg-purple-100 text-purple-700 border-purple-200",
    green: "bg-green-100 text-green-700 border-green-200",
    amber: "bg-amber-100 text-amber-700 border-amber-200",
    indigo: "bg-indigo-100 text-indigo-700 border-indigo-200",
    slate: "bg-slate-100 text-slate-700 border-slate-200",
};

/* ─── Framer-motion variants ─── */
const containerVariants = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.08 } },
};

const cardVariants = {
    hidden: { opacity: 0, y: 30, filter: "blur(6px)" },
    visible: {
        opacity: 1,
        y: 0,
        filter: "blur(0px)",
        transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] },
    },
};

const fadeUp = {
    hidden: { opacity: 0, y: 20 },
    visible: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] },
    },
};

export default function BlogClientShell({ posts, categories, featuredPost }) {
    const [activeCategory, setActiveCategory] = useState("all");
    const [scrollProgress, setScrollProgress] = useState(0);

    /* ── Lenis smooth scrolling ── */
    useEffect(() => {
        const lenis = new Lenis({
            duration: 1.2,
            easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
            smoothWheel: true,
        });

        function raf(time) {
            lenis.raf(time);
            requestAnimationFrame(raf);
        }
        requestAnimationFrame(raf);

        return () => lenis.destroy();
    }, []);

    /* ── Reading progress bar ── */
    useEffect(() => {
        function handleScroll() {
            const scrollTop = window.scrollY;
            const docHeight =
                document.documentElement.scrollHeight - window.innerHeight;
            setScrollProgress(docHeight > 0 ? (scrollTop / docHeight) * 100 : 0);
        }
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    /* ── Filter posts ── */
    const filteredPosts = useMemo(() => {
        if (activeCategory === "all") return posts;
        return posts.filter((p) => p.category === activeCategory);
    }, [posts, activeCategory]);

    /* ── Category lookup helper ── */
    const getCategoryName = (slug) => {
        const cat = categories.find((c) => c.slug === slug);
        return cat?.name ?? slug;
    };

    const getCategoryColor = (slug) => {
        const cat = categories.find((c) => c.slug === slug);
        return colorMap[cat?.color] ?? colorMap.slate;
    };

    return (
        <>
            {/* ── Scroll progress indicator ── */}
            <div className="fixed top-0 left-0 right-0 z-[100] h-[3px]">
                <motion.div
                    className="h-full bg-gradient-to-r from-blue-500 via-cyan-400 to-emerald-400"
                    style={{ width: `${scrollProgress}%` }}
                    transition={{ duration: 0.1, ease: "linear" }}
                />
            </div>

            {/* ═══════════════ HERO ═══════════════ */}
            <section className="relative overflow-hidden -mt-20">
                {/* Shader background — only covers top portion */}
                <div className="absolute inset-x-0 top-0 h-[85%] z-0 pointer-events-none">
                    <MeshGradientShader
                        style={{
                            width: "100%",
                            height: "100%",
                            position: "absolute",
                            top: 0,
                            left: 0,
                        }}
                        colors={[
                            "#0ea5e9",
                            "#38bdf8",
                            "#7dd3fc",
                            "#0284c7",
                            "#06b6d4",
                        ]}
                        speed={1.5}
                        distortion={0.3}
                        swirl={0.2}
                    />
                    {/* Fade to pure white */}
                    <div
                        className="absolute bottom-0 left-0 right-0 h-[60%] z-10"
                        style={{
                            background:
                                "linear-gradient(to bottom, transparent 0%, rgba(255,255,255,0.2) 20%, rgba(255,255,255,0.5) 40%, rgba(255,255,255,0.85) 65%, #ffffff 100%)",
                        }}
                    />
                </div>

                <div className="relative z-[1] max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 sm:pt-40 pb-28 sm:pb-40">
                    <motion.div
                        initial="hidden"
                        animate="visible"
                        variants={containerVariants}
                        className="text-center"
                    >
                        {/* <motion.div variants={fadeUp}>
                            <span className="inline-flex items-center gap-2 text-xs text-white/90 font-geist bg-white/20 backdrop-blur-md border border-white/30 rounded-full px-3 py-1">
                                <span className="inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                metricx Blog
                            </span>
                        </motion.div> */}

                        <motion.h1
                            variants={fadeUp}
                            className="mt-6 text-4xl sm:text-5xl md:text-6xl lg:text-7xl tracking-tighter font-geist text-gray-950 leading-[0.95]"
                        >
                            Insights for
                            <br />
                            <span className="text-gray-950">smarter ad spend</span>
                        </motion.h1>

                        <motion.p
                            variants={fadeUp}
                            className="mt-6 text-base sm:text-lg text-gray-950 font-geist max-w-2xl mx-auto"
                        >
                            Expert guides on ROAS optimisation, multi-platform tracking,
                            attribution, and data-driven e-commerce growth — written by
                            industry veterans.
                        </motion.p>
                    </motion.div>
                </div>
            </section>

            {/* ═══════════════ FEATURED POST ═══════════════ */}
            {featuredPost && (
                <section className="relative bg-white">
                    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 -mt-8 sm:-mt-12 relative z-10">
                        <motion.div
                            initial={{ opacity: 0, y: 40 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-100px" }}
                            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                        >
                            <Link href={`/blog/${featuredPost.slug}`} className="group block">
                                <article className="relative rounded-3xl bg-gray-950 p-6 sm:p-10 ring-1 ring-white/10 overflow-hidden hover:ring-white/20 transition-all duration-500 shadow-2xl">
                                    {/* Gradient blobs */}
                                    <div className="absolute -right-20 -top-20 h-60 w-60 rounded-full bg-blue-500/20 blur-3xl" />
                                    <div className="absolute -left-10 -bottom-20 h-60 w-60 rounded-full bg-emerald-400/15 blur-3xl" />

                                    <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-10 items-center">
                                        {/* Left: Content */}
                                        <div>
                                            <div className="flex items-center gap-3 mb-4">
                                                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-400/10 rounded-full px-2.5 py-1 border border-emerald-400/20">
                                                    Featured
                                                </span>
                                                <span className="text-xs text-white/50 font-geist">
                                                    {featuredPost.readTime} min read
                                                </span>
                                            </div>
                                            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-geist tracking-tight text-white group-hover:text-white/90 transition-colors leading-tight">
                                                {featuredPost.title}
                                            </h2>
                                            <p className="mt-3 text-sm sm:text-base text-white/60 font-geist line-clamp-3">
                                                {featuredPost.excerpt}
                                            </p>
                                            <div className="mt-6 inline-flex items-center gap-2 text-sm text-white/80 font-geist group-hover:text-white transition-colors">
                                                Read article
                                                <svg
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    width="16"
                                                    height="16"
                                                    viewBox="0 0 24 24"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    strokeWidth="2"
                                                    className="transition-transform group-hover:translate-x-1"
                                                >
                                                    <path d="M5 12h14" />
                                                    <path d="m12 5 7 7-7 7" />
                                                </svg>
                                            </div>
                                        </div>

                                        {/* Right: Decorative card */}
                                        <div className="hidden lg:block">
                                            <div className="relative aspect-[4/3] rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 overflow-hidden">
                                                <div className="absolute inset-0 flex items-center justify-center">
                                                    <div className="text-center">
                                                        <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center mb-4">
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5">
                                                                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                                                                <polyline points="14 2 14 8 20 8" />
                                                                <path d="M16 13H8" />
                                                                <path d="M16 17H8" />
                                                                <path d="M10 9H8" />
                                                            </svg>
                                                        </div>
                                                        <p className="text-sm text-white/40 font-geist">
                                                            {getCategoryName(featuredPost.category)}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </article>
                            </Link>
                        </motion.div>
                    </div>
                </section>
            )}

            {/* ═══════════════ CATEGORY FILTERS + GRID ═══════════════ */}
            <section className="bg-white relative">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
                    {/* Category pills */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.6 }}
                        className="flex flex-wrap gap-2 mb-12"
                    >
                        <button
                            onClick={() => setActiveCategory("all")}
                            className={`px-4 py-2 rounded-full text-sm font-medium font-geist transition-all duration-300 border ${activeCategory === "all"
                                ? "bg-gray-900 text-white border-gray-900 shadow-lg shadow-gray-900/20"
                                : "bg-white text-gray-600 border-gray-200 hover:border-gray-300 hover:text-gray-900"
                                }`}
                        >
                            All Posts
                        </button>
                        {categories.slice(0, 8).map((cat) => (
                            <button
                                key={cat.slug}
                                onClick={() => setActiveCategory(cat.slug)}
                                className={`px-4 py-2 rounded-full text-sm font-medium font-geist transition-all duration-300 border ${activeCategory === cat.slug
                                    ? "bg-gray-900 text-white border-gray-900 shadow-lg shadow-gray-900/20"
                                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-300 hover:text-gray-900"
                                    }`}
                            >
                                {cat.name}
                            </button>
                        ))}
                    </motion.div>

                    {/* Post grid */}
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeCategory}
                            variants={containerVariants}
                            initial="hidden"
                            animate="visible"
                            exit="hidden"
                            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                        >
                            {filteredPosts.map((post) => (
                                <motion.div key={post.slug} variants={cardVariants}>
                                    <BlogCard
                                        post={post}
                                        categoryName={getCategoryName(post.category)}
                                        categoryColor={getCategoryColor(post.category)}
                                    />
                                </motion.div>
                            ))}
                        </motion.div>
                    </AnimatePresence>

                    {filteredPosts.length === 0 && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="text-center py-20"
                        >
                            <p className="text-gray-400 font-geist text-lg">
                                No posts in this category yet. Check back soon!
                            </p>
                        </motion.div>
                    )}
                </div>
            </section>

            {/* ═══════════════ NEWSLETTER CTA ═══════════════ */}
            <section className="bg-gray-950 relative overflow-hidden">
                <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute -left-1/4 top-10 h-[600px] w-[600px] rounded-full bg-indigo-500/10 blur-3xl" />
                    <div className="absolute -right-1/3 bottom-0 h-[800px] w-[800px] rounded-full bg-blue-500/10 blur-3xl" />
                </div>

                <div className="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28 text-center">
                    <motion.div
                        initial={{ opacity: 0, y: 30 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                    >
                        <span className="inline-flex items-center gap-2 text-xs text-white/70 font-geist bg-white/5 backdrop-blur-md border border-white/10 rounded-full px-3 py-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
                            Stay in the loop
                        </span>
                        <h2 className="mt-6 text-3xl sm:text-4xl md:text-5xl font-geist tracking-tight text-white">
                            Get smarter about
                            <br />
                            <span className="text-white/50">your ad spend</span>
                        </h2>
                        <p className="mt-4 text-sm sm:text-base text-white/60 font-geist max-w-lg mx-auto">
                            Join 3,000+ e-commerce marketers receiving weekly insights on ad
                            analytics, ROAS optimization, and growth strategies.
                        </p>
                        <div className="mt-8">
                            <Link
                                href="/sign-up"
                                className="group inline-flex items-center gap-3 bg-white text-gray-900 rounded-full px-8 py-4 text-sm font-medium hover:bg-gray-100 transition-all duration-300 shadow-xl font-geist"
                            >
                                Start Free Trial
                                <div className="relative flex items-center justify-center w-5 h-5 bg-gray-900/10 rounded-full group-hover:bg-gray-900/20 transition-all duration-300">
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                        className="transition-transform duration-300 group-hover:translate-x-0.5"
                                    >
                                        <path d="M5 12h14" />
                                        <path d="m12 5 7 7-7 7" />
                                    </svg>
                                </div>
                            </Link>
                        </div>
                    </motion.div>
                </div>
            </section>
        </>
    );
}

/* ═══════════════════════════════════════════════
   BlogCard — Single post card
   ═══════════════════════════════════════════════ */

function BlogCard({ post, categoryName, categoryColor }) {
    return (
        <Link href={`/blog/${post.slug}`} className="group block h-full">
            <article className="relative h-full rounded-2xl sm:rounded-3xl bg-white/80 backdrop-blur-md ring-1 ring-gray-200 p-5 sm:p-6 hover:shadow-xl hover:-translate-y-1 transition-all duration-500 flex flex-col">
                {/* Top: Category + Read time */}
                <div className="flex items-center justify-between mb-4">
                    <span
                        className={`inline-flex items-center text-[11px] font-medium rounded-full px-2.5 py-1 border ${categoryColor}`}
                    >
                        {categoryName}
                    </span>
                    <span className="text-xs text-gray-400 font-geist">
                        {post.readTime} min
                    </span>
                </div>

                {/* Title */}
                <h3 className="text-lg sm:text-xl font-geist tracking-tight text-gray-900 group-hover:text-gray-700 transition-colors leading-snug line-clamp-2">
                    {post.title}
                </h3>

                {/* Excerpt */}
                <p className="mt-2 text-sm text-gray-500 font-geist line-clamp-3 flex-1">
                    {post.excerpt}
                </p>

                {/* Bottom: Date + Arrow */}
                <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
                    <time
                        className="text-xs text-gray-400 font-geist"
                        dateTime={post.publishedAt}
                    >
                        {new Date(post.publishedAt).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                        })}
                    </time>
                    <span className="inline-flex items-center gap-1 text-xs text-gray-500 font-geist group-hover:text-gray-900 transition-colors">
                        Read
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            className="transition-transform group-hover:translate-x-0.5"
                        >
                            <path d="M5 12h14" />
                            <path d="m12 5 7 7-7 7" />
                        </svg>
                    </span>
                </div>
            </article>
        </Link>
    );
}
