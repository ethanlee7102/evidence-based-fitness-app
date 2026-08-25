import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useIsGuest } from '../../auth/hooks'

const SEEN_KEY = 'demo-intro-seen'

/**
 * Guest-only chrome: a persistent "you're in guest mode" banner plus a one-time
 * explainer modal (dismissal remembered in localStorage). Renders nothing for
 * signed-in (non-anonymous) users.
 */
export function GuestDemoChrome() {
  const isGuest = useIsGuest()
  const location = useLocation()
  // The chat screen owns a full-height (h-screen, negative-margin) layout, so an
  // in-flow banner above it overflows the viewport. Suppress the banner there; the
  // modal below is position:fixed and unaffected.
  const onChat = location.pathname.startsWith('/dashboard/chat')
  const [showIntro, setShowIntro] = useState(() => {
    try {
      return localStorage.getItem(SEEN_KEY) !== '1'
    } catch {
      return true
    }
  })

  if (!isGuest) return null

  const dismissIntro = () => {
    try {
      localStorage.setItem(SEEN_KEY, '1')
    } catch {
      /* ignore storage failures */
    }
    setShowIntro(false)
  }

  return (
    <>
      {!onChat && (
        <div className="mb-6 flex items-start gap-3 p-3 rounded-lg bg-flame-500/10 border border-flame-500/30 text-sm text-flame-300">
          <p>
            You're exploring in <span className="font-semibold">guest mode</span>. We've loaded a
            sample training history so the app isn't empty. Your session and anything you log reset
            periodically.
          </p>
        </div>
      )}

      {showIntro && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={dismissIntro}
        >
          <div
            className="max-w-md w-full bg-gray-900 border border-gray-700 rounded-xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-xl font-bold mb-3">Welcome to the demo</h2>
            <ul className="space-y-2 text-gray-300 text-sm mb-5 list-disc pl-5">
              <li>This is a guest account, no sign-up needed.</li>
              <li>
                A sample <span className="font-medium">12-week training history</span> is preloaded
                so the screens are populated.
              </li>
              <li>
                The highlight is the <span className="font-medium">Chat</span> tab: ask
                exercise-science questions and get answers cited to research papers.
              </li>
              <li>You can log your own workouts too; some actions are limited in the demo.</li>
            </ul>
            <button
              onClick={dismissIntro}
              className="w-full py-2.5 rounded-lg bg-flame-600 hover:bg-flame-500 font-medium transition-colors"
            >
              Start exploring
            </button>
          </div>
        </div>
      )}
    </>
  )
}
