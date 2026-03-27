import React, { useState } from 'react';
import { Group, FormLayout, Input, Button, File, Div, Alert, Progress } from '@vkontakte/vkui';
import { supabase } from '../supabaseClient';
import { formatPace, formatDate } from '../utils/helpers';

function AddActivity({ user, navigate }) {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [distance, setDistance] = useState('');
  const [duration, setDuration] = useState('');
  const [screenshot, setScreenshot] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  
  const pace = formatPace(parseFloat(distance), parseFloat(duration));
  
  const handleSubmit = async () => {
    if (!date || !distance || !duration) {
      setError('Заполните все поля');
      return;
    }
    
    setUploading(true);
    setError(null);
    
    // Подсчет номера тренировки за день
    const { data: dayActivities } = await supabase
      .from('activities')
      .select('id')
      .eq('user_id', user.id)
      .eq('activity_date', date);
    
    const number = (dayActivities?.length || 0) + 1;
    const name = `${formatDate(date)}_тренировка_${number}`;
    
    let screenshotUrl = null;
    if (screenshot) {
      const fileExt = screenshot.name.split('.').pop();
      const fileName = `${user.id}/${Date.now()}.${fileExt}`;
      const { error: uploadError } = await supabase.storage
        .from('activity-screenshots')
        .upload(fileName, screenshot);
      
      if (!uploadError) {
        const { data: urlData } = supabase.storage
          .from('activity-screenshots')
          .getPublicUrl(fileName);
        screenshotUrl = urlData.publicUrl;
      }
    }
    
    const { error: insertError } = await supabase
      .from('activities')
      .insert({
        user_id: user.id,
        name: name,
        distance_km: parseFloat(distance),
        duration_min: parseFloat(duration),
        pace_min_per_km: pace,
        activity_date: date,
        screenshot_url: screenshotUrl,
        created_at: new Date().toISOString()
      });
    
    if (insertError) {
      setError(insertError.message);
      setUploading(false);
    } else {
      navigate('activities');
    }
  };
  
  return (
    <div style={{ paddingBottom: '16px' }}>
      <Group>
        <FormLayout>
          <Input
            type="date"
            top="Дата тренировки"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <Input
            type="number"
            step="0.01"
            top="Дистанция (км)"
            value={distance}
            onChange={(e) => setDistance(e.target.value)}
            placeholder="Например: 5.23"
          />
          <Input
            type="number"
            step="0.1"
            top="Время (минуты)"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder="Например: 29.5"
          />
          {pace !== '—' && (
            <Div style={{ color: 'var(--accent)', textAlign: 'center' }}>
              Темп: {pace} /км
            </Div>
          )}
          <File
            top="Скриншот трека (опционально)"
            accept="image/*"
            onChange={(e) => setScreenshot(e.target.files[0])}
          />
          {uploading && <Progress value={50} />}
          {error && <Div style={{ color: 'var(--destructive)' }}>{error}</Div>}
          <Button
            size="l"
            stretched
            onClick={handleSubmit}
            disabled={uploading}
            loading={uploading}
          >
            Сохранить тренировку
          </Button>
        </FormLayout>
      </Group>
    </div>
  );
}

export default AddActivity;
