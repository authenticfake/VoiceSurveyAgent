/**
 * Campaign form component for create/edit.
 * REQ-023: Frontend campaign management UI
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Input, Select, Textarea, Card, CardHeader, CardTitle, CardContent, CardFooter, Alert } from '@/components/ui';
import { useCampaignStore } from '@/store/campaign-store';
import { Campaign, CampaignCreateRequest, CampaignUpdateRequest, QuestionType, CampaignLanguage } from '@/types/campaign';

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'it', label: 'Italian' },
];

const QUESTION_TYPE_OPTIONS = [
  { value: 'free_text', label: 'Free Text' },
  { value: 'numeric', label: 'Numeric' },
  { value: 'scale', label: 'Scale (1-10)' },
];

interface CampaignFormProps {
  campaign?: Campaign;
  mode: 'create' | 'edit';
}

interface FormData {
  name: string;
  description: string;
  language: CampaignLanguage;
  intro_script: string;
  question_1_text: string;
  question_1_type: QuestionType;
  question_2_text: string;
  question_2_type: QuestionType;
  question_3_text: string;
  question_3_type: QuestionType;
  max_attempts: number;
  retry_interval_minutes: number;
  allowed_call_start_local: string;
  allowed_call_end_local: string;
}

interface FormErrors {
  [key: string]: string;
}

const defaultFormData: FormData = {
  name: '',
  description: '',
  language: 'en',
  intro_script: '',
  question_1_text: '',
  question_1_type: 'free_text',
  question_2_text: '',
  question_2_type: 'free_text',
  question_3_text: '',
  question_3_type: 'free_text',
  max_attempts: 3,
  retry_interval_minutes: 60,
  allowed_call_start_local: '09:00',
  allowed_call_end_local: '20:00',
};

export function CampaignForm({ campaign, mode }: CampaignFormProps) {
  const router = useRouter();
  const { createCampaign, updateCampaign } = useCampaignStore();
  
  const [formData, setFormData] = useState<FormData>(defaultFormData);
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (campaign && mode === 'edit') {
      setFormData({
        name: campaign.name,
        description: campaign.description || '',
        language: campaign.language,
        intro_script: campaign.intro_script || '',
        question_1_text: campaign.question_1_text || '',
        question_1_type: campaign.question_1_type || 'free_text',
        question_2_text: campaign.question_2_text || '',
        question_2_type: campaign.question_2_type || 'free_text',
        question_3_text: campaign.question_3_text || '',
        question_3_type: campaign.question_3_type || 'free_text',
        max_attempts: campaign.max_attempts,
        retry_interval_minutes: campaign.retry_interval_minutes,
        allowed_call_start_local: campaign.allowed_call_start_local || '09:00',
        allowed_call_end_local: campaign.allowed_call_end_local || '20:00',
      });
    }
  }, [campaign, mode]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'max_attempts' || name === 'retry_interval_minutes' 
        ? parseInt(value, 10) || 0 
        : value,
    }));
    // Clear error when field is modified
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Campaign name is required';
    }

    if (formData.max_attempts < 1 || formData.max_attempts > 5) {
      newErrors.max_attempts = 'Max attempts must be between 1 and 5';
    }

    if (formData.retry_interval_minutes < 1) {
      newErrors.retry_interval_minutes = 'Retry interval must be at least 1 minute';
    }

    if (formData.allowed_call_start_local >= formData.allowed_call_end_local) {
      newErrors.allowed_call_end_local = 'End time must be after start time';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const payload: CampaignCreateRequest | CampaignUpdateRequest = {
        name: formData.name,
        description: formData.description || null,
        language: formData.language,
        intro_script: formData.intro_script || null,
        question_1_text: formData.question_1_text || null,
        question_1_type: formData.question_1_type,
        question_2_text: formData.question_2_text || null,
        question_2_type: formData.question_2_type,
        question_3_text: formData.question_3_text || null,
        question_3_type: formData.question_3_type,
        max_attempts: formData.max_attempts,
        retry_interval_minutes: formData.retry_interval_minutes,
        allowed_call_start_local: formData.allowed_call_start_local,
        allowed_call_end_local: formData.allowed_call_end_local,
      };

      if (mode === 'create') {
        const newCampaign = await createCampaign(payload);
        router.push(`/campaigns/${newCampaign.id}`);
      } else if (campaign) {
        await updateCampaign(campaign.id, payload);
        router.push(`/campaigns/${campaign.id}`);
      }
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to save campaign');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (campaign) {
      router.push(`/campaigns/${campaign.id}`);
    } else {
      router.push('/campaigns');
    }
  };

  const isEditable = !campaign || campaign.status === 'draft';

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-6">
        {submitError && (
          <Alert variant="error" title="Error">
            {submitError}
          </Alert>
        )}

        {!isEditable && (
          <Alert variant="warning" title="Limited editing">
            This campaign is not in draft status. Some fields cannot be modified.
          </Alert>
        )}

        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              label="Campaign Name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              error={errors.name}
              required
              disabled={!isEditable}
            />
            <Textarea
              label="Description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              rows={3}
              disabled={!isEditable}
            />
            <Select
              label="Language"
              name="language"
              value={formData.language}
              onChange={handleChange}
              options={LANGUAGE_OPTIONS}
              disabled={!isEditable}
            />
          </CardContent>
        </Card>

        {/* Survey Script */}
        <Card>
          <CardHeader>
            <CardTitle>Survey Script</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              label="Introduction Script"
              name="intro_script"
              value={formData.intro_script}
              onChange={handleChange}
              rows={4}
              helperText="This script will be read at the beginning of each call. Include caller identity, purpose, and consent request."
              disabled={!isEditable}
            />
          </CardContent>
        </Card>

        {/* Questions */}
        <Card>
          <CardHeader>
            <CardTitle>Survey Questions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {[1, 2, 3].map((num) => (
              <div key={num} className="space-y-3 pb-4 border-b border-gray-200 last:border-0 last:pb-0">
                <h4 className="font-medium text-gray-700">Question {num}</h4>
                <Textarea
                  label="Question Text"
                  name={`question_${num}_text`}
                  value={formData[`question_${num}_text` as keyof FormData] as string}
                  onChange={handleChange}
                  rows={2}
                  disabled={!isEditable}
                />
                <Select
                  label="Answer Type"
                  name={`question_${num}_type`}
                  value={formData[`question_${num}_type` as keyof FormData] as string}
                  onChange={handleChange}
                  options={QUESTION_TYPE_OPTIONS}
                  disabled={!isEditable}
                />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Call Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Call Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Max Attempts per Contact"
                name="max_attempts"
                type="number"
                min={1}
                max={5}
                value={formData.max_attempts}
                onChange={handleChange}
                error={errors.max_attempts}
                helperText="Number of call attempts before marking as not reached (1-5)"
                disabled={!isEditable}
              />
              <Input
                label="Retry Interval (minutes)"
                name="retry_interval_minutes"
                type="number"
                min={1}
                value={formData.retry_interval_minutes}
                onChange={handleChange}
                error={errors.retry_interval_minutes}
                helperText="Minimum time between call attempts"
                disabled={!isEditable}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Call Window Start (Local Time)"
                name="allowed_call_start_local"
                type="time"
                value={formData.allowed_call_start_local}
                onChange={handleChange}
                disabled={!isEditable}
              />
              <Input
                label="Call Window End (Local Time)"
                name="allowed_call_end_local"
                type="time"
                value={formData.allowed_call_end_local}
                onChange={handleChange}
                error={errors.allowed_call_end_local}
                disabled={!isEditable}
              />
            </div>
          </CardContent>
        </Card>

        {/* Form Actions */}
        <div className="flex items-center justify-end gap-4">
          <Button type="button" variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting} disabled={!isEditable}>
            {mode === 'create' ? 'Create Campaign' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </form>
  );
}