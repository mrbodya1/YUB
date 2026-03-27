import React from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider, AdaptivityProvider, AppRoot } from '@vkontakte/vkui';
import bridge from '@vkontakte/vk-bridge';
import App from './App';
import '@vkontakte/vkui/dist/vkui.css';

bridge.send('VKWebAppInit');

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <ConfigProvider>
    <AdaptivityProvider>
      <AppRoot>
        <App />
      </AppRoot>
    </AdaptivityProvider>
  </ConfigProvider>
);
