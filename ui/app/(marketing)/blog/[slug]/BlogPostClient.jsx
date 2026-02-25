"use client";
/**
 * BlogPostClient — Premium individual blog post renderer
 *
 * WHAT: Client component rendering a single blog post with reading progress,
 *       smooth scroll, animated content blocks, author card, and related posts.
 * WHY:  Interactive features (scroll tracking, Lenis, framer-motion) require
 *       a client component. Design matches the AWWWARD-level blog index.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import Lenis from "lenis";

const fadeUp = {
    hidden: { opacity: 0, y: 24 },
    visible: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] },
    },
};

const stagger = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.12 } },
};

/* ── Colour map ── */
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

export default function BlogPostClient({ post, author, category, relatedPosts }) {
    const [scrollProgress, setScrollProgress] = useState(0);

    /* Lenis smooth scrolling */
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

    /* Scroll progress */
    useEffect(() => {
        function onScroll() {
            const top = window.scrollY;
            const h = document.documentElement.scrollHeight - window.innerHeight;
            setScrollProgress(h > 0 ? (top / h) * 100 : 0);
        }
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => window.removeEventListener("scroll", onScroll);
    }, []);

    const catColor = colorMap[category?.color] ?? colorMap.slate;
    const publishedDate = new Date(post.publishedAt).toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
    });

    /* Build table of contents from headings */
    const toc = (post.content ?? [])
        .filter((b) => b.type === "heading" && b.level === 2)
        .map((b) => ({
            text: b.text,
            id: b.text
                .toLowerCase()
                .replace(/[^a-z0-9]+/g, "-")
                .replace(/(^-|-$)/g, ""),
        }));

    return (
        <>
            {/* ── Scroll progress ── */}
            <div className="fixed top-0 left-0 right-0 z-[100] h-[3px]">
                <motion.div
                    className="h-full bg-gradient-to-r from-blue-500 via-cyan-400 to-emerald-400"
                    style={{ width: `${scrollProgress}%` }}
                    transition={{ duration: 0.1, ease: "linear" }}
                />
            </div>

            {/* ═══ HERO ═══ */}
            <section className="relative bg-white border-b border-gray-100">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 sm:pt-28 pb-12 sm:pb-16">
                    <motion.div initial="hidden" animate="visible" variants={stagger}>
                        {/* Breadcrumb */}
                        <motion.nav variants={fadeUp} className="flex items-center gap-2 text-sm text-gray-400 font-geist mb-8">
                            <Link href="/blog" className="hover:text-gray-900 transition-colors">
                                Blog
                            </Link>
                            <span>/</span>
                            <span className={`inline-flex items-center text-[11px] font-medium rounded-full px-2.5 py-0.5 border ${catColor}`}>
                                {category?.name ?? post.category}
                            </span>
                        </motion.nav>

                        {/* Title */}
                        <motion.h1
                            variants={fadeUp}
                            className="text-3xl sm:text-4xl md:text-5xl font-geist tracking-tight text-gray-900 leading-tight"
                        >
                            {post.title}
                        </motion.h1>

                        {/* Meta row */}
                        <motion.div variants={fadeUp} className="mt-6 flex flex-wrap items-center gap-4">
                            {/* Author */}
                            {author && (
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-white text-sm font-bold font-geist">
                                        {author.name.charAt(0)}
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium text-gray-900 font-geist">
                                            {author.name}
                                        </p>
                                        <p className="text-xs text-gray-400 font-geist">
                                            {author.role}
                                        </p>
                                    </div>
                                </div>
                            )}

                            <div className="hidden sm:block h-6 w-px bg-gray-200" />

                            <div className="flex items-center gap-3 text-xs text-gray-400 font-geist">
                                <time dateTime={post.publishedAt}>{publishedDate}</time>
                                <span>·</span>
                                <span>{post.readTime} min read</span>
                            </div>
                        </motion.div>

                        {/* Tags */}
                        {post.tags && post.tags.length > 0 && (
                            <motion.div variants={fadeUp} className="mt-6 flex flex-wrap gap-2">
                                {post.tags.map((tag) => (
                                    <span
                                        key={tag}
                                        className="text-[11px] font-medium text-gray-500 bg-gray-100 rounded-full px-2.5 py-1 font-geist"
                                    >
                                        {tag}
                                    </span>
                                ))}
                            </motion.div>
                        )}
                    </motion.div>
                </div>
            </section>

            {/* ═══ CONTENT ═══ */}
            <section className="bg-white">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
                    <div className="grid grid-cols-1 lg:grid-cols-[1fr_200px] gap-12">
                        {/* Article body */}
                        <motion.article
                            initial="hidden"
                            whileInView="visible"
                            viewport={{ once: true, margin: "-50px" }}
                            variants={stagger}
                            className="prose-custom"
                        >
                            {(post.content ?? []).map((block, i) => (
                                <ContentBlock key={i} block={block} />
                            ))}
                        </motion.article>

                        {/* Table of contents sidebar (desktop only) */}
                        {toc.length > 0 && (
                            <aside className="hidden lg:block">
                                <div className="sticky top-28">
                                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider font-geist mb-4">
                                        On this page
                                    </p>
                                    <nav className="space-y-2">
                                        {toc.map((item) => (
                                            <a
                                                key={item.id}
                                                href={`#${item.id}`}
                                                className="block text-sm text-gray-400 hover:text-gray-900 transition-colors font-geist leading-relaxed"
                                            >
                                                {item.text}
                                            </a>
                                        ))}
                                    </nav>
                                </div>
                            </aside>
                        )}
                    </div>
                </div>
            </section>

            {/* ═══ RELATED POSTS ═══ */}
            {relatedPosts.length > 0 && (
                <section className="bg-gray-50 border-t border-gray-100">
                    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.6 }}
                        >
                            <h2 className="text-2xl sm:text-3xl font-geist tracking-tight text-gray-900 mb-8">
                                Related articles
                            </h2>
                        </motion.div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {relatedPosts.map((rp, i) => (
                                <motion.div
                                    key={rp.slug}
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ delay: i * 0.1, duration: 0.6 }}
                                >
                                    <Link href={`/blog/${rp.slug}`} className="group block h-full">
                                        <article className="h-full rounded-2xl bg-white ring-1 ring-gray-200 p-5 hover:shadow-lg hover:-translate-y-1 transition-all duration-500 flex flex-col">
                                            <span className="text-xs text-gray-400 font-geist">
                                                {rp.readTime} min read
                                            </span>
                                            <h3 className="mt-2 text-base font-geist tracking-tight text-gray-900 group-hover:text-gray-600 transition-colors line-clamp-2 flex-1">
                                                {rp.title}
                                            </h3>
                                            <p className="mt-2 text-sm text-gray-400 font-geist line-clamp-2">
                                                {rp.excerpt}
                                            </p>
                                        </article>
                                    </Link>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </section>
            )}

            {/* ═══ CTA — FLOATING ISLANDS ═══ */}
            <section className="bg-white border-t border-gray-100">
                <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20">
                    <motion.div
                        initial="hidden"
                        whileInView="visible"
                        viewport={{ once: true, margin: "-60px" }}
                        variants={stagger}
                        className="flex flex-col gap-4"
                    >
                        {/* ── Island 1: Main CTA card ── */}
                        <motion.div variants={fadeUp}>
                            <Link href="/sign-up" className="group block">
                                <div className="relative overflow-hidden rounded-2xl bg-gray-950 p-8 sm:p-10 transition-shadow duration-500 hover:shadow-2xl">
                                    {/* Soft ambient glow */}
                                    <div className="absolute -top-24 -right-24 w-64 h-64 rounded-full bg-blue-500/10 blur-[80px] pointer-events-none" />
                                    <div className="absolute -bottom-20 -left-20 w-56 h-56 rounded-full bg-cyan-400/8 blur-[80px] pointer-events-none" />

                                    <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
                                        <div className="flex-1 min-w-0">
                                            <h2 className="text-2xl sm:text-3xl font-geist tracking-tight text-white leading-snug">
                                                All your ad data.{" "}
                                                <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-cyan-300 to-emerald-400">
                                                    One clear view.
                                                </span>
                                            </h2>
                                            <p className="mt-3 text-sm sm:text-base text-gray-400 leading-relaxed font-geist max-w-md">
                                                Metricx connects Meta &amp; Google ads to your
                                                Shopify store — see what drives revenue, cut what doesn&apos;t.
                                            </p>
                                        </div>

                                        <div className="shrink-0">
                                            <span className="inline-flex items-center gap-2 bg-white text-gray-900 px-6 py-3 rounded-full text-sm font-semibold font-geist group-hover:scale-[1.04] transition-transform duration-300">
                                                Start Free Trial
                                                <svg
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    width="16"
                                                    height="16"
                                                    viewBox="0 0 24 24"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    strokeWidth="2"
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    className="transition-transform duration-300 group-hover:translate-x-1"
                                                >
                                                    <path d="M5 12h14" />
                                                    <path d="m12 5 7 7-7 7" />
                                                </svg>
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </Link>
                        </motion.div>

                        {/* ── Island 2: Trust row — three small cards ── */}
                        <motion.div variants={fadeUp} className="grid grid-cols-3 gap-3 sm:gap-4">
                            {[
                                { text: "14-day free trial", icon: "M5 13l4 4L19 7" },
                                { text: "No credit card", icon: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" },
                                { text: "2-min setup", icon: "M13 2L3 14h9l-1 8 10-12h-9l1-8z" },
                            ].map((item) => (
                                <div
                                    key={item.text}
                                    className="rounded-xl bg-white ring-1 ring-gray-200 px-4 py-3.5 text-center hover:ring-gray-300 hover:shadow-sm transition-all duration-300"
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        width="16"
                                        height="16"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        className="mx-auto text-gray-400 mb-1.5"
                                    >
                                        <path d={item.icon} />
                                    </svg>
                                    <p className="text-xs font-medium text-gray-500 font-geist">
                                        {item.text}
                                    </p>
                                </div>
                            ))}
                        </motion.div>
                    </motion.div>
                </div>
            </section>

            {/* ═══ BACK TO BLOG CTA ═══ */}
            <section className="bg-white border-t border-gray-100">
                <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center">
                    <Link
                        href="/blog"
                        className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors font-geist"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M19 12H5" />
                            <path d="m12 19-7-7 7-7" />
                        </svg>
                        Back to all articles
                    </Link>
                </div>
            </section>
        </>
    );
}

/* ═══════════════════════════════════════════
   ContentBlock — renders a single content block
   ═══════════════════════════════════════════ */

function ContentBlock({ block }) {
    if (block.type === "heading") {
        const id = block.text
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/(^-|-$)/g, "");

        if (block.level === 2) {
            return (
                <motion.h2
                    id={id}
                    variants={fadeUp}
                    className="mt-12 mb-4 text-2xl sm:text-3xl font-geist tracking-tight text-gray-900 scroll-mt-28"
                >
                    {block.text}
                </motion.h2>
            );
        }
        if (block.level === 3) {
            return (
                <motion.h3
                    id={id}
                    variants={fadeUp}
                    className="mt-8 mb-3 text-xl sm:text-2xl font-geist tracking-tight text-gray-900 scroll-mt-28"
                >
                    {block.text}
                </motion.h3>
            );
        }
    }

    if (block.type === "paragraph") {
        return (
            <motion.p
                variants={fadeUp}
                className="mb-6 text-base sm:text-lg leading-relaxed text-gray-600 font-geist"
            >
                {block.text}
            </motion.p>
        );
    }

    return null;
}
