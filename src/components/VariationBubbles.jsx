import { useEffect, useRef } from 'react'

const MIN_RADIUS = 76
const RADIUS_PER_BUBBLE = 6
const MAX_RADIUS = 150

// Fixed-position overlay so bubbles float above the grid regardless of the
// button's stacking/overflow context. Positions are computed once from the
// anchor button's bounding rect at the moment the long press fires.
function VariationBubbles({ anchorRect, variations, onPick, onClose }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const handleOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        onClose()
      }
    }
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('pointerdown', handleOutside, true)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handleOutside, true)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  const centerX = anchorRect.left + anchorRect.width / 2
  const centerY = anchorRect.top + anchorRect.height / 2
  const count = variations.length
  const radius = Math.min(MIN_RADIUS + count * RADIUS_PER_BUBBLE, MAX_RADIUS)

  return (
    <div className="variation-bubbles" ref={containerRef}>
      {variations.map((variation, i) => {
        const angle = (i / count) * 2 * Math.PI - Math.PI / 2
        const x = centerX + radius * Math.cos(angle)
        const y = centerY + radius * Math.sin(angle)
        return (
          <button
            key={`${variation.name}-${variation.path}-${variation.startTime}`}
            type="button"
            className="variation-bubble"
            style={{ left: `${x}px`, top: `${y}px` }}
            title={variation.name}
            onClick={(event) => {
              event.stopPropagation()
              onPick(variation)
            }}
          >
            {variation.name}
          </button>
        )
      })}
    </div>
  )
}

export default VariationBubbles
