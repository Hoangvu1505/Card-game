import random

class BlackjackGame:
    def __init__(self, room_id, host_sid=None):
        self.room_id = room_id
        self.host_sid = host_sid
        self.players = {} 
        self.deck = []
        self.state = "WAITING"
        # Nếu host_sid là None -> Chế độ chơi với máy (PvC)
        self.is_pvc = (host_sid is None)
        self.bot_dealer_hand = []

    def create_deck(self):
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [f"{r}{s}" for s in suits for r in ranks]
        random.shuffle(self.deck)

    def calculate_score(self, hand):
        score = 0
        aces = 0
        for card in hand:
            if card == "??": continue
            rank = card[:-1]
            if rank in ['J', 'Q', 'K']: score += 10
            elif rank == 'A': 
                aces += 1
                score += 11
            else: score += int(rank)
        while score > 21 and aces > 0:
            score -= 10
            aces -= 1
        return score

    def add_player(self, sid, name):
        if self.state != "WAITING":
            return False, "Ván đang chạy, vui lòng chờ."
        if len(self.players) >= 6:
            return False, "Phòng đã đầy (Max 6)."
        
        role = "player"
        # Trong chế độ Multi, người tạo phòng là Dealer
        if not self.is_pvc and sid == self.host_sid:
            role = "dealer"
        
        self.players[sid] = {
            "name": name, 
            "hand": [], 
            "score": 0, 
            "role": role, 
            "status": "waiting"
        }
        return True, "Success"

    def remove_player(self, sid):
        if sid in self.players:
            del self.players[sid]

    def start_round(self):
        if len(self.players) < 1: return False
        self.create_deck()
        self.state = "PLAYING"
        
        # Nếu chơi với máy, tạo bài cho Bot Dealer
        if self.is_pvc:
            self.bot_dealer_hand = [self.deck.pop(), self.deck.pop()]

        for sid in self.players:
            self.players[sid]["hand"] = [self.deck.pop(), self.deck.pop()]
            self.players[sid]["score"] = self.calculate_score(self.players[sid]["hand"])
            
            # --- LOGIC TRẠNG THÁI ---
            # PvC: Luôn là playing
            if self.is_pvc:
                self.players[sid]["status"] = "playing"
            else:
                # Multiplayer: Nhà cái chờ, Tay con chơi
                if self.players[sid]['role'] == 'dealer':
                    self.players[sid]["status"] = "waiting"
                else:
                    self.players[sid]["status"] = "playing"
                
        return True

    def hit(self, sid):
        if self.state != "PLAYING": return None
        
        # Nếu bộ bài hết (hiếm gặp), tạo bộ mới
        if not self.deck: self.create_deck()

        card = self.deck.pop()
        self.players[sid]["hand"].append(card)
        self.players[sid]["score"] = self.calculate_score(self.players[sid]["hand"])
        
        status = self.players[sid]["status"] # Giữ nguyên status cũ nếu chưa bust
        
        if self.players[sid]["score"] > 21:
            status = "bust"
        elif len(self.players[sid]["hand"]) == 5:
            # Ngũ linh: 5 lá mà <= 21 điểm
            if self.players[sid]["score"] <= 21:
                status = "ngu_linh"
            else:
                status = "bust"
        
        self.players[sid]["status"] = status
        return self.players[sid]

    def stand(self, sid):
        self.players[sid]["status"] = "stand"

    def check_all_players_done(self):
        # Kiểm tra tất cả Tay Con đã chơi xong chưa
        for sid, p in self.players.items():
            if p['role'] == 'player' and p['status'] == 'playing':
                return False
        return True

    def bot_play(self):
        # Logic cho máy tự rút (PvC)
        score = self.calculate_score(self.bot_dealer_hand)
        while score < 17:
            if not self.deck: self.create_deck()
            self.bot_dealer_hand.append(self.deck.pop())
            score = self.calculate_score(self.bot_dealer_hand)
        return self.bot_dealer_hand, score