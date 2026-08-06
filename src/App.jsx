import { useEffect, useMemo, useState } from 'react'
import { filterSounds, loadSounds } from './csvParser'
import { setEffect, setSpeed, setVolume, stopAll } from './audioEngine'
import EffectsBar from './components/EffectsBar'
import Tabs from './components/Tabs'
import SearchBar from './components/SearchBar'
import SoundGrid from './components/SoundGrid'
import './App.css'

function App() {
  const [effects, setEffects] = useState({
    echo: 0,
    distortion: 0,
    reverb: 0,
    speed: 1,
    volume: 0.9,
  })
  const [tabsData, setTabsData] = useState(null)
  const [activeTab, setActiveTab] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const isSearching = searchQuery.trim().length > 0

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
    else if (name === 'volume') setVolume(value)
    else setEffect(name, value)
  }

  const visibleSounds = useMemo(() => {
    if (!tabsData) return []
    if (isSearching) return filterSounds(tabsData.tabsMap.All, searchQuery)
    return tabsData.tabsMap[activeTab] ?? []
  }, [tabsData, activeTab, isSearching, searchQuery])

  return (
    <div className="app">
      <EffectsBar effects={effects} onChange={handleEffectChange} onStopAll={stopAll} />

      <SearchBar value={searchQuery} onChange={setSearchQuery} />

      {loadError && <p className="load-error">Couldn't load sounds.csv: {loadError}</p>}

      {tabsData && (
        <>
          {!isSearching && (
            <Tabs tabOrder={tabsData.tabOrder} active={activeTab} onSelect={setActiveTab} />
          )}
          <SoundGrid
            sounds={visibleSounds}
            emptyMessage={
              isSearching ? `Nenhum som encontrado para "${searchQuery}".` : undefined
            }
          />
        </>
      )}
    </div>
  )
}

export default App
