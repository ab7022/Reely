import React from 'react';
import { Download, Clock, CheckCircle, XCircle, Loader } from 'lucide-react';
import { formatDistanceToNow } from '../utils/dateUtils';

interface VideoCardProps {
  video: {
    id: string;
    filename: string;
    status: string;
    created_at: string;
    completed_at?: string;
    captioned_video_url?: string;
    error?: string;
  };
  onDownload: (url: string, filename: string) => void;
}

const VideoCard: React.FC<VideoCardProps> = ({ video, onDownload }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'processing':
        return <Loader className="w-5 h-5 text-blue-600 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-yellow-600" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'processing':
        return 'Processing';
      default:
        return 'Pending';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-yellow-100 text-yellow-800';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-gray-900 truncate">
            {video.filename}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Created {formatDistanceToNow(video.created_at)} ago
          </p>
          {video.completed_at && (
            <p className="text-sm text-gray-500">
              Completed {formatDistanceToNow(video.completed_at)} ago
            </p>
          )}
        </div>
        
        <div className="flex items-center space-x-2 ml-4">
          {getStatusIcon(video.status)}
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(video.status)}`}>
            {getStatusText(video.status)}
          </span>
        </div>
      </div>

      {video.error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-800">{video.error}</p>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-500">
          ID: {video.id.slice(0, 8)}...
        </div>
        
        {video.status === 'completed' && video.captioned_video_url && (
          <button
            onClick={() => onDownload(video.captioned_video_url!, video.filename)}
            className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            <Download className="w-4 h-4 mr-2" />
            Download
          </button>
        )}
      </div>
    </div>
  );
};

export default VideoCard;