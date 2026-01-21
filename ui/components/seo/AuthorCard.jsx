/**
 * Author Card Component
 *
 * WHAT: Displays author information for content attribution
 * WHY: Author attribution improves E-E-A-T (Experience, Expertise,
 *      Authoritativeness, Trustworthiness) signals for SEO
 *
 * @example
 * import { AuthorCard } from '@/components/seo/AuthorCard';
 *
 * <AuthorCard
 *   author={{
 *     name: "metricx Team",
 *     role: "Ad Analytics Experts",
 *     bio: "The metricx team...",
 *     avatar: "/team/metricx.png"
 *   }}
 * />
 */

import Image from "next/image";
import Link from "next/link";
import { Twitter, Linkedin, Globe } from "lucide-react";

/**
 * Author card with avatar and bio.
 *
 * @param {Object} props - Component props
 * @param {Object} props.author - Author data
 * @param {string} props.author.name - Author name
 * @param {string} [props.author.role] - Author role/title
 * @param {string} [props.author.bio] - Short bio
 * @param {string} [props.author.avatar] - Avatar image URL
 * @param {string} [props.author.slug] - Author page slug
 * @param {Object} [props.author.social] - Social links
 * @param {string} [props.className] - Additional CSS classes
 * @param {string} [props.variant="default"] - Card variant
 * @returns {JSX.Element} Author card
 */
export function AuthorCard({ author, className = "", variant = "default" }) {
  if (!author) return null;

  const { name, role, bio, avatar, slug, social } = author;

  if (variant === "compact") {
    return (
      <div className={`flex items-center gap-3 ${className}`}>
        {avatar && (
          <div className="relative w-10 h-10 rounded-full overflow-hidden bg-slate-100">
            <Image
              src={avatar}
              alt={name}
              fill
              className="object-cover"
              sizes="40px"
            />
          </div>
        )}
        <div>
          <p className="font-medium text-slate-900 text-sm">{name}</p>
          {role && <p className="text-xs text-slate-500">{role}</p>}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`author-card bg-slate-50 rounded-xl p-6 ${className}`}
      itemScope
      itemType="https://schema.org/Person"
    >
      <div className="flex items-start gap-4">
        {/* Avatar */}
        {avatar && (
          <div className="relative w-16 h-16 rounded-full overflow-hidden bg-slate-200 flex-shrink-0">
            <Image
              src={avatar}
              alt={name}
              fill
              className="object-cover"
              sizes="64px"
              itemProp="image"
            />
          </div>
        )}

        {/* Info */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-900" itemProp="name">
            {slug ? (
              <Link
                href={`/authors/${slug}`}
                className="hover:text-cyan-600 transition-colors"
              >
                {name}
              </Link>
            ) : (
              name
            )}
          </h3>

          {role && (
            <p className="text-sm text-slate-500 mt-0.5" itemProp="jobTitle">
              {role}
            </p>
          )}

          {bio && (
            <p className="text-sm text-slate-600 mt-2" itemProp="description">
              {bio}
            </p>
          )}

          {/* Social Links */}
          {social && (
            <div className="flex items-center gap-3 mt-3">
              {social.twitter && (
                <a
                  href={social.twitter}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-cyan-600 transition-colors"
                  aria-label={`${name} on Twitter`}
                >
                  <Twitter className="w-4 h-4" />
                </a>
              )}
              {social.linkedin && (
                <a
                  href={social.linkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-cyan-600 transition-colors"
                  aria-label={`${name} on LinkedIn`}
                >
                  <Linkedin className="w-4 h-4" />
                </a>
              )}
              {social.website && (
                <a
                  href={social.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-cyan-600 transition-colors"
                  aria-label={`${name}'s website`}
                >
                  <Globe className="w-4 h-4" />
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Author byline for article headers.
 *
 * @param {Object} props - Component props
 * @param {Object} props.author - Author data
 * @param {string} [props.publishDate] - Publication date
 * @param {string} [props.readTime] - Estimated read time
 * @returns {JSX.Element} Author byline
 */
export function AuthorByline({ author, publishDate, readTime }) {
  if (!author) return null;

  const formattedDate = publishDate
    ? new Date(publishDate).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <div className="flex items-center gap-3 text-sm">
      {author.avatar && (
        <div className="relative w-8 h-8 rounded-full overflow-hidden bg-slate-100">
          <Image
            src={author.avatar}
            alt={author.name}
            fill
            className="object-cover"
            sizes="32px"
          />
        </div>
      )}
      <div className="flex items-center gap-2 text-slate-500">
        <span className="font-medium text-slate-700">{author.name}</span>
        {formattedDate && (
          <>
            <span aria-hidden="true">&middot;</span>
            <time dateTime={publishDate}>{formattedDate}</time>
          </>
        )}
        {readTime && (
          <>
            <span aria-hidden="true">&middot;</span>
            <span>{readTime}</span>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Default author data for content without specific author.
 */
export const defaultAuthor = {
  name: "metricx Team",
  role: "Ad Analytics Experts",
  bio: "The metricx team brings together experts in advertising, analytics, and e-commerce to help merchants understand and optimize their ad performance.",
  avatar: "/team/metricx-team.png",
  social: {
    twitter: "https://twitter.com/metricx_ai",
  },
};

export default AuthorCard;
