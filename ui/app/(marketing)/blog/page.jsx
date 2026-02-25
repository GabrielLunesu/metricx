/**
 * Blog Index Page
 */

import Link from "next/link";
import { getAllPosts, getCategories, getFeaturedPosts } from "@/lib/blog";
import BlogClientShell from "./BlogClientShell";

export function generateMetadata() {
  return {
    title: "Blog — E-commerce Ad Analytics Insights | metricx",
    description:
      "Expert insights on ROAS optimization, multi-platform tracking, attribution strategies, and data-driven e-commerce growth.",
    openGraph: {
      title: "Blog | metricx",
      description: "Expert insights on e-commerce advertising and analytics.",
      type: "website",
      url: "https://www.metricx.ai/blog",
    },
    alternates: { canonical: "https://www.metricx.ai/blog" },
  };
}

export default function BlogPage() {
  const posts = getAllPosts();
  const categories = getCategories();
  const featuredPosts = getFeaturedPosts(1);

  return (
    <BlogClientShell
      posts={posts}
      categories={categories}
      featuredPost={featuredPosts[0] ?? null}
    />
  );
}
