/**
 * NotificationFeedFullscreen - Fullscreen modal for notification feed
 * ====================================================================
 *
 * WHAT: Expanded fullscreen view of the notification feed
 * WHY: Users need detailed investigation of agent activity
 *
 * FEATURES:
 * - Full screen dialog using shadcn Dialog
 * - Larger notification items with more detail
 * - Full scrollable history
 * - Keyboard shortcut (Esc to close)
 * - Smooth animations on open/close
 *
 * DESIGN:
 * - Uses shadcn Dialog for accessibility
 * - White background with subtle shadow
 * - Consistent with other modal patterns
 *
 * REFERENCES:
 * - ui/components/agents/NotificationFeed.jsx
 * - ui/app/(dashboard)/agents/page.jsx
 */

'use client';

import { motion, AnimatePresence } from 'framer-motion';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogOverlay,
  DialogPortal,
} from '@/components/ui/dialog';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { Button } from '@/components/ui/button';
import { X, Bell, Minimize2 } from 'lucide-react';
import { NotificationFeed } from './NotificationFeed';
import { cn } from '@/lib/utils';

/**
 * NotificationFeedFullscreen component
 *
 * @param {Object} props
 * @param {boolean} props.open - Whether the dialog is open
 * @param {Function} props.onClose - Callback to close the dialog
 * @param {string} props.workspaceId - Workspace UUID
 */
export function NotificationFeedFullscreen({
  open,
  onClose,
  workspaceId,
}) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <AnimatePresence>
        {open && (
          <DialogPortal forceMount>
            {/* Custom animated overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
              onClick={onClose}
            />

            {/* Custom animated content */}
            <DialogPrimitive.Content asChild>
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{
                  duration: 0.25,
                  ease: [0.4, 0, 0.2, 1]
                }}
                className={cn(
                  "fixed top-[50%] left-[50%] z-50",
                  "translate-x-[-50%] translate-y-[-50%]",
                  "w-full max-w-4xl h-[85vh]",
                  "bg-white rounded-2xl shadow-2xl",
                  "border border-neutral-200/60",
                  "flex flex-col overflow-hidden",
                  "outline-none"
                )}
              >
                {/* Header */}
                <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-neutral-100 bg-neutral-50/50">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-white border border-neutral-200/60 shadow-sm">
                      <Bell className="h-5 w-5 text-neutral-600" />
                    </div>
                    <div>
                      <DialogTitle className="text-lg font-semibold text-neutral-900">
                        Agent Notifications
                      </DialogTitle>
                      <p className="text-sm text-neutral-500 mt-0.5">
                        Full history of agent activity
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={onClose}
                      className="h-9 px-3 text-neutral-500 hover:text-neutral-900 hover:bg-white"
                    >
                      <Minimize2 className="h-4 w-4 mr-2" />
                      Minimize
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={onClose}
                      className="h-9 w-9 text-neutral-400 hover:text-neutral-600 hover:bg-white rounded-lg"
                    >
                      <X className="h-5 w-5" />
                    </Button>
                  </div>
                </div>

                {/* Feed content - takes remaining height */}
                <div className="flex-1 overflow-hidden p-6 bg-white">
                  <NotificationFeed
                    workspaceId={workspaceId}
                    maxHeight="calc(85vh - 140px)"
                    onEventClick={(event) => {
                      // Could navigate to agent detail in fullscreen
                      // For now, just close and let parent handle
                      onClose();
                    }}
                  />
                </div>
              </motion.div>
            </DialogPrimitive.Content>
          </DialogPortal>
        )}
      </AnimatePresence>
    </Dialog>
  );
}

export default NotificationFeedFullscreen;
