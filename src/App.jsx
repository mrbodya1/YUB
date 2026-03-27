import React from 'react';
import { Panel, PanelHeader, Group, Cell, Button } from '@vkontakte/vkui';
import '@vkontakte/vkui/dist/vkui.css';

function App() {
  return (
    <Panel>
      <PanelHeader>Спортивный челлендж</PanelHeader>
      <Group>
        <Cell>
          🏃‍♂️ Добро пожаловать в спортивный челлендж!
        </Cell>
        <Button mode="primary" style={{ margin: '16px' }}>
          Добавить тренировку
        </Button>
        <Button mode="outline" style={{ margin: '16px' }}>
          Мои тренировки
        </Button>
      </Group>
    </Panel>
  );
}

export default App;
