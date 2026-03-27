import React, { useState, useEffect } from 'react';
import bridge from '@vkontakte/vk-bridge';
import { View, Panel, PanelHeader, ScreenSpinner } from '@vkontakte/vkui';
import { useRouter, useActivePanel } from '@vkontakte/vk-miniapps-router';
import '@vkontakte/vkui/dist/vkui.css';

import Home from './panels/Home';
import Activities from './panels/Activities';
import AddActivity from './panels/AddActivity';
import Profile from './panels/Profile';
import Settings from './panels/Settings';
import News from './panels/News';

import { supabase } from './supabaseClient';

function App() {
  const [activePanel, setActivePanel] = useState('home');
  const [user, setUser] = useState(null);
  const [popout, setPopout] = useState(null);
  const router = useRouter();

  useEffect(() => {
    // Инициализация VK Bridge
    bridge.send('VKWebAppInit').then(() => {
      // Получаем данные пользователя ВКонтакте
      bridge.send('VKWebAppGetUserInfo').then(async (vkUser) => {
        setPopout(<ScreenSpinner />);
        
        // Проверяем, есть ли пользователь в Supabase
        const { data: existingUser } = await supabase
          .from('profiles')
          .select('*')
          .eq('vk_id', vkUser.id)
          .single();
        
        let userData;
        
        if (!existingUser) {
          // Создаем нового пользователя
          const { data: newUser, error } = await supabase
            .from('profiles')
            .insert({
              vk_id: vkUser.id,
              first_name: vkUser.first_name,
              last_name: vkUser.last_name,
              name_full: `${vkUser.first_name} ${vkUser.last_name}`,
              avatar_url: vkUser.photo_100,
              avatar_color: ['#ffd966', '#ffb347', '#ff6b6b', '#4ecdc4'][Math.floor(Math.random() * 4)]
            })
            .select()
            .single();
          
          userData = newUser;
        } else {
          userData = existingUser;
        }
        
        setUser(userData);
        setPopout(null);
      });
    });
  }, []);

  // Обработка навигации через VK Router
  useActivePanel(activePanel, setActivePanel);

  if (!user) {
    return <ScreenSpinner />;
  }

  return (
    <View activePanel={activePanel} popout={popout}>
      <Panel id="home">
        <PanelHeader>Спортивный челлендж</PanelHeader>
        <Home user={user} navigate={setActivePanel} />
      </Panel>

      <Panel id="activities">
        <PanelHeader>Мои тренировки</PanelHeader>
        <Activities user={user} navigate={setActivePanel} />
      </Panel>

      <Panel id="add">
        <PanelHeader>Добавить тренировку</PanelHeader>
        <AddActivity user={user} navigate={setActivePanel} />
      </Panel>

      <Panel id="profile">
        <PanelHeader>Профиль</PanelHeader>
        <Profile user={user} navigate={setActivePanel} />
      </Panel>

      <Panel id="settings">
        <PanelHeader>Настройки</PanelHeader>
        <Settings user={user} navigate={setActivePanel} />
      </Panel>

      <Panel id="news">
        <PanelHeader>Лента новостей</PanelHeader>
        <News user={user} navigate={setActivePanel} />
      </Panel>
    </View>
  );
}

export default App;
