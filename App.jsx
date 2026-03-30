import React, { useState, useEffect } from 'react';
import { supabase } from './supabaseClient';

function App() {
  const [activeTab, setActiveTab] = useState('rating');
  const [participants, setParticipants] = useState([]);
  const [filteredParticipants, setFilteredParticipants] = useState([]);
  const [nominations, setNominations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [sortBy, setSortBy] = useState('total_km');
  const [sortOrder, setSortOrder] = useState('desc');
  const [filterGender, setFilterGender] = useState('all');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    applyFiltersAndSort();
  }, [participants, sortBy, sortOrder, filterGender]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const { data: participantsData, error: participantsError } = await supabase
        .from('participants')
        .select('*')
        .eq('status', 'active');
      
      if (participantsError) throw participantsError;
      
      const participantsWithPace = (participantsData || []).map(p => {
        let avg_pace = 0;
        if (p.total_km > 0 && p.total_min > 0) {
          avg_pace = p.total_min / p.total_km;
        }
        return {
          ...p,
          avg_pace: parseFloat(avg_pace.toFixed(2))
        };
      });
      
      setParticipants(participantsWithPace);
      calculateNominations(participantsWithPace);
      
    } catch (err) {
      console.error('Ошибка загрузки:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const calculateNominations = (participantsData) => {
    let longestDistance = { value: 0, name: '' };
    let bestPace = { value: Infinity, name: '' };
    let mostWorkouts = { value: 0, name: '' };
    let mostSnowflakes = { value: 0, name: '' };
    
    participantsData.forEach(p => {
      if (p.total_workouts > mostWorkouts.value) {
        mostWorkouts = { value: p.total_workouts, name: `${p.first_name} ${p.last_name}` };
      }
      if (p.total_km > longestDistance.value) {
        longestDistance = { value: p.total_km, name: `${p.first_name} ${p.last_name}` };
      }
      if (p.avg_pace > 0 && p.avg_pace < bestPace.value) {
        bestPace = { value: p.avg_pace, name: `${p.first_name} ${p.last_name}` };
      }
      if ((p.snowflake_balance || 0) > mostSnowflakes.value) {
        mostSnowflakes = { value: p.snowflake_balance || 0, name: `${p.first_name} ${p.last_name}` };
      }
    });
    
    const formatPace = (pace) => {
      if (pace === Infinity) return '—';
      const mins = Math.floor(pace);
      const secs = Math.round((pace - mins) * 60);
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    };
    
    setNominations([
      { name: 'Дальний удар', winner: longestDistance.name, value: `${longestDistance.value} км`, icon: '📏', desc: 'Общий километраж' },
      { name: 'Ракета', winner: bestPace.name, value: formatPace(bestPace.value), icon: '⚡️', desc: 'Лучший средний темп' },
      { name: 'Трудоголик', winner: mostWorkouts.name, value: `${mostWorkouts.value} тренировок`, icon: '🔄', desc: 'Больше всего тренировок' },
      { name: 'Снежинки', winner: mostSnowflakes.name, value: `${mostSnowflakes.value} ❄️`, icon: '❄️', desc: 'Больше всего снежинок' }
    ]);
  };

  const applyFiltersAndSort = () => {
    let result = [...participants];
    if (filterGender !== 'all') {
      result = result.filter(p => p.gender === filterGender);
    }
    result.sort((a, b) => {
      let aVal = a[sortBy] || 0;
      let bVal = b[sortBy] || 0;
      return sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
    });
    setFilteredParticipants(result);
  };

  const formatKm = (km) => `${km?.toFixed(1) || 0} км`;
  const formatTime = (min) => {
    if (!min || min === 0) return '0 мин';
    if (min < 60) return `${min} мин`;
    return `${Math.floor(min / 60)} ч ${min % 60} мин`;
  };
  const formatPace = (totalKm, totalMin) => {
    if (!totalKm || totalKm === 0) return '—';
    const pace = totalMin / totalKm;
    return `${Math.floor(pace)}:${Math.round((pace % 1) * 60).toString().padStart(2, '0')}`;
  };

  const getMedal = (idx) => {
    if (idx === 0) return '🥇';
    if (idx === 1) return '🥈';
    if (idx === 2) return '🥉';
    return `${idx + 1}`;
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  if (loading) {
    return <div className="loading"><div className="spinner"></div><p>Загрузка...</p></div>;
  }

  if (error) {
    return <div className="error"><p>⚠️ {error}</p><button onClick={() => window.location.reload()}>Повторить</button></div>;
  }

  return (
    <div className="app">
      <header><h1>🏔️ Королевская битва</h1><p>Спортивный челлендж 2026</p></header>
      
      <div className="tabs">
        <button className={activeTab === 'rating' ? 'active' : ''} onClick={() => setActiveTab('rating')}>🏆 Рейтинг</button>
        <button className={activeTab === 'nominations' ? 'active' : ''} onClick={() => setActiveTab('nominations')}>🎯 Номинации</button>
      </div>

      {activeTab === 'rating' && (
        <>
          <div className="filters">
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="total_km">📏 По километрам</option>
              <option value="total_workouts">🏋️ По тренировкам</option>
              <option value="total_min">⏱️ По времени</option>
              <option value="avg_pace">⚡ По темпу</option>
            </select>
            <select value={filterGender} onChange={(e) => setFilterGender(e.target.value)}>
              <option value="all">👥 Все</option>
              <option value="М">👨 Мужчины</option>
              <option value="Ж">👩 Женщины</option>
            </select>
          </div>
          
          <div className="sort-row">
            <button onClick={() => handleSort('total_km')}>Км {sortBy === 'total_km' && (sortOrder === 'desc' ? '↓' : '↑')}</button>
            <button onClick={() => handleSort('total_workouts')}>Тренировки {sortBy === 'total_workouts' && (sortOrder === 'desc' ? '↓' : '↑')}</button>
            <button onClick={() => handleSort('total_min')}>Время {sortBy === 'total_min' && (sortOrder === 'desc' ? '↓' : '↑')}</button>
            <button onClick={() => handleSort('avg_pace')}>Темп {sortBy === 'avg_pace' && (sortOrder === 'desc' ? '↓' : '↑')}</button>
          </div>

          <div className="list">
            {filteredParticipants.length === 0 ? <div className="empty">Нет участников</div> : 
              filteredParticipants.map((p, idx) => (
                <div key={p.id} className="card">
                  <div className="rank">{getMedal(idx)}</div>
                  <div className="info">
                    <div className="name">{p.first_name} {p.last_name} <span>{p.gender === 'Ж' ? '👩' : '👨'}</span></div>
                    <div className="stats">
                      <span>🏋️ {p.total_workouts || 0}</span>
                      <span>⏱️ {formatTime(p.total_min)}</span>
                      <span>⚡ {formatPace(p.total_km, p.total_min)}/км</span>
                      <span>❄️ {p.snowflake_balance || 0}</span>
                    </div>
                  </div>
                  <div className="km">{formatKm(p.total_km)}</div>
                </div>
              ))
            }
          </div>
        </>
      )}

      {activeTab === 'nominations' && (
        <div className="list">
          {nominations.map((nom, idx) => (
            <div key={idx} className="nom-card">
              <div className="nom-icon">{nom.icon}</div>
              <div className="nom-info">
                <div className="nom-name">{nom.name}</div>
                <div className="nom-desc">{nom.desc}</div>
              </div>
              <div className="nom-value">
                <div>{nom.value}</div>
                <div className="nom-winner">{nom.winner}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
