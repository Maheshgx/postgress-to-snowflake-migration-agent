import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { CheckCircle, XCircle, Clock, Download, ArrowLeft } from 'lucide-react'

interface Props {
  runId: string
  onViewArtifacts: () => void
  onBackToConfig: () => void
}

export default function MigrationProgress({ runId, onViewArtifacts, onBackToConfig }: Props) {
  const { data: progress, isLoading } = useQuery({
    queryKey: ['progress', runId],
    queryFn: async () => {
      const response = await axios.get(`/api/v1/migrate/${runId}/progress`)
      return response.data
    },
    refetchInterval: 2000, // Poll every 2 seconds
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  const statusColor = {
    pending: 'bg-gray-200',
    analyzing: 'bg-blue-500',
    planning: 'bg-indigo-500',
    awaiting_confirmation: 'bg-yellow-500',
    executing: 'bg-green-500',
    validating: 'bg-purple-500',
    completed: 'bg-green-600',
    failed: 'bg-red-600',
  }[progress?.status] || 'bg-gray-200'

  const isComplete = progress?.status === 'completed' || progress?.status === 'failed'

  return (
    <div className="space-y-6">
      {/* Status Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Migration Progress</h2>
            <p className="text-sm text-gray-600 mt-1">
              Run ID: {runId}
            </p>
          </div>
          <div className={`px-4 py-2 rounded-full text-white font-medium ${statusColor}`}>
            {progress?.status?.replace('_', ' ').toUpperCase()}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="relative pt-1">
          <div className="flex mb-2 items-center justify-between">
            <div>
              <span className="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-blue-600 bg-blue-200">
                {progress?.phase}
              </span>
            </div>
            <div className="text-right">
              <span className="text-xs font-semibold inline-block text-blue-600">
                {Math.round(progress?.progress_percent || 0)}%
              </span>
            </div>
          </div>
          <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-gray-200">
            <div
              style={{ width: `${progress?.progress_percent || 0}%` }}
              className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500 transition-all duration-500"
            ></div>
          </div>
        </div>

        {/* Tables Progress */}
        {progress?.tables_total > 0 && (
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-gray-600">
              Tables: {progress.tables_completed} / {progress.tables_total}
            </span>
            {progress.current_operation && (
              <span className="text-gray-500 text-xs">
                {progress.current_operation}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Table Statuses */}
      {progress?.table_statuses && progress.table_statuses.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Table Migration Status</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Schema
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Table
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rows
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {progress.table_statuses.map((table, idx) => (
                  <tr key={idx}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {table.schema_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {table.table_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className="flex items-center space-x-1">
                        {table.status === 'completed' ? (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        ) : table.status === 'failed' ? (
                          <XCircle className="h-4 w-4 text-red-600" />
                        ) : (
                          <Clock className="h-4 w-4 text-yellow-600" />
                        )}
                        <span>{table.status}</span>
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {table.rows_loaded?.toLocaleString() || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {table.duration_ms ? `${(table.duration_ms / 1000).toFixed(2)}s` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Actions */}
      {isComplete && (
        <div className="flex items-center justify-between bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <button
            onClick={onBackToConfig}
            className="flex items-center space-x-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
          >
            <ArrowLeft className="h-5 w-5" />
            <span>Back to Configuration</span>
          </button>
          
          <button
            onClick={onViewArtifacts}
            className="flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            <Download className="h-5 w-5" />
            <span>View Artifacts</span>
          </button>
        </div>
      )}
    </div>
  )
}
