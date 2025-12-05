import { formatDistanceToNow, format } from 'date-fns';

/**
 * Format a date string to relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch (error) {
    return 'Unknown';
  }
}

/**
 * Format a date string to full date and time
 */
export function formatDateTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    return format(date, 'MMM d, yyyy h:mm a');
  } catch (error) {
    return 'Unknown';
  }
}

/**
 * Format a date string to just the date
 */
export function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return format(date, 'MMM d, yyyy');
  } catch (error) {
    return 'Unknown';
  }
}

/**
 * Get status badge color classes based on run status
 */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'queued':
      return 'bg-gray-100 text-gray-800';
    case 'running':
      return 'bg-blue-100 text-blue-800';
    case 'succeeded':
      return 'bg-green-100 text-green-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    case 'cancelled':
      return 'bg-yellow-100 text-yellow-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

/**
 * Get status icon/emoji based on run status
 */
export function getStatusIcon(status: string): string {
  switch (status) {
    case 'queued':
      return '⏳';
    case 'running':
      return '🔧';
    case 'succeeded':
      return '✅';
    case 'failed':
      return '❌';
    case 'cancelled':
      return '⚠️';
    default:
      return '❓';
  }
}

/**
 * Calculate duration between two dates
 */
export function calculateDuration(startDate: string, endDate: string): string {
  try {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffMs = end.getTime() - start.getTime();
    
    const seconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  } catch (error) {
    return 'Unknown';
  }
}

/**
 * Truncate long text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}
