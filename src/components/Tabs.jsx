function Tabs({ tabOrder, active, onSelect }) {
  return (
    <div className="tabs">
      {tabOrder.map((tab) => (
        <button
          key={tab}
          type="button"
          className={`tab${tab === active ? ' active' : ''}`}
          onClick={() => onSelect(tab)}
        >
          {tab}
        </button>
      ))}
    </div>
  )
}

export default Tabs
