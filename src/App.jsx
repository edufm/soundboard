import { useEffect, useState } from 'react'
import { loadSounds } from './csvParser'
import { setEffect, setSpeed } from './audioEngine'
import EffectsBar from './components/EffectsBar'
import Tabs from './components/Tabs'
import SoundGrid from './components/SoundGrid'
import './App.css'

function App() {
  const [effects, setEffects] = useState({
    echo: 0,
    distortion: 0,
    reverb: 0,
    speed: 1,
  })
  const [tabsData, setTabsData] = useState(null)
  const [activeTab, setActiveTab] = useState(null)
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    loadSounds()
      .then((data) => {
        setTabsData(data)
        setActiveTab(data.tabOrder[0] ?? null)
      })
      .catch((err) => setLoadError(err.message))
  }, [])

  const handleEffectChange = (name, value) => {
    setEffects((prev) => ({ ...prev, [name]: value }))
    if (name === 'speed') setSpeed(value)
    else setEffect(name, value)
  }

  return (
    <div className="app">
      <EffectsBar effects={effects} onChange={handleEffectChange} />

      {loadError && <p className="load-error">Couldn't load sounds.csv: {loadError}</p>}

      {tabsData && (
        <>
          <Tabs
            tabOrder={tabsData.tabOrder}
            active={activeTab}
            onSelect={setActiveTab}
          />
          <SoundGrid sounds={tabsData.tabsMap[activeTab] ?? []} />
        </>
      )}
    </div>
  )
}

export default App
