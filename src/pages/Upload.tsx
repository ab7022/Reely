import React, { useState, useRef } from 'react';
import { Upload as UploadIcon, Link as LinkIcon, Palette, Type, Square } from 'lucide-react';
import { useApi } from '../contexts/ApiContext';
import { useNavigate } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';

interface CaptionStyle {
  font_type: string;
  font_size: number;
  font_color: string;
  stroke_color: string;
  stroke_width: number;
  padding: number;
}

const Upload: React.FC = () => {
  const { api } = useApi();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [uploadMethod, setUploadMethod] = useState<'file' | 'url'>('file');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const [captionStyle, setCaptionStyle] = useState<CaptionStyle>({
    font_type: 'Arial',
    font_size: 24,
    font_color: '#FFFFFF',
    stroke_color: '#000000',
    stroke_width: 2,
    padding: 10
  });

  const handleFileSelect = (file: File) => {
    if (file.type.startsWith('video/')) {
      setSelectedFile(file);
    } else {
      alert('Please select a valid video file');
    }
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile && !videoUrl) {
      alert('Please select a video file or enter a video URL');
      return;
    }

    setIsUploading(true);
    
    try {
      const formData = new FormData();
      
      if (uploadMethod === 'file' && selectedFile) {
        formData.append('video_file', selectedFile);
      } else if (uploadMethod === 'url' && videoUrl) {
        formData.append('video_url', videoUrl);
      }

      // Add caption style parameters
      Object.entries(captionStyle).forEach(([key, value]) => {
        formData.append(key, value.toString());
      });

      const response = await api.post('/api/caption', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Success - redirect to dashboard
      navigate('/', { 
        state: { 
          message: 'Video uploaded successfully! Processing will begin shortly.' 
        } 
      });

    } catch (error: any) {
      console.error('Upload error:', error);
      alert(error.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Create New Caption</h1>
        <p className="text-gray-600 mt-1">Upload a video or provide a URL to automatically generate captions</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Upload Method Selection */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Video Source</h2>
          
          <div className="flex space-x-4 mb-6">
            <button
              type="button"
              onClick={() => setUploadMethod('file')}
              className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                uploadMethod === 'file'
                  ? 'bg-blue-100 text-blue-700 border border-blue-300'
                  : 'bg-gray-100 text-gray-700 border border-gray-300'
              }`}
            >
              <UploadIcon className="w-4 h-4 mr-2" />
              Upload File
            </button>
            <button
              type="button"
              onClick={() => setUploadMethod('url')}
              className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                uploadMethod === 'url'
                  ? 'bg-blue-100 text-blue-700 border border-blue-300'
                  : 'bg-gray-100 text-gray-700 border border-gray-300'
              }`}
            >
              <LinkIcon className="w-4 h-4 mr-2" />
              Video URL
            </button>
          </div>

          {uploadMethod === 'file' ? (
            <div
              className={`relative border-2 border-dashed rounded-lg p-6 transition-colors ${
                dragOver
                  ? 'border-blue-400 bg-blue-50'
                  : selectedFile
                  ? 'border-green-400 bg-green-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleFileDrop}
            >
              <div className="text-center">
                <UploadIcon className="mx-auto h-12 w-12 text-gray-400" />
                {selectedFile ? (
                  <div className="mt-2">
                    <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <>
                    <p className="mt-2 text-sm text-gray-600">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="font-medium text-blue-600 hover:text-blue-500"
                      >
                        Click to upload
                      </button>{' '}
                      or drag and drop
                    </p>
                    <p className="text-xs text-gray-500">MP4, AVI, MOV up to 100MB</p>
                  </>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept="video/*"
                onChange={handleFileChange}
              />
            </div>
          ) : (
            <div>
              <label htmlFor="video-url" className="block text-sm font-medium text-gray-700 mb-2">
                Video URL
              </label>
              <input
                id="video-url"
                type="url"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="https://example.com/video.mp4"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          )}
        </div>

        {/* Caption Styling Options */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Palette className="w-5 h-5 mr-2" />
            Caption Styling
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Font Settings */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Font Type</label>
                <select
                  value={captionStyle.font_type}
                  onChange={(e) => setCaptionStyle({...captionStyle, font_type: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="Arial">Arial</option>
                  <option value="Helvetica">Helvetica</option>
                  <option value="Times New Roman">Times New Roman</option>
                  <option value="Courier">Courier</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Font Size: {captionStyle.font_size}px
                </label>
                <input
                  type="range"
                  min="12"
                  max="72"
                  value={captionStyle.font_size}
                  onChange={(e) => setCaptionStyle({...captionStyle, font_size: parseInt(e.target.value)})}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Padding: {captionStyle.padding}px
                </label>
                <input
                  type="range"
                  min="0"
                  max="50"
                  value={captionStyle.padding}
                  onChange={(e) => setCaptionStyle({...captionStyle, padding: parseInt(e.target.value)})}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>
            </div>

            {/* Color Settings */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Font Color</label>
                <div className="flex items-center space-x-3">
                  <input
                    type="color"
                    value={captionStyle.font_color}
                    onChange={(e) => setCaptionStyle({...captionStyle, font_color: e.target.value})}
                    className="h-10 w-16 border border-gray-300 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={captionStyle.font_color}
                    onChange={(e) => setCaptionStyle({...captionStyle, font_color: e.target.value})}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Stroke Color</label>
                <div className="flex items-center space-x-3">
                  <input
                    type="color"
                    value={captionStyle.stroke_color}
                    onChange={(e) => setCaptionStyle({...captionStyle, stroke_color: e.target.value})}
                    className="h-10 w-16 border border-gray-300 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={captionStyle.stroke_color}
                    onChange={(e) => setCaptionStyle({...captionStyle, stroke_color: e.target.value})}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Stroke Width: {captionStyle.stroke_width}px
                </label>
                <input
                  type="range"
                  min="0"
                  max="10"
                  value={captionStyle.stroke_width}
                  onChange={(e) => setCaptionStyle({...captionStyle, stroke_width: parseInt(e.target.value)})}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Caption Preview */}
          <div className="mt-6 p-4 bg-gray-900 rounded-lg">
            <div className="text-center">
              <span
                style={{
                  fontFamily: captionStyle.font_type,
                  fontSize: `${Math.max(captionStyle.font_size * 0.6, 14)}px`,
                  color: captionStyle.font_color,
                  textShadow: `1px 1px ${captionStyle.stroke_width}px ${captionStyle.stroke_color}`,
                  padding: `${captionStyle.padding}px`
                }}
              >
                Caption Preview Text
              </span>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end space-x-4">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Cancel
          </button>
          
          <button
            type="submit"
            disabled={isUploading || (!selectedFile && !videoUrl)}
            className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isUploading ? (
              <>
                <LoadingSpinner size="small" className="inline mr-2" />
                Processing...
              </>
            ) : (
              'Start Captioning'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default Upload;