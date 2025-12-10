/**
 * Contact table component with pagination and filtering.
 * REQ-024: Frontend dashboard and export UI
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Spinner, Alert, Button, Select, Badge } from '@/components/ui';
import { Contact, ContactListResponse, ContactState } from '@/types/contact';
import { formatDateTime } from '@/lib/utils';
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api/client';

interface ContactTableProps {
  campaignId: string;
}

const OUTCOME_OPTIONS = [
  { value: '', label: 'All Outcomes' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'refused', label: 'Refused' },
  { value: 'not_reached', label: 'Not Reached' },
  { value: 'excluded', label: 'Excluded' },
];

const PAGE_SIZE_OPTIONS = [
  { value: '10', label: '10 per page' },
  { value: '25', label: '25 per page' },
  { value: '50', label: '50 per page' },
];

function getOutcomeBadgeVariant(state: ContactState): 'default' | 'success' | 'warning' | 'error' | 'info' {
  switch (state) {
    case 'completed':
      return 'success';
    case 'refused':
      return 'error';
    case 'not_reached':
      return 'warning';
    case 'in_progress':
      return 'info';
    case 'excluded':
      return 'error';
    default:
      return 'default';
  }
}

export function ContactTable({ campaignId }: ContactTableProps) {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 10,
    totalItems: 0,
    totalPages: 0,
  });
  const [outcomeFilter, setOutcomeFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchContacts = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params: Record<string, string | number> = {
        page: pagination.page,
        page_size: pagination.pageSize,
      };
      
      if (outcomeFilter) {
        params.state = outcomeFilter;
      }

      const response = await apiClient.get<ContactListResponse>(
        `/api/campaigns/${campaignId}/contacts`,
        { params }
      );

      setContacts(response.data.items);
      setPagination((prev) => ({
        ...prev,
        totalItems: response.data.pagination.total_items,
        totalPages: response.data.pagination.total_pages,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch contacts');
    } finally {
      setIsLoading(false);
    }
  }, [campaignId, pagination.page, pagination.pageSize, outcomeFilter]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  const handlePageChange = (newPage: number) => {
    setPagination((prev) => ({ ...prev, page: newPage }));
  };

  const handlePageSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setPagination((prev) => ({
      ...prev,
      pageSize: parseInt(e.target.value, 10),
      page: 1,
    }));
  };

  const handleOutcomeFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setOutcomeFilter(e.target.value);
    setPagination((prev) => ({ ...prev, page: 1 }));
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Contacts</CardTitle>
          <div className="flex items-center gap-4">
            <Select
              options={OUTCOME_OPTIONS}
              value={outcomeFilter}
              onChange={handleOutcomeFilterChange}
              className="w-40"
            />
            <Select
              options={PAGE_SIZE_OPTIONS}
              value={pagination.pageSize.toString()}
              onChange={handlePageSizeChange}
              className="w-36"
            />
            <Button variant="ghost" size="sm" onClick={fetchContacts}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="flex items-center justify-center h-64">
            <Spinner size="lg" />
          </div>
        )}

        {error && (
          <Alert variant="error" title="Failed to load contacts">
            {error}
            <button
              onClick={fetchContacts}
              className="ml-2 text-sm underline hover:no-underline"
            >
              Retry
            </button>
          </Alert>
        )}

        {!isLoading && !error && contacts.length === 0 && (
          <div className="flex items-center justify-center h-64 text-gray-500">
            No contacts found
          </div>
        )}

        {!isLoading && !error && contacts.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Phone Number
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      External ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Outcome
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Attempts
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Attempt
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {contacts.map((contact) => (
                    <tr key={contact.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {contact.phone_number}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {contact.external_contact_id || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge variant={getOutcomeBadgeVariant(contact.state)}>
                          {contact.state.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {contact.attempts_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {contact.last_attempt_at
                          ? formatDateTime(contact.last_attempt_at)
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-4 px-2">
              <div className="text-sm text-gray-500">
                Showing {(pagination.page - 1) * pagination.pageSize + 1} to{' '}
                {Math.min(pagination.page * pagination.pageSize, pagination.totalItems)} of{' '}
                {pagination.totalItems} contacts
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handlePageChange(pagination.page - 1)}
                  disabled={pagination.page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <span className="text-sm text-gray-500">
                  Page {pagination.page} of {pagination.totalPages}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handlePageChange(pagination.page + 1)}
                  disabled={pagination.page >= pagination.totalPages}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}