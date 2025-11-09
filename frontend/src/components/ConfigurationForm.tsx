import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { Database, Snowflake, Play, FileCheck, TestTube } from 'lucide-react'
import axios from 'axios'

interface ConfigFormData {
  // PostgreSQL
  pgHost: string
  pgPort: number
  pgDatabase: string
  pgUsername: string
  pgPassword: string
  pgSchemas: string
  
  // Snowflake
  sfAccount: string
  sfWarehouse: string
  sfDatabase: string
  sfRole: string
  sfSchema: string
  sfStage: string
  sfFileFormat: string
  
  // Auth
  accessToken: string
  
  // Preferences
  format: 'CSV' | 'PARQUET'
  maxChunkMb: number
  parallelism: number
  useIdentityForSerial: boolean
  caseStyle: 'UPPER' | 'LOWER' | 'PRESERVE'
  dryRun: boolean
}

interface Props {
  onMigrationStart: (runId: string) => void
}

export default function ConfigurationForm({ onMigrationStart }: Props) {
  const [testing, setTesting] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  
  const { register, handleSubmit, formState: { errors }, getValues } = useForm<ConfigFormData>({
    defaultValues: {
      pgPort: 5432,
      pgSchemas: '*',
      sfSchema: 'PUBLIC',
      sfStage: 'MIGRATION_STAGE',
      sfFileFormat: 'MIGRATION_CSV_FORMAT',
      format: 'CSV',
      maxChunkMb: 200,
      parallelism: 4,
      useIdentityForSerial: true,
      caseStyle: 'UPPER',
      dryRun: false
    }
  })

  const testConnections = async () => {
    setTesting(true)
    
    try {
      const values = getValues()
      const payload = buildPayload(values)
      
      const response = await axios.post('/api/v1/test-connections', payload)
      const results = response.data
      
      if (results.postgres.status === 'success' && results.snowflake.status === 'success') {
        toast.success('Connection test successful!', {
          description: 'Both PostgreSQL and Snowflake connections verified.'
        })
      } else {
        if (results.postgres.status === 'error') {
          toast.error('PostgreSQL connection failed', {
            description: results.postgres.message
          })
        }
        if (results.snowflake.status === 'error') {
          toast.error('Snowflake connection failed', {
            description: results.snowflake.message
          })
        }
      }
    } catch (error: any) {
      toast.error('Connection test failed', {
        description: error.response?.data?.error || error.message
      })
    } finally {
      setTesting(false)
    }
  }

  const buildPayload = (data: ConfigFormData) => {
    return {
      postgres: {
        host: data.pgHost,
        port: data.pgPort,
        database: data.pgDatabase,
        username: data.pgUsername,
        password: data.pgPassword,
        schemas: data.pgSchemas.split(',').map(s => s.trim())
      },
      snowflake: {
        account: data.sfAccount,
        warehouse: data.sfWarehouse,
        database: data.sfDatabase,
        default_role: data.sfRole,
        schema: data.sfSchema,
        stage: data.sfStage,
        file_format: data.sfFileFormat
      },
      auth: {
        access_token: data.accessToken
      },
      preferences: {
        format: data.format,
        max_chunk_mb: data.maxChunkMb,
        parallelism: data.parallelism,
        use_identity_for_serial: data.useIdentityForSerial,
        case_style: data.caseStyle,
        dry_run: data.dryRun
      },
      control: {
        confirm: !data.dryRun
      }
    }
  }

  const onSubmit = async (data: ConfigFormData) => {
    setSubmitting(true)
    
    try {
      const payload = buildPayload(data)
      const response = await axios.post('/api/v1/migrate', payload)
      
      toast.success('Migration started!', {
        description: response.data.message
      })
      
      onMigrationStart(response.data.run_id)
    } catch (error: any) {
      toast.error('Failed to start migration', {
        description: error.response?.data?.error || error.message
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      {/* PostgreSQL Configuration */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-blue-50 border-b border-blue-100 px-6 py-4">
          <div className="flex items-center space-x-3">
            <Database className="h-6 w-6 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900">PostgreSQL Source</h2>
          </div>
        </div>
        
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Host *</label>
            <input
              {...register('pgHost', { required: 'Host is required' })}
              type="text"
              placeholder="localhost"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {errors.pgHost && <p className="mt-1 text-sm text-red-600">{errors.pgHost.message}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Port *</label>
            <input
              {...register('pgPort', { required: 'Port is required', valueAsNumber: true })}
              type="number"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {errors.pgPort && <p className="mt-1 text-sm text-red-600">{errors.pgPort.message}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Database *</label>
            <input
              {...register('pgDatabase', { required: 'Database is required' })}
              type="text"
              placeholder="mydb"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {errors.pgDatabase && <p className="mt-1 text-sm text-red-600">{errors.pgDatabase.message}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Username *</label>
            <input
              {...register('pgUsername', { required: 'Username is required' })}
              type="text"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {errors.pgUsername && <p className="mt-1 text-sm text-red-600">{errors.pgUsername.message}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password *</label>
            <input
              {...register('pgPassword', { required: 'Password is required' })}
              type="password"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {errors.pgPassword && <p className="mt-1 text-sm text-red-600">{errors.pgPassword.message}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Schemas (comma-separated, * for all)
            </label>
            <input
              {...register('pgSchemas')}
              type="text"
              placeholder="*"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {/* Snowflake Configuration */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-indigo-50 border-b border-indigo-100 px-6 py-4">
          <div className="flex items-center space-x-3">
            <Snowflake className="h-6 w-6 text-indigo-600" />
            <h2 className="text-lg font-semibold text-gray-900">Snowflake Target</h2>
          </div>
        </div>
        
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Account *</label>
            <input
              {...register('sfAccount', { required: 'Account is required' })}
              type="text"
              placeholder="abc12345.us-east-1"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            {errors.sfAccount && <p className="mt-1 text-sm text-red-600">{errors.sfAccount.message}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Warehouse *</label>
            <input
              {...register('sfWarehouse', { required: 'Warehouse is required' })}
              type="text"
              placeholder="COMPUTE_WH"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            {errors.sfWarehouse && <p className="mt-1 text-sm text-red-600">{errors.sfWarehouse.message}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Database *</label>
            <input
              {...register('sfDatabase', { required: 'Database is required' })}
              type="text"
              placeholder="MY_DATABASE"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            {errors.sfDatabase && <p className="mt-1 text-sm text-red-600">{errors.sfDatabase.message}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Role *</label>
            <input
              {...register('sfRole', { required: 'Role is required' })}
              type="text"
              placeholder="ACCOUNTADMIN"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            {errors.sfRole && <p className="mt-1 text-sm text-red-600">{errors.sfRole.message}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Schema</label>
            <input
              {...register('sfSchema')}
              type="text"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Stage Name *</label>
            <input
              {...register('sfStage', { required: 'Stage is required' })}
              type="text"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            {errors.sfStage && <p className="mt-1 text-sm text-red-600">{errors.sfStage.message}</p>}
          </div>
          
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">File Format Name *</label>
            <input
              {...register('sfFileFormat', { required: 'File format is required' })}
              type="text"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            {errors.sfFileFormat && <p className="mt-1 text-sm text-red-600">{errors.sfFileFormat.message}</p>}
          </div>
          
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Okta OAuth Access Token *
            </label>
            <input
              {...register('accessToken', { required: 'Access token is required' })}
              type="password"
              placeholder="Enter your Okta External OAuth token"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
            />
            {errors.accessToken && <p className="mt-1 text-sm text-red-600">{errors.accessToken.message}</p>}
            <p className="mt-1 text-xs text-gray-500">
              This token will be used for Snowflake authentication via Okta External OAuth
            </p>
          </div>
        </div>
      </div>

      {/* Migration Preferences */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-green-50 border-b border-green-100 px-6 py-4">
          <div className="flex items-center space-x-3">
            <FileCheck className="h-6 w-6 text-green-600" />
            <h2 className="text-lg font-semibold text-gray-900">Migration Preferences</h2>
          </div>
        </div>
        
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Data Format</label>
            <select
              {...register('format')}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            >
              <option value="CSV">CSV (Gzipped)</option>
              <option value="PARQUET">Parquet (Snappy)</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Max Chunk Size (MB)</label>
            <input
              {...register('maxChunkMb', { valueAsNumber: true })}
              type="number"
              min="1"
              max="1000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Parallelism</label>
            <input
              {...register('parallelism', { valueAsNumber: true })}
              type="number"
              min="1"
              max="16"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Case Style</label>
            <select
              {...register('caseStyle')}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            >
              <option value="UPPER">UPPER CASE</option>
              <option value="LOWER">lower case</option>
              <option value="PRESERVE">Preserve Original</option>
            </select>
          </div>
          
          <div className="flex items-center space-x-3">
            <input
              {...register('useIdentityForSerial')}
              type="checkbox"
              className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
            />
            <label className="text-sm font-medium text-gray-700">
              Use IDENTITY for serial columns
            </label>
          </div>
          
          <div className="flex items-center space-x-3">
            <input
              {...register('dryRun')}
              type="checkbox"
              className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
            />
            <label className="text-sm font-medium text-gray-700">
              Dry Run (analyze and plan only)
            </label>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <button
          type="button"
          onClick={testConnections}
          disabled={testing || submitting}
          className="flex items-center space-x-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          <TestTube className="h-5 w-5" />
          <span>{testing ? 'Testing...' : 'Test Connections'}</span>
        </button>
        
        <button
          type="submit"
          disabled={testing || submitting}
          className="flex items-center space-x-2 px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-sm"
        >
          <Play className="h-5 w-5" />
          <span>{submitting ? 'Starting...' : 'Start Migration'}</span>
        </button>
      </div>
    </form>
  )
}
