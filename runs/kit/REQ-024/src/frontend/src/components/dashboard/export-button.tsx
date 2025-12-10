/**
 * Export button component with status tracking.
 * REQ-024: Frontend dashboard and export UI
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Download, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Button, Alert } from '@/components/ui';
import { useDashboardStore } from '@/store/dashboard-store';

interface ExportButtonProps {
  campaignId: string;
  campaignName: string;
}

export function ExportButton({ campaignId, campaignName }: ExportButtonProps) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);
  
  const {
    currentExport,
    isExporting,
    exportError,
    initiateExport,
    pollExportStatus,
    downloadExport,
  } = useDashboardStore();

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [pollInterval]);

  // Poll for export status
  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const status = await pollExportStatus(jobId);
        
        if (status.status === 'completed' || status.status === 'failed') {
          if (pollInterval) {
            clearInterval(pollInterval);
            setPollInterval(null);
          }
        }
      } catch (error) {
        console.error('Failed to poll export status:', error);
      }
    };

    // Initial poll
    poll();

    // Set up interval polling
    const interval = setInterval(poll, 2000);
    setPollInterval(interval);

    return () => {
      clearInterval(interval);
    };
  }, [jobId, pollExportStatus]);

  const handleExport = useCallback(async () => {
    try {
      const newJobId = await initiateExport(campaignId);
      setJobId(newJobId);
    } catch (error) {
      console.error('Failed to initiate export:', error);
    }
  }, [campaignId, initiateExport]);

  const handleDownload = useCallback(async () => {
    if (!currentExport?.download_url) return;
    
    const filename = `campaign_${campaignName.replace(/\s+/g, '_')}_export.csv`;
    await downloadExport(currentExport.download_url, filename);
  }, [currentExport, campaignName, downloadExport]);

  const isProcessing = isExporting || currentExport?.status === 'pending' || currentExport?.status === 'processing';
  const isComplete = currentExport?.status === 'completed';
  const isFailed = currentExport?.status === 'failed';

  return (
    <div className="space-y-2">
      {!isComplete && !isFailed && (
        <Button
          onClick={handleExport}
          disabled={isProcessing}
          variant="secondary"
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              {isExporting ? 'Starting...' : 'Processing...'}
            </>
          ) : (
            <>
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </>
          )}
        </Button>
      )}

      {isComplete && currentExport?.download_url && (
        <div className="flex items-center gap-2">
          <Button onClick={handleDownload} variant="primary">
            <CheckCircle className="h-4 w-4 mr-2" />
            Download CSV
          </Button>
          <Button onClick={handleExport} variant="ghost" size="sm">
            New Export
          </Button>
        </div>
      )}

      {isFailed && (
        <div className="space-y-2">
          <Alert variant="error" title="Export failed">
            {currentExport?.error_message || exportError || 'An error occurred during export'}
          </Alert>
          <Button onClick={handleExport} variant="secondary">
            <XCircle className="h-4 w-4 mr-2" />
            Retry Export
          </Button>
        </div>
      )}

      {exportError && !isFailed && (
        <Alert variant="error" title="Export error">
          {exportError}
        </Alert>
      )}
    </div>
  );
}