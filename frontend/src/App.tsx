import { useState } from 'react'
import { Toaster } from 'sonner'
import { Database, Snowflake, ArrowRight, Settings, FileText } from 'lucide-react'
import ConfigurationForm from './components/ConfigurationForm'
import MigrationProgress from './components/MigrationProgress'
import ArtifactsViewer from './components/ArtifactsViewer'

function App() {
  const [currentStep, setCurrentStep] = useState<'config' | 'progress' | 'artifacts'>('config')
  const [runId, setRunId] = useState<string | null>(null)

  const handleMigrationStart = (newRunId: string) => {
    setRunId(newRunId)
    setCurrentStep('progress')
  }

  const handleViewArtifacts = () => {
    setCurrentStep('artifacts')
  }

  const handleBackToConfig = () => {
    setCurrentStep('config')
    setRunId(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <Toaster position="top-right" />
      
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Database className="h-8 w-8 text-blue-600" />
                <ArrowRight className="h-6 w-6 text-gray-400" />
                <Snowflake className="h-8 w-8 text-indigo-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  PostgreSQL → Snowflake Migration Agent
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  Auditable, web-hosted migration with Okta SSO
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {runId && (
                <span className="text-xs font-mono text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                  Run ID: {runId.substring(0, 8)}...
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <button
              onClick={() => setCurrentStep('config')}
              className={`flex items-center space-x-2 px-3 py-4 border-b-2 text-sm font-medium transition-colors ${
                currentStep === 'config'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Settings className="h-4 w-4" />
              <span>Configuration</span>
            </button>
            <button
              onClick={() => runId && setCurrentStep('progress')}
              disabled={!runId}
              className={`flex items-center space-x-2 px-3 py-4 border-b-2 text-sm font-medium transition-colors ${
                currentStep === 'progress' && runId
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } ${!runId && 'opacity-50 cursor-not-allowed'}`}
            >
              <Database className="h-4 w-4" />
              <span>Migration Progress</span>
            </button>
            <button
              onClick={() => runId && setCurrentStep('artifacts')}
              disabled={!runId}
              className={`flex items-center space-x-2 px-3 py-4 border-b-2 text-sm font-medium transition-colors ${
                currentStep === 'artifacts' && runId
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } ${!runId && 'opacity-50 cursor-not-allowed'}`}
            >
              <FileText className="h-4 w-4" />
              <span>Artifacts</span>
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentStep === 'config' && (
          <ConfigurationForm onMigrationStart={handleMigrationStart} />
        )}
        {currentStep === 'progress' && runId && (
          <MigrationProgress 
            runId={runId} 
            onViewArtifacts={handleViewArtifacts}
            onBackToConfig={handleBackToConfig}
          />
        )}
        {currentStep === 'artifacts' && runId && (
          <ArtifactsViewer runId={runId} />
        )}
      </main>

      {/* Footer */}
      <footer className="mt-12 bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-sm text-gray-500 text-center">
            PostgreSQL to Snowflake Migration Agent v1.0.0 - Built with FastAPI, React, and Snowflake
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
