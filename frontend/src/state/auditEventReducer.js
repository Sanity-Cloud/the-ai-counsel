/**
 * Pure state reducer for handling Stage 2 (including Audit mode sub-stages) SSE events.
 */
export function auditEventReducer(message, event, councilModels = []) {
  const now = Date.now();

  switch (event.type) {
    case 'stage2_start':
    case 'stage2a_start': {
      const isAudit = event.type === 'stage2a_start';
      return {
        ...message,
        loading: {
          ...message.loading,
          stage2: true,
          stage2a: isAudit ? true : message.loading.stage2a,
        },
        timers: {
          ...message.timers,
          stage2Start: message.timers.stage2Start || now,
          stage2aStart: isAudit ? now : message.timers.stage2aStart,
        }
      };
    }

    case 'stage2_init':
    case 'stage2a_init': {
      const isAudit = event.type === 'stage2a_init';
      const models = councilModels && councilModels.length > 0 ? councilModels : [];
      const initialStage2 = models.map(m => ({ model: m, pending: true }));
      return {
        ...message,
        progress: {
          ...message.progress,
          stage2: {
            count: 0,
            total: event.total,
            currentModel: null
          },
          ...(isAudit ? {
            stage2a: {
              count: 0,
              total: event.total,
              currentModel: null
            }
          } : {})
        },
        stage2: initialStage2,
        ...(isAudit ? { stage2a: initialStage2 } : {})
      };
    }

    case 'stage2_progress':
    case 'stage2a_progress': {
      const isAudit = event.type === 'stage2a_progress';
      const lastStage2 = isAudit ? (message.stage2a || message.stage2) : message.stage2;
      const updatedStage2 = lastStage2
        ? lastStage2.some(r => r.model === event.data.model)
          ? lastStage2.map(r => r.model === event.data.model ? event.data : r)
          : [...lastStage2, event.data]
        : [event.data];

      return {
        ...message,
        progress: {
          ...message.progress,
          stage2: {
            count: event.count,
            total: event.total,
            currentModel: event.data.model
          },
          ...(isAudit ? {
            stage2a: {
              count: event.count,
              total: event.total,
              currentModel: event.data.model
            }
          } : {})
        },
        stage2: updatedStage2,
        ...(isAudit ? { stage2a: updatedStage2 } : {})
      };
    }

    case 'stage2_complete':
    case 'stage2a_complete': {
      const isAudit = event.type === 'stage2a_complete';
      return {
        ...message,
        stage2: event.data,
        ...(isAudit ? { stage2a: event.data } : {}),
        loading: {
          ...message.loading,
          stage2a: isAudit ? false : message.loading.stage2a,
          stage2: isAudit ? message.loading.stage2 : false,
        },
        timers: {
          ...message.timers,
          stage2aEnd: isAudit ? now : message.timers.stage2aEnd,
          stage2End: isAudit ? message.timers.stage2End : now,
        },
        metadata: {
          ...message.metadata,
          ...event.metadata
        }
      };
    }

    case 'stage2b_start':
      return {
        ...message,
        loading: {
          ...message.loading,
          stage2b: true,
        },
        timers: {
          ...message.timers,
          stage2bStart: now,
        }
      };

    case 'stage2b_init': {
      const models = councilModels && councilModels.length > 0 ? councilModels : [];
      const initialStage2b = models.map(m => ({ model: m, pending: true }));
      return {
        ...message,
        progress: {
          ...message.progress,
          stage2b: {
            count: 0,
            total: event.total,
            currentModel: null
          }
        },
        stage2b: initialStage2b,
      };
    }

    case 'stage2b_progress': {
      const updatedStage2b = message.stage2b
        ? message.stage2b.some(r => r.model === event.data.model)
          ? message.stage2b.map(r => r.model === event.data.model ? event.data : r)
          : [...message.stage2b, event.data]
        : [event.data];

      return {
        ...message,
        progress: {
          ...message.progress,
          stage2b: {
            count: event.count,
            total: event.total,
            currentModel: event.data.model
          }
        },
        stage2b: updatedStage2b,
      };
    }

    case 'stage2b_complete':
      return {
        ...message,
        stage2b: event.data,
        loading: {
          ...message.loading,
          stage2b: false,
        },
        timers: {
          ...message.timers,
          stage2bEnd: now,
        }
      };

    case 'stage2c_start':
      return {
        ...message,
        loading: {
          ...message.loading,
          stage2c: true,
        },
        timers: {
          ...message.timers,
          stage2cStart: now,
        }
      };

    case 'stage2c_complete':
      return {
        ...message,
        stage2c: event.data,
        loading: {
          ...message.loading,
          stage2c: false,
          stage2: false,
        },
        timers: {
          ...message.timers,
          stage2cEnd: now,
          stage2End: now,
        },
        metadata: {
          ...message.metadata,
          aggregated_2b: event.aggregated,
          stage2c_result: event.data,
        }
      };

    case 'stage2a_error':
    case 'stage2b_error':
    case 'stage2c_error':
      return {
        ...message,
        loading: {
          ...message.loading,
          stage2: false,
          stage2a: false,
          stage2b: false,
          stage2c: false,
        },
        error: event.message,
      };

    default:
      return message;
  }
}
