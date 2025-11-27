"use client";

import React from "react";
import { cn } from "@/lib/cn";

export const FloatingNav = ({
  navItems,
  className
}) => {
  return (
    <div
      className={cn(
        "flex max-w-2xl fixed top-10 inset-x-0 mx-auto rounded-full z-[5000] px-6 py-2 items-center justify-between border border-white/40 backdrop-blur-sm bg-white/30 shadow-2xl shadow-black/5",
        className
      )}
      style={{
        boxShadow: 'inset 0 1px 0 0 rgba(255, 255, 255, 0.2), 0 2px 8px rgba(0, 0, 0, 0.05)'
      }}
    >
      {/* Logo on the left */}
      <a href="/" className="flex items-center flex-shrink-0">
        <img src="/metricx-logo.png" alt="metricx" className="h-10 w-auto" />
      </a>

      {/* Navigation items in the center */}
      <div className="flex items-center justify-center space-x-4 flex-1">
        {navItems.map((navItem, idx) => (
          <a
            key={`link=${idx}`}
            href={navItem.link}
            className={cn(
              "relative items-center flex space-x-1 text-neutral-600 hover:text-neutral-900 transition-colors"
            )}
          >
            <span className="block sm:hidden">{navItem.icon}</span>
            <span className="hidden sm:block text-sm font-medium">{navItem.name}</span>
          </a>
        ))}
      </div>

      {/* Launch Dashboard button on the right */}
      <a
        href="/dashboard"
        className="text-sm font-medium relative text-black px-4 py-2 rounded-full flex-shrink-0 border border-white/40 backdrop-blur-sm bg-white/40 hover:scale-105 hover:bg-white/50 transition-all duration-300"
        style={{
          boxShadow: 'inset 0 1px 0 0 rgba(255, 255, 255, 0.3), 0 1px 2px rgba(0, 0, 0, 0.05)'
        }}
      >
        <span>Launch Dashboard</span>
      </a>
    </div>
  );
};

