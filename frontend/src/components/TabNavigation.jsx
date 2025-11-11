import React from 'react'
import './TabNavigation.css'

function TabNavigation({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'main', label: ' 취향 분석 ' },
    { id: 'popular', label: ' 인기영화 '}
  ]

  return (
    <nav className="tab-navigation">
      <div className="tab-container">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </div>
    </nav>
  )
}

export default TabNavigation
