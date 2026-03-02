import { HashRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import HomePage from './components/pages/HomePage'
import ClarifyPage from './components/pages/ClarifyPage'
import ConfirmPage from './components/pages/ConfirmPage'
import CreatePage from './components/pages/CreatePage'
import EditorPage from './components/pages/EditorPage'
import SettingsPage from './components/pages/SettingsPage'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/project/:id/clarify" element={<ClarifyPage />} />
          <Route path="/project/:id/confirm" element={<ConfirmPage />} />
          <Route path="/project/:id/create" element={<CreatePage />} />
          <Route path="/project/:id/edit" element={<EditorPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
