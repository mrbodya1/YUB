import React, { useState, useEffect } from 'react';
import { Group, Card, CardGrid, Header, Button, Div, Spinner, Cell, Avatar, Tabs, TabsItem } from '@vkontakte/vkui';
import { Icon28AddOutline, Icon28SportOutline, Icon28StatisticsOutline, Icon28NewsfeedOutline } from '@vkontakte/icons';
import { supabase } from '../supabaseClient';
import { formatDuration, formatDate, formatPace, formatRelativeTime } from '../utils/helpers';
import WeeklyChart from '../components/WeeklyChart';
import NewsFeed from '../components/NewsFeed';

function Home({ user, navigate }) {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ totalKm: 0, totalTime: 0, trainingsCount: 0, avgDistance: 0 });
  const [weeklyData, setWeeklyData] = useState([]);
  const [newsTab, setNewsTab] = useState('my');
  const [news, setNews] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    
    // Загружаем статистику
    const { data: activities } = await supabase
      .from('activities')
      .select('distance_km, duration_min')
      .eq('user_id', user.id);
    
    if (activities) {
      const totalKm = activities.reduce((s, a) => s + (a.distance_km || 0), 0);
      const totalTime = activities.reduce((s, a) => s + (a.duration_min || 0), 0);
      const trainingsCount = activities.length;
      const avgDistance = trainingsCount > 0 ? (totalKm / trainingsCount).toFixed(2) : 0;
      setStats({ totalKm: totalKm.toFixed(2), totalTime: formatDuration(totalTime), trainingsCount, avgDistance });
    }
    
    // Загружаем недельную динамику
    const today = new Date();
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - today.getDay() + (today.getDay() === 0 ? -6 : 1));
    startOfWeek.setHours(0, 0, 0, 0);
    
    const { data: weekly } = await supabase
      .from('activities')
      .select('distance_km, activity_date')
      .eq('user_id', user.id)
      .gte('activity_date', startOfWeek.toISOString().split('T')[0]);
    
    const days = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek);
      date.setDate(startOfWeek.getDate() + i);
      days.push({ name: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][i], date: date.toISOString().split('T')[0], km: 0 });
    }
    
    weekly?.forEach(a => {
      const day = days.find(d => d.date === a.activity_date);
      if (day) day.km += a.distance_km || 0;
    });
    setWeeklyData(days);
    
    // Загружаем ленту новостей
    const { data: newsData } = await supabase
      .from('activities')
      .select('*, profiles!user_id(name_full, avatar_color)')
      .neq('user_id', user.id)
      .order('created_at', { ascending: false })
      .limit(20);
    
    const formattedNews = newsData?.map(a => ({
      id: a.id,
      user_name: a.profiles?.name_full || 'Пользователь',
      text: `добавил(а) тренировку: ${a.distance_km.toFixed(2)} км за ${formatDuration(a.duration_min)}`,
      time: formatRelativeTime(a.created_at),
      icon: '🏃‍♂️',
      activity: a
    })) || [];
    
    setNews(formattedNews);
    setLoading(false);
  };

  if (loading) {
    return <Div style={{ textAlign: 'center', padding: '40px' }}><Spinner size="large" /></Div>;
  }

  return (
    <div style={{ paddingBottom: '16px' }}>
      {/* Карточка профиля */}
      <Group style={{ marginTop: '8px' }}>
        <Card mode="outline" style={{ padding: '16px', margin: '0 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Avatar size={72} style={{ background: `linear-gradient(135deg, ${user.avatar_color || '#ffd966'}, #ffb347)` }}>
              {user.first_name?.charAt(0) || '👤'}
            </Avatar>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '18px', fontWeight: '600' }}>{user.name_full}</div>
              <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
                <div><strong>{stats.trainingsCount}</strong> тренировок</div>
                <div><strong>{stats.totalKm}</strong> км</div>
                <div><strong>{stats.totalTime}</strong> время</div>
              </div>
            </div>
            <Button onClick={() => navigate('add')} before={<Icon28AddOutline />} size="m">+</Button>
          </div>
          {user.bio && <div style={{ marginTop: '12px', color: 'var(--text-subtle)' }}>{user.bio}</div>}
        </Card>
      </Group>
      
      {/* Статистика */}
      <Group header={<Header mode="secondary">Общая статистика</Header>}>
        <CardGrid size="l">
          <Card mode="outline">
            <div style={{ textAlign: 'center', padding: '16px' }}>
              <Icon28SportOutline width={32} height={32} />
              <div style={{ fontSize: '24px', fontWeight: '700', marginTop: '8px' }}>{stats.totalKm}</div>
              <div style={{ color: 'var(--text-subtle)' }}>км всего</div>
            </div>
          </Card>
          <Card mode="outline">
            <div style={{ textAlign: 'center', padding: '16px' }}>
              <Icon28StatisticsOutline width={32} height={32} />
              <div style={{ fontSize: '24px', fontWeight: '700', marginTop: '8px' }}>{stats.totalTime}</div>
              <div style={{ color: 'var(--text-subtle)' }}>время</div>
            </div>
          </Card>
          <Card mode="outline">
            <div style={{ textAlign: 'center', padding: '16px' }}>
              <Icon28SportOutline width={32} height={32} />
              <div style={{ fontSize: '24px', fontWeight: '700', marginTop: '8px' }}>{stats.avgDistance}</div>
              <div style={{ color: 'var(--text-subtle)' }}>средняя дистанция</div>
            </div>
          </Card>
        </CardGrid>
      </Group>
      
      {/* График */}
      <Group header={<Header mode="secondary">Недельная динамика</Header>}>
        <WeeklyChart data={weeklyData} />
      </Group>
      
      {/* Новости с вкладками */}
      <Group>
        <Tabs>
          <TabsItem onClick={() => setNewsTab('my')} selected={newsTab === 'my'}>Мои события</TabsItem>
          <TabsItem onClick={() => setNewsTab('all')} selected={newsTab === 'all'}>Лента новостей</TabsItem>
        </Tabs>
        
        {newsTab === 'my' ? (
          <div style={{ padding: '12px' }}>
            <Cell before={<Icon28StatisticsOutline />} onClick={() => navigate('activities')}>
              Всего тренировок: <strong>{stats.trainingsCount}</strong>
            </Cell>
            <Cell before={<Icon28SportOutline />} onClick={() => navigate('profile')}>
              Общий километраж: <strong>{stats.totalKm} км</strong>
            </Cell>
          </div>
        ) : (
          <NewsFeed news={news} onActivityClick={(activity) => {
            // Показываем модальное окно с тренировкой
            navigate('activities', { state: { openModal: activity } });
          }} />
        )}
      </Group>
    </div>
  );
}

export default Home;
