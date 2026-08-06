const EFFECTS = [
  { key: 'echo', label: 'Echo', min: 0, max: 1, step: 0.01 },
  { key: 'distortion', label: 'Distortion', min: 0, max: 1, step: 0.01 },
  { key: 'reverb', label: 'Reverb', min: 0, max: 1, step: 0.01 },
  { key: 'speed', label: 'Speed', min: 0.5, max: 2, step: 0.01 },
  { key: 'volume', label: 'Volume', min: 0, max: 1.5, step: 0.01 },
]

function formatValue(key, value) {
  return key === 'speed' ? `${value.toFixed(2)}x` : `${Math.round(value * 100)}%`
}

function EffectsBar({ effects, onChange, onStopAll }) {
  return (
    <div className="effects-bar">
      {EFFECTS.map(({ key, label, min, max, step }) => {
        const value = effects[key]
        const pct = ((value - min) / (max - min)) * 100
        return (
          <div className="effect-control" key={key} style={{ '--pct': `${pct}%` }}>
            <input
              aria-label={label}
              type="range"
              min={min}
              max={max}
              step={step}
              value={value}
              onChange={(e) => onChange(key, Number(e.target.value))}
            />
            <div className="effect-label-overlay" aria-hidden="true">
              <span>{label}</span>
              <span className="effect-value">{formatValue(key, value)}</span>
            </div>
          </div>
        )
      })}
      <button type="button" className="stop-all-button" onClick={onStopAll}>
        ⏹ Parar Tudo
      </button>
    </div>
  )
}

export default EffectsBar
