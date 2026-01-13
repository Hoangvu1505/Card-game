import random

# --- HELPER CLASSES ---
class CardUtil:
    # Ranks: 3,4,5,6,7,8,9,10,J,Q,K,A,2
    # Scores: 0.......................51
    RANKS = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
    SUITS = {'♠': 0, '♣': 1, '♦': 2, '♥': 3}

    @staticmethod
    def get_score(card_str):
        if not card_str: return -1
        rank_str = card_str[:-1]
        suit_str = card_str[-1]
        rank_idx = CardUtil.RANKS.index(rank_str)
        return rank_idx * 4 + CardUtil.SUITS[suit_str]

    @staticmethod
    def get_rank_idx(score):
        return score // 4

    @staticmethod
    def sort_hand(hand):
        return sorted(hand, key=CardUtil.get_score)

    @staticmethod
    def get_combo_type(cards):
        """
        Trả về (loại_bộ, điểm_so_sánh)
        Types: 'single', 'pair', 'triple', 'quad', 'straight', '3_pine', '4_pine', None
        """
        if not cards: return None, 0
        n = len(cards)
        sorted_cards = CardUtil.sort_hand(cards)
        scores = [CardUtil.get_score(c) for c in sorted_cards]
        ranks = [CardUtil.get_rank_idx(s) for s in scores]
        max_score = scores[-1]

        # 1. Rác
        if n == 1: return 'single', max_score

        # 2. Đôi
        if n == 2 and ranks[0] == ranks[1]: return 'pair', max_score

        # 3. Sám cô (3 lá)
        if n == 3 and ranks[0] == ranks[1] == ranks[2]: return 'triple', max_score

        # 4. Tứ quý
        if n == 4 and ranks[0] == ranks[3]: return 'quad', max_score

        # 5. Sảnh (Dây) - Không chứa Heo (Rank 12)
        if n >= 3 and 12 not in ranks:
            is_straight = True
            for i in range(n - 1):
                if ranks[i+1] != ranks[i] + 1:
                    is_straight = False; break
            if is_straight: return 'straight', max_score

        # 6. Đôi thông (3 đôi hoặc 4 đôi)
        if n >= 6 and n % 2 == 0:
            pairs = []
            for i in range(0, n, 2):
                if ranks[i] != ranks[i+1]: return None, 0 
                pairs.append(ranks[i])
            
            if 12 in pairs: return None, 0 # Không chứa Heo
            
            is_pine = True
            for i in range(len(pairs) - 1):
                if pairs[i+1] != pairs[i] + 1:
                    is_pine = False; break
            
            if is_pine:
                if n == 6: return '3_pine', max_score
                if n == 8: return '4_pine', max_score

        return None, 0

    @staticmethod
    def can_beat(last_cards, new_cards):
        """Kiểm tra xem bộ bài mới (new_cards) có chặt được bộ bài cũ (last_cards) không"""
        last_type, last_score = CardUtil.get_combo_type(last_cards)
        new_type, new_score = CardUtil.get_combo_type(new_cards)
        
        if new_type is None: return False # Bài đánh ra không hợp lệ

        # --- LUẬT CHẶT HEO / CHẶT HÀNG ---
        last_rank_idx = CardUtil.get_rank_idx(last_score)

        # Heo (Rank 12)
        last_is_pig = (last_type == 'single' and last_rank_idx == 12)
        last_is_pig_pair = (last_type == 'pair' and last_rank_idx == 12)

        # Tứ quý chặt: Heo, Đôi Heo, 3 Đôi thông, Tứ quý nhỏ hơn
        if new_type == 'quad':
            if last_is_pig or last_is_pig_pair: return True
            if last_type == '3_pine': return True
            if last_type == 'quad' and new_score > last_score: return True

        # 3 Đôi thông chặt: Heo, 3 Đôi thông nhỏ hơn
        if new_type == '3_pine':
            if last_is_pig: return True
            if last_type == '3_pine' and new_score > last_score: return True

        # 4 Đôi thông chặt: Heo, Đôi Heo, 3 đôi thông, Tứ quý, 4 đôi thông nhỏ hơn
        if new_type == '4_pine':
            if last_is_pig or last_is_pig_pair: return True
            if last_type in ['3_pine', 'quad']: return True
            if last_type == '4_pine' and new_score > last_score: return True

        # --- LUẬT BÌNH THƯỜNG (Cùng loại, cùng độ dài, lớn hơn) ---
        if last_type == new_type:
            # Sảnh và Đôi thông phải cùng độ dài
            if last_type in ['straight', '3_pine', '4_pine'] and len(last_cards) != len(new_cards):
                return False
            
            # So điểm
            return new_score > last_score

        return False

# --- BOT CLASS ---
class TienLenBot:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.is_bot = True

    def choose_move(self, last_move_data):
        last_cards = last_move_data['cards']
        sorted_hand = CardUtil.sort_hand(self.hand)

        # 1. Nếu được đi tự do (Vòng mới)
        if not last_cards:
            return [sorted_hand[0]] # Đánh lá nhỏ nhất

        # 2. Tìm bài đỡ
        # Logic đơn giản: Bot chỉ đỡ Rác và Đôi.
        last_type, last_score = CardUtil.get_combo_type(last_cards)
        
        # Đỡ Rác
        if last_type == 'single':
            for card in sorted_hand:
                if CardUtil.can_beat(last_cards, [card]):
                    return [card]
                    
        # Đỡ Đôi
        elif last_type == 'pair':
            ranks = {}
            for c in sorted_hand:
                r = c[:-1]
                if r not in ranks: ranks[r] = []
                ranks[r].append(c)
            
            for r in ranks:
                if len(ranks[r]) >= 2:
                    pair = ranks[r][:2]
                    if CardUtil.can_beat(last_cards, pair):
                        return pair

        return [] # Bỏ lượt

# --- GAME CLASS ---
class TienLenGame:
    # --- FIX QUAN TRỌNG: Thêm tham số host_name ---
    def __init__(self, room_id, host_sid, is_bot_mode=False, host_name="Chủ Phòng"):
        self.room_id = room_id
        self.host_sid = host_sid
        self.seats = [None] * 4
        self.state = "WAITING"
        self.turn_index = 0
        self.last_move = {'cards': [], 'sid': None} 
        self.passed_sids = set()
        self.is_bot_mode = is_bot_mode
        self.first_turn_ever = True

        if is_bot_mode:
            # Gán tên người chơi đúng
            self.seats[0] = {'sid': host_sid, 'name': host_name, 'type': 'human', 'hand': []}
            names = ['Máy 1', 'Máy 2', 'Máy 3']
            for i in range(1, 4):
                self.seats[i] = {'sid': f'bot{i}', 'name': names[i-1], 'type': 'bot', 'obj': TienLenBot(names[i-1]), 'hand': []}

    def add_player(self, sid, name):
        if self.is_bot_mode: return False, "Chế độ chơi đơn"
        for i in range(4):
            if self.seats[i] is None:
                self.seats[i] = {'sid': sid, 'name': name, 'type': 'human', 'hand': []}
                return True, "OK"
        return False, "Phòng đầy"

    def remove_player(self, sid):
        for i in range(4):
            if self.seats[i] and self.seats[i]['sid'] == sid:
                self.seats[i] = None
                return True
        return False

    def start_game(self):
        active_seats = [i for i, s in enumerate(self.seats) if s]
        if len(active_seats) < 2: return False

        # Tạo và chia bài
        deck = [f"{r}{s}" for s in CardUtil.SUITS for r in CardUtil.RANKS]
        random.shuffle(deck)

        lowest_card = None
        lowest_card_holder = -1

        for i in active_seats:
            hand = []
            for _ in range(13):
                if deck: hand.append(deck.pop())
            self.seats[i]['hand'] = CardUtil.sort_hand(hand)
            
            if self.seats[i]['type'] == 'bot':
                self.seats[i]['obj'].hand = self.seats[i]['hand']

            # Tìm người đi đầu (lá nhỏ nhất)
            if self.first_turn_ever:
                curr_min = self.seats[i]['hand'][0]
                if lowest_card is None or CardUtil.get_score(curr_min) < CardUtil.get_score(lowest_card):
                    lowest_card = curr_min
                    lowest_card_holder = i

        self.state = "PLAYING"
        self.last_move = {'cards': [], 'sid': None}
        self.passed_sids = set()
        
        if self.first_turn_ever:
            self.turn_index = lowest_card_holder
            self.first_turn_card = lowest_card
        else:
            self.turn_index = active_seats[0]

        return True

    def play_cards(self, sid, cards):
        current_p = self.seats[self.turn_index]
        if not current_p or current_p['sid'] != sid: return False, "Chưa đến lượt"

        # 1. Check bài
        for c in cards:
            if c not in current_p['hand']: return False, "Không có bài này"

        # 2. Check luật ván đầu
        if self.first_turn_ever and self.last_move['sid'] is None:
            if self.first_turn_card not in cards:
                return False, f"Ván đầu phải đánh {self.first_turn_card}"

        # 3. Check chặt bài
        if self.last_move['cards']:
            # Gọi hàm can_beat mới (truyền cả list bài cũ)
            if not CardUtil.can_beat(self.last_move['cards'], cards):
                return False, "Bài không chặt được"
        else:
            if CardUtil.get_combo_type(cards)[0] is None:
                return False, "Bộ bài không hợp lệ"

        # Đánh bài
        for c in cards: current_p['hand'].remove(c)
        if current_p['type'] == 'bot': current_p['obj'].hand = current_p['hand']

        self.last_move = {'cards': cards, 'sid': sid}
        self.passed_sids = set()
        
        if self.first_turn_ever: self.first_turn_ever = False

        if len(current_p['hand']) == 0:
            self.state = "FINISHED"
            self.first_turn_ever = False 
            return True, "WIN"

        self.next_turn()
        return True, "OK"

    def pass_turn(self, sid):
        if self.seats[self.turn_index]['sid'] != sid: return False, "Lỗi lượt"
        if self.last_move['sid'] is None: return False, "Không được bỏ lượt đầu vòng"

        self.passed_sids.add(sid)
        self.next_turn()
        return True, "Passed"

    def next_turn(self):
        while True:
            self.turn_index = (self.turn_index + 1) % 4
            p = self.seats[self.turn_index]
            
            # Hết vòng -> Người cuối cùng đánh bài mới
            if p and p['sid'] == self.last_move['sid']:
                self.last_move = {'cards': [], 'sid': None}
                self.passed_sids = set()
                break 

            if p and p['sid'] not in self.passed_sids:
                break