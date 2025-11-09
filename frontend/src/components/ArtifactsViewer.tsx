import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { FileText, Download } from 'lucide-react'

interface Props {
  runId: string
}

export default function ArtifactsViewer({ runId }: Props) {
  const { data: artifactsData, isLoading } = useQuery({
    queryKey: ['artifacts', runId],
    queryFn: async () => {
      const response = await axios.get(`/api/v1/migrate/${runId}/artifacts`)
      return response.data
    },
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading artifacts...</div>
  }

  const artifacts = artifactsData?.artifacts || []

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const getFileIcon = (filename: string) => {
    if (filename.endsWith('.md')) return '📝'
    if (filename.endsWith('.json')) return '📊'
    if (filename.endsWith('.yml') || filename.endsWith('.yaml')) return '⚙️'
    if (filename.endsWith('.sql')) return '🗃️'
    if (filename.endsWith('.ndjson')) return '📋'
    return '📄'
  }

  const downloadArtifact = (filename: string) => {
    window.open(`/api/v1/migrate/${runId}/artifacts/${filename}`, '_blank')
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Migration Artifacts</h2>
            <p className="text-sm text-gray-600 mt-1">
              Generated files and reports for run: {runId.substring(0, 8)}...
            </p>
          </div>
          <span className="px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
            {artifacts.length} files
          </span>
        </div>

        {artifacts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>No artifacts available yet</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {artifacts.map((artifact: any, idx: number) => (
              <div
                key={idx}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-4 flex-1">
                  <span className="text-3xl">{getFileIcon(artifact.filename)}</span>
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-gray-900">{artifact.filename}</h3>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatBytes(artifact.size_bytes)} • Modified: {new Date(artifact.modified).toLocaleString()}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => downloadArtifact(artifact.filename)}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  <Download className="h-4 w-4" />
                  <span>Download</span>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Access to Key Files */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">📚 Key Artifacts</h3>
        <div className="space-y-2 text-sm text-blue-800">
          <p><strong>summary.md</strong> - Complete migration summary with next steps</p>
          <p><strong>snowflake_objects.sql</strong> - DDL scripts for Snowflake objects</p>
          <p><strong>mapping_decisions.yml</strong> - Type mapping decisions and rationale</p>
          <p><strong>improvement_recommendations.md</strong> - Performance and optimization tips</p>
          <p><strong>post_migration_checks.sql</strong> - Validation queries to run</p>
          <p><strong>analysis_report.json</strong> - Complete PostgreSQL analysis results</p>
        </div>
      </div>
    </div>
  )
}
