// Type definitions for the admin dashboard

export const QueryStatus = {
  SUCCESS: 'success',
  ERROR: 'error',
  PENDING: 'pending'
}

export const TimeRanges = {
  HOUR: '1h',
  SIX_HOURS: '6h',
  DAY: '24h',
  WEEK: '7d',
  MONTH: '30d'
}

export const ChartTypes = {
  LINE: 'line',
  BAR: 'bar',
  PIE: 'pie',
  DOUGHNUT: 'doughnut'
}

export const ExportFormats = {
  CSV: 'csv',
  JSON: 'json',
  XLSX: 'xlsx'
}

// Helper functions for data formatting
export const formatNumber = (num) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  } else {
    return num.toString()
  }
}

export const formatDuration = (ms) => {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`
  } else if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`
  } else {
    return `${(ms / 60000).toFixed(1)}m`
  }
}

export const formatBytes = (bytes) => {
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB']
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 Bytes'
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), sizes.length - 1)
  const value = bytes / Math.pow(1024, i)
  return `${value.toFixed(value >= 10 || i === 0 ? 0 : 2)} ${sizes[i]}`
}

export const formatDate = (date) => {
  // Parse the date - if it's a string without timezone info, assume it's UTC
  let dateObj
  if (typeof date === 'string' && !date.includes('T') && !date.includes('Z') && !date.includes('+')) {
    // Database timestamp format: "2025-08-30 12:26:29" - assume UTC
    dateObj = new Date(date + 'Z') // Add Z to indicate UTC
  } else {
    dateObj = new Date(date)
  }
  
  // Use toLocaleString for proper date and time formatting in local timezone
  return dateObj.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  })
}

export const getStatusColor = (status) => {
  switch (status) {
    case QueryStatus.SUCCESS:
      return 'success'
    case QueryStatus.ERROR:
      return 'error'
    case QueryStatus.PENDING:
      return 'warning'
    default:
      return 'secondary'
  }
}

export const getTrendIcon = (change) => {
  if (change > 0) return '$trendUp'
  if (change < 0) return '$trendDown'
  return '$clock'
}

export const getTrendColor = (change, inverse = false) => {
  if (change > 0) return inverse ? 'error' : 'success'
  if (change < 0) return inverse ? 'success' : 'error'
  return 'secondary'
}