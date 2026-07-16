const EFFECTS = [
  { key: 'echo', label: 'Echo', min: 0, max: 1, step: 0.01 },
  { key: 'distortion', label: 'Distortion', min: 0, max: 1, step: 0.01 },
  { key: 'reverb', label: 'Reverb', min: 0, max: 1, step: 0.01 },
  { key: 'speed', label: 'Speed', min: 0.5, max: 2, step: 0.01 },
]

function formatValue(key, value) {
  return key === 'speed' ? `${value.toFixed(2)}x` : `${Math.round(value * 100)}%`
}

function EffectsBar({ effects, onChange }) {
  return (
    <div className="effects-bar">
      {EFFECTS.map(({ key, label, min, max, step }) => (
        <div className="effect-control" key={key}>
          <label htmlFor={`effect-${key}`}>{label}</label>
          <input
            id={`effect-${key}`}
            type="range"
            min={min}
            max={max}
            step={step}
            value={effects[key]}
            onChange={(e) => onChange(key, Number(e.target.value))}
          />
          <span className="effect-value">{formatValue(key, effects[key])}</span>
        </div>
      ))}
    </div>
  )
}

export default EffectsBar
