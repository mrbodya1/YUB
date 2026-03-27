import React from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider, AdaptivityProvider, AppRoot } from '@vkontakte/vkui';
import { RouterProvider } from '@vkontakte/vk-miniapps-router';
import bridge from '@vkontakte/vk-bridge';
import App from './App';

bridge.send('VKWebAppInit');

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <ConfigProvider>
    <AdaptivityProvider>
      <AppRoot>
        <RouterProvider>
          <App />
        </RouterProvider>
      </AppRoot>
    </AdaptivityProvider>
  </ConfigProvider>
);
