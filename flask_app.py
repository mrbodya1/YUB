from flask import Flask, request
from flask_cors import CORS
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import config
from db import Database
import re
import random
from datetime import datetime, timedelta
from yookassa_client import create_payment, is_payment_successful, get_payment_status

app = Flask(__name__)
CORS(app)

db = Database()
CONFIRMATION_TOKEN = "4bbe78bb"

SETTINGS = {}

def load_settings():
    global SETTINGS
    SETTINGS = {
        'START_DATE': db.get_setting('START_DATE', '2026-04-01'),
        'MIN_KM': db.get_int_setting('MIN_KM', 3),
        'MIN_MINUTES': db.get_int_setting('MIN_MINUTES', 0),
        'BASE_SNOWFLAKES': db.get_int_setting('BASE_SNOWFLAKES', 30),
        'DAY_BONUS': db.get_int_setting('DAY_BONUS', 20),
        'DAY_HOUR_LIMIT': db.get_int_setting('DAY_HOUR_LIMIT', 22),
        'ABILITIES_COSTS': db.get_abilities_costs()
    }

load_settings()

# Хранилища состояний
user_states = {}
ability_search = {}

def clean_text(text):
    if not text:
        return text
    text = re.sub(r'\[club\d+\|@[^\]]+\]\s*', '', text)
    text = re.sub(r'@\w+\s*', '', text)
    return text.strip()

def send_message(peer_id, text, keyboard=None):
    try:
        vk = vk_api.VkApi(token=config.config.VK_TOKEN).get_api()
        params = {
            'peer_id': peer_id,
            'message': text,
            'random_id': 0,
            'from_group': 1
        }
        is_private = peer_id < 2000000000
        if is_private and keyboard:
            params['keyboard'] = keyboard
        vk.messages.send(**params)
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

def get_main_keyboard(user_id=None):
    keyboard = VkKeyboard()
    if user_id:
        participant = db.get_participant_by_vk(user_id)
        if not participant or participant.get('status') != 'active':
            keyboard.add_button('💰 Оплатить участие', color=VkKeyboardColor.POSITIVE)
            keyboard.add_line()
            keyboard.add_button('❓ Помощь', color=VkKeyboardColor.SECONDARY)
            if user_id and user_id in config.config.ADMINS:
                keyboard.add_line()
                keyboard.add_button('👑 Админ-панель', color=VkKeyboardColor.NEGATIVE)
            return keyboard.get_keyboard()

    keyboard.add_button('➕ Добавить тренировку', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('📊 Статистика', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('⭐️ Рейтинг', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('⚡️ Способности', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('🏅 Достижения', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('📋 Правила', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('❓ Помощь', color=VkKeyboardColor.SECONDARY)

    if user_id and user_id in config.config.ADMINS:
        keyboard.add_line()
        keyboard.add_button('👑 Админ-панель', color=VkKeyboardColor.NEGATIVE)

    return keyboard.get_keyboard()

def get_cancel_keyboard():
    keyboard = VkKeyboard()
    keyboard.add_button('❌ Отмена', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_edit_keyboard():
    keyboard = VkKeyboard()
    keyboard.add_button('✏️ Изменить', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('❌ Отмена', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_back_keyboard():
    keyboard = VkKeyboard()
    keyboard.add_button('◀️ Назад', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_abilities_keyboard():
    keyboard = VkKeyboard()
    costs = SETTINGS['ABILITIES_COSTS']
    keyboard.add_button('🎲 Рулетка (бесплатно)', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button(f'⚡ Удвоение ({costs.get("x2boost", 150)}🌼)', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(f'🛡️ Щит ({costs.get("shield", 100)}🌼)', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button(f'✂️ Разделение ({costs.get("frostbite", 150)}🌼)', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(f'🌊 Потоп ({costs.get("avalanche", 150)}🌼)', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button(f'💀 Обнуление ({costs.get("annihilation", 200)}🌼)', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('◀️ Назад', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_current_day():
    try:
        start = datetime.strptime(SETTINGS['START_DATE'], '%Y-%m-%d')
        now = db.get_current_time()
        start = start.replace(tzinfo=now.tzinfo)
        diff = (now - start).days + 1
        return diff if diff > 0 else 0
    except:
        return 0

def get_available_targets(exclude_participant_id):
    all_participants = db.get_all_participants()
    targets = []
    for p in all_participants:
        if exclude_participant_id and p['id'] == exclude_participant_id:
            continue
        if not p.get('vk_id'):
            continue
        last_workout = db.get_last_workout(p['id'])
        if not last_workout:
            continue
        if last_workout.get('mod_neg'):
            continue
        targets.append({
            'id': p['id'],
            'vk_id': p['vk_id'],
            'first_name': p['first_name'],
            'last_name': p['last_name'],
            'workout_id': last_workout['id'],
            'workout_day': last_workout['day'],
            'workout_km': last_workout['original_km']
        })
    return targets

def get_top5_targets_by_gender(attacker_id, attacker_gender):
    all_participants = db.get_all_participants()
    same_gender = [p for p in all_participants
                   if p.get('gender') == attacker_gender and p['id'] != attacker_id]
    same_gender.sort(key=lambda x: x.get('total_km', 0), reverse=True)

    targets = []
    for p in same_gender:
        last_workout = db.get_last_workout(p['id'])
        if not last_workout:
            continue
        if last_workout.get('mod_neg'):
            continue
        targets.append({
            'id': p['id'],
            'vk_id': p['vk_id'],
            'first_name': p['first_name'],
            'last_name': p['last_name'],
            'workout_id': last_workout['id'],
            'workout_day': last_workout['day'],
            'workout_km': last_workout['original_km'],
            'total_km': p.get('total_km', 0)
        })
        if len(targets) >= 5:
            break
    return targets

def search_targets_by_name(query, exclude_participant_id):
    if exclude_participant_id:
        all_targets = get_available_targets(exclude_participant_id)
    else:
        all_targets = db.get_all_participants()

    query_lower = query.lower()
    matches = []
    for t in all_targets:
        if query_lower in t['first_name'].lower() or query_lower in t['last_name'].lower():
            matches.append(t)
    return matches

def get_top3_participants():
    rating = db.get_rating()
    return rating[:3] if rating else []

def check_and_award_achievements(user_id, workout_data=None, ability_data=None):
    participant = db.get_participant_by_vk(user_id)
    if not participant:
        return []

    user_achievements = db.get_user_achievements(user_id)
    completed_ids = set(a['achievement_id'] for a in user_achievements)
    workouts = db.get_workouts_by_participant(participant['id'])
    total_workouts = len(workouts)

    avg_pace = 0
    if participant['total_km'] > 0 and participant['total_min'] > 0:
        avg_pace = participant['total_min'] / participant['total_km']

    max_distance = 0
    slow_count = 0
    night_count = 0
    morning_count = 0

    for w in workouts:
        if w['original_km'] > max_distance:
            max_distance = w['original_km']
        if w['original_km'] > 0 and w['original_min'] > 0:
            pace = w['original_min'] / w['original_km']
            if pace > 7.0:
                slow_count += 1
        if workout_data and workout_data.get('hour') is not None:
            hour = workout_data.get('hour')
            if 0 <= hour < 5:
                night_count += 1
            elif 5 <= hour < 8:
                morning_count += 1

    days = sorted(set(w['day'] for w in workouts))
    streak = 1
    max_streak = 1
    for i in range(1, len(days)):
        if days[i] - days[i-1] == 1:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 1

    abilities = db.get_user_abilities(participant['id'])
    annihilations = len([a for a in abilities if a['ability_id'] == 'annihilation'])
    frostbites = len([a for a in abilities if a['ability_id'] == 'frostbite'])
    lucky_uses = len([a for a in abilities if a['ability_id'] == 'lucky'])
    attacks_received = db.get_attacks_received(participant['id'])

    awarded = []

    if 1 not in completed_ids and total_workouts >= 1: awarded.append(1)
    if 2 not in completed_ids and total_workouts >= 3: awarded.append(2)
    if 3 not in completed_ids and total_workouts >= 7: awarded.append(3)
    if 4 not in completed_ids and total_workouts >= 14: awarded.append(4)
    if 5 not in completed_ids and total_workouts >= 21: awarded.append(5)
    if 6 not in completed_ids and total_workouts >= 28: awarded.append(6)
    if 7 not in completed_ids and max_streak >= 3: awarded.append(7)
    if 8 not in completed_ids and max_streak >= 7: awarded.append(8)
    if 9 not in completed_ids and max_streak >= 14: awarded.append(9)
    if 10 not in completed_ids and max_streak >= 21: awarded.append(10)
    if 11 not in completed_ids and avg_pace >= 7.0 and avg_pace > 0: awarded.append(11)
    if 12 not in completed_ids and avg_pace <= 4.0 and avg_pace > 0: awarded.append(12)
    if 13 not in completed_ids and slow_count >= 5: awarded.append(13)
    if 14 not in completed_ids and max_distance >= 21: awarded.append(14)
    if 15 not in completed_ids and max_distance >= 42: awarded.append(15)
    if 16 not in completed_ids and max_distance >= 70: awarded.append(16)

    if workout_data:
        hour = workout_data.get('hour', -1)
        if 17 not in completed_ids and 0 <= hour < 5: awarded.append(17)
        if 18 not in completed_ids and 5 <= hour < 8: awarded.append(18)

    if 19 not in completed_ids and night_count >= 5: awarded.append(19)
    if 20 not in completed_ids and morning_count >= 5: awarded.append(20)

    if ability_data and ability_data.get('target_in_top3'):
        if 21 not in completed_ids and ability_data.get('type') == 'annihilation': awarded.append(21)
        if 22 not in completed_ids and ability_data.get('type') == 'frostbite': awarded.append(22)

    if 23 not in completed_ids and ability_data and ability_data.get('revenge'): awarded.append(23)
    if 24 not in completed_ids and attacks_received >= 3: awarded.append(24)
    if 25 not in completed_ids and annihilations >= 3: awarded.append(25)
    if 26 not in completed_ids and frostbites >= 5: awarded.append(26)
    if 27 not in completed_ids and attacks_received >= 10: awarded.append(27)

    if ability_data and ability_data.get('type') == 'lucky':
        if 28 not in completed_ids and ability_data.get('result') == 'zero': awarded.append(28)
        if 29 not in completed_ids and ability_data.get('result') == 'combo': awarded.append(29)

    if 30 not in completed_ids and lucky_uses >= 5: awarded.append(30)

    for ach_id in awarded:
        db.award_achievement(user_id, ach_id)

    return awarded

def use_ability_lucky(user_id, peer_id, participant):
    if not db.can_use_lucky(participant['id']):
        send_message(peer_id, "🎲 Ты уже использовал рулетку сегодня!", get_main_keyboard(participant['vk_id']))
        return

    effects = [
        {'type': 'snowflakes', 'value': 100, 'text': '💰 +100 ромашек!', 'result': 'snow'},
        {'type': 'snowflakes', 'value': 250, 'text': '💰💰 +250 ромашек!', 'result': 'snow'},
        {'type': 'multiply', 'value': 1.5, 'mod': 'pos', 'text': '✨ Удача! +50%!', 'result': 'multiply'},
        {'type': 'multiply', 'value': 2.0, 'mod': 'pos', 'text': '⭐ Большая удача! ×2!', 'result': 'multiply'},
        {'type': 'multiply', 'value': 0.5, 'mod': 'neg', 'text': '🌧 Неудача... ÷2!', 'result': 'zero' if 0.5 == 0 else 'multiply'},
        {'type': 'multiply', 'value': 0, 'mod': 'neg', 'text': '💔 Обнуление!', 'result': 'zero'},
        {'type': 'shield', 'value': 1, 'text': '🛡️ Щит!', 'result': 'shield'},
        {'type': 'nothing', 'value': 0, 'text': '😕 Пусто...', 'result': 'nothing'},
        {'type': 'combo', 'value': {'multiply': 2.0, 'snowflakes': 200}, 'text': '🔥 КОМБО! ×2 + 200🌼!', 'result': 'combo'}
    ]

    selected = random.choice(effects)
    last_workout = db.get_last_workout(participant['id'])

    if selected['type'] in ['multiply', 'shield', 'combo'] and not last_workout:
        send_message(peer_id, "🎲 У тебя пока нет тренировок!", get_main_keyboard(participant['vk_id']))
        return

    result_text = ""
    result_flag = None

    if selected['type'] == 'snowflakes':
        new_balance = db.add_snowflakes(participant['id'], selected['value'], f'Рулетка: {selected["text"]}')
        result_text = f"{selected['text']}\n💰 Баланс: {new_balance} 🌼"
        result_flag = selected['result']
        db.log_lucky_usage(participant['id'], result_flag, selected['text'])

    elif selected['type'] == 'multiply':
        mod_type = selected['mod']
        mod_value = selected['value']
        if mod_type == 'neg' and last_workout.get('mod_neg') is not None:
            send_message(peer_id, "🛡️ Тренировка защищена щитом!", get_main_keyboard(participant['vk_id']))
            db.log_lucky_usage(participant['id'], 'blocked', selected['text'])
            return
        if mod_type == 'pos' and last_workout.get('mod_pos') is not None:
            send_message(peer_id, "⚠️ Уже применена позитивная способность!", get_back_keyboard())
            return

        updated_workout = db.apply_ability_mod(last_workout['id'], mod_type, mod_value)
        if not updated_workout:
            send_message(peer_id, "❌ Не удалось применить эффект", get_back_keyboard())
            return

        new_km = updated_workout['final_km']
        base_km = last_workout['original_km']
        result_text = f"{selected['text']}\n📊 {base_km} км → {new_km} км"
        result_flag = 'zero' if mod_value == 0 else selected['result']
        db.log_lucky_usage(participant['id'], result_flag, selected['text'])

    elif selected['type'] == 'shield':
        if last_workout.get('mod_neg') is not None:
            send_message(peer_id, "🛡️ Уже есть защита или атака!", get_main_keyboard(participant['vk_id']))
            db.log_lucky_usage(participant['id'], 'blocked', selected['text'])
            return

        updated_workout = db.apply_ability_mod(last_workout['id'], 'neg', 1.0)
        if not updated_workout:
            send_message(peer_id, "❌ Не удалось поставить щит", get_back_keyboard())
            return

        base_km = last_workout['original_km']
        result_text = f"{selected['text']}\n📊 Тренировка защищена! ({base_km} км)"
        result_flag = 'shield'
        db.log_lucky_usage(participant['id'], 'shield', selected['text'])

    elif selected['type'] == 'combo':
        if last_workout.get('mod_pos') is not None:
            send_message(peer_id, "⚠️ Уже применена позитивная способность!", get_back_keyboard())
            return

        updated_workout = db.apply_ability_mod(last_workout['id'], 'pos', 2.0)
        if not updated_workout:
            send_message(peer_id, "❌ Не удалось применить эффект", get_back_keyboard())
            return

        new_km = updated_workout['final_km']
        new_balance = db.add_snowflakes(participant['id'], 200, 'Рулетка: комбо!')
        base_km = last_workout['original_km']
        result_text = f"{selected['text']}\n📊 {base_km} км → {new_km} км\n💰 Баланс: {new_balance} 🌼"
        result_flag = 'combo'
        db.log_lucky_usage(participant['id'], 'combo', selected['text'])

    elif selected['type'] == 'nothing':
        result_text = selected['text']
        result_flag = 'nothing'
        db.log_lucky_usage(participant['id'], 'nothing', selected['text'])

    send_message(peer_id, f"🎲 РУЛЕТКА\n\n{result_text}", get_main_keyboard(participant['vk_id']))

    awarded = check_and_award_achievements(user_id, ability_data={'type': 'lucky', 'result': result_flag})
    if awarded:
        ach_text = "\n\n🏅 НОВЫЕ ДОСТИЖЕНИЯ!\n"
        for ach_id in awarded:
            ach = db.get_achievement_by_id(ach_id)
            if ach:
                ach_text += f"{ach['emoji']} {ach['name']} +{ach['snowflakes_reward']}🌼\n"
        send_message(peer_id, ach_text)

    chat_id = config.config.VK_CHAT_ID
    if chat_id:
        send_message(chat_id, f"🎲 РУЛЕТКА\n\n{participant['first_name']} {participant['last_name']}\n{selected['text']}")

def use_ability_shield(user_id, peer_id, participant):
    costs = SETTINGS['ABILITIES_COSTS']
    cost = costs.get('shield', 100)

    if participant['snowflake_balance'] < cost:
        send_message(peer_id, f"❌ Недостаточно ромашек! Нужно {cost}🌼", get_back_keyboard())
        return

    last_workout = db.get_last_workout(participant['id'])
    if not last_workout:
        send_message(peer_id, "❌ У тебя пока нет тренировок!", get_back_keyboard())
        return

    if last_workout.get('mod_neg') is not None:
        send_message(peer_id, "❌ На эту тренировку уже поставлена защита или атака!", get_back_keyboard())
        return

    new_balance = db.add_snowflakes(participant['id'], -cost, 'Щит')
    if new_balance is None:
        send_message(peer_id, "❌ Ошибка при списании ромашек", get_back_keyboard())
        return

    updated_workout = db.apply_ability_mod(last_workout['id'], 'neg', 1.0)
    if not updated_workout:
        db.add_snowflakes(participant['id'], cost, 'Возврат при ошибке')
        send_message(peer_id, "❌ Не удалось поставить щит", get_back_keyboard())
        return

    msg = f"""✅ Способность «Щит» применена!

🛡️ Твоя последняя тренировка защищена!
📊 День {last_workout['day']}: {last_workout['original_km']} км
💰 Баланс: {new_balance} 🌼"""
    send_message(peer_id, msg, get_main_keyboard(participant['vk_id']))

    chat_id = config.config.VK_CHAT_ID
    if chat_id:
        send_message(chat_id, f"🛡️ ЩИТ\n\n{participant['first_name']} {participant['last_name']} защитил тренировку!\n📏 {last_workout['original_km']} км")

    db.log_ability_usage(participant['id'], 'shield', None, last_workout['id'], cost, "shield applied")

def use_ability_x2boost(user_id, peer_id, participant):
    costs = SETTINGS['ABILITIES_COSTS']
    cost = costs.get('x2boost', 150)

    if participant['snowflake_balance'] < cost:
        send_message(peer_id, f"❌ Недостаточно ромашек! Нужно {cost}🌼", get_back_keyboard())
        return

    last_workout = db.get_last_workout(participant['id'])
    if not last_workout:
        send_message(peer_id, "❌ У тебя пока нет тренировок!", get_back_keyboard())
        return

    if last_workout.get('mod_pos'):
        send_message(peer_id, "❌ На эту тренировку уже применена способность!", get_back_keyboard())
        return

    new_balance = db.add_snowflakes(participant['id'], -cost, 'Удвоение')
    if new_balance is None:
        send_message(peer_id, "❌ Ошибка при списании ромашек", get_back_keyboard())
        return

    updated_workout = db.apply_ability_mod(last_workout['id'], 'pos', 2.0)
    if not updated_workout:
        db.add_snowflakes(participant['id'], cost, 'Возврат при ошибке')
        send_message(peer_id, "❌ Не удалось применить способность", get_back_keyboard())
        return

    new_km = updated_workout['final_km']
    msg = f"""✅ Способность «Удвоение» применена!

⚡ Твоя последняя тренировка увеличена в 2 раза!
📊 День {last_workout['day']}: {last_workout['original_km']} км → {new_km} км
💰 Баланс: {new_balance} 🌼"""
    send_message(peer_id, msg, get_main_keyboard(participant['vk_id']))

    chat_id = config.config.VK_CHAT_ID
    if chat_id:
        send_message(chat_id, f"⚡ УДВОЕНИЕ\n\n{participant['first_name']} {participant['last_name']}\n📏 {last_workout['original_km']} км → {new_km} км")

    db.log_ability_usage(participant['id'], 'x2boost', None, last_workout['id'], cost, f"original_km={last_workout['original_km']}, new_km={new_km}")

def execute_frostbite(attacker_id, attacker_participant, target_info, peer_id):
    costs = SETTINGS['ABILITIES_COSTS']
    cost = costs.get('frostbite', 150)

    if attacker_participant['snowflake_balance'] < cost:
        send_message(peer_id, f"❌ Недостаточно ромашек! Нужно {cost}🌼", get_back_keyboard())
        return False

    target_workout = db.get_workout_by_id(target_info['workout_id'])
    if not target_workout:
        send_message(peer_id, "❌ Тренировка цели не найдена", get_back_keyboard())
        return False

    if target_workout.get('mod_neg'):
        send_message(peer_id, "❌ На эту тренировку уже применена способность!", get_back_keyboard())
        return False

    new_balance = db.add_snowflakes(attacker_id, -cost, f'Разделение: {target_info["first_name"]} {target_info["last_name"]}')
    if new_balance is None:
        send_message(peer_id, "❌ Ошибка при списании ромашек", get_back_keyboard())
        return False

    updated_workout = db.apply_ability_mod(target_workout['id'], 'neg', 0.5)
    if not updated_workout:
        db.add_snowflakes(attacker_id, cost, 'Возврат при ошибке')
        send_message(peer_id, "❌ Не удалось применить способность", get_back_keyboard())
        return False

    new_km = updated_workout['final_km']
    base_km = target_workout['original_km']

    msg = f"""✅ Способность «Разделение» применена!

🌨 Ты заморозил тренировку {target_info['first_name']} {target_info['last_name']}!
📊 День {target_workout['day']}: {base_km} км → {new_km} км
💰 Баланс: {new_balance} 🌼"""
    send_message(peer_id, msg, get_main_keyboard(attacker_participant['vk_id']))

    target_msg = f"""⚠️ ВНИМАНИЕ!

{attacker_participant['first_name']} {attacker_participant['last_name']} использовал «Разделение» на тебя!
🌨 Твоя тренировка за день {target_workout['day']} уменьшена в 2 раза:
📊 {base_km} км → {new_km} км"""
    send_message(target_info['vk_id'], target_msg)

    chat_id = config.config.VK_CHAT_ID
    if chat_id:
        send_message(chat_id, f"✂️ РАЗДЕЛЕНИЕ\n\n{attacker_participant['first_name']} {attacker_participant['last_name']} атакует {target_info['first_name']} {target_info['last_name']}")

    db.log_ability_usage(attacker_participant['id'], 'frostbite', target_info['id'], target_info['workout_id'], cost, f"original_km={target_workout['original_km']}, new_km={new_km}")

    top3 = get_top3_participants()
    target_in_top3 = any(t['id'] == target_info['id'] for t in top3)
    awarded = check_and_award_achievements(attacker_participant['vk_id'], ability_data={'type': 'frostbite', 'target_in_top3': target_in_top3})
    if awarded:
        ach_text = "\n\n🏅 НОВЫЕ ДОСТИЖЕНИЯ!\n"
        for ach_id in awarded:
            ach = db.get_achievement_by_id(ach_id)
            if ach:
                ach_text += f"{ach['emoji']} {ach['name']} +{ach['snowflakes_reward']}🌼\n"
        send_message(peer_id, ach_text)

    return True

def execute_avalanche(attacker_id, attacker_participant, peer_id):
    costs = SETTINGS['ABILITIES_COSTS']
    cost = costs.get('avalanche', 150)

    if attacker_participant['snowflake_balance'] < cost:
        send_message(peer_id, f"❌ Недостаточно ромашек! Нужно {cost}🌼", get_back_keyboard())
        return False

    targets_to_attack = get_top5_targets_by_gender(attacker_id, attacker_participant['gender'])

    if len(targets_to_attack) == 0:
        send_message(peer_id, "❌ Нет доступных целей для атаки!", get_back_keyboard())
        return False

    new_balance = db.add_snowflakes(attacker_id, -cost, f'Потоп: {len(targets_to_attack)} целей из топа')
    if new_balance is None:
        send_message(peer_id, "❌ Ошибка при списании ромашек", get_back_keyboard())
        return False

    attacked_names = []
    for target in targets_to_attack:
        target_workout = db.get_workout_by_id(target['workout_id'])
        if not target_workout:
            continue
        if target_workout.get('mod_neg'):
            continue

        updated_workout = db.apply_ability_mod(target_workout['id'], 'neg', 0.8)
        if not updated_workout:
            continue

        new_km = updated_workout['final_km']
        base_km = target_workout['original_km']
        attacked_names.append(f"{target['first_name']} {target['last_name']}")

        if target['vk_id']:
            target_msg = f"""⚠️ ВНИМАНИЕ!

{attacker_participant['first_name']} {attacker_participant['last_name']} использовал «Потоп»!
🌊 Твоя тренировка за день {target_workout['day']} уменьшена на 20%:
📊 {base_km} км → {new_km} км"""
            send_message(target['vk_id'], target_msg)

        db.log_ability_usage(attacker_participant['id'], 'avalanche', target['id'], target['workout_id'], cost, f"original_km={target_workout['original_km']}, new_km={new_km}")

    if len(attacked_names) == 0:
        db.add_snowflakes(attacker_id, cost, 'Возврат при ошибке')
        send_message(peer_id, "❌ Не удалось атаковать ни одну цель", get_back_keyboard())
        return False

    names_preview = ", ".join(attacked_names[:5])
    msg = f"""✅ Способность «Потоп» применена!

🌪 Атакованы лидеры рейтинга ({len(attacked_names)}):
{names_preview}
💰 Баланс: {new_balance} 🌼"""
    send_message(peer_id, msg, get_main_keyboard(attacker_participant['vk_id']))

    chat_id = config.config.VK_CHAT_ID
    if chat_id:
        send_message(chat_id, f"🌊 ПОТОП\n\n{attacker_participant['first_name']} {attacker_participant['last_name']} атакует лидеров!\n🎯 {len(attacked_names)} участников:\n{names_preview}")

    return True

def execute_annihilation(attacker_id, attacker_participant, target_info, peer_id):
    costs = SETTINGS['ABILITIES_COSTS']
    cost = costs.get('annihilation', 200)

    if attacker_participant['snowflake_balance'] < cost:
        send_message(peer_id, f"❌ Недостаточно ромашек! Нужно {cost}🌼", get_back_keyboard())
        return False

    target_workout = db.get_workout_by_id(target_info['workout_id'])
    if not target_workout:
        send_message(peer_id, "❌ Тренировка цели не найдена", get_back_keyboard())
        return False

    if target_workout.get('mod_neg'):
        send_message(peer_id, "❌ На эту тренировку уже применена способность!", get_back_keyboard())
        return False

    new_balance = db.add_snowflakes(attacker_id, -cost, f'Обнуление: {target_info["first_name"]} {target_info["last_name"]}')
    if new_balance is None:
        send_message(peer_id, "❌ Ошибка при списании ромашек", get_back_keyboard())
        return False

    updated_workout = db.apply_ability_mod(target_workout['id'], 'neg', 0)
    if not updated_workout:
        db.add_snowflakes(attacker_id, cost, 'Возврат при ошибке')
        send_message(peer_id, "❌ Не удалось применить способность", get_back_keyboard())
        return False

    base_km = target_workout['original_km']

    msg = f"""✅ Способность «Обнуление» применена!

💀 Ты уничтожил тренировку {target_info['first_name']} {target_info['last_name']}!
📊 День {target_workout['day']}: {base_km} км → 0 км
💰 Баланс: {new_balance} 🌼"""
    send_message(peer_id, msg, get_main_keyboard(attacker_participant['vk_id']))

    target_msg = f"""💀 ВНИМАНИЕ! ПОЛНОЕ ОБНУЛЕНИЕ 💀

{attacker_participant['first_name']} {attacker_participant['last_name']} использовал «Обнуление» на тебя!
Твоя тренировка за день {target_workout['day']} УНИЧТОЖЕНА:
📊 {base_km} км → 0 км"""
    send_message(target_info['vk_id'], target_msg)

    chat_id = config.config.VK_CHAT_ID
    if chat_id:
        send_message(chat_id, f"💀 ОБНУЛЕНИЕ 💀\n\n{attacker_participant['first_name']} {attacker_participant['last_name']} уничтожил тренировку {target_info['first_name']} {target_info['last_name']}\n📏 {base_km} км → 0 км")

    db.log_ability_usage(attacker_participant['id'], 'annihilation', target_info['id'], target_info['workout_id'], cost, f"original_km={target_workout['original_km']}, new_km=0")

    top3 = get_top3_participants()
    target_in_top3 = any(t['id'] == target_info['id'] for t in top3)
    awarded = check_and_award_achievements(attacker_participant['vk_id'], ability_data={'type': 'annihilation', 'target_in_top3': target_in_top3})
    if awarded:
        ach_text = "\n\n🏅 НОВЫЕ ДОСТИЖЕНИЯ!\n"
        for ach_id in awarded:
            ach = db.get_achievement_by_id(ach_id)
            if ach:
                ach_text += f"{ach['emoji']} {ach['name']} +{ach['snowflakes_reward']}🌼\n"
        send_message(peer_id, ach_text)

    return True

def start_ability_frostbite(user_id, peer_id):
    ability_search[user_id] = {'ability': 'frostbite', 'step': 'waiting_name'}
    send_message(peer_id, "✂️ РАЗДЕЛЕНИЕ (150🌼)\n\nВведи имя или фамилию участника:")

def start_ability_annihilation(user_id, peer_id):
    ability_search[user_id] = {'ability': 'annihilation', 'step': 'waiting_name'}
    send_message(peer_id, "💀 ОБНУЛЕНИЕ (200🌼)\n\nВведи имя или фамилию участника:")

def send_abilities_menu(peer_id, user_id):
    participant = db.get_participant_by_vk(user_id)
    if not participant:
        send_message(peer_id, "❌ Ты не зарегистрирован!", get_back_keyboard())
        return

    costs = SETTINGS['ABILITIES_COSTS']
    text = f"""⚡️ СПОСОБНОСТИ

💰 Твой баланс: {participant['snowflake_balance']} 🌼

🎲 Рулетка (бесплатно, 1 раз/день)
⚡ Удвоение ({costs.get('x2boost', 150)}🌼) — ×2 к своей тренировке
🛡️ Щит ({costs.get('shield', 100)}🌼) — защита от атак
✂️ Разделение ({costs.get('frostbite', 150)}🌼) — ÷2 тренировку соперника
🌊 Потоп ({costs.get('avalanche', 150)}🌼) — атака топ-5 лидеров (-20%)
💀 Обнуление ({costs.get('annihilation', 200)}🌼) — полное уничтожение тренировки соперника"""
    send_message(peer_id, text, get_abilities_keyboard())

def send_achievements_menu(peer_id, user_id):
    participant = db.get_participant_by_vk(user_id)
    if not participant:
        send_message(peer_id, "❌ Ты не зарегистрирован!", get_back_keyboard())
        return

    user_achievements = db.get_user_achievements(user_id)
    completed_ids = set(a['achievement_id'] for a in user_achievements)
    all_achievements = db.get_all_achievements()

    text = "🏅 ВАШИ ДОСТИЖЕНИЯ\n\n"
    total_snowflakes = 0
    for ach in all_achievements:
        if ach['id'] in completed_ids:
            status = "✅"
            total_snowflakes += ach['snowflakes_reward']
        else:
            status = "❌"
        text += f"{status} {ach['emoji']} {ach['condition']} +{ach['snowflakes_reward']}🌼\n"
    text += f"\n📊 Всего заработано: {total_snowflakes} 🌼"
    send_message(peer_id, text, get_main_keyboard(participant['vk_id']))

def calculate_weekly_scores():
    now = db.get_current_time()
    today = now.date()
    days_since_monday = today.weekday()
    last_week_start = today - timedelta(days=days_since_monday + 7)
    last_week_end = last_week_start + timedelta(days=6)

    week_number = (last_week_start - datetime(2026, 3, 9).date()).days // 7 + 1
    year = last_week_start.year

    if db.get_weekly_calculation_log(week_number, year):
        return

    all_participants = db.get_all_participants()
    men = [p for p in all_participants if p.get('gender') == 'М']
    women = [p for p in all_participants if p.get('gender') == 'Ж']

    workouts = db.get_weekly_stats_for_period(last_week_start.isoformat(), last_week_end.isoformat())
    abilities = db.get_abilities_count_for_period(last_week_start.isoformat(), last_week_end.isoformat())

    ability_count = {}
    for a in abilities:
        pid = a['initiator_id']
        ability_count[pid] = ability_count.get(pid, 0) + 1

    weekly_stats = {}
    for w in workouts:
        pid = w['participant_id']
        if pid not in weekly_stats:
            weekly_stats[pid] = {'total_km': 0, 'max_km': 0, 'total_min': 0, 'has_workout': False}
        weekly_stats[pid]['total_km'] += w['original_km']
        weekly_stats[pid]['max_km'] = max(weekly_stats[pid]['max_km'], w['original_km'])
        weekly_stats[pid]['total_min'] += w['original_min']
        weekly_stats[pid]['has_workout'] = True

    for pid, count in ability_count.items():
        if pid in weekly_stats:
            weekly_stats[pid]['abilities_count'] = count
        else:
            weekly_stats[pid] = {'total_km': 0, 'max_km': 0, 'total_min': 0, 'has_workout': False, 'abilities_count': count}

    for pid, stats in weekly_stats.items():
        if stats['total_km'] > 0:
            stats['avg_pace'] = stats['total_min'] / stats['total_km']
        else:
            stats['avg_pace'] = 999

    def calculate_group_scores(group):
        participants_data = []
        for p in group:
            pid = p['id']
            stats = weekly_stats.get(pid, {})
            if stats.get('has_workout'):
                participants_data.append({
                    'id': pid,
                    'first_name': p['first_name'],
                    'last_name': p['last_name'],
                    'total_km': stats.get('total_km', 0),
                    'max_km': stats.get('max_km', 0),
                    'avg_pace': stats.get('avg_pace', 999),
                    'abilities_count': stats.get('abilities_count', 0)
                })

        participants_data.sort(key=lambda x: x['total_km'], reverse=True)

        points_table = [50, 45, 41, 38, 36, 34, 32, 30, 28, 26, 24, 22, 20, 18, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

        for idx, p in enumerate(participants_data):
            if idx < 30:
                p['km_points'] = points_table[idx]
                p['km_place'] = idx + 1
            else:
                p['km_points'] = 0
                p['km_place'] = 0

        if participants_data:
            max_km = max(p['total_km'] for p in participants_data)
            max_single = max(p['max_km'] for p in participants_data)
            valid_pace = [p for p in participants_data if p['avg_pace'] < 999]
            max_abilities = max(p.get('abilities_count', 0) for p in participants_data)

            for p in participants_data:
                if p['total_km'] == max_km:
                    p['bonus_max_km'] = True
                if p['max_km'] == max_single:
                    p['bonus_longest_km'] = True
                if valid_pace and p['avg_pace'] == min(v for v in [p2['avg_pace'] for p2 in valid_pace]):
                    p['bonus_best_pace'] = True
                if max_abilities > 0 and p.get('abilities_count', 0) == max_abilities:
                    p['bonus_most_abilities'] = True

        results = []
        for p in participants_data:
            total = p['km_points']
            if p.get('bonus_max_km'): total += 10
            if p.get('bonus_longest_km'): total += 10
            if p.get('bonus_best_pace'): total += 10
            if p.get('bonus_most_abilities'): total += 10

            db.save_weekly_score({
                'participant_id': p['id'],
                'week_number': week_number,
                'year': year,
                'week_start': last_week_start.isoformat(),
                'week_end': last_week_end.isoformat(),
                'km_place': p.get('km_place', 0),
                'km_points': p.get('km_points', 0),
                'bonus_longest_km': p.get('bonus_longest_km', False),
                'bonus_best_pace': p.get('bonus_best_pace', False),
                'bonus_most_abilities': p.get('bonus_most_abilities', False),
                'bonus_max_km': p.get('bonus_max_km', False),
                'total_points': total
            })

            if p.get('km_place', 0) > 0 or total > 0:
                results.append({'name': f"{p['first_name']} {p['last_name']}", 'place': p.get('km_place', 0), 'points': total})

        return results

    men_results = calculate_group_scores(men)
    women_results = calculate_group_scores(women)

    chat_id = config.config.VK_CHAT_ID
    if chat_id:
        msg = f"🏆 ЕЖЕНЕДЕЛЬНЫЙ РЕЙТИНГ\n\n📅 {last_week_start.strftime('%d.%m')} - {last_week_end.strftime('%d.%m')}\n\n"
        msg += "👨 МУЖЧИНЫ:\n"
        for r in men_results[:10]:
            msg += f"{r['place']}. {r['name']} — {r['points']} очков\n"
        if not men_results:
            msg += "— нет данных\n"
        msg += "\n👩 ЖЕНЩИНЫ:\n"
        for r in women_results[:10]:
            msg += f"{r['place']}. {r['name']} — {r['points']} очков\n"
        if not women_results:
            msg += "— нет данных\n"
        send_message(chat_id, msg)

    db.save_weekly_calculation_log(week_number, year)

def send_admin_panel(peer_id):
    text = """👑 АДМИН-ПАНЕЛЬ

Выбери действие:

🗑 Удалить тренировку
🚫 Дисквалифицировать участника
⚙️ Настройки
📋 Список участников"""

    keyboard = VkKeyboard()
    keyboard.add_button('🗑 Удалить тренировку', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('🚫 Дисквалифицировать участника', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('⚙️ Настройки', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('📋 Список участников', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('◀️ Назад', color=VkKeyboardColor.SECONDARY)
    send_message(peer_id, text, keyboard.get_keyboard())

def send_settings_panel(peer_id):
    text = f"""⚙️ НАСТРОЙКИ

📅 Дата старта: {SETTINGS['START_DATE']}

/set_start_date 2026-04-15
/set_setting MIN_KM 5
/set_setting BASE_SNOWFLAKES 30"""
    send_message(peer_id, text, get_back_keyboard())

def send_participants_list(peer_id):
    participants = db.get_all_participants()
    men = [p for p in participants if p.get('gender') == 'М']
    women = [p for p in participants if p.get('gender') == 'Ж']

    text = "📋 СПИСОК УЧАСТНИКОВ\n\n"
    text += f"👨 Мужчины ({len(men)}):\n"
    for p in men[:20]:
        text += f"• {p['first_name']} {p['last_name']} (ID: {p['vk_id']})\n"
    if len(men) > 20:
        text += f"  и ещё {len(men)-20}\n"

    text += f"\n👩 Женщины ({len(women)}):\n"
    for p in women[:20]:
        text += f"• {p['first_name']} {p['last_name']} (ID: {p['vk_id']})\n"
    if len(women) > 20:
        text += f"  и ещё {len(women)-20}\n"

    send_message(peer_id, text, get_back_keyboard())

def get_workouts_by_participant_admin(participant_id):
    try:
        response = db.supabase.table('workouts')\
            .select('*')\
            .eq('participant_id', participant_id)\
            .order('day', desc=True)\
            .execute()
        return response.data if response.data else []
    except:
        return []

@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.json
        if data.get('type') == 'confirmation':
            return CONFIRMATION_TOKEN

        if data.get('type') == 'message_new':
            msg = data['object']['message']
            user_id = msg['from_id']
            peer_id = msg['peer_id']
            raw_text = msg.get('text', '').strip()
            text = clean_text(raw_text)

            is_chat = peer_id > 2000000000

            if text == '/chatid':
                send_message(peer_id, f"Peer ID: {peer_id}")
                return 'ok'

            if is_chat:
                return 'ok'

            today = db.get_current_time().date()
            if today.weekday() == 0:
                calculate_weekly_scores()

            participant = db.get_participant_by_vk(user_id)

            if text == '/reload_settings' and user_id in config.config.ADMINS:
                load_settings()
                send_message(peer_id, "✅ Настройки перезагружены!")
                return 'ok'

            if text == '/clear_chat_keyboard' and user_id in config.config.ADMINS:
                chat_id = config.config.VK_CHAT_ID
                if chat_id:
                    try:
                        vk = vk_api.VkApi(token=config.config.VK_TOKEN).get_api()
                        empty_keyboard = '{"one_time":false,"buttons":[]}'
                        vk.messages.send(peer_id=chat_id, message=".", keyboard=empty_keyboard, random_id=0, from_group=1)
                        send_message(peer_id, "✅ Клавиатура скрыта")
                    except Exception as e:
                        send_message(peer_id, f"❌ Ошибка: {e}")
                return 'ok'

            if text.startswith('/set_start_date') and user_id in config.config.ADMINS:
                parts = raw_text.split()
                if len(parts) >= 2:
                    new_date = parts[1]
                    try:
                        datetime.strptime(new_date, '%Y-%m-%d')
                        db.update_setting('START_DATE', new_date)
                        load_settings()
                        send_message(peer_id, f"✅ Дата старта: {new_date}")
                    except:
                        send_message(peer_id, "❌ Формат: /set_start_date 2026-04-15")
                return 'ok'

            if text.startswith('/set_setting') and user_id in config.config.ADMINS:
                parts = raw_text.split()
                if len(parts) >= 3:
                    key = parts[1]
                    value = ' '.join(parts[2:])
                    db.update_setting(key, value)
                    load_settings()
                    send_message(peer_id, f"✅ {key} = {value}")
                return 'ok'

            if not participant:
                if text in ['/start', 'начать', 'старт']:
                    ref = msg.get('ref', None)
                    try:
                        vk = vk_api.VkApi(token=config.config.VK_TOKEN).get_api()
                        user_info = vk.users.get(user_ids=user_id, fields='sex')[0]
                        first_name = user_info.get('first_name', '')
                        last_name = user_info.get('last_name', '')
                        gender_code = user_info.get('sex', 0)
                        gender = 'Ж' if gender_code == 1 else 'М'

                        initial_status = 'pending_payment'
                        activation_message = ""

                        if ref:
                            payment = db.get_payment_by_ref(ref)
                            if payment and payment.get('status') == 'succeeded':
                                initial_status = 'active'
                                activation_message = "\n\n✅ Платёж подтверждён! Ты активирован!"

                        data = {
                            'vk_id': user_id,
                            'first_name': first_name,
                            'last_name': last_name,
                            'gender': gender,
                            'snowflake_balance': 0,
                            'total_workouts': 0,
                            'total_km': 0,
                            'total_min': 0,
                            'status': initial_status
                        }
                        response = db.supabase.table('participants').insert(data).execute()

                        if response.data:
                            if initial_status == 'active':
                                send_message(peer_id, f"✅ Регистрация успешна!\n\n👋 {first_name} {last_name}!{activation_message}\n\n🌼 Баланс: 0\n\nМожно добавлять тренировки! 🏃‍♂️", get_main_keyboard(user_id))
                            else:
                                keyboard = VkKeyboard()
                                keyboard.add_button('💰 Оплатить участие', color=VkKeyboardColor.POSITIVE)
                                keyboard.add_line()
                                keyboard.add_button('❓ Помощь', color=VkKeyboardColor.SECONDARY)
                                send_message(peer_id, f"✅ Регистрация успешна!\n\n👋 {first_name} {last_name}!\n\n⚠️ Для участия оплати взнос 990₽.", keyboard.get_keyboard())
                            return 'ok'
                        else:
                            send_message(peer_id, "❌ Ошибка регистрации.", get_main_keyboard())
                            return 'ok'
                    except Exception as e:
                        print(f"❌ Ошибка регистрации: {e}")
                        send_message(peer_id, "❌ Ошибка регистрации.", get_main_keyboard())
                        return 'ok'
                else:
                    return 'ok'

            if participant and participant.get('status') != 'active':
                if text == '💰 Оплатить участие':
                    payment_result = create_payment(
                        user_id=user_id,
                        amount=990,
                        description=f"Взнос ({participant['first_name']} {participant['last_name']})",
                        return_url=config.config.YOOKASSA_RETURN_URL_BOT
                    )
                    if payment_result['success']:
                        db.save_payment(
                            payment_id=payment_result['payment_id'],
                            payment_ref=payment_result['payment_ref'],
                            vk_id=user_id,
                            amount=990,
                            status='pending'
                        )
                        keyboard = VkKeyboard()
                        keyboard.add_open_link_button('💳 Перейти к оплате', payment_result['payment_url'])
                        send_message(peer_id, f"💳 Оплати взнос 990₽.\n\nПосле оплаты ты будешь активирован автоматически!", keyboard.get_keyboard())
                    else:
                        send_message(peer_id, "❌ Не удалось создать платёж.", get_main_keyboard(user_id))
                    return 'ok'
                else:
                    send_message(peer_id, "❌ Аккаунт не активирован. Нажми «Оплатить участие».", get_main_keyboard(user_id))
                    return 'ok'

            # Обработка поиска цели
            if user_id in ability_search:
                search_data = ability_search[user_id]
                ability = search_data['ability']
                if search_data['step'] == 'waiting_name':
                    if text:
                        matches = search_targets_by_name(text, participant['id'])
                        if len(matches) == 0:
                            send_message(peer_id, "❌ Участник не найден.")
                            return 'ok'
                        elif len(matches) == 1:
                            target = matches[0]
                            if ability == 'frostbite':
                                execute_frostbite(participant['id'], participant, target, peer_id)
                            elif ability == 'annihilation':
                                execute_annihilation(participant['id'], participant, target, peer_id)
                            del ability_search[user_id]
                            return 'ok'
                        else:
                            ability_search[user_id]['step'] = 'waiting_choice'
                            ability_search[user_id]['candidates'] = matches
                            keyboard = VkKeyboard()
                            for i, t in enumerate(matches[:10]):
                                keyboard.add_button(f"{t['first_name']} {t['last_name']}", color=VkKeyboardColor.PRIMARY)
                                if (i + 1) % 2 == 0:
                                    keyboard.add_line()
                            keyboard.add_line()
                            keyboard.add_button('◀️ Отмена', color=VkKeyboardColor.SECONDARY)
                            send_message(peer_id, f"🔍 Найдено {len(matches)} участников. Выбери цель:", keyboard.get_keyboard())
                            return 'ok'
                elif search_data['step'] == 'waiting_choice':
                    if text == '◀️ Отмена':
                        del ability_search[user_id]
                        send_abilities_menu(peer_id, user_id)
                        return 'ok'
                    selected = None
                    for t in search_data['candidates']:
                        if text == f"{t['first_name']} {t['last_name']}":
                            selected = t
                            break
                    if selected:
                        if ability == 'frostbite':
                            execute_frostbite(participant['id'], participant, selected, peer_id)
                        elif ability == 'annihilation':
                            execute_annihilation(participant['id'], participant, selected, peer_id)
                        del ability_search[user_id]
                    else:
                        send_message(peer_id, "❌ Выбери цель из списка.")
                    return 'ok'

            state = user_states.get(user_id)

            # Админ: удаление тренировки
            if state and state.get('action') == 'admin_delete_workout_search':
                if text == '❌ Отмена':
                    del user_states[user_id]
                    send_admin_panel(peer_id)
                    return 'ok'
                matches = search_targets_by_name(text, None)
                if len(matches) == 0:
                    send_message(peer_id, "❌ Участник не найден.")
                    return 'ok'
                elif len(matches) == 1:
                    user_states[user_id] = {'action': 'admin_delete_workout', 'step': 'select_workout', 'target_participant': matches[0]}
                    workouts = get_workouts_by_participant_admin(matches[0]['id'])
                    if not workouts:
                        send_message(peer_id, "❌ Нет тренировок")
                        del user_states[user_id]
                        send_admin_panel(peer_id)
                        return 'ok'
                    user_states[user_id]['workouts'] = workouts
                    keyboard = VkKeyboard()
                    for w in workouts[:10]:
                        keyboard.add_button(f"День {w['day']} - {w['original_km']} км ({w['workout_date']})", color=VkKeyboardColor.PRIMARY)
                        keyboard.add_line()
                    keyboard.add_button('◀️ Отмена', color=VkKeyboardColor.SECONDARY)
                    send_message(peer_id, f"👤 {matches[0]['first_name']} {matches[0]['last_name']}\n\nВыбери тренировку:", keyboard.get_keyboard())
                    return 'ok'
                else:
                    user_states[user_id] = {'action': 'admin_delete_workout', 'step': 'select_participant', 'candidates': matches}
                    keyboard = VkKeyboard()
                    for p in matches[:10]:
                        keyboard.add_button(f"{p['first_name']} {p['last_name']}", color=VkKeyboardColor.PRIMARY)
                        keyboard.add_line()
                    keyboard.add_button('◀️ Отмена', color=VkKeyboardColor.SECONDARY)
                    send_message(peer_id, f"🔍 Найдено {len(matches)}. Выбери:", keyboard.get_keyboard())
                    return 'ok'

            if state and state.get('action') == 'admin_delete_workout' and state.get('step') == 'select_participant':
                if text == '◀️ Отмена':
                    del user_states[user_id]
                    send_admin_panel(peer_id)
                    return 'ok'
                selected = None
                for p in state.get('candidates', []):
                    if text == f"{p['first_name']} {p['last_name']}":
                        selected = p
                        break
                if selected:
                    user_states[user_id]['target_participant'] = selected
                    user_states[user_id]['step'] = 'select_workout'
                    del user_states[user_id]['candidates']
                    workouts = get_workouts_by_participant_admin(selected['id'])
                    if not workouts:
                        send_message(peer_id, "❌ Нет тренировок")
                        del user_states[user_id]
                        send_admin_panel(peer_id)
                        return 'ok'
                    user_states[user_id]['workouts'] = workouts
                    keyboard = VkKeyboard()
                    for w in workouts[:10]:
                        keyboard.add_button(f"День {w['day']} - {w['original_km']} км ({w['workout_date']})", color=VkKeyboardColor.PRIMARY)
                        keyboard.add_line()
                    keyboard.add_button('◀️ Отмена', color=VkKeyboardColor.SECONDARY)
                    send_message(peer_id, f"👤 {selected['first_name']} {selected['last_name']}\n\nВыбери тренировку:", keyboard.get_keyboard())
                return 'ok'

            if state and state.get('action') == 'admin_delete_workout' and state.get('step') == 'select_workout':
                if text == '◀️ Отмена':
                    del user_states[user_id]
                    send_admin_panel(peer_id)
                    return 'ok'
                selected_workout = None
                for w in state.get('workouts', []):
                    if text == f"День {w['day']} - {w['original_km']} км ({w['workout_date']})":
                        selected_workout = w
                        break
                if selected_workout:
                    user_states[user_id]['selected_workout'] = selected_workout
                    user_states[user_id]['step'] = 'confirm'
                    target = state['target_participant']
                    w = selected_workout
                    msg = f"""📋 УДАЛЕНИЕ ТРЕНИРОВКИ

👤 {target['first_name']} {target['last_name']}
📅 {w['workout_date']}
📊 День {w['day']}: {w['original_km']} км

Подтверждаешь?"""
                    keyboard = VkKeyboard()
                    keyboard.add_button('✅ Подтвердить', color=VkKeyboardColor.NEGATIVE)
                    keyboard.add_button('❌ Отмена', color=VkKeyboardColor.SECONDARY)
                    send_message(peer_id, msg, keyboard.get_keyboard())
                return 'ok'

            if state and state.get('action') == 'admin_delete_workout' and state.get('step') == 'confirm':
                if text == '✅ Подтвердить':
                    workout = state['selected_workout']
                    target = state['target_participant']
                    db.update_workout_status(workout['id'], 'deleted')
                    send_message(peer_id, f"✅ Тренировка удалена!\n\n{target['first_name']} {target['last_name']}\nДень {workout['day']}: {workout['original_km']} км")
                    chat_id = config.config.VK_CHAT_ID
                    if chat_id:
                        send_message(chat_id, f"👑 Админ удалил тренировку\n{target['first_name']} {target['last_name']}\nДень {workout['day']}: {workout['original_km']} км")
                    del user_states[user_id]
                    send_admin_panel(peer_id)
                elif text == '❌ Отмена':
                    del user_states[user_id]
                    send_admin_panel(peer_id)
                return 'ok'

            # Админ: бан
            if state and state.get('action') == 'admin_ban_search':
                if text == '❌ Отмена':
                    del user_states[user_id]
                    send_admin_panel(peer_id)
                    return 'ok'
                matches = search_targets_by_name(text, None)
                if len(matches) == 0:
                    send_message(peer_id, "❌ Участник не найден.")
                    return 'ok'
                elif len(matches) == 1:
                    user_states[user_id] = {'action': 'admin_ban', 'step': 'confirm_ban', 'target_participant': matches[0]}
                    target = matches[0]
                    msg = f"""📋 ДИСКВАЛИФИКАЦИЯ

👤 {target['first_name']} {target['last_name']}
👫 {target.get('gender', '-')}
🏃 Тренировок: {target.get('total_workouts', 0)}
🌼 Км: {target.get('total_km', 0)}

Подтверждаешь?"""
                    keyboard = VkKeyboard()
                    keyboard.add_button('✅ Подтвердить', color=VkKeyboardColor.NEGATIVE)
                    keyboard.add_button('❌ Отмена', color=VkKeyboardColor.SECONDARY)
                    send_message(peer_id, msg, keyboard.get_keyboard())
                    return 'ok'
                else:
                    user_states[user_id] = {'action': 'admin_ban', 'step': 'select_participant_ban', 'candidates': matches}
                    keyboard = VkKeyboard()
                    for p in matches[:10]:
                        keyboard.add_button(f"{p['first_name']} {p['last_name']}", color=VkKeyboardColor.PRIMARY)
                        keyboard.add_line()
                    keyboard.add_button('◀️ Отмена', color=VkKeyboardColor.SECONDARY)
                    send_message(peer_id, f"🔍 Найдено {len(matches)}. Выбери:", keyboard.get_keyboard())
                    return 'ok'

            if state and state.get('action') == 'admin_ban' and state.get('step') == 'select_participant_ban':
                if text == '◀️ Отмена':
                    del user_states[user_id]
                    send_admin_panel(peer_id)
                    return 'ok'
                selected = None
                for p in state.get('candidates', []):
                    if text == f"{p['first_name']} {p['last_name']}":
                        selected = p
                        break
                if selected:
                    user_states[user_id]['target_participant'] = selected
                    user_states[user_id]['step'] = 'confirm_ban'
                    del user_states[user_id]['candidates']
                    msg = f"""📋 ДИСКВАЛИФИКАЦИЯ

👤 {selected['first_name']} {selected['last_name']}
👫 {selected.get('gender', '-')}
🏃 Тренировок: {selected.get('total_workouts', 0)}
🌼 Км: {selected.get('total_km', 0)}

Подтверждаешь?"""
                    keyboard = VkKeyboard()
                    keyboard.add_button('✅ Подтвердить', color=VkKeyboardColor.NEGATIVE)
                    keyboard.add_button('❌ Отмена', color=VkKeyboardColor.SECONDARY)
                    send_message(peer_id, msg, keyboard.get_keyboard())
                return 'ok'

            if state and state.get('action') == 'admin_ban' and state.get('step') == 'confirm_ban':
                if text == '✅ Подтвердить':
                    target = state['target_participant']
                    db.update_participant_status(target['id'], 'banned')
                    send_message(peer_id, f"✅ {target['first_name']} {target['last_name']} дисквалифицирован!")
                    chat_id = config.config.VK_CHAT_ID
                    if chat_id:
                        send_message(chat_id, f"🚫 {target['first_name']} {target['last_name']} дисквалифицирован")
                    if target.get('vk_id'):
                        send_message(target['vk_id'], "🚫 Вы дисквалифицированы.")
                    del user_states[user_id]
                    send_admin_panel(peer_id)
                elif text == '❌ Отмена':
                    del user_states[user_id]
                    send_admin_panel(peer_id)
                return 'ok'

            if state and state.get('action') == 'add_workout':
                step = state.get('step')
                if text == '❌ Отмена':
                    del user_states[user_id]
                    send_main_menu(peer_id, participant)
                    return 'ok'
                if text == '✏️ Изменить':
                    if step in ['distance', 'duration_after_distance']:
                        user_states[user_id]['step'] = 'distance'
                        send_message(peer_id, "Введи дистанцию (км):", get_cancel_keyboard())
                        return 'ok'
                    elif step in ['duration', 'photo']:
                        user_states[user_id]['step'] = 'duration'
                        send_message(peer_id, "Введи время (мин):", get_cancel_keyboard())
                        return 'ok'
                if step == 'distance':
                    try:
                        distance = int(float(text.split()[0]))
                    except:
                        distance = None
                    if distance and distance >= SETTINGS['MIN_KM']:
                        user_states[user_id]['distance'] = distance
                        user_states[user_id]['step'] = 'duration_after_distance'
                        send_message(peer_id, f"✅ Дистанция: {distance} км\n\nВведи время (мин):", get_edit_keyboard())
                    else:
                        send_message(peer_id, f"❌ Дистанция должна быть ≥ {SETTINGS['MIN_KM']} км.", get_cancel_keyboard())
                    return 'ok'
                if step == 'duration_after_distance':
                    try:
                        duration = int(float(text.split()[0]))
                    except:
                        duration = None
                    if duration is not None and duration >= SETTINGS['MIN_MINUTES']:
                        user_states[user_id]['duration'] = duration
                        user_states[user_id]['step'] = 'photo'
                        send_message(peer_id, f"✅ Время: {duration} мин\n\n📸 Отправь фото GPS-трека.", get_edit_keyboard())
                    else:
                        send_message(peer_id, f"❌ Время должно быть ≥ {SETTINGS['MIN_MINUTES']} мин.", get_cancel_keyboard())
                    return 'ok'
                if step == 'duration':
                    try:
                        duration = int(float(text.split()[0]))
                    except:
                        duration = None
                    if duration is not None and duration >= SETTINGS['MIN_MINUTES']:
                        user_states[user_id]['duration'] = duration
                        user_states[user_id]['step'] = 'photo'
                        send_message(peer_id, f"✅ Время: {duration} мин\n\n📸 Отправь фото GPS-трека.", get_edit_keyboard())
                    else:
                        send_message(peer_id, f"❌ Время должно быть ≥ {SETTINGS['MIN_MINUTES']} мин.", get_cancel_keyboard())
                    return 'ok'
                if step == 'photo':
                    if msg.get('attachments'):
                        has_photo = any(att['type'] == 'photo' for att in msg['attachments'])
                        if has_photo:
                            today = db.get_current_date().isoformat()
                            if db.get_workout_count_by_date(participant['id'], today) >= 1:
                                send_message(peer_id, "❌ Сегодня уже была тренировка!", get_main_keyboard(participant['vk_id']))
                                del user_states[user_id]
                                return 'ok'

                            photo_attachment = None
                            for att in msg['attachments']:
                                if att['type'] == 'photo':
                                    photo = att['photo']
                                    owner_id = photo.get('owner_id')
                                    photo_id = photo.get('id')
                                    access_key = photo.get('access_key', '')
                                    if owner_id and photo_id:
                                        photo_attachment = f"photo{owner_id}_{photo_id}"
                                        if access_key:
                                            photo_attachment += f"_{access_key}"
                                    break

                            distance = state['distance']
                            duration = state['duration']
                            day = get_current_day()
                            workout_hour = db.get_current_hour()

                            workout = db.add_workout(participant['id'], day, distance, duration)
                            if not workout:
                                send_message(peer_id, "❌ Ошибка сохранения.", get_main_keyboard(participant['vk_id']))
                                del user_states[user_id]
                                return 'ok'

                            base_snowflakes = SETTINGS['BASE_SNOWFLAKES']
                            hour = workout_hour
                            if hour < SETTINGS['DAY_HOUR_LIMIT']:
                                total_snowflakes = base_snowflakes + SETTINGS['DAY_BONUS']
                            else:
                                total_snowflakes = base_snowflakes

                            new_balance = db.add_snowflakes(participant['id'], total_snowflakes, f'Тренировка день {day}')
                            msg_text = f"✅ Тренировка записана!\n\n📊 День {day}: {distance} км / {duration} мин\n\n🌼 +{total_snowflakes} ромашек\n💰 Баланс: {new_balance} 🌼"
                            send_message(peer_id, msg_text, get_main_keyboard(participant['vk_id']))

                            awarded = check_and_award_achievements(user_id, workout_data={'hour': workout_hour})
                            if awarded:
                                ach_text = "\n\n🏅 НОВЫЕ ДОСТИЖЕНИЯ!\n"
                                for ach_id in awarded:
                                    ach = db.get_achievement_by_id(ach_id)
                                    if ach:
                                        ach_text += f"{ach['emoji']} {ach['name']} +{ach['snowflakes_reward']}🌼\n"
                                send_message(peer_id, ach_text)

                            chat_id = config.config.VK_CHAT_ID
                            if chat_id:
                                chat_msg = f"✅ ОТЧЕТ ПРИНЯТ\n\n{participant['first_name']} {participant['last_name']}\n📏 {distance} км за {duration} мин\n📅 #day{day}\n\n🌼 +{total_snowflakes} ромашек"
                                if photo_attachment:
                                    try:
                                        vk = vk_api.VkApi(token=config.config.VK_TOKEN).get_api()
                                        vk.messages.send(peer_id=chat_id, message=chat_msg, attachment=photo_attachment, random_id=0, from_group=1)
                                    except:
                                        send_message(chat_id, chat_msg)
                                else:
                                    send_message(chat_id, chat_msg)

                            del user_states[user_id]
                            return 'ok'
                        else:
                            send_message(peer_id, "❌ Отправь фото.", get_cancel_keyboard())
                            return 'ok'
                    else:
                        send_message(peer_id, "❌ Отправь фото тренировки.", get_cancel_keyboard())
                        return 'ok'

            if text in ['/start', '/menu', 'меню', 'главное меню']:
                send_main_menu(peer_id, participant)
                return 'ok'
            if text == '➕ Добавить тренировку':
                user_states[user_id] = {'action': 'add_workout', 'step': 'distance'}
                send_message(peer_id, "Введи дистанцию (км):", get_cancel_keyboard())
                return 'ok'
            if text in ['📊 Статистика', '/stats']:
                send_stats(peer_id, participant)
                return 'ok'
            if text in ['⭐️ Рейтинг', '/rating']:
                all_participants = db.get_all_participants()
                men = [p for p in all_participants if p.get('gender') == 'М' and p.get('total_km', 0) > 0]
                women = [p for p in all_participants if p.get('gender') == 'Ж' and p.get('total_km', 0) > 0]
                men.sort(key=lambda x: x.get('total_km', 0), reverse=True)
                women.sort(key=lambda x: x.get('total_km', 0), reverse=True)
                msg = "🏆 РЕЙТИНГ\n\n👨 МУЖЧИНЫ:\n"
                for i, p in enumerate(men[:3], 1):
                    medal = "🥇" if i==1 else "🥈" if i==2 else "🥉"
                    msg += f"{medal} {p['first_name']} {p['last_name']} — {p['total_km']} км\n"
                if not men: msg += "— пока нет\n"
                msg += "\n👩 ЖЕНЩИНЫ:\n"
                for i, p in enumerate(women[:3], 1):
                    medal = "🥇" if i==1 else "🥈" if i==2 else "🥉"
                    msg += f"{medal} {p['first_name']} {p['last_name']} — {p['total_km']} км\n"
                if not women: msg += "— пока нет\n"
                msg += "\n🔗 https://mrbodya1.github.io/YUB/"
                send_message(peer_id, msg, get_main_keyboard(participant['vk_id']))
                return 'ok'
            if text in ['⚡️ Способности', '/abilities']:
                send_abilities_menu(peer_id, user_id)
                return 'ok'
            if text in ['🏅 Достижения', '/achievements']:
                send_achievements_menu(peer_id, user_id)
                return 'ok'
            if text == '🎲 Рулетка (бесплатно)':
                use_ability_lucky(user_id, peer_id, participant)
                return 'ok'
            if text.startswith('⚡ Удвоение'):
                use_ability_x2boost(user_id, peer_id, participant)
                return 'ok'
            if text.startswith('🛡️ Щит'):
                use_ability_shield(user_id, peer_id, participant)
                return 'ok'
            if text.startswith('✂️ Разделение'):
                start_ability_frostbite(user_id, peer_id)
                return 'ok'
            if text.startswith('🌊 Потоп'):
                execute_avalanche(participant['id'], participant, peer_id)
                return 'ok'
            if text.startswith('💀 Обнуление'):
                start_ability_annihilation(user_id, peer_id)
                return 'ok'
            if text == '👑 Админ-панель' and user_id in config.config.ADMINS:
                send_admin_panel(peer_id)
                return 'ok'
            if text == '🗑 Удалить тренировку' and user_id in config.config.ADMINS:
                user_states[user_id] = {'action': 'admin_delete_workout_search', 'step': 'search'}
                send_message(peer_id, "Введи имя/фамилию участника:", get_cancel_keyboard())
                return 'ok'
            if text == '🚫 Дисквалифицировать участника' and user_id in config.config.ADMINS:
                user_states[user_id] = {'action': 'admin_ban_search', 'step': 'search'}
                send_message(peer_id, "Введи имя/фамилию участника:", get_cancel_keyboard())
                return 'ok'
            if text == '⚙️ Настройки' and user_id in config.config.ADMINS:
                send_settings_panel(peer_id)
                return 'ok'
            if text == '📋 Список участников' and user_id in config.config.ADMINS:
                send_participants_list(peer_id)
                return 'ok'
            if text in ['📋 Правила', '/rules']:
                send_rules(peer_id)
                return 'ok'
            if text in ['❓ Помощь', '/help']:
                send_help(peer_id)
                return 'ok'
            if text in ['◀️ Назад', 'назад']:
                send_main_menu(peer_id, participant)
                return 'ok'

            return 'ok'
        return 'ok'
    except Exception as e:
        print(f"❌ Ошибка webhook: {e}")
        return 'ok'

def send_main_menu(peer_id, participant):
    current_day = get_current_day()
    rating = db.get_rating()
    place = 1
    for i, p in enumerate(rating, 1):
        if p['id'] == participant['id']:
            place = i
            break
    if place == 1: place_text = "🥇 1 место"
    elif place == 2: place_text = "🥈 2 место"
    elif place == 3: place_text = "🥉 3 место"
    else: place_text = f"{place} место из {len(rating)}"

    text = f"""🏔️ КОРОЛЕВСКАЯ БИТВА

Привет, {participant['first_name']}!
День {current_day}

🌼 Баланс: {participant['snowflake_balance']}
🏃 Всего км: {participant['total_km']}
🏆 {place_text}

Выбери действие:"""
    send_message(peer_id, text, get_main_keyboard(participant['vk_id']))

def send_stats(peer_id, participant):
    avg_pace = participant['total_min'] / participant['total_km'] if participant['total_km'] > 0 else 0
    gender_text = "Мужской" if participant['gender'] == 'М' else "Женский"
    text = f"""📊 СТАТИСТИКА

👤 {participant['first_name']} {participant['last_name']}
👫 {gender_text}

🏃 Тренировок: {participant['total_workouts']}
🌼 Км: {participant['total_km']}
⏱️ Время: {participant['total_min']} мин
📈 Темп: {avg_pace:.2f} мин/км

🌼 Ромашек: {participant['snowflake_balance']}"""
    send_message(peer_id, text, get_main_keyboard(participant['vk_id']))

def send_help(peer_id):
    text = """❓ ПОМОЩЬ

Используй меню.

Проблема? Напиши https://vk.com/bodya1"""
    send_message(peer_id, text, get_main_keyboard())

def send_rules(peer_id):
    text = "📜 Правила: https://mrbodya1.github.io/YUB/rules"
    send_message(peer_id, text, get_main_keyboard())

@app.route('/yookassa-webhook', methods=['POST'])
def yookassa_webhook():
    try:
        data = request.json
        print(f"📨 Webhook: {data}")
        event = data.get('event')
        payment_obj = data.get('object', {})
        if event == 'payment.succeeded':
            payment_id = payment_obj.get('id')
            metadata = payment_obj.get('metadata', {})
            payment_ref = metadata.get('payment_ref')
            user_id = metadata.get('user_id')
            amount_value = payment_obj.get('amount', {}).get('value', '990')
            amount = int(float(amount_value))
            db.save_payment(payment_id=payment_id, payment_ref=payment_ref, vk_id=int(user_id) if user_id else None, amount=amount, status='succeeded', metadata=metadata)
            if payment_ref:
                db.supabase.table('pending_registrations').update({'status': 'paid'}).eq('payment_ref', payment_ref).execute()
            if user_id:
                try:
                    db.activate_participant_by_vk(int(user_id))
                    send_message(int(user_id), "✅ Оплата получена! Ты активирован!\n\nУдачи в битве! 🏔️", get_main_keyboard(int(user_id)))
                except Exception as e:
                    print(f"❌ Ошибка активации: {e}")
            for admin_id in config.config.ADMINS:
                try:
                    send_message(admin_id, f"💰 Новая оплата!\n\nСумма: {amount} ₽\nref: {payment_ref}")
                except:
                    pass
        elif event == 'payment.canceled':
            db.update_payment_status(payment_obj.get('id'), 'canceled')
        return 'ok', 200
    except Exception as e:
        print(f"❌ Ошибка вебхука: {e}")
        return 'error', 500

@app.route('/create-landing-payment', methods=['POST', 'OPTIONS'])
def create_landing_payment_endpoint():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.json
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        gender = data.get('gender', '').strip()
        if not first_name or not last_name or not gender:
            return {'success': False, 'error': 'Заполни все поля'}, 400
        import uuid
        payment_ref = str(uuid.uuid4())[:8]
        from yookassa_client import create_payment
        payment_result = create_payment(
            user_id=None,
            amount=990,
            description=f"Взнос ({first_name} {last_name})",
            return_url="https://mrbodya1.github.io/YUB/thankyou.html",
            payment_ref=payment_ref
        )
        if payment_result['success']:
            try:
                db.supabase.table('pending_registrations').insert({
                    'first_name': first_name,
                    'last_name': last_name,
                    'gender': gender,
                    'payment_ref': payment_ref,
                    'payment_id': payment_result['payment_id'],
                    'created_at': db.get_current_time().isoformat()
                }).execute()
            except Exception as e:
                print(f"❌ Ошибка сохранения: {e}")
            return {'success': True, 'payment_url': payment_result['payment_url']}
        else:
            return {'success': False, 'error': payment_result.get('error', 'Ошибка')}, 500
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/payment-status', methods=['GET'])
def payment_status():
    payment_ref = request.args.get('ref')
    if not payment_ref:
        return {'success': False, 'error': 'No ref'}, 400

    # Ищем платёж в БД через payments
    payment = db.get_payment_by_ref(payment_ref)
    if payment:
        return {'success': True, 'status': payment.get('status')}

    return {'success': False, 'status': 'not_found'}

if __name__ == '__main__':
    app.run()
