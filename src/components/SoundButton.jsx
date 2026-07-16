import { useRef, useState } from 'react'
import { playClip } from '../audioEngine'
import VariationBubbles from './VariationBubbles'

const LONG_PRESS_MS = 450

function SoundButton({ name, path, startTime, endTime, gainDb = 0, variations = [] }) {
  const [status, setStatus] = useState('idle')
  const [expanded, setExpanded] = useState(false)
  const [anchorRect, setAnchorRect] = useState(null)
  const buttonRef = useRef(null)
  const timerRef = useRef(null)
  const longPressFiredRef = useRef(false)

  const hasVariations = variations.length > 0

  const play = async (clip, label) => {
    try {
      await playClip(clip)
      setStatus('idle')
    } catch (err) {
      console.warn(`Couldn't play "${label}" (${clip.path}):`, err.message)
      setStatus('error')
    }
  }

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  const handlePointerDown = () => {
    if (!hasVariations) return
    longPressFiredRef.current = false
    timerRef.current = setTimeout(() => {
      longPressFiredRef.current = true
      setAnchorRect(buttonRef.current.getBoundingClientRect())
      setExpanded(true)
    }, LONG_PRESS_MS)
  }

  const handlePointerUp = () => {
    clearTimer()
    // The long press already opened the bubbles; this release shouldn't
    // also trigger the main sound.
    if (longPressFiredRef.current) return
    play({ path: `/${path}`, startTime, endTime, gainDb }, name)
  }

  const handleClick = () => {
    // Sounds without variations skip the pointer down/up timing entirely —
    // a plain click is simplest and most robust across input devices.
    if (hasVariations) return
    play({ path: `/${path}`, startTime, endTime, gainDb }, name)
  }

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className={`sound-button${status === 'error' ? ' error' : ''}${expanded ? ' expanded' : ''}`}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerLeave={clearTimer}
        onContextMenu={(e) => hasVariations && e.preventDefault()}
        onClick={handleClick}
        title={status === 'error' ? `File not found: ${path}` : undefined}
      >
        {name}
      </button>
      {expanded && anchorRect && (
        <VariationBubbles
          anchorRect={anchorRect}
          variations={variations}
          onPick={(variation) => {
            setExpanded(false)
            play(
              {
                path: `/${variation.path}`,
                startTime: variation.startTime,
                endTime: variation.endTime,
                gainDb: variation.gainDb,
              },
              variation.name,
            )
          }}
          onClose={() => setExpanded(false)}
        />
      )}
    </>
  )
}

export default SoundButton
