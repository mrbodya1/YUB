import React, { useState, useEffect } from 'react';
import { Group, List, Cell, Div, Spinner, Alert } from '@vkontakte/vkui';
import { supabase } from '../supabaseClient';
import { formatDuration, formatDate } from '../utils/helpers';

function Activities({ user }) {
  const [loading, setLoading] = useState(true);
  const [activities, setActivities] = useState([]);
  const [selectedActivity, setSelectedActivity] = useState(null);

  useEffect(() => {
    loadActivities();
  }, []);

  const loadActivities = async () => {
    const { data } = await supabase
      .from('activities')
      .select('*')
      .eq('user_id', user.id)
      .order('activity_date', { ascending: false });
    
    setActivities(data || []);
    setLoading(false);
  };

  const openActivityModal = (activity) => {
    setSelectedActivity(activity);
  };

  if (loading) {
    return <Div style={{ textAlign: 'center', padding: '40px' }}><Spinner size="large" /></Div>;
  }

  return (
    <div style={{ paddingBottom: '16px' }}>
      <Group>
        <List>
          {activities.map(activity => (
            <Cell
              key={activity.id}
              onClick={() => openActivityModal(activity)}
              description={formatDate(activity.activity_date)}
              after={
                <div style={{ textAlign: 'right' }}>
                  <div>{activity.distance_km.toFixed(2)} км</div>
                  <div>{formatDuration(activity.duration_min)}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-subtle)' }}>
                    темп {activity.pace_min_per_km || '—'}
                  </div>
                </div>
              }
            >
              {activity.name}
            </Cell>
          ))}
        </List>
        {activities.length === 0 && (
          <Div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-subtle)' }}>
            Нет тренировок. Нажмите + чтобы добавить
          </Div>
        )}
      </Group>
      
      {selectedActivity && (
        <Alert
          actions={[{
            title: 'Закрыть',
            mode: 'cancel',
            autoclose: true
          }]}
          onClose={() => setSelectedActivity(null)}
        >
          <h3 style={{ marginBottom: '12px' }}>{selectedActivity.name}</h3>
          <div>📅 {formatDate(selectedActivity.activity_date)}</div>
          <div>📏 {selectedActivity.distance_km.toFixed(2)} км</div>
          <div>⏱ {formatDuration(selectedActivity.duration_min)}</div>
          <div>⚡ темп {selectedActivity.pace_min_per_km || '—'}</div>
          {selectedActivity.screenshot_url && (
            <img
              src={selectedActivity.screenshot_url}
              alt="Скриншот тренировки"
              style={{ maxWidth: '100%', marginTop: '16px', borderRadius: '12px' }}
            />
          )}
        </Alert>
      )}
    </div>
  );
}

export default Activities;
