function SearchBar({ value, onChange }) {
  return (
    <div className="search-bar">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Buscar som..."
        aria-label="Buscar som"
      />
      {value && (
        <button
          type="button"
          className="search-clear"
          onClick={() => onChange('')}
          aria-label="Limpar busca"
        >
          ×
        </button>
      )}
    </div>
  )
}

export default SearchBar
