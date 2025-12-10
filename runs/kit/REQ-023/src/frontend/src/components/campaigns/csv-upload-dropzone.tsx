/**
 * CSV upload dropzone component with drag-drop and progress.
 * REQ-023: Frontend campaign management UI
 */

'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { Button, Alert, Spinner } from '@/components/ui';
import { useCampaignStore } from '@/store/campaign-store';
import { cn, formatPercentage } from '@/lib/utils';

interface CSVUploadDropzoneProps {
  campaignId: string;
  onComplete?: () => void;
}

export function CSVUploadDropzone({ campaignId, onComplete }: CSVUploadDropzoneProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  const {
    uploadProgress,
    uploadResult,
    uploadContacts,
    resetUploadState,
  } = useCampaignStore();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
      resetUploadState();
    }
  }, [resetUploadState]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.csv'],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    try {
      await uploadContacts(campaignId, selectedFile);
    } catch (error) {
      // Error is handled in store
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    resetUploadState();
  };

  const isUploading = uploadProgress.status === 'uploading' || uploadProgress.status === 'processing';
  const isComplete = uploadProgress.status === 'complete';
  const isError = uploadProgress.status === 'error';

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      {!isComplete && !isError && (
        <div
          {...getRootProps()}
          className={cn(
            'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
            isDragActive && !isDragReject && 'border-primary-500 bg-primary-50',
            isDragReject && 'border-red-500 bg-red-50',
            !isDragActive && 'border-gray-300 hover:border-gray-400',
            isUploading && 'pointer-events-none opacity-50'
          )}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-sm text-gray-600">
            {isDragActive
              ? isDragReject
                ? 'This file type is not supported'
                : 'Drop the CSV file here'
              : 'Drag and drop a CSV file here, or click to select'}
          </p>
          <p className="mt-2 text-xs text-gray-500">
            Maximum file size: 10MB
          </p>
        </div>
      )}

      {/* Selected File */}
      {selectedFile && !isComplete && !isError && (
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-3">
            <FileText className="h-8 w-8 text-gray-400" />
            <div>
              <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
              <p className="text-xs text-gray-500">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
          {!isUploading && (
            <Button variant="ghost" size="sm" onClick={handleReset}>
              Remove
            </Button>
          )}
        </div>
      )}

      {/* Upload Progress */}
      {isUploading && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">{uploadProgress.message}</span>
            <span className="text-gray-900 font-medium">{uploadProgress.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Upload Result */}
      {isComplete && uploadResult && (
        <div className="space-y-4">
          <Alert
            variant={uploadResult.rejected_rows > 0 ? 'warning' : 'success'}
            title={uploadResult.rejected_rows > 0 ? 'Upload completed with warnings' : 'Upload successful'}
          >
            <div className="space-y-2">
              <p>
                <strong>{uploadResult.accepted_rows}</strong> of{' '}
                <strong>{uploadResult.total_rows}</strong> contacts imported successfully
                ({formatPercentage(uploadResult.acceptance_rate)})
              </p>
              {uploadResult.rejected_rows > 0 && (
                <p className="text-sm">
                  {uploadResult.rejected_rows} rows were rejected due to validation errors.
                </p>
              )}
            </div>
          </Alert>

          {/* Error Details */}
          {uploadResult.errors.length > 0 && (
            <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Line</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Field</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {uploadResult.errors.slice(0, 50).map((error, index) => (
                    <tr key={index}>
                      <td className="px-4 py-2 text-sm text-gray-900">{error.line_number}</td>
                      <td className="px-4 py-2 text-sm text-gray-900">{error.field}</td>
                      <td className="px-4 py-2 text-sm text-red-600">{error.error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {uploadResult.errors.length > 50 && (
                <p className="px-4 py-2 text-sm text-gray-500 bg-gray-50">
                  ... and {uploadResult.errors.length - 50} more errors
                </p>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={handleReset}>
              Upload Another File
            </Button>
            {onComplete && (
              <Button onClick={onComplete}>
                Done
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="space-y-4">
          <Alert variant="error" title="Upload failed">
            {uploadProgress.message}
          </Alert>
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleReset}>
              Try Again
            </Button>
          </div>
        </div>
      )}

      {/* Upload Button */}
      {selectedFile && !isUploading && !isComplete && !isError && (
        <div className="flex justify-end">
          <Button onClick={handleUpload}>
            <Upload className="h-4 w-4 mr-2" />
            Upload Contacts
          </Button>
        </div>
      )}

      {/* CSV Format Help */}
      {!selectedFile && !isComplete && (
        <div className="text-xs text-gray-500 space-y-1">
          <p className="font-medium">Expected CSV format:</p>
          <p>Required columns: phone_number</p>
          <p>Optional columns: external_contact_id, email, language, has_prior_consent, do_not_call</p>
        </div>
      )}
    </div>
  );
}