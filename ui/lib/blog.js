/**
 * Blog Utility Library
 * ====================
 *
 * WHAT: Provides functions to read, parse, and filter blog posts from
 *       the content/blog directory.
 * WHY:  Centralises blog data access so pages and components can fetch
 *       posts without knowing the underlying file structure.
 *
 * Related files:
 *  - content/blog/posts/*.json   — individual blog post data
 *  - content/blog/authors.json   — author profiles
 *  - content/blog/categories.json — category definitions
 *  - app/(marketing)/blog/       — blog route pages
 */

import fs from "fs";
import path from "path";

const CONTENT_DIR = path.join(process.cwd(), "content", "blog");
const POSTS_DIR = path.join(CONTENT_DIR, "posts");

/**
 * getAllPosts - Reads every post JSON in content/blog/posts/ and returns
 * them sorted by publishedAt (newest first).
 *
 * @returns {Array<Object>} Sorted array of post objects.
 */
export function getAllPosts() {
    if (!fs.existsSync(POSTS_DIR)) return [];

    const files = fs.readdirSync(POSTS_DIR).filter((f) => f.endsWith(".json"));

    const posts = files.map((file) => {
        const raw = fs.readFileSync(path.join(POSTS_DIR, file), "utf-8");
        return JSON.parse(raw);
    });

    // Sort newest first
    return posts.sort(
        (a, b) => new Date(b.publishedAt) - new Date(a.publishedAt)
    );
}

/**
 * getPostBySlug - Returns a single post matching the given slug.
 *
 * @param {string} slug — URL-safe identifier for the post.
 * @returns {Object|null} The post object, or null if not found.
 */
export function getPostBySlug(slug) {
    const posts = getAllPosts();
    return posts.find((p) => p.slug === slug) ?? null;
}

/**
 * getPostsByCategory - Returns posts filtered by category slug.
 *
 * @param {string} categorySlug — The category slug to filter by.
 * @returns {Array<Object>} Filtered and sorted posts.
 */
export function getPostsByCategory(categorySlug) {
    return getAllPosts().filter((p) => p.category === categorySlug);
}

/**
 * getFeaturedPosts - Returns the subset of posts marked as featured.
 *
 * @param {number} limit — Max posts to return (default 3).
 * @returns {Array<Object>}
 */
export function getFeaturedPosts(limit = 3) {
    return getAllPosts()
        .filter((p) => p.featured)
        .slice(0, limit);
}

/**
 * getCategories - Reads content/blog/categories.json.
 *
 * @returns {Array<Object>} Array of category definitions.
 */
export function getCategories() {
    const raw = fs.readFileSync(
        path.join(CONTENT_DIR, "categories.json"),
        "utf-8"
    );
    return JSON.parse(raw);
}

/**
 * getAuthors - Reads content/blog/authors.json.
 *
 * @returns {Array<Object>} Array of author profiles.
 */
export function getAuthors() {
    const raw = fs.readFileSync(path.join(CONTENT_DIR, "authors.json"), "utf-8");
    return JSON.parse(raw);
}

/**
 * getAuthorById - Returns a single author by their id.
 *
 * @param {string} id — Author identifier (e.g. "sarah-chen").
 * @returns {Object|null}
 */
export function getAuthorById(id) {
    return getAuthors().find((a) => a.id === id) ?? null;
}
