import { useState } from 'react'
import TabNavigation from './components/TabNavigation'
import MainAnalysis from './pages/MainAnalysis'
import PopularMovies from './pages/PopularMovies'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('main')

  return (
    <div className="app">
      <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
      
      <div className="tab-content">
        {activeTab === 'main' && <MainAnalysis />}
        {activeTab === 'popular' && <PopularMovies />}
      </div>
    </div>
  )
}

export default App
