export interface UserEvent {
  id: number;
  user_id: string;
  event_type: 'page_view' | 'button_click' | 'form_submit';
  element_id: string | null;
  timestamp: string;
  created_at: string;
}

export interface EventStats {
  total_events: number;
  event_type_breakdown: Array<{
    event_type: string;
    count: number;
  }>;
  top_clicked_elements: Array<{
    element_id: string;
    count: number;
  }>;
}

export interface MessageQueue {
  id: string;
  message_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  status_display: string;
  source: 'kafka' | 'api' | 'mock';
  source_display: string;
  user_id: string;
  event_type: string;
  element_id: string | null;
  message_data: any;
  queued_at: string;
  processing_started_at: string | null;
  completed_at: string | null;
  processing_duration_ms: number | null;
  processing_duration_seconds: number | null;
  error_message: string | null;
  retry_count: number;
  user_event: number | null;
}

export interface QueueStats {
  total_messages: number;
  status_breakdown: { [key: string]: number };
  source_breakdown: { [key: string]: number };
  avg_processing_time_ms: number | null;
  avg_retry_count: number | null;
  currently_processing: number;
  queued_count: number;
}

export interface WebSocketMessage {
  type: 'initial_data' | 'new_event' | 'stats_update' | 'queue_update';
  events?: UserEvent[];
  event?: UserEvent;
  stats?: EventStats;
  queue_message?: MessageQueue;
}
