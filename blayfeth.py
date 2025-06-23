# blayfeth.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import json
import time
import os # os modülünü import ediyoruz

app = Flask(__name__)
# Güvenli bir anahtar kullanın. Üretim ortamında daha karmaşık bir anahtar olmalı.
app.config['SECRET_KEY'] = 'your_super_secret_key_123'
# Herhangi bir kaynaktan gelen bağlantılara izin verir. Güvenlik için üretimde kısıtlanmalı.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent') # async_mode='gevent' doğru kütüphanelerle çalışır

# --- Oyun Mantığı Sınıfı ---
class CountryConquestGame:
    def __init__(self):
        self.players = []
        # Ülkelerin başlangıç durumunu ve komşuluklarını başlatır
        self.countries = self._initialize_countries()
        # Oyun aşaması: 'selection' (ülke seçimi), 'playing' (oyun devam ediyor), 'game_over' (oyun bitti)
        self.game_phase = 'selection'
        self.current_player_index = 0
        # Her oyuncunun başlangıçta seçeceği ülke sayısı
        self.selection_count_per_player = 2
        # Savaş durumu bilgileri
        self.war_state = {
            'attacker_id': None,
            'defender_id': None,
            'target_country_id': None,
            'attacker_score': 0,
            'defender_score': 0,
            'rps_choices': {} # Oyuncuların taş-kağıt-makas seçimleri
        }
        self.messages = [] # Oyun içi mesajlar listesi
        self.game_id = str(uuid.uuid4()) # Her oyun için benzersiz ID
        self.last_update_time = time.time() # Son güncelleme zamanı

    def _initialize_countries(self):
        # DÜZELTME: Avrupa ülkeleri için daha gerçekçi isimler ve basitleştirilmiş SVG yolları
        # ve komşuluk ilişkileri eklendi.
        countries_data = [
            {'id': 'france', 'name': 'Fransa', 'neighbors': ['germany', 'italy', 'spain', 'belgium', 'switzerland'], 'path': 'M150 100 L180 80 L220 90 L200 130 L160 140 Z'},
            {'id': 'germany', 'name': 'Almanya', 'neighbors': ['france', 'poland', 'czech_republic', 'austria', 'netherlands', 'belgium', 'switzerland'], 'path': 'M220 70 L280 60 L300 90 L250 120 L200 100 Z'},
            {'id': 'italy', 'name': 'İtalya', 'neighbors': ['france', 'switzerland', 'austria'], 'path': 'M200 150 L220 130 L230 180 L210 200 L190 170 Z'},
            {'id': 'spain', 'name': 'İspanya', 'neighbors': ['france', 'portugal'], 'path': 'M100 160 L140 140 L160 180 L120 200 L90 180 Z'},
            {'id': 'united_kingdom', 'name': 'Birleşik Krallık', 'neighbors': ['france'], 'path': 'M50 50 L80 40 L90 70 L60 80 Z'},
            {'id': 'poland', 'name': 'Polonya', 'neighbors': ['germany', 'czech_republic', 'ukraine', 'belorussia', 'lithuania', 'russia'], 'path': 'M300 60 L350 50 L370 80 L320 110 L280 90 Z'},
            {'id': 'ukraine', 'name': 'Ukrayna', 'neighbors': ['poland', 'belorussia', 'russia', 'romania', 'moldova'], 'path': 'M380 70 L450 60 L480 120 L400 150 Z'},
            {'id': 'russia', 'name': 'Rusya', 'neighbors': ['ukraine', 'belorussia', 'finland', 'norway', 'poland', 'latvia', 'lithuania', 'estonia'], 'path': 'M460 20 L550 10 L580 100 L500 150 Z'},
            {'id': 'sweden', 'name': 'İsveç', 'neighbors': ['norway', 'finland'], 'path': 'M280 10 L320 0 L350 40 L300 50 Z'},
            {'id': 'norway', 'name': 'Norveç', 'neighbors': ['sweden', 'finland'], 'path': 'M250 0 L280 10 L260 40 L230 30 Z'},
            {'id': 'finland', 'name': 'Finlandiya', 'neighbors': ['sweden', 'norway', 'russia'], 'path': 'M330 0 L380 10 L370 40 L320 50 Z'},
            {'id': 'belgium', 'name': 'Belçika', 'neighbors': ['france', 'germany', 'netherlands'], 'path': 'M185 85 L200 80 L205 95 L190 100 Z'},
            {'id': 'netherlands', 'name': 'Hollanda', 'neighbors': ['belgium', 'germany'], 'path': 'M190 70 L210 65 L215 80 L195 85 Z'},
            {'id': 'switzerland', 'name': 'İsviçre', 'neighbors': ['france', 'germany', 'italy', 'austria'], 'path': 'M200 125 L215 120 L220 135 L205 140 Z'},
            {'id': 'austria', 'name': 'Avusturya', 'neighbors': ['germany', 'italy', 'switzerland', 'czech_republic', 'hungary', 'slovakia'], 'path': 'M230 130 L260 120 L270 140 L240 150 Z'},
            {'id': 'czech_republic', 'name': 'Çek Cumhuriyeti', 'neighbors': ['germany', 'poland', 'slovakia', 'austria'], 'path': 'M260 100 L290 90 L300 110 L270 120 Z'},
            {'id': 'slovakia', 'name': 'Slovakya', 'neighbors': ['czech_republic', 'poland', 'hungary', 'austria', 'ukraine'], 'path': 'M290 110 L320 100 L330 120 L300 130 Z'},
            {'id': 'hungary', 'name': 'Macaristan', 'neighbors': ['austria', 'slovakia', 'romania', 'croatia', 'serbia'], 'path': 'M270 140 L300 130 L310 150 L280 160 Z'},
            {'id': 'romania', 'name': 'Romanya', 'neighbors': ['ukraine', 'hungary', 'bulgaria', 'moldova', 'serbia'], 'path': 'M320 120 L370 110 L380 140 L330 150 Z'},
            {'id': 'bulgaria', 'name': 'Bulgaristan', 'neighbors': ['romania', 'serbia', 'greece', 'turkey'], 'path': 'M330 150 L360 140 L370 160 L340 170 Z'},
            {'id': 'greece', 'name': 'Yunanistan', 'neighbors': ['bulgaria', 'turkey', 'albania', 'macedonia'], 'path': 'M320 170 L340 160 L350 190 L330 200 Z'},
            {'id': 'turkey', 'name': 'Türkiye', 'neighbors': ['bulgaria', 'greece', 'syria', 'iraq', 'iran', 'georgia', 'armenia'], 'path': 'M380 150 L450 140 L480 200 L400 210 Z'},
            {'id': 'belorussia', 'name': 'Belarus', 'neighbors': ['poland', 'ukraine', 'russia', 'lithuania', 'latvia'], 'path': 'M350 50 L380 60 L390 90 L360 100 Z'},
            {'id': 'lithuania', 'name': 'Litvanya', 'neighbors': ['poland', 'belorussia', 'latvia', 'russia'], 'path': 'M320 40 L340 30 L350 50 L330 60 Z'},
            {'id': 'latvia', 'name': 'Letonya', 'neighbors': ['lithuania', 'estonia', 'russia', 'belorussia'], 'path': 'M310 20 L330 10 L340 30 L320 40 Z'},
            {'id': 'estonia', 'name': 'Estonya', 'neighbors': ['finland', 'latvia', 'russia'], 'path': 'M300 0 L320 0 L330 20 L310 20 Z'},
            {'id': 'portugal', 'name': 'Portekiz', 'neighbors': ['spain'], 'path': 'M70 170 L90 160 L100 180 L80 190 Z'},
            {'id': 'ireland', 'name': 'İrlanda', 'neighbors': ['united_kingdom'], 'path': 'M30 60 L45 55 L50 70 L35 75 Z'},
            {'id': 'albania', 'name': 'Arnavutluk', 'neighbors': ['greece', 'macedonia', 'montenegro', 'kosovo'], 'path': 'M290 170 L300 165 L305 180 L295 185 Z'},
            {'id': 'macedonia', 'name': 'Kuzey Makedonya', 'neighbors': ['greece', 'bulgaria', 'serbia', 'albania', 'kosovo'], 'path': 'M305 160 L315 155 L320 170 L310 175 Z'},
            {'id': 'croatia', 'name': 'Hırvatistan', 'neighbors': ['bosnia_herzegovina', 'serbia', 'hungary', 'slovenia'], 'path': 'M240 150 L260 140 L270 160 L250 170 Z'},
            {'id': 'bosnia_herzegovina', 'name': 'Bosna-Hersek', 'neighbors': ['croatia', 'serbia', 'montenegro'], 'path': 'M250 170 L265 165 L270 180 L255 185 Z'},
            {'id': 'serbia', 'name': 'Sırbistan', 'neighbors': ['hungary', 'romania', 'bulgaria', 'macedonia', 'kosovo', 'montenegro', 'bosnia_herzegovina', 'croatia'], 'path': 'M280 160 L300 150 L310 170 L290 180 Z'},
            {'id': 'moldova', 'name': 'Moldova', 'neighbors': ['romania', 'ukraine'], 'path': 'M370 110 L380 105 L385 120 L375 125 Z'},
        ]
        return [{'id': c['id'], 'name': c['name'], 'owner_id': None, 'neighbors': c['neighbors'], 'path': c['path']} for c in countries_data]


    def add_player(self, player_id, player_name=None):
        # Oyuncunun zaten oyunda olup olmadığını kontrol et
        if any(p['id'] == player_id for p in self.players):
            return False # Oyuncu zaten oyunda

        if player_name is None:
            player_name = f"Oyuncu {len(self.players) + 1}"

        # Sadece seçim aşamasında yeni oyuncu eklenebilir veya oyun henüz başlamamışsa
        if self.game_phase == 'selection' or not self.players:
            self.players.append({'id': player_id, 'name': player_name, 'country_ids': []})
            self._add_message(f"{player_name} oyuna katıldı.")
            # Eğer ilk oyuncu ise, sırayı ona ver
            if len(self.players) == 1:
                self.current_player_index = 0
            return True
        else:
            self._add_message("Oyuna yalnızca seçim aşamasında katılabilirsiniz.")
            return False

    def _get_player_by_id(self, player_id):
        # ID'ye göre oyuncuyu bulur
        return next((p for p in self.players if p['id'] == player_id), None)

    def _get_country_by_id(self, country_id):
        # ID'ye göre ülkeyi bulur
        return next((c for c in self.countries if c['id'] == country_id), None)

    def _get_current_player(self):
        # Sırası gelen oyuncuyu döndürür
        if not self.players:
            return None
        return self.players[self.current_player_index]

    def _advance_turn(self):
        # Sırayı bir sonraki oyuncuya geçirir
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self._add_message(f"Sıra şimdi {self._get_current_player()['name']} oyuncusunda.")

    def _add_message(self, msg):
        # Oyun içi mesaj ekler
        self.messages.append(msg)

    def select_country(self, player_id, country_id):
        # Ülke seçme aşamasında olup olmadığını kontrol et
        if self.game_phase != 'selection':
            self._add_message("Şu anda ülke seçme aşaması değil.")
            return False

        current_player = self._get_current_player()
        # Sıranın bu oyuncuda olup olmadığını kontrol et
        if current_player and current_player['id'] != player_id:
            self._add_message("Sıra sizde değil!")
            return False

        country = self._get_country_by_id(country_id)
        if not country:
            self._add_message("Geçersiz ülke.")
            return False
        # Ülkenin zaten seçilmiş olup olmadığını kontrol et
        if country['owner_id'] is not None:
            self._add_message("Bu ülke zaten seçilmiş.")
            return False

        player_obj = self._get_player_by_id(player_id)
        # Oyuncunun zaten yeterli sayıda ülke seçip seçmediğini kontrol et
        if len(player_obj['country_ids']) >= self.selection_count_per_player:
            self._add_message(f"Zaten {self.selection_count_per_player} ülke seçtiniz.")
            return False

        # Ülke sahibini güncelle
        country['owner_id'] = player_id
        player_obj['country_ids'].append(country_id)
        self._add_message(f"{current_player['name']} {country['name']} ülkesini seçti.")

        # Eğer oyuncu yeterli sayıda ülke seçtiyse veya tüm ülkeler seçildiyse sırayı ilerlet
        if len(player_obj['country_ids']) >= self.selection_count_per_player:
            all_players_selected = all(len(p['country_ids']) >= self.selection_count_per_player for p in self.players)
            if all_players_selected:
                self.game_phase = 'playing'
                self._add_message("Ülke seçimi tamamlandı. Oyun başlıyor!")
            self._advance_turn()
        return True

    def initiate_war(self, attacker_id, target_country_id):
        # Oyun aşamasında olup olmadığını kontrol et
        if self.game_phase != 'playing':
            self._add_message("Şu anda savaş aşaması değil.")
            return False

        current_player = self._get_current_player()
        # Sıranın bu oyuncuda olup olmadığını kontrol et
        if current_player and current_player['id'] != attacker_id:
            self._add_message("Sıra sizde değil!")
            return False

        target_country = self._get_country_by_id(target_country_id)
        if not target_country:
            self._add_message("Geçersiz hedef ülke.")
            return False
        # Kendi ülkesine savaş açıp açmadığını kontrol et
        if target_country['owner_id'] == attacker_id:
            self._add_message("Kendi ülkenize savaş açamazsınız.")
            return False
        # Sahipsiz ülkeye savaş açıp açmadığını kontrol et
        if target_country['owner_id'] is None:
            self._add_message("Sahipsiz ülkelere savaş açamazsınız.")
            return False

        # Komşuluk kontrolü: Saldıranın sahip olduğu ülkelerden herhangi biri hedef ülkeye komşu mu?
        attacker_owned_countries = [c for c in self.countries if c['owner_id'] == attacker_id]
        is_neighbor = any(target_country_id in c['neighbors'] for c in attacker_owned_countries)

        if not is_neighbor:
            self._add_message("Sadece sınır komşusu olan ülkelere savaş açabilirsiniz.")
            return False

        # Savaş durumunu başlat
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
        return True

    def make_rps_move(self, player_id, choice):
        # Devam eden bir savaş olup olmadığını kontrol et
        if not self.war_state['attacker_id']:
            self._add_message("Şu anda devam eden bir savaş yok.")
            return False

        # Oyuncunun savaşta olup olmadığını kontrol et
        if player_id not in [self.war_state['attacker_id'], self.war_state['defender_id']]:
            self._add_message("Taş-Kağıt-Makas oyununda değilsiniz.")
            return False

        # Oyuncunun zaten bir seçim yapıp yapmadığını kontrol et
        if player_id in self.war_state['rps_choices']:
            self._add_message("Zaten bir seçim yaptınız.")
            return False

        valid_choices = ['rock', 'paper', 'scissors']
        if choice not in valid_choices:
            self._add_message("Geçersiz seçim. 'rock', 'paper' veya 'scissors' seçin.")
            return False

        # Oyuncunun seçimini kaydet
        self.war_state['rps_choices'][player_id] = choice
        self._add_message(f"{self._get_player_by_id(player_id)['name']} seçimini yaptı.")

        # Her iki oyuncu da seçim yaptı mı?
        if self.war_state['attacker_id'] in self.war_state['rps_choices'] and \
           self.war_state['defender_id'] in self.war_state['rps_choices']:
            self._resolve_rps_round() # Turu çöz
        return True

    def _resolve_rps_round(self):
        # Oyuncuların seçimlerini al
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

        # Genel savaş kazananı kontrolü (ilk 3 puanı alan)
        if self.war_state['attacker_score'] >= 3 or self.war_state['defender_score'] >= 3:
            self._resolve_war_outcome() # Savaş sonucunu çöz
        # else: savaş devam ediyor, yeni tur için bekliyor

    def _resolve_war_outcome(self):
        attacker_id = self.war_state['attacker_id']
        defender_id = self.war_state['defender_id']
        target_country_id = self.war_state['target_country_id']
        
        target_country = self._get_country_by_id(target_country_id)
        attacker_player = self._get_player_by_id(attacker_id)
        defender_player = self._get_player_by_id(defender_id)

        if self.war_state['attacker_score'] >= 3:
            # Saldıran kazanır: Ülke el değiştirir
            target_country['owner_id'] = attacker_id
            attacker_player['country_ids'].append(target_country_id)
            if target_country_id in defender_player['country_ids']:
                defender_player['country_ids'].remove(target_country_id)
            self._add_message(f"{attacker_player['name']} {target_country['name']} ülkesini fethetti!")
        else:
            # Savunan kazanır: Ülke sahibinde kalır
            self._add_message(f"{defender_player['name']} ülkesini başarıyla savundu!")

        # Savaş durumunu sıfırla
        self.war_state = {
            'attacker_id': None, 'defender_id': None, 'target_country_id': None,
            'attacker_score': 0, 'defender_score': 0, 'rps_choices': {}
        }
        # Sıra bir sonraki oyuncuya geçer
        self._advance_turn()
        self._check_game_over() # Oyunun bitip bitmediğini kontrol et

    def _check_game_over(self):
        # Bir oyuncunun tüm ülkeleri fethetmesi veya tek başına kalması durumu
        remaining_players = [p for p in self.players if p['country_ids']]
        # Seçim aşamasında tek oyuncu kalabilir, bu yüzden sadece oyun aşamasında kontrol et
        if len(remaining_players) <= 1 and self.game_phase != 'selection':
            self.game_phase = 'game_over'
            if remaining_players:
                self._add_message(f"Oyun bitti! Kazanan: {remaining_players[0]['name']}!")
            else:
                self._add_message("Oyun bitti! Berabere, kimse kazanamadı.")

    def get_game_state(self):
        # Frontend'e gönderilecek oyun durumunu döndürür
        state = {
            'players': self.players,
            'countries': self.countries,
            'game_phase': self.game_phase,
            'current_player_index': self.current_player_index,
            'selection_count_per_player': self.selection_count_per_player,
            'war_state': self.war_state,
            'messages': self.messages # Mesajları gönder ve sonra temizle
        }
        self.messages = [] # Mesajları gönderdikten sonra temizle
        return state

# --- Global Oyun Durumu ---
# Basitlik için, tek bir oyun örneği tutuyoruz.
# Birden fazla oyun odası için bu bir sözlük olmalıydı: games = {}
game = CountryConquestGame()

# --- SocketIO Olay İşleyicileri ---
@socketio.on('connect')
def handle_connect():
    # Her bağlantı için benzersiz bir session ID kullanılır
    player_id = request.sid
    # Eğer bu oyuncu zaten oyunda değilse ekle
    if game.add_player(player_id):
        join_room(game.game_id) # Oyuncuyu oyun odasına ekle
        emit('game_state_update', game.get_game_state(), room=game.game_id) # Tüm odaya güncel durumu gönder
        print(f"Oyuncu {player_id} bağlandı ve oyuna katıldı.")
    else:
        # Oyuncu zaten oyundaysa veya katılamadıysa sadece ona durumu gönder
        emit('game_state_update', game.get_game_state(), room=player_id)
        print(f"Oyuncu {player_id} zaten oyunda veya katılamadı.")

@socketio.on('disconnect')
def handle_disconnect():
    player_id = request.sid
    # Oyuncu bağlantısı kesildiğinde yapılacak işlemler (örn. oyuncuyu oyundan çıkarma)
    print(f"Oyuncu {player_id} bağlantısı kesildi.")

@socketio.on('select_country')
def handle_select_country(data):
    player_id = request.sid
    country_id = data.get('countryId')
    
    if game.select_country(player_id, country_id):
        emit('game_state_update', game.get_game_state(), room=game.game_id) # Başarılıysa tüm odaya güncelleme gönder
    else:
        # Hata durumunda sadece ilgili oyuncuya mesaj gönder
        emit('game_state_update', game.get_game_state(), room=player_id)

@socketio.on('initiate_war')
def handle_initiate_war(data):
    player_id = request.sid
    target_country_id = data.get('targetCountryId')

    if game.initiate_war(player_id, target_country_id):
        emit('game_state_update', game.get_game_state(), room=game.game_id) # Başarılıysa tüm odaya güncelleme gönder
    else:
        emit('game_state_update', game.get_game_state(), room=player_id) # Hata durumunda sadece ilgili oyuncuya mesaj gönder

@socketio.on('make_rps_move')
def handle_make_rps_move(data):
    player_id = request.sid
    choice = data.get('choice')

    if game.make_rps_move(player_id, choice):
        emit('game_state_update', game.get_game_state(), room=game.game_id) # Başarılıysa tüm odaya güncelleme gönder
    else:
        emit('game_state_update', game.get_game_state(), room=player_id) # Hata durumunda sadece ilgili oyuncuya mesaj gönder

# --- Flask Yönlendirmesi ---
@app.route('/')
def index():
    # Bu, oyunun HTML dosyasını sunacak
    # Flask'a templates klasörünün yolunu açıkça belirtiyoruz
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    app.template_folder = template_dir # template_folder'ı burada set ediyoruz
    return render_template('index.html')

if __name__ == '__main__':
    print(f"Oyun sunucusu başlatılıyor. Oyun ID: {game.game_id}")
    print("Tarayıcınızda http://127.0.0.1:5000 adresine gidin.")
    # Debug modunda çalıştırmak, kod değişikliklerinde otomatik yeniden yükleme sağlar
    socketio.run(app, debug=True, port=5000)

