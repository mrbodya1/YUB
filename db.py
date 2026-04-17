from supabase import create_client, Client
from datetime import datetime
import pytz
import config
import json

class Database:
    def __init__(self):
        self.supabase: Client = create_client(
            'https://ohaspovkdvtihosvzpli.supabase.co',
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9oYXNwb3ZrZHZ0aWhvc3Z6cGxpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ1NjI1ODEsImV4cCI6MjA5MDEzODU4MX0.5OvphjjVlBP8hXvLMIALsD6pZn5453mkSEpCeOl8280'
        )
        self._tz = None

    def _get_timezone(self):
        if self._tz is None:
            tz_str = self.get_setting('TIMEZONE', 'Asia/Yekaterinburg')
            try:
                self._tz = pytz.timezone(tz_str)
            except:
                self._tz = pytz.timezone('Asia/Yekaterinburg')
        return self._tz

    def get_current_time(self):
        return datetime.now(self._get_timezone())

    def get_current_date(self):
        return self.get_current_time().date()

    def get_current_hour(self):
        return self.get_current_time().hour

    # ---------- НАСТРОЙКИ ----------
    def get_setting(self, key, default=None):
        try:
            response = self.supabase.table('challenge_settings')\
                .select('setting_value')\
                .eq('setting_key', key)\
                .execute()
            if response.data:
                return response.data[0]['setting_value']
        except:
            pass
        return default

    def get_int_setting(self, key, default=0):
        value = self.get_setting(key)
        if value is not None:
            try:
                return int(value)
            except:
                pass
        return default

    def get_float_setting(self, key, default=0.0):
        value = self.get_setting(key)
        if value is not None:
            try:
                return float(value)
            except:
                pass
        return default

    def get_abilities_costs(self):
        value = self.get_setting('ABILITIES')
        if value:
            try:
                return json.loads(value)
            except:
                pass
        return {'x2boost': 150, 'frostbite': 150, 'avalanche': 150, 'annihilation': 200, 'shield': 100}

    def update_setting(self, key, value):
        """Обновить настройку"""
        try:
            response = self.supabase.table('challenge_settings')\
                .update({'setting_value': value, 'updated_at': self.get_current_time().isoformat()})\
                .eq('setting_key', key)\
                .execute()
            return True
        except Exception as e:
            print(f'❌ Ошибка update_setting: {e}')
            return False

    # ---------- УЧАСТНИКИ ----------
    def get_participant_by_vk(self, vk_id):
        try:
            response = self.supabase.table('participants')\
                .select('*')\
                .eq('vk_id', vk_id)\
                .execute()
            return response.data[0] if response.data else None
        except:
            return None

    def get_participant_by_id(self, participant_id):
        try:
            response = self.supabase.table('participants')\
                .select('*')\
                .eq('id', participant_id)\
                .execute()
            return response.data[0] if response.data else None
        except:
            return None

    def get_all_participants(self):
        try:
            response = self.supabase.table('participants')\
                .select('*')\
                .eq('status', 'active')\
                .execute()
            return response.data
        except:
            return []

    def get_rating(self):
        try:
            response = self.supabase.table('participants')\
                .select('id, first_name, last_name, total_km, total_workouts, gender')\
                .eq('status', 'active')\
                .gt('total_km', 0)\
                .order('total_km', desc=True)\
                .execute()
            return response.data
        except:
            return []

    def update_participant_status(self, participant_id, status):
        """Изменить статус участника (active, banned, inactive)"""
        try:
            response = self.supabase.table('participants')\
                .update({'status': status})\
                .eq('id', participant_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f'❌ Ошибка update_participant_status: {e}')
            return None

    def activate_participant_by_vk(self, vk_id):
        """Активировать участника по VK ID (после оплаты)"""
        try:
            response = self.supabase.table('participants')\
                .update({'status': 'active'})\
                .eq('vk_id', vk_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f'❌ Ошибка activate_participant_by_vk: {e}')
            return None

    # ---------- ТРЕНИРОВКИ ----------
    def add_workout(self, participant_id, day, km, minutes):
        try:
            data = {
                'participant_id': participant_id,
                'day': day,
                'workout_date': self.get_current_date().isoformat(),
                'original_km': km,
                'original_min': minutes,
                'final_km': km,
                'final_min': minutes,
                'status': 'accepted',
                'created_at': self.get_current_time().isoformat()
            }
            response = self.supabase.table('workouts').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f'❌ Ошибка add_workout: {e}')
            return None

    def get_last_workout(self, participant_id):
        try:
            response = self.supabase.table('workouts')\
                .select('*')\
                .eq('participant_id', participant_id)\
                .eq('status', 'accepted')\
                .order('day', desc=True)\
                .limit(1)\
                .execute()
            return response.data[0] if response.data else None
        except:
            return None

    def get_workouts_by_participant(self, participant_id):
        try:
            response = self.supabase.table('workouts')\
                .select('*')\
                .eq('participant_id', participant_id)\
                .eq('status', 'accepted')\
                .order('day', desc=True)\
                .execute()
            return response.data
        except:
            return []

    def get_workout_count_by_date(self, participant_id, date):
        """Проверить, была ли уже принятая тренировка в указанную дату"""
        try:
            response = self.supabase.table('workouts')\
                .select('id')\
                .eq('participant_id', participant_id)\
                .eq('workout_date', date)\
                .eq('status', 'accepted')\
                .execute()
            return len(response.data)
        except:
            return 0

    def get_workout_by_id(self, workout_id):
        try:
            response = self.supabase.table('workouts')\
                .select('*')\
                .eq('id', workout_id)\
                .execute()
            return response.data[0] if response.data else None
        except:
            return None

    def apply_ability_mod(self, workout_id, mod_type, mod_value):
        try:
            workout = self.get_workout_by_id(workout_id)
            if not workout:
                return None

            update_data = {}
            if mod_type == 'pos':
                update_data['mod_pos'] = mod_value
            else:
                update_data['mod_neg'] = mod_value

            final_km = workout['original_km']
            final_min = workout['original_min']

            pos_mod = workout.get('mod_pos')
            if mod_type == 'pos':
                pos_mod = mod_value
            if pos_mod is not None:
                final_km *= pos_mod
                final_min *= pos_mod

            neg_mod = workout.get('mod_neg')
            if mod_type == 'neg':
                neg_mod = mod_value
            if neg_mod is not None:
                final_km *= neg_mod
                final_min *= neg_mod

            update_data['final_km'] = int(final_km)
            update_data['final_min'] = int(final_min)

            print(f"🔍 apply_ability_mod: workout_id={workout_id}, mod_type={mod_type}, mod_value={mod_value}, final_km={final_km}")

            response = self.supabase.table('workouts')\
                .update(update_data)\
                .eq('id', workout_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f'❌ Ошибка apply_ability_mod: {e}')
            return None

    def update_workout_status(self, workout_id, status):
        """Изменить статус тренировки (accepted, deleted, cancelled)"""
        try:
            response = self.supabase.table('workouts')\
                .update({'status': status})\
                .eq('id', workout_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f'❌ Ошибка update_workout_status: {e}')
            return None

    # ---------- РОМАШКИ ----------
    def add_snowflakes(self, participant_id, amount, reason):
        try:
            participant = self.get_participant_by_id(participant_id)
            if not participant:
                return None
            new_balance = participant['snowflake_balance'] + amount
            self.supabase.table('participants')\
                .update({'snowflake_balance': new_balance})\
                .eq('id', participant_id)\
                .execute()
            self.supabase.table('snowflake_operations')\
                .insert({
                    'participant_id': participant_id,
                    'amount': amount,
                    'reason': reason,
                    'balance_after': new_balance,
                    'created_at': self.get_current_time().isoformat()
                })\
                .execute()
            return new_balance
        except Exception as e:
            print(f'❌ Ошибка add_snowflakes: {e}')
            return None

    # ---------- ДОСТИЖЕНИЯ ----------
    def get_user_achievements(self, vk_id):
        try:
            participant = self.get_participant_by_vk(vk_id)
            if not participant:
                return []
            response = self.supabase.table('user_achievements')\
                .select('*')\
                .eq('participant_id', participant['id'])\
                .execute()
            return response.data if response.data else []
        except:
            return []

    def get_all_achievements(self):
        try:
            response = self.supabase.table('achievements_catalog')\
                .select('*')\
                .order('id', desc=False)\
                .execute()
            return response.data if response.data else []
        except:
            return []

    def get_achievement_by_id(self, ach_id):
        try:
            response = self.supabase.table('achievements_catalog')\
                .select('*')\
                .eq('id', ach_id)\
                .execute()
            return response.data[0] if response.data else None
        except:
            return None

    def award_achievement(self, vk_id, achievement_id):
        try:
            participant = self.get_participant_by_vk(vk_id)
            if not participant:
                return None

            existing = self.supabase.table('user_achievements')\
                .select('*')\
                .eq('participant_id', participant['id'])\
                .eq('achievement_id', achievement_id)\
                .execute()
            if existing.data:
                return None

            achievement = self.get_achievement_by_id(achievement_id)
            if not achievement:
                return None

            self.supabase.table('user_achievements')\
                .insert({
                    'participant_id': participant['id'],
                    'achievement_id': achievement_id,
                    'earned_at': self.get_current_time().isoformat()
                })\
                .execute()

            self.add_snowflakes(participant['id'], achievement['snowflakes_reward'], f'Достижение: {achievement["name"]}')

            # Отправка в общий чат
            try:
                import vk_api
                chat_id = config.config.VK_CHAT_ID
                if chat_id and chat_id != 0:
                    msg = f"🏅 НОВОЕ ДОСТИЖЕНИЕ!\n\n{participant['first_name']} {participant['last_name']}\n{achievement['emoji']} {achievement['name']}\n{achievement['condition']}\n\n🌼 +{achievement['snowflakes_reward']} ромашек"

                    vk = vk_api.VkApi(token=config.config.VK_TOKEN).get_api()
                    vk.messages.send(
                        peer_id=chat_id,
                        message=msg,
                        random_id=0,
                        from_group=1
                    )
                    print(f"✅ Уведомление о достижении отправлено в общий чат")
            except Exception as e:
                print(f'❌ Ошибка отправки уведомления о достижении: {e}')

            return achievement
        except Exception as e:
            print(f'❌ Ошибка award_achievement: {e}')
            return None

    # ---------- СПОСОБНОСТИ ----------
    def get_user_abilities(self, participant_id):
        try:
            response = self.supabase.table('abilities_usage')\
                .select('*')\
                .eq('initiator_id', participant_id)\
                .execute()
            return response.data if response.data else []
        except:
            return []

    def get_attacks_received(self, participant_id):
        try:
            response = self.supabase.table('abilities_usage')\
                .select('*')\
                .eq('target_id', participant_id)\
                .execute()
            return len(response.data) if response.data else 0
        except:
            return 0

    def log_ability_usage(self, initiator_id, ability_id, target_id, workout_id, cost, result):
        try:
            self.supabase.table('abilities_usage')\
                .insert({
                    'initiator_id': initiator_id,
                    'ability_id': ability_id,
                    'target_id': target_id,
                    'workout_id': workout_id,
                    'cost': cost,
                    'result': result,
                    'used_at': self.get_current_time().isoformat()
                })\
                .execute()
        except:
            pass

    # ---------- РУЛЕТКА ----------
    def can_use_lucky(self, participant_id):
        today = self.get_current_date().isoformat()
        try:
            response = self.supabase.table('lucky_usage')\
                .select('id')\
                .eq('participant_id', participant_id)\
                .eq('used_date', today)\
                .execute()
            return len(response.data) == 0
        except:
            return True

    def log_lucky_usage(self, participant_id, result, effect_text):
        """Сохраняет результат рулетки (создаёт или обновляет запись за сегодня)"""
        today = self.get_current_date().isoformat()
        try:
            # Проверяем, есть ли уже запись за сегодня
            response = self.supabase.table('lucky_usage')\
                .select('id')\
                .eq('participant_id', participant_id)\
                .eq('used_date', today)\
                .execute()

            if response.data:
                # Обновляем существующую запись
                self.supabase.table('lucky_usage')\
                    .update({'result': result, 'effect_text': effect_text})\
                    .eq('id', response.data[0]['id'])\
                    .execute()
            else:
                # Создаём новую запись с полными данными
                self.supabase.table('lucky_usage')\
                    .insert({
                        'participant_id': participant_id,
                        'used_date': today,
                        'result': result,
                        'effect_text': effect_text
                    })\
                    .execute()
        except Exception as e:
            print(f'❌ Ошибка log_lucky_usage: {e}')

    # ---------- ЕЖЕНЕДЕЛЬНЫЕ ОЧКИ ----------
    def get_weekly_stats_for_period(self, week_start, week_end):
        try:
            response = self.supabase.table('workouts')\
                .select('participant_id, original_km, original_min, workout_date')\
                .gte('workout_date', week_start)\
                .lte('workout_date', week_end)\
                .eq('status', 'accepted')\
                .execute()
            return response.data if response.data else []
        except:
            return []

    def get_abilities_count_for_period(self, week_start, week_end):
        try:
            response = self.supabase.table('abilities_usage')\
                .select('initiator_id')\
                .gte('used_at', week_start)\
                .lte('used_at', week_end)\
                .execute()
            return response.data if response.data else []
        except:
            return []

    def save_weekly_score(self, data):
        try:
            self.supabase.table('weekly_scores')\
                .upsert(data, on_conflict='participant_id, week_number, year')\
                .execute()
            return True
        except:
            return False

    def get_weekly_calculation_log(self, week_number, year):
        try:
            response = self.supabase.table('weekly_calculation_log')\
                .select('id')\
                .eq('week_number', week_number)\
                .eq('year', year)\
                .execute()
            return len(response.data) > 0
        except:
            return False

    def save_weekly_calculation_log(self, week_number, year):
        try:
            self.supabase.table('weekly_calculation_log')\
                .insert({'week_number': week_number, 'year': year})\
                .execute()
            return True
        except:
            return False

        # ---------- ПЛАТЕЖИ ----------
    def save_payment(self, payment_id, payment_ref, vk_id=None, amount=990, status='pending', metadata=None):
        """Сохраняет информацию о платеже"""
        try:
            data = {
                'payment_id': payment_id,
                'payment_ref': payment_ref,
                'vk_id': vk_id,
                'amount': amount,
                'status': status,
                'metadata': metadata
            }
            response = self.supabase.table('payments').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f'❌ Ошибка save_payment: {e}')
            return None

    def update_payment_status(self, payment_id, status, paid_at=None):
        """Обновляет статус платежа"""
        try:
            data = {'status': status}
            if paid_at:
                data['paid_at'] = paid_at
            elif status == 'succeeded':
                data['paid_at'] = self.get_current_time().isoformat()

            response = self.supabase.table('payments')\
                .update(data)\
                .eq('payment_id', payment_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f'❌ Ошибка update_payment_status: {e}')
            return None

    def get_payment_by_ref(self, payment_ref):
        try:
            response = self.supabase.table('payments')\
                .select('*')\
                .eq('payment_ref', payment_ref)\
                .execute()
            return response.data[0] if response.data else None
        except:
            return None

    def get_payment_by_id(self, payment_id):
        """Находит платеж по payment_id"""
        try:
            response = self.supabase.table('payments')\
                .select('*')\
                .eq('payment_id', payment_id)\
                .execute()
            return response.data[0] if response.data else None
        except:
            return None

    def mark_payment_as_paid(self, payment_id):
        """Отмечает платеж как оплаченный"""
        return self.update_payment_status(payment_id, 'succeeded')