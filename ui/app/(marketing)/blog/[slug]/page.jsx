/**
 * Individual Blog Post Page (server component)
 *
 * WHAT: Renders a single blog post by slug with SEO metadata.
 * WHY:  Enables deep-linking and SEO for individual articles.
 *
 * Related files:
 *  - lib/blog.js          — data access
 *  - ./BlogPostClient.jsx — client rendering with animations
 */

import { notFound } from "next/navigation";
import { getAllPosts, getPostBySlug, getAuthorById, getCategories } from "@/lib/blog";
import BlogPostClient from "./BlogPostClient";

/**
 * generateStaticParams — Pre-render all known post slugs at build time.
 */
export function generateStaticParams() {
    return getAllPosts().map((post) => ({ slug: post.slug }));
}

/**
 * generateMetadata — Dynamic SEO metadata per post.
 */
export async function generateMetadata({ params }) {
    const { slug } = await params;
    const post = getPostBySlug(slug);
    if (!post) return {};

    return {
        title: `${post.title} | metricx Blog`,
        description: post.excerpt,
        openGraph: {
            title: post.title,
            description: post.excerpt,
            type: "article",
            publishedTime: post.publishedAt,
            url: `https://www.metricx.ai/blog/${post.slug}`,
        },
        alternates: {
            canonical: `https://www.metricx.ai/blog/${post.slug}`,
        },
    };
}

export default async function BlogPostPage({ params }) {
    const { slug } = await params;
    const post = getPostBySlug(slug);
    if (!post) notFound();

    const author = getAuthorById(post.author);
    const categories = getCategories();
    const category = categories.find((c) => c.slug === post.category);

    // Get related posts (same category, exclude current)
    const allPosts = getAllPosts();
    const relatedPosts = allPosts
        .filter((p) => p.category === post.category && p.slug !== post.slug)
        .slice(0, 3);

    return (
        <BlogPostClient
            post={post}
            author={author}
            category={category}
            relatedPosts={relatedPosts}
        />
    );
}
