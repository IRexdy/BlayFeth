# blayfeth.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import json
import time
import os
import socket
import random
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key_123'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

class CountryConquestGame:
    def __init__(self):
        self.players = []
        self.countries = self._initialize_countries()
        self.game_phase = 'selection'
        self.current_player_index = 0
        self.war_state = {
            'attacker_id': None,
            'defender_id': None,
            'target_country_id': None,
            'attacker_score': 0,
            'defender_score': 0,
            'rps_choices': {}
        }
        self.messages = []
        self.game_id = str(uuid.uuid4())
        self.last_update_time = time.time()
        self.ai_player_id = None # AI olmayacağı için bu her zaman None kalacak

    def _initialize_countries(self):
        countries_data = [
            {'id': 'france', 'name': 'Fransa', 'neighbors': ['germany', 'italy', 'spain', 'belgium', 'switzerland', 'luxembourg'], 'path': 'M170 100 Q180 80 200 85 L220 70 Q230 65 240 75 L230 110 Q210 140 180 150 Q160 140 150 120 Z'},
            {'id': 'germany', 'name': 'Almanya', 'neighbors': ['france', 'poland', 'czech_republic', 'austria', 'netherlands', 'belgium', 'switzerland', 'denmark', 'luxembourg'], 'path': 'M220 70 Q280 60 300 65 L320 90 Q300 120 250 125 Q230 110 220 70 Z'},
            {'id': 'italy', 'name': 'İtalya', 'neighbors': ['france', 'switzerland', 'austria', 'slovenia'], 'path': 'M200 150 Q220 130 230 140 L240 190 Q220 200 200 180 Z'},
            {'id': 'spain', 'name': 'İspanya', 'neighbors': ['france', 'portugal'], 'path': 'M100 160 Q140 140 160 150 Q180 180 140 200 Q110 190 90 170 Z'},
            {'id': 'united_kingdom', 'name': 'Birleşik Krallık', 'neighbors': ['ireland', 'france'], 'path': 'M50 50 Q80 40 90 50 L95 70 Q80 80 60 85 Q40 70 50 50 Z'},
            {'id': 'poland', 'name': 'Polonya', 'neighbors': ['germany', 'czech_republic', 'ukraine', 'belarus', 'lithuania', 'russia_kaliningrad', 'slovakia'], 'path': 'M300 65 Q350 55 370 65 L390 100 Q350 120 320 110 Q280 95 300 65 Z'},
            {'id': 'ukraine', 'name': 'Ukrayna', 'neighbors': ['poland', 'belarus', 'russia', 'romania', 'moldova', 'slovakia', 'hungary'], 'path': 'M390 100 Q450 90 480 110 L490 160 Q450 180 400 170 Q370 150 390 100 Z'},
            {'id': 'russia', 'name': 'Rusya', 'neighbors': ['ukraine', 'belarus', 'finland', 'norway', 'poland', 'latvia', 'lithuania', 'estonia'], 'path': 'M460 20 Q550 10 580 50 L590 110 Q550 150 500 140 Q470 90 460 20 Z'},
            {'id': 'sweden', 'name': 'İsveç', 'neighbors': ['norway', 'finland', 'denmark'], 'path': 'M280 10 Q320 0 350 10 L360 40 Q320 50 300 40 Z'},
            {'id': 'norway', 'name': 'Norveç', 'neighbors': ['sweden', 'finland'], 'path': 'M250 0 Q280 5 290 20 L270 35 Q240 20 250 0 Z'},
            {'id': 'finland', 'name': 'Finlandiya', 'neighbors': ['sweden', 'norway', 'russia'], 'path': 'M330 0 Q380 5 370 30 L360 50 Q320 40 330 0 Z'},
            {'id': 'belgium', 'name': 'Belçika', 'neighbors': ['france', 'germany', 'netherlands', 'luxembourg'], 'path': 'M185 85 Q200 80 205 88 L195 95 Q180 90 185 85 Z'},
            {'id': 'netherlands', 'name': 'Hollanda', 'neighbors': ['belgium', 'germany'], 'path': 'M190 70 Q210 65 215 75 L200 82 Q185 75 190 70 Z'},
            {'id': 'switzerland', 'name': 'İsviçre', 'neighbors': ['france', 'germany', 'italy', 'austria'], 'path': 'M200 125 Q215 120 220 128 L210 135 Q195 130 200 125 Z'},
            {'id': 'austria', 'name': 'Avusturya', 'neighbors': ['germany', 'italy', 'switzerland', 'czech_republic', 'hungary', 'slovakia', 'slovenia'], 'path': 'M230 130 Q260 120 270 125 L280 140 Q250 150 230 130 Z'},
            {'id': 'czech_republic', 'name': 'Çek Cumhuriyeti', 'neighbors': ['germany', 'poland', 'slovakia', 'austria'], 'path': 'M260 100 Q290 95 300 105 L280 115 Q265 105 260 100 Z'},
            {'id': 'slovakia', 'name': 'Slovakya', 'neighbors': ['czech_republic', 'poland', 'hungary', 'austria', 'ukraine'], 'path': 'M290 110 Q320 105 330 115 L310 125 Q295 118 290 110 Z'},
            {'id': 'hungary', 'name': 'Macaristan', 'neighbors': ['austria', 'slovakia', 'romania', 'croatia', 'serbia', 'slovenia', 'ukraine'], 'path': 'M270 140 Q300 135 310 145 L300 155 Q275 150 270 140 Z'},
            {'id': 'romania', 'name': 'Romanya', 'neighbors': ['ukraine', 'hungary', 'bulgaria', 'moldova', 'serbia'], 'path': 'M320 120 Q370 115 380 130 L370 150 Q330 155 320 120 Z'},
            {'id': 'bulgaria', 'name': 'Bulgaristan', 'neighbors': ['romania', 'serbia', 'greece', 'turkey', 'north_macedonia'], 'path': 'M330 150 Q360 145 370 155 L350 170 Q335 160 330 150 Z'},
            {'id': 'greece', 'name': 'Yunanistan', 'neighbors': ['bulgaria', 'turkey', 'albania', 'north_macedonia'], 'path': 'M320 170 Q340 165 350 180 L330 195 Q315 185 320 170 Z'},
            {'id': 'turkey', 'name': 'Türkiye', 'neighbors': ['bulgaria', 'greece', 'syria', 'iraq', 'iran', 'georgia', 'armenia'], 'path': 'M380 150 Q450 140 480 170 L460 200 Q400 210 380 150 Z'},
            {'id': 'belarus', 'name': 'Belarus', 'neighbors': ['poland', 'ukraine', 'russia', 'lithuania', 'latvia'], 'path': 'M350 50 Q380 55 390 70 L370 90 Q355 80 350 50 Z'},
            {'id': 'lithuania', 'name': 'Litvanya', 'neighbors': ['poland', 'belarus', 'latvia', 'russia_kaliningrad'], 'path': 'M320 40 Q340 35 350 45 L330 55 Q315 48 320 40 Z'},
            {'id': 'latvia', 'name': 'Letonya', 'neighbors': ['lithuania', 'estonia', 'russia', 'belarus'], 'path': 'M310 20 Q330 15 340 25 L325 35 Q305 28 310 20 Z'},
            {'id': 'estonia', 'name': 'Estonya', 'neighbors': ['finland', 'latvia', 'russia'], 'path': 'M300 0 Q320 0 330 10 L315 20 Q295 10 300 0 Z'},
            {'id': 'portugal', 'name': 'Portekiz', 'neighbors': ['spain'], 'path': 'M70 170 Q90 160 100 170 L80 190 Q65 180 70 170 Z'},
            {'id': 'ireland', 'name': 'İrlanda', 'neighbors': ['united_kingdom'], 'path': 'M30 60 Q45 55 50 65 L40 75 Q25 70 30 60 Z'},
            {'id': 'albania', 'name': 'Arnavutluk', 'neighbors': ['greece', 'north_macedonia', 'montenegro', 'kosovo'], 'path': 'M290 170 Q300 165 305 175 L295 185 Q285 178 290 170 Z'},
            {'id': 'north_macedonia', 'name': 'Kuzey Makedonya', 'neighbors': ['greece', 'bulgaria', 'serbia', 'albania', 'kosovo'], 'path': 'M305 160 Q315 155 320 165 L310 175 Q300 168 305 160 Z'},
            {'id': 'croatia', 'name': 'Hırvatistan', 'neighbors': ['bosnia_herzegovina', 'serbia', 'hungary', 'slovenia'], 'path': 'M240 150 Q260 145 270 155 L250 165 Q235 158 240 150 Z'},
            {'id': 'bosnia_herzegovina', 'name': 'Bosna-Hersek', 'neighbors': ['croatia', 'serbia', 'montenegro'], 'path': 'M250 170 Q265 165 270 175 L255 185 Q245 178 250 170 Z'},
            {'id': 'serbia', 'name': 'Sırbistan', 'neighbors': ['hungary', 'romania', 'bulgaria', 'north_macedonia', 'kosovo', 'montenegro', 'bosnia_herzegovina', 'croatia'], 'path': 'M280 160 Q300 155 310 165 L290 175 Q275 168 280 160 Z'},
            {'id': 'moldova', 'name': 'Moldova', 'neighbors': ['romania', 'ukraine'], 'path': 'M370 110 Q380 105 385 115 L375 125 Q365 118 370 110 Z'},
            {'id': 'slovenia', 'name': 'Slovenya', 'neighbors': ['italy', 'austria', 'croatia', 'hungary'], 'path': 'M225 140 Q230 135 235 142 L230 148 Q220 145 225 140 Z'},
            {'id': 'luxembourg', 'name': 'Lüksemburg', 'neighbors': ['france', 'germany', 'belgium'], 'path': 'M200 90 Q205 88 208 92 L203 95 Q198 92 200 90 Z'},
            {'id': 'denmark', 'name': 'Danimarka', 'neighbors': ['germany', 'sweden'], 'path': 'M250 50 Q260 45 270 50 L260 60 Q245 55 250 50 Z'},
            {'id': 'kosovo', 'name': 'Kosova', 'neighbors': ['serbia', 'albania', 'north_macedonia', 'montenegro'], 'path': 'M295 180 Q300 178 303 182 L298 185 Q293 182 295 180 Z'},
            {'id': 'montenegro', 'name': 'Karadağ', 'neighbors': ['albania', 'serbia', 'bosnia_herzegovina', 'kosovo'], 'path': 'M280 185 Q285 182 288 187 L283 190 Q278 187 280 185 Z'},
            {'id': 'russia_kaliningrad', 'name': 'Rusya (Kaliningrad)', 'neighbors': ['poland', 'lithuania'], 'path': 'M300 30 Q305 28 308 32 L303 35 Q298 32 300 30 Z'}
        ]
        return [{'id': c['id'], 'name': c['name'], 'owner_id': None, 'neighbors': c['neighbors'], 'path': c['path']} for c in countries_data]

    def add_player(self, player_id, player_name=None, is_ai=False):
        if any(p['id'] == player_id for p in self.players):
            return False

        if player_name is None:
            player_name = f"Oyuncu {len(self.players) + 1}"

        if self.game_phase == 'selection' or not self.players:
            self.players.append({'id': player_id, 'name': player_name, 'country_ids': [], 'is_ai': is_ai})
            self._add_message(f"{player_name} oyuna katıldı.")
            
            # DÜZELTME: AI oyuncusu ekleme kısmı tamamen kaldırıldı
            # if len(self.players) == 1 and not is_ai:
            #     ai_id = "ai_player_1"
            #     if not any(p['id'] == ai_id for p in self.players):
            #         self.add_player(ai_id, "AI Oyuncu", is_ai=True)
            #         self.ai_player_id = ai_id
            
            self._calculate_selection_count_per_player()
            
            # Current player'ı düzgünce ayarla. AI olmadığı için AI turunu tetiklemeyecek.
            if len(self.players) == 1: # İlk bağlanan her zaman başlar
                self.current_player_index = 0
            
            return True
        else:
            self._add_message("Oyuna yalnızca seçim aşamasında katılabilirsiniz.")
            return False

    def update_player_name(self, player_id, new_name):
        player = self._get_player_by_id(player_id)
        # AI oyuncularının adını değiştirmeye izin verme (is_ai kontrolü)
        if player and not player['is_ai']: 
            old_name = player['name']
            player['name'] = new_name
            self._add_message(f"{old_name} adını {new_name} olarak değiştirdi.")
            return True
        return False

    def _calculate_selection_count_per_player(self):
        num_players = len(self.players)
        num_countries = len(self.countries)

        if num_players == 0:
            self.selection_count_per_player = 0
            return

        base_selection = math.floor(num_countries / num_players)
        min_selection = 3 # Minimum 3 ülke seçimi

        self.selection_count_per_player = max(base_selection, min_selection)

    def _get_player_by_id(self, player_id):
        return next((p for p in self.players if p['id'] == player_id), None)

    def _get_country_by_id(self, country_id):
        return next((c for c in self.countries if c['id'] == country_id), None)

    def _get_current_player(self):
        if not self.players:
            return None
        return self.players[self.current_player_index]

    def _advance_turn(self):
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self._add_message(f"Sıra şimdi {self._get_current_player()['name']} oyuncusunda.")
        
        # DÜZELTME: AI olmadığı için AI turu tetiklenmeyecek
        # current_player = self._get_current_player()
        # if current_player and current_player['is_ai']:
        #     socketio.sleep(1) 
        #     self._ai_turn()

    def _add_message(self, msg):
        self.messages.append(msg)

    def select_country(self, player_id, country_id):
        if self.game_phase != 'selection':
            self._add_message("Şu anda ülke seçme aşaması değil.")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False

        current_player = self._get_current_player()
        if current_player and current_player['id'] != player_id:
            self._add_message("Sıra sizde değil!")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False

        country = self._get_country_by_id(country_id)
        if not country:
            self._add_message("Geçersiz ülke.")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False
        if country['owner_id'] is not None:
            self._add_message("Bu ülke zaten seçilmiş.")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False

        player_obj = self._get_player_by_id(player_id)
        if len(player_obj['country_ids']) >= self.selection_count_per_player:
            self._add_message(f"{player_obj['name']} zaten {self.selection_count_per_player} ülke seçti.")
            # DÜZELTME: AI olmadığı için bu kısım kaldırıldı
            # if player_obj['is_ai'] and self.game_phase == 'selection':
            #     self._advance_turn()
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False

        country['owner_id'] = player_id
        player_obj['country_ids'].append(country_id)
        self._add_message(f"{current_player['name']} {country['name']} ülkesini seçti.")

        if self.game_phase == 'selection':
            all_players_completed_selection_quota = all(len(p['country_ids']) >= self.selection_count_per_player for p in self.players)
            
            if all_players_completed_selection_quota:
                self.game_phase = 'playing'
                self._add_message("Ülke seçimi tamamlandı. Oyun başlıyor!")
            
            self._advance_turn()

        emit('game_state_update', self.get_game_state(), room=self.game_id)
        return True

    def initiate_war(self, attacker_id, target_country_id):
        if self.game_phase != 'playing':
            self._add_message("Şu anda savaş aşaması değil.")
            emit('game_state_update', self.get_game_state(), room=attacker_id)
            return False

        current_player = self._get_current_player()
        if current_player and current_player['id'] != attacker_id:
            self._add_message("Sıra sizde değil!")
            emit('game_state_update', self.get_game_state(), room=attacker_id)
            return False

        target_country = self._get_country_by_id(target_country_id)
        if not target_country:
            self._add_message("Geçersiz hedef ülke.")
            emit('game_state_update', self.get_game_state(), room=attacker_id)
            return False
        if target_country['owner_id'] == attacker_id:
            self._add_message("Kendi ülkenize savaş açamazsınız.")
            emit('game_state_update', self.get_game_state(), room=attacker_id)
            return False
        if target_country['owner_id'] is None:
            self._add_message("Sahipsiz ülkelere savaş açamazsiniz.")
            emit('game_state_update', self.get_game_state(), room=attacker_id)
            return False

        attacker_owned_countries = [c for c in self.countries if c['owner_id'] == attacker_id]
        is_neighbor = any(target_country_id in c['neighbors'] for c in attacker_owned_countries)

        if not is_neighbor:
            self._add_message("Sadece sınır komşusu olan ülkelere savaş açabilirsiniz.")
            emit('game_state_update', self.get_game_state(), room=attacker_id)
            return False

        self.war_state = {
            'attacker_id': attacker_id,
            'defender_id': target_country['owner_id'],
            'target_country_id': target_country_id,
            'attacker_score': 0,
            'defender_score': 0,
            'rps_choices': {}
        }
        attacker_name = self._get_player_by_id(attacker_id)['name']
        defender_name = self._get_player_by_id(target_country['owner_id'])['name']
        self._add_message(f"{attacker_name} ({target_country['name']}) ülkesine savaş açtı! {attacker_name} vs {defender_name} Taş-Kağıt-Makas başlıyor.")

        emit('game_state_update', self.get_game_state(), room=self.game_id)
        return True

    def make_rps_move(self, player_id, choice):
        if not self.war_state['attacker_id']:
            self._add_message("Şu anda devam eden bir savaş yok.")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False

        if player_id not in [self.war_state['attacker_id'], self.war_state['defender_id']]:
            self._add_message("Taş-Kağıt-Makas oyununda değilsiniz.")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False

        if player_id in self.war_state['rps_choices']:
            self._add_message("Zaten bir seçim yaptınız.")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False

        valid_choices = ['rock', 'paper', 'scissors']
        if choice not in valid_choices:
            self._add_message("Geçersiz seçim. 'rock', 'paper' veya 'scissors' seçin.")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False

        self.war_state['rps_choices'][player_id] = choice
        self._add_message(f"{self._get_player_by_id(player_id)['name']} seçimini yaptı.")

        other_player_id = self.war_state['defender_id'] if player_id == self.war_state['attacker_id'] else self.war_state['attacker_id']
        other_player_obj = self._get_player_by_id(other_player_id)

        # DÜZELTME: AI olmadığı için bu kısım kaldırıldı
        # if other_player_obj and other_player_obj['is_ai'] and other_player_id not in self.war_state['rps_choices']:
        #     self._ai_rps_move(other_player_id)

        if self.war_state['attacker_id'] in self.war_state['rps_choices'] and \
           self.war_state['defender_id'] in self.war_state['rps_choices']:
            self._resolve_rps_round()
        
        emit('game_state_update', self.get_game_state(), room=self.game_id)
        return True

    def _resolve_rps_round(self):
        attacker_choice = self.war_state['rps_choices'][self.war_state['attacker_id']]
        defender_choice = self.war_state['rps_choices'][self.war_state['defender_id']]

        winner = None
        if attacker_choice == defender_choice:
            winner = 'draw'
        elif (attacker_choice == 'rock' and defender_choice == 'scissors') or \
             (attacker_choice == 'paper' and defender_choice == 'rock') or \
             (attacker_choice == 'scissors' and defender_choice == 'paper'):
            winner = 'attacker'
            self.war_state['attacker_score'] += 1
        else:
            winner = 'defender'
            self.war_state['defender_score'] += 1

        self._add_message(f"Taş-Kağıt-Makas: {attacker_choice} vs {defender_choice}. Tur Kazananı: {winner.capitalize()}!")

        self.war_state['rps_choices'] = {} # Bir sonraki tur için seçimleri sıfırla

        if self.war_state['attacker_score'] >= 3 or self.war_state['defender_score'] >= 3:
            self._resolve_war_outcome()
        
    def _resolve_war_outcome(self):
        attacker_id = self.war_state['attacker_id']
        defender_id = self.war_state['defender_id']
        target_country_id = self.war_state['target_country_id']
        
        target_country = self._get_country_by_id(target_country_id)
        attacker_player = self._get_player_by_id(attacker_id)
        defender_player = self._get_player_by_id(defender_id)

        if self.war_state['attacker_score'] >= 3:
            target_country['owner_id'] = attacker_id
            attacker_player['country_ids'].append(target_country_id)
            if target_country_id in defender_player['country_ids']:
                defender_player['country_ids'].remove(target_country_id)
            self._add_message(f"{attacker_player['name']} {target_country['name']} ülkesini fethetti!")
        else:
            self._add_message(f"{defender_player['name']} ülkesini başarıyla savundu!")

        self.war_state = {
            'attacker_id': None, 'defender_id': None, 'target_country_id': None,
            'attacker_score': 0, 'defender_score': 0, 'rps_choices': {}
        }
        self._advance_turn()
        self._check_game_over()
        emit('game_state_update', self.get_game_state(), room=self.game_id)

    def pass_turn(self, player_id):
        if self.game_phase != 'playing':
            self._add_message("Şu anda pas geçemezsiniz.")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False
        
        current_player = self._get_current_player()
        if current_player and current_player['id'] != player_id:
            self._add_message("Sıra sizde değil!")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False

        if self.war_state['attacker_id']:
            self._add_message("Savaş devam ederken pas geçemezsiniz. Lütfen Taş-Kağıt-Makas hamlenizi yapın.")
            emit('game_state_update', self.get_game_state(), room=player_id)
            return False
        
        self._add_message(f"{current_player['name']} pas geçti.")
        self._advance_turn()
        emit('game_state_update', self.get_game_state(), room=self.game_id)
        return True

    def _check_game_over(self):
        remaining_players = [p for p in self.players if p['country_ids']]
        if len(remaining_players) <= 1 and self.game_phase != 'selection':
            self.game_phase = 'game_over'
            if remaining_players:
                self._add_message(f"Oyun bitti! Kazanan: {remaining_players[0]['name']}!")
            else:
                self._add_message("Oyun bitti! Berabere, kimse kazanamadı.")

    # DÜZELTME: AI turn ve RPS move metodları artık kullanılmayacak
    # Ancak kodda dursalar bile çağrılmayacakları için sorun yaratmazlar.
    def _ai_turn(self):
        # Bu metod artık AI oyuncusu eklenmediği için çağrılmayacak
        pass 

    def _ai_rps_move(self, ai_id):
        # Bu metod artık AI oyuncusu eklenmediği için çağrılmayacak
        pass

    def get_game_state(self):
        state = {
            'players': self.players,
            'countries': self.countries,
            'game_phase': self.game_phase,
            'current_player_index': self.current_player_index,
            'selection_count_per_player': self.selection_count_per_player,
            'war_state': self.war_state,
            'messages': self.messages
        }
        self.messages = []
        return state

# --- Global Oyun Durumu ---
game = CountryConquestGame()

# --- SocketIO Olay İşleyicileri ---
@socketio.on('connect')
def handle_connect():
    player_id = request.sid
    # DÜZELTME: AI oyuncusu ekleme kontrolü tamamen kaldırıldı
    # Oyun sadece insan oyuncularla başlar.
    if game.add_player(player_id, "Oyuncu"):
        join_room(game.game_id)
        emit('game_state_update', game.get_game_state(), room=game.game_id)
        print(f"Oyuncu {player_id} bağlandı ve oyuna katıldı.")
    else:
        # Eğer oyuncu zaten oyundaysa veya seçim aşaması geçtiyse, sadece ona durumu gönder
        # Artık insan-AI modu kontrolüne gerek yok.
        emit('game_state_update', game.get_game_state(), room=player_id)
        print(f"Oyuncu {player_id} zaten oyunda veya katılamadı.")


@socketio.on('disconnect')
def handle_disconnect():
    player_id = request.sid
    player = game._get_player_by_id(player_id)
    if player: # AI olmadığı için is_ai kontrolüne gerek kalmadı
        game.players = [p for p in game.players if p['id'] != player_id]
        # DÜZELTME: Kalan oyuncu yoksa oyunu bitir. AI olmadığından sadece insan oyuncular kontrol edilir.
        if not game.players: 
            game._add_message("Tüm oyuncular ayrıldı. Oyun sona erdi.")
            game.game_phase = 'game_over'
        else:
            # Oyuncu ayrıldıktan sonra sıra kalan oyunculardan birine denk geliyorsa
            # Geçerli oyuncu index'ini ayarla
            game.current_player_index = game.current_player_index % len(game.players)
            game._add_message(f"Oyuncu {player.name} oyundan ayrıldı. Sıra {game._get_current_player()['name']} oyuncusunda.")
        emit('game_state_update', game.get_game_state(), room=game.game_id)
    print(f"Oyuncu {player_id} bağlantısı kesildi.")

@socketio.on('select_country')
def handle_select_country(data):
    player_id = request.sid
    country_id = data.get('countryId')
    
    # AI kontrolü kaldırıldı
    # current_player = game._get_current_player()
    # if current_player and current_player['is_ai'] and current_player['id'] != player_id:
    #     emit('message', {'text': 'Şu an AI\'nin sırası. Lütfen bekleyin.'}, room=player_id)
    #     emit('game_state_update', game.get_game_state(), room=player_id)
    #     return

    game.select_country(player_id, country_id)


@socketio.on('initiate_war')
def handle_initiate_war(data):
    player_id = request.sid
    target_country_id = data.get('targetCountryId')

    # AI kontrolü kaldırıldı
    # current_player = game._get_current_player()
    # if current_player and current_player['is_ai'] and current_player['id'] != player_id:
    #     emit('message', {'text': 'Şu an AI\'nin sırası. Lütfen bekleyin.'}, room=player_id)
    #     emit('game_state_update', game.get_game_state(), room=player_id)
    #     return

    game.initiate_war(player_id, target_country_id)


@socketio.on('make_rps_move')
def handle_make_rps_move(data):
    player_id = request.sid
    choice = data.get('choice')

    # AI kontrolü kaldırıldı
    # current_player = game._get_current_player()
    # if current_player and current_player['is_ai'] and current_player['id'] != player_id:
    #     emit('message', {'text': 'Şu an AI\'nin sırası. Lütfen bekleyin.'}, room=player_id)
    #     emit('game_state_update', game.get_game_state(), room=player_id)
    #     return
        
    if game.war_state['attacker_id'] != player_id and game.war_state['defender_id'] != player_id:
        emit('message', {'text': 'Taş-Kağıt-Makas oyununda değilsiniz.'}, room=player_id)
        emit('game_state_update', game.get_game_state(), room=player_id)
        return
    
    game.make_rps_move(player_id, choice)

@socketio.on('pass_turn')
def handle_pass_turn():
    player_id = request.sid

    # AI kontrolü kaldırıldı
    # current_player = game._get_current_player()
    # if current_player and current_player['is_ai'] and current_player['id'] != player_id:
    #     emit('message', {'text': 'Şu an AI\'nin sırası. Lütfen bekleyin.'}, room=player_id)
    #     emit('game_state_update', game.get_game_state(), room=player_id)
    #     return

    game.pass_turn(player_id)

@socketio.on('change_player_name')
def handle_change_player_name(data):
    player_id = request.sid
    new_name = data.get('newName')
    
    if not new_name or len(new_name) > 20 or not new_name.strip():
        emit('message', {'text': 'Geçerli bir isim girin (en fazla 20 karakter).'}, room=player_id)
        emit('game_state_update', game.get_game_state(), room=player_id)
        return
        
    if game.update_player_name(player_id, new_name.strip()):
        emit('game_state_update', game.get_game_state(), room=game.game_id)
    else:
        emit('message', {'text': 'İsim değiştirilemedi.'}, room=player_id)
        emit('game_state_update', game.get_game_state(), room=player_id)

# --- Flask Yönlendirmesi ---
@app.route('/')
def index():
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    app.template_folder = template_dir
    return render_template('index.html')

if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = "127.0.0.1"
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        pass
    
    port = int(os.environ.get('PORT', 5000)) 
    
    print(f"Oyun sunucusu başlatılıyor. Oyun ID: {game.game_id}")
    print(f"Siz kendi bilgisayarınızda http://127.0.0.1:{port} adresine gidin.")
    print(f"Arkadaşlarınız aynı ağdaysa, {local_ip}:{port} adresine gidebilirler.")
    print("DİKKAT: Bu sadece yerel ağınızda çalışır. İnternet üzerinden erişim için sunucuya yükleme (deploy) yapmanız gerekir.")
    socketio.run(app, debug=True, host='0.0.0.0', port=port)
