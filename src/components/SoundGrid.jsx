import SoundButton from './SoundButton'

function SoundGrid({ sounds }) {
  if (sounds.length === 0) {
    return <p className="empty-tab">No sounds in this tab.</p>
  }

  return (
    <div className="sound-grid">
      {sounds.map((sound) => (
        <SoundButton
          key={`${sound.name}-${sound.path}-${sound.startTime}`}
          name={sound.name}
          path={sound.path}
          startTime={sound.startTime}
          endTime={sound.endTime}
          gainDb={sound.gainDb}
          variations={sound.variations}
        />
      ))}
    </div>
  )
}

export default SoundGrid
